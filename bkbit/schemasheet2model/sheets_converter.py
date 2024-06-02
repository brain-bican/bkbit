import os, sys
import csv, yaml
from io import StringIO
import click
from pathlib import Path
import requests

from linkml_runtime.linkml_model.meta import SchemaDefinition, SlotDefinition
from linkml_runtime.utils.schema_as_dict import schema_as_dict
from schemasheets import schemamaker as sm


def fix_tsv_files(tsv_files):
    """
    Check if the tsv files have changed
    :param tsv_files:
    :return:
    """
    tsv_file_fixed_list = []
    dir_fixed = Path(tsv_files[0]).parent / "fixed_sheets"
    dir_fixed.mkdir(exist_ok=True)
    for tsv_file in list(tsv_files):
        modified_rows = []
        with open(tsv_file, 'r', newline='') as file:
            # cleaned of any ^M characters
            content = file.read().replace('\r', '')
        # convert the cleaned content back to a file-like object
        data = StringIO(content)
        # read the file-like object as a csv file
        tsv_reader = csv.reader(data, delimiter='\t')
        for ii, row in enumerate(tsv_reader):
            if ii == 1:
                columns_to_change = []
                for jj, col in enumerate(row):
                    if "mapping" in col.lower():
                        columns_to_change.append(jj)
            if ii > 1:
                for jj in columns_to_change:
                    if jj > len(row)-1: breakpoint()
                    if row[jj]:
                        row[jj] = row[jj].replace(" ", "%20")
            modified_rows.append(row)

        tsv_file_fixed = dir_fixed / Path(tsv_file).name
        tsv_file_fixed_list.append(str(tsv_file_fixed))
        with open(tsv_file_fixed, 'w', newline='') as file:
            tsv_writer = csv.writer(file, delimiter='\t')
            tsv_writer.writerows(modified_rows)
    return tsv_file_fixed_list



def bican_fix(schema: SchemaDefinition) -> SchemaDefinition:
    """
    Apply BICAN specific fixes to the schema
    :param schema:
    :return:
    """
    # fixing values for categories
    for nm, cl in schema.classes.items():
        cl.slot_usage["category"] = SlotDefinition(name="category", pattern=r"^bican:[A-Z][A-Za-z]+$")
        # not needed anymore
        # if "name_pr" in cl.slots:
        #     cl.slots["name"] = cl.slots.pop("name_pr")
        # if "slot_usage" in cl and "name_pr" in cl["slot_usage"]:
        #     cl.slot_usage["name"] = cl.slot_usage.pop("name_pr")

    # removing names from the slots
    if "name" in schema.slots:
        del schema.slots["name"]
    # removing empty subsets that are from imported biolink schema
    biolink_subsets = []
    for nm, subs in schema.subsets.items():
        if not subs.description and not subs.from_schema:
            biolink_subsets.append(nm)
    for nm in biolink_subsets:
        del schema.subsets[nm]
    return schema


def adding_template(schema:SchemaDefinition, template_yaml) -> SchemaDefinition:
    with (template_yaml).open() as file:
        classes_base = yaml.safe_load(file)
        for key, val in classes_base["classes"].items():
            schema.classes[key] = val
        for key, val in classes_base["slots"].items():
            schema.slots[key] = val
    return schema


def download_google_sheet_as_tsv(sheet_id, save_path, sheet_gid):
    # Construct the URL to export the Google Sheet as TSV
    tsv_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=tsv&gid={sheet_gid}'
    response = requests.get(tsv_url)
    response.raise_for_status()  # Ensure the request was successful
    # Save the TSV content to a file
    with open(save_path, 'wb') as file:
        file.write(response.content)


def read_and_parse_gid_file(gid_filepath):
    gid_dict = {}
    with open(gid_filepath, 'r', encoding='utf-8') as file:
        for line in file:
            line_spl = line.split()
            if len(line_spl) == 1:
                gid_dict[line_spl[0]] = line_spl[0]
            elif len(line_spl) == 2:
                gid_dict[line_spl[0]] = line_spl[1]
            else:
                raise(f"wrong format of git file, each line should eitehr have gid or gid and tab name, got {line}")
    return gid_dict


def download_gsheets(gsheet_id, gsheet_download_dir, gid_filepath):
    gid_dict = read_and_parse_gid_file(gid_filepath)

    downloaded_files = []

    for gid, shnm in gid_dict.items():
        gsheet_save_path = gsheet_download_dir / f"{shnm}.tsv"
        download_google_sheet_as_tsv(gsheet_id, gsheet_save_path, gid)
        downloaded_files.append(gsheet_save_path)
    return downloaded_files



@click.command()
@click.option('-o', '--output',
              type=click.File(mode="w"),
              default=sys.stdout,
              help="output file")
@click.option('-t', '--template',
              type=click.Path(exists=True),
              default=None,
              help="template file")
@click.option("--gsheet-id",
              help="Google sheets ID. If this is specified then the arguments MUST be a file with list of gid")
@click.option("--gsheet-download-dir",
              type=click.Path(),
              default=None,
              help="Path used to download Google Sheets")
@click.option("--fix_tsv/--no-fix_tsv",
              default=False,
              show_default=True,
              help="Auto-repair tsv files")
@click.option("--repair/--no-repair",
              default=True,
              show_default=True,
              help="Auto-repair schema")
@click.option("--fix_bican_model/--no-fix_bican_model",
              default=False,
              show_default=True,
              help="Auto-repair specifically for bican yaml model")
@click.argument('tsv_files', nargs=-1)
def generateSchema(tsv_files, output, fix_tsv, repair, fix_bican_model, template, gsheet_id, gsheet_download_dir):
    schema_maker = sm.SchemaMaker()

    if gsheet_id:
        if not gsheet_download_dir:
            gsheet_download_dir = Path(".") / f"google_sheet_{gsheet_id}"
        if len(tsv_files) != 1 or not Path(tsv_files[0]).exists:
            raise Exception(f"if gsheet-if is used the argument must me a file with gsheet_id, "
                            f"but file {tsv_files} doesn't exist")

        gsheet_download_dir.mkdir(exist_ok=True)
        tsv_files = download_gsheets(gsheet_id, gsheet_download_dir, tsv_files[0])

    # checking template and default name of template
    if template:
        template = Path(template)
    elif (Path(tsv_files[0]).parent / "classes_base.yaml").exists():
        template = Path(tsv_files[0]).parent / "classes_base.yaml"

    if fix_tsv:
        tsv_files = fix_tsv_files(list(tsv_files))

    schema = schema_maker.create_schema(list(tsv_files))
    if repair:
        schema = schema_maker.repair_schema(schema)

    if fix_bican_model:
        schema = bican_fix(schema)

    if template:
        schema = adding_template(schema, template_yaml=template)

    schema_dict = schema_as_dict(schema)
    output.write(yaml.dump(schema_dict, sort_keys=False))
    output.close()


if __name__ == '__main__':
    generateSchema()
