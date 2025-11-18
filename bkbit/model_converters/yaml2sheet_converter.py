import csv, yaml
import click
from pathlib import Path

from linkml_runtime.utils.schemaview import SchemaView

SIMPLE_TYPES_NOSTR = ["integer", "float", "boolean", "date", "datetime"]

CLASS_HEADERS = [
    # header, linkml_header, linkml_header_minor
    ("Class Name", "> class", ">"),
    ("Inheritance: is_a", "is_a", ""),
    ("Inheritance: mixin", "mixins", 'internal_separator: "|"'),
    ("Subsets", "in_subset", 'internal_separator: "|"'),
    ("Description", "description", ""),
    ("NIMP Terminology NHash", "exact_mappings: {curie_prefix: NIMP}", "")
]

SLOTS_HEADERS = [
    # header, linkml_header, linkml_header_minor
    ("Proposed BICAN Field", "> alias", ">"),
    ("LinkML Slot or Attribute Name", "attribute", ""),
    ("BICAN UUID", "slot_uri: {curie_prefix: bican}", ""),
    ("SubGroup/LinkML Class Name", "class", ""),
    ("Definition", "description", ""),
    ("Required (True/False)", "is_required", ""),
    ("Multivalued (True/False)", "multivalued", ""),
    ("Data Type/Value Set", "range", ""),
    ("Data Examples", "ignore", ""),
    ("Min Value", "ignore", ""),
    ("Max Value", "ignore", ""),
    ("Unit", "ignore", ""),
    ("Statistical Type", "ignore", ""),
    ("Subsets", "in_subset", ""),
    ("Notes", "ignore", ""),
    ("NIMP Category", "ignore", ""),
    ("NIMP Terminology NHash", "exact_mappings: {curie_prefix: NIMP}", ""),
    ("Local Variable Name (e.g. NIMP)", "local_names", "inner_key: local_name_value"),
    ("Local Variable Source (e.g. NIMP)", "local_names", "inner_key: local_name_source")
]

ENUM_HEADERS = [
    # header, linkml_header, linkml_header_minor
    ("Value Set Name", "> enum", ">"),
    ("Permissible Value", "permissible_value", ""),
    ("Description", "description", ""),
    ("NIMP Terminology NHash", "meaning: {curie_prefix: NIMP}", "")
]

PREFIXES_HEADERS = [
    # header, linkml_header
    ("Schema Name", "> schema"),
    ("Title", "title"),
    ("Description", "description"),
    ("ID", "id"),
    ("Default Prefix", "default_prefix"),
    ("Imports", "imports"),
    ("Prefix", "prefix"),
    ("Prefix URI", "prefix_reference"),
]


def create_classes_slots_cvs(classes: dict, output_dir: Path):
    # creating headers (including linkml header lines)
    classes_cvs = [[], [], []]
    for header, linkml_header, linkml_header_minor in CLASS_HEADERS:
        classes_cvs[0].append(header)
        classes_cvs[1].append(linkml_header)
        classes_cvs[2].append(linkml_header_minor)

    slots_cvs = [[], [], []]
    for header, linkml_header, linkml_header_minor in SLOTS_HEADERS:
        slots_cvs[0].append(header)
        slots_cvs[1].append(linkml_header)
        slots_cvs[2].append(linkml_header_minor)

    sl_header = \
        ["Proposed BICAN Field", "LinkML Slot or Attribute Name", "BICAN UUID",	"SubGroup/LinkML Class Name", "Definition", "Required (True/False)", "Multivalued (True/False)", "Data Type/Value Set",	"Data Examples", "Min Value", "Max Value", "Unit", "Statistical Type", "Subsets", "Notes", "NIMP Category",	"NIMP Terminology NHash",               "Local Variable Name (e.g. NIMP)", "Local Variable Source (e.g. NIMP)"]
    sl_linkml_header = \
        ["> alias",              "attribute", "slot_uri: {curie_prefix: bican}", "class",                    "description", "is_required",          "multivalued",              "range",               "ignore",        "ignore",    "ignore",    "ignore", "ignore",         "in_subset", "ignore", "ignore",     "exact_mappings: {curie_prefix: NIMP}", "local_names",                     "local_names"]
    sl_linkml_header_minor = [">",        "",          "",                                "",                         "",            "",                     "",                         "",                    "",              "",          "",          "",       "", 'internal_separator: "|"',	"",       "",           "",                                     "inner_key: local_name_value",     "inner_key: local_name_source"]
    slots_cvs = [sl_header, sl_linkml_header, sl_linkml_header_minor]
    for class_name, class_d in classes.items():
        if class_name in "NamedThing":
            continue
        cl_l = [class_name, class_d.is_a, "|".join(class_d.mixins), "|".join(class_d.in_subset), class_d.description, ""]
        classes_cvs.append(cl_l)
        class_attr_dict = class_d.attributes
        class_attr_dict.update(class_d.slot_usage)
        for slot_name, slot_obj in class_attr_dict.items():
            if slot_obj.range:
                range = slot_obj.range
            elif slot_obj.any_of:
                # removing an additional type
                range = "|".join(_removing_str_type(slot_obj.any_of))
            else:
                range = "string" # default range
            sl_l = ["", slot_name, slot_obj.slot_uri, class_name, slot_obj.description, slot_obj.required, slot_obj.multivalued, range, "", "", "", "", "", "", "", "", "", "", ""]
            slots_cvs.append(sl_l)
    _write_cvs(Path(output_dir / "classes.csv"), classes_cvs)
    _write_cvs(Path(output_dir / "slots.csv"), slots_cvs)


def create_enums_cvs(enums: dict, output_dir: Path):
    enums_cvs = [[], [], []]
    for header, linkml_header, linkml_header_minor in ENUM_HEADERS:
        enums_cvs[0].append(header)
        enums_cvs[1].append(linkml_header)
        enums_cvs[2].append(linkml_header_minor)
    if enums:
        for enum_name, enum in enums.items():
            for value_nm, value_obj in enum.permissible_values.items():
                enums_cvs.append([enum_name, value_nm, value_obj.title, value_obj.meaning])
    _write_cvs(Path(output_dir / "enums.csv"), enums_cvs)

def create_prefix_headers_csv(schema: SchemaView, output_dir: Path):
    prefixes_cvs = [[], []]
    for header, linkml_header in PREFIXES_HEADERS:
        prefixes_cvs[0].append(header)
        prefixes_cvs[1].append(linkml_header)

    prefixes_cvs.append([schema.name, schema.title, schema.description, schema.id, schema.default_prefix, "", "", ""])
    for imp in schema.imports:
        if imp != "linkml:types": # this is imported by default
            prefixes_cvs.append(["", "", "", "", "", imp, "", ""])
    for prefix in schema.prefixes.values():
        prefixes_cvs.append(["", "", "", "", "", "", prefix.prefix_prefix, prefix.prefix_reference])
    _write_cvs(Path(output_dir / "prefixes.csv"), prefixes_cvs)

def _removing_str_type(any_of_list: list):
    """If the range list contains only more complex types, it removes string from the list.
    String is used in these cases as an additional type to be able to refer by id,
    no need to include it in the google sheet
    """
    range_list = [el.range for el in any_of_list]
    simple_types = ["integer", "float", "boolean", "date", "datetime"]
    if "string" in range_list and not(any([el in simple_types for el in range_list])):
        range_list.remove("string")
    return range_list


def _write_cvs(filename, data):
    with open(filename, 'w', newline='') as file:
        csv_writer = csv.writer(file)
        csv_writer.writerows(data)

@click.command()
@click.option('-o', '--output_dir',
              type=click.Path(),
              default="output_dir_cvs",
              help="Path to the output directory, where csv files will be stored.")
@click.argument('yaml_model', type=click.Path(exists=True))
def yaml2cvs(yaml_model, output_dir):
    """
    This converter create csv files from the yaml model.
    The cvs files can be used to create Google Spreadsheet (automation TODO)
    Takes a path to yaml model as an input.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    schema = SchemaView(yaml_model)
    create_prefix_headers_csv(schema.schema, output_dir)
    create_enums_cvs(schema.all_enums(), output_dir)
    create_classes_slots_cvs(schema.all_classes(), output_dir)

if __name__ == "__main__":
    yaml2cvs()