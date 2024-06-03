import os, sys, shutil
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


def read_and_parse_gsheet_yaml(gsheet_yaml):
    with open(gsheet_yaml, 'r') as file:
        data = yaml.safe_load(file)

    gsheet_id = data['gsheet_id']
    sheets = data['sheets']
    return gsheet_id, sheets


def download_gsheets(gsheet_id, sheets, gsheet_download_dir):
    downloaded_files = []
    for sht in sheets:
        if "gid" not in sht:
            raise Exception(f"Each sheet has to have gid,but not found in {sht}")
        shnm = sht.get("name", sht["gid"])
        gsheet_save_path = gsheet_download_dir / f"{shnm}.tsv"
        download_google_sheet_as_tsv(gsheet_id, gsheet_save_path, sht["gid"])
        downloaded_files.append(gsheet_save_path)
    return downloaded_files


@click.command()
@click.option('-o', '--output',
              type=click.File(mode="w"),
              default=sys.stdout,
              help="Path for the yaml output file.")
@click.option('-t', '--template',
              type=click.Path(exists=True),
              default=None,
              help="Optional template yaml file with standard classes that will be added to the model.")
@click.option("--gsheet/--no-gsheet",
              default=False,
              show_default=True,
              help="Using Google Sheet as a source. "
                   "If True, the arguments MUST be a yaml file with gsheet_id and gid of all the sheets")
@click.option("--gsheet-download-dir",
              type=click.Path(),
              default=None,
              help="Path used to download Google Sheets. If not specified a default directory will be created.")
@click.option("--fix_tsv/--no-fix_tsv",
              default=True,
              show_default=True,
              help="Fixing known issues with tsv files from Google Sheets.")
@click.option("--fix_tsv_save/--no-fix_tsv_save",
              default=False,
              show_default=True,
              help="Keeping the fixed files, relevant only if fix_tsv=True")
@click.option("--repair/--no-repair",
              default=True,
              show_default=True,
              help="Standard Linkml auto-repair schema")
@click.option("--fix_bican_model/--no-fix_bican_model",
              default=True,
              show_default=True,
              help="Automated repair specifically for the BICAN YAML model")
@click.argument('spreadsheets', nargs=-1)
def schema2model(spreadsheets, output, fix_tsv, fix_tsv_save, repair, fix_bican_model, template,
                 gsheet, gsheet_download_dir):
    """
    This converter allows to create a yaml linkml model from set of spreadsheets.
    It can either use tsv files or Google Sheet as an input.

    The default behavior is to run the converter starting with TSV files,
     specifying their paths as arguments, for example, model_spreadsheets/*tsv.

    If `--gsheet` option is used, the converter starts from downloading spreadsheets
     from Google Sheets.
     The argument must be a YAML file that has `gsheet_id` and a list of `sheets`
     with `gid` (a unique identifier for each individual sheet) and `name` (optionally)
     that will be used as a name of the downloaded TSV file (if not available `gid` wil be used).
    """

    schema_maker = sm.SchemaMaker()

    if gsheet:
        if len(spreadsheets) != 1 or not Path(spreadsheets[0]).exists:
            raise Exception(f"if gsheet is used the argument must me a yaml file with gsheet_id, "
                            f"but file {spreadsheets} doesn't exist")
        gsheet_id, sheets = read_and_parse_gsheet_yaml(spreadsheets[0])
        if gsheet_download_dir:
            gsheet_download_dir = Path(gsheet_download_dir)
        else:
            gsheet_download_dir = Path(".") / f"google_sheet_{gsheet_id}"

        gsheet_download_dir.mkdir(exist_ok=True)
        spreadsheets = download_gsheets(gsheet_id, sheets, gsheet_download_dir)

    # checking template and default name of template
    if template:
        template = Path(template)
    elif (Path(spreadsheets[0]).parent / "classes_base.yaml").exists():
        template = Path(spreadsheets[0]).parent / "classes_base.yaml"

    if fix_tsv:
        spreadsheets = fix_tsv_files(list(spreadsheets))

    schema = schema_maker.create_schema(list(spreadsheets))
    if repair:
        schema = schema_maker.repair_schema(schema)

    if fix_bican_model:
        schema = bican_fix(schema)

    if template:
        schema = adding_template(schema, template_yaml=template)

    schema_dict = schema_as_dict(schema)
    output.write(yaml.dump(schema_dict, sort_keys=False))
    output.close()

    # removing the fixed files:
    if fix_tsv and not fix_tsv_save:
        shutil.rmtree(Path(spreadsheets[0]).parent)


if __name__ == '__main__':
    schema2model()
