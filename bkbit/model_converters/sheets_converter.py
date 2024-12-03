import os, sys, shutil
import csv, yaml
from io import StringIO
import click
from pathlib import Path
import requests

from linkml_runtime.linkml_model.meta import SchemaDefinition, SlotDefinition
from linkml_runtime.utils.schema_as_dict import schema_as_dict
from linkml_runtime.utils.schemaview import SchemaView
from schemasheets import schemamaker as sm
import pandas as pd


SIMPLE_TYPES_NOSTR = ["integer", "float", "boolean", "date", "datetime"]


def fix_tsv_files(tsv_files, inlined=False, ref_by_ind=True):
    """
    Fixing all the tsv files, modyfying the range column, and adding any_of, exactly_one_of, and inlined columns.
    :param tsv_files: list of tsv files
    :param inlined: if True, the inlined column will be added
    "param ref_by_ind: if True (and if inlined is True) the range will be modified (adding string) to be able to reference by index
    :return: list of fixed tsv files
    """

    tsv_file_fixed_list = []
    dir_fixed = Path(tsv_files[0]).parent / "fixed_sheets"
    dir_fixed.mkdir(exist_ok=True)
    for tsv_file in list(tsv_files):
        # TODO: check if the file indeed has 3 lines of headers
        tsv_file_fixed = dir_fixed / Path(tsv_file).name
        tsv_file_fixed_list.append(str(tsv_file_fixed))

        with open(tsv_file, 'r', newline='') as file:
            # cleaned of any ^M characters
            content = file.read().replace('\r', '')
        # convert the cleaned content back to a file-like object
        data = StringIO(content)

        # read the file-like object to a pandas dataframe
        df = pd.read_csv(data, header=[0, 1, 2], delimiter='\t')

        columns_to_change_new = []
        for ind in df.columns:
            if "mapping" in ind[1].lower():
                columns_to_change_new.append(ind)
        for col in columns_to_change_new:
            df[col] = df[col].str.replace(" ", "%20")

        # finding the range column, and other columns that are relevant for the following changes
        range_ind, range_col = None, None
        multival_col, exactlyone_col, valset_col = None, None, None
        for ind, col in enumerate(df.columns):
            if "range" in col[1].lower().strip():
                range_ind = ind
                range_col = col
            elif "multivalued" in col[0].lower().strip():
                multival_col = col
            elif "exactlyoneof" in col[0].lower().strip():
                exactlyone_col = col
            elif "permissible" in col[0].lower().strip():
                valset_col = col

        if range_ind is not None:
            any_of_col = (f"{range_col[0]}: any_of", "any_of", "inner_key: range")
            exactly_one_of_col = (f"{range_col[0]}: exactly_one_of", "exactly_one_of", "inner_key: range")
            if inlined:
                inline_col = ("inlined", "inlined", "")
            else: # ignoring if inlined is set to False
                inline_col = ("inlined", "ignore", "")
            df.insert(range_ind + 1, any_of_col, None)
            df.insert(range_ind + 2, exactly_one_of_col, None)
            df.insert(range_ind + 3, inline_col, None)

            def fix_range(row):
                """ Fixing the range column, moving some ranges to any_of or exactly_one_of columns
                It also depends on the values of ref_by_ind and inlined.
                """
                if pd.isna(row[range_col]):
                    return row
                # do not add string to range if range already has string or all the elements are simple types
                elif "string" in row[range_col] or all([el in SIMPLE_TYPES_NOSTR for el in row[range_col].split("|")]):
                    pass
                # checking if the range is not value set (TODO: in the future might need modification)
                elif valset_col is not None and row[valset_col]:
                    pass
                elif inlined:  # setting inlined to True for range that have complex types
                    row[inline_col] = True
                    if ref_by_ind: # adding string to the range to be able to reference by index
                        row[range_col] = row[range_col] + "|string"

                # checking if range has multiple values, and if it should be treated as any_of or exactly_one_of
                if "|" in row[range_col]:
                    if (row[multival_col] is True) and (exactlyone_col is not None) and (row[exactlyone_col] is True):
                        row[exactly_one_of_col] = row[range_col]
                    else:
                        row[any_of_col] = row[range_col]
                    row[range_col] = None
                return row

            df = df.apply(fix_range, axis=1)

        df.to_csv(tsv_file_fixed, sep='\t', index=False)

        # fixing the headers that are saved by pandas
        with open(tsv_file_fixed, 'r') as file:
            lines = file.readlines()
        lines[2] = "\t".join(["" if el.startswith("Unnamed") else el for el in lines[2].split("\t")]) + "\n"
        lines[1] = "\t".join(["" if el.startswith("Unnamed") else el for el in lines[1].split("\t")]) + "\n"
        with open(tsv_file_fixed, 'w') as file:
            file.writelines(lines)

    return tsv_file_fixed_list



def bican_fix(schema: SchemaDefinition) -> SchemaDefinition:
    """
    Apply BICAN specific fixes to the schema
    :param schema:
    :return: SchemaDefinition
    """

    # removing names from the slots
    if "name" in schema.slots:
        del schema.slots["name"]

    # removing slots that are from the imported schemas
    slots_from_imports = []
    for el in schema.imports:
        if Path(f"{el}.yaml").exists():
            sv = SchemaView(f'{el}.yaml')
            slots_from_imports.extend(sv.schema.slots.keys())
    slots_to_remove = list(set(schema.slots) & set(slots_from_imports))

    for nm in slots_to_remove:
        del schema.slots[nm]

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
@click.option("--inlined/--no-inlined",
              default=True,
              show_default=True,
              help="Adding inlined=True to all slots that have complex type as a range")
@click.option("--ref_by_ind/--no-ref_by_ind",
              default=True,
              show_default=True,
              help="Adding string to the range to be able to reference by index (relevant only if inlined=True)")
@click.option("--fix_bican_model/--no-fix_bican_model",
              default=True,
              show_default=True,
              help="Automated repair specifically for the BICAN YAML model")
@click.argument('spreadsheets', nargs=-1)
def schema2model(spreadsheets, output, fix_tsv, fix_tsv_save, repair, fix_bican_model, template,
                 gsheet, gsheet_download_dir, inlined, ref_by_ind):
    """
    This converter allows creating a yaml linkml model from a set of spreadsheets.
    It can either use tsv files or Google Sheet as an input.

    The default behavior is to run the converter starting with TSV files,
     specifying their paths as arguments, for example, model_spreadsheets/*tsv.

    If `--gsheet` option is used, the converter starts from downloading spreadsheets
     from Google Sheets.
     The argument must be a YAML file that has `gsheet_id` and a list of `sheets`
     with `gid` (a unique identifier for each individual sheet) and `name` (optionally)
     that will be used as a name of the downloaded TSV file (if not available `gid` will be used).
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
        spreadsheets = fix_tsv_files(list(spreadsheets), inlined=inlined, ref_by_ind=ref_by_ind)
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
