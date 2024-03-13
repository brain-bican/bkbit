import os, sys
import yaml
import click
from pathlib import Path

from linkml_runtime.linkml_model.meta import SchemaDefinition
from linkml_runtime.utils.schema_as_dict import schema_as_dict
from schemasheets import schemamaker as sm


def changed_tsv_files(tsv_files):
    """
    Check if the tsv files have changed
    :param tsv_files:
    :return:
    """

    for tsv_file in list(tsv_files):
        modified_rows = []
        with open(tsv_file, 'r', newline='') as file:
            tsv_reader = csv.reader(file, delimiter='\t')
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

        with open(tsv_file, 'w', newline='') as file:
            tsv_writer = csv.writer(file, delimiter='\t')
            tsv_writer.writerows(modified_rows)



def bican_fix(schema: SchemaDefinition, template_yaml) -> SchemaDefinition:
    """
    Apply BICAN specific fixes to the schema
    :param schema:
    :return:
    """

    with (template_yaml).open() as file:
        classes_base = yaml.safe_load(file)
        for key, val in classes_base["classes"].items():
            schema.classes[key] = val
        for key, val in classes_base["slots"].items():
            schema.slots[key] = val

    return schema

def fixing_name_keys_yaml(output_file):
    with Path(output_file).open() as file:
        model = yaml.safe_load(file)

    for key, cl in model["classes"].items():
        #breakpoint()
        if "name_pr" in cl["slots"]:
            cl["slots"] = ["name" if el == "name_pr" else el for el in cl["slots"]]
        if "slot_usage" in cl and "name_pr" in cl["slot_usage"]:
            cl["slot_usage"]["name"] = cl["slot_usage"].pop("name_pr")

    if "name_pr" in model["slots"]:
        model["slots"]["name"] = model["slots"].pop("name_pr")

    with Path(output_file).open("w") as file:
        yaml.safe_dump(model, file, sort_keys=False)


@click.command()
@click.option('-o', '--output',
              type=click.File(mode="w"),
              default=sys.stdout,
              help="output file")
@click.option("--fix_tsv/--no-fix_tsv",
              default=False,
              show_default=True,
              help="Auto-repair tsv files")
@click.option("--repair/--no-repair",
              default=True,
              show_default=True,
              help="Auto-repair schema")
@click.option("--fix_bican_model/--no-fix_bican_model",
              default=True,
              show_default=True,
              help="Auto-repair specifically for bican yaml model")
@click.argument('tsv_files', nargs=-1)
def generateSchema(tsv_files, output, fix_tsv, repair, fix_bican_model):
    schema_maker = sm.SchemaMaker()

    if fix_tsv:
        changed_tsv_files(list(tsv_files))

    schema = schema_maker.create_schema(list(tsv_files))
    if repair:
        schema = schema_maker.repair_schema(schema)

    if fix_bican_model:
        schema = bican_fix(schema, template_yaml=Path(tsv_files[0]).parent / "classes_base.yaml")

    schema_dict = schema_as_dict(schema)
    output.write(yaml.dump(schema_dict, sort_keys=False))
    output.close()

    if fix_bican_model:
         fixing_name_keys_yaml(Path(output.name))



if __name__ == '__main__':
    generateSchema()
