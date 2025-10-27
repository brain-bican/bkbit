import itertools
import click
import pkg_resources
from bkbit.models import bke_taxonomy
import json
import hashlib
import pandas as pd
import json
from linkml_runtime.dumpers import json_dumper


class BKETaxonomy:
    def __init__(self):
        self.abbreviations = {}
        self.group_ctt = {}
        self.subclass_ctt = {}
        self.class_ctt = {}
        self.neighborhood_ctt = {}
        self.display_colors = {}
        self.cell_type_sets = {}
        self.spatial_proportions = {}

    def parse_taxonomy_level(self, row, level, parent_id=None):
        """
        Parse taxonomy data from a pandas Series and generate CellTypeTaxon and DisplayColor objects.

        Args:
            row (pd.Series): Series containing taxonomy data
            level (str): The taxonomy level ("Group", "Subclass", "Class", "Neighborhood")
            parent_id (str, optional): Parent taxon ID

        Returns:
            str: The ID of the created CellTypeTaxon
        """
        # Define the storage dictionaries for each level
        storage_map = {
            "Group": self.group_ctt,
            "Subclass": self.subclass_ctt,
            "Class": self.class_ctt,
            "Neighborhood": self.neighborhood_ctt,
        }

        # Create CellTypeTaxon
        ctt_attributes = self._helper_parse_cell_type_taxon_attributes(row, level)
        if parent_id:
            ctt_attributes["has_parent"] = parent_id

        cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, ctt_attributes)
        storage_map[level].setdefault(cell_type_taxon.id, cell_type_taxon)

        # Create DisplayColor
        color_column = "color_hex_" + level.lower()
        if color_column in row and pd.notna(row[color_column]):
            display_color = generate_object(
                bke_taxonomy.DisplayColor,
                {
                    "color_hex_triplet": row[color_column],
                    "is_color_for_taxon": cell_type_taxon.id,
                },
            )
            self.display_colors.setdefault(display_color.id, display_color)

        return cell_type_taxon.id

    def parse_abbreviations(self, df):
        """
        Parses a DataFrame to generate a dictionary of abbreviation objects.

        Args:
            df (pandas.DataFrame): A DataFrame containing abbreviation data.
                Expected columns:
                    - primary_identifier: Primary identifier for the abbreviation.
                    - secondary_identifier: Secondary identifier for the abbreviation.
                    - token: The abbreviation term.
                    - abbreviation_meaning: The meaning of the abbreviation.
                    - type: The entity type associated with the abbreviation.
        """
        for row in df.itertuples():
            # define Abbreviation instance for each row
            abbreviation_attributes = {
                "term": row.token,
                "meaning": row.meaning,
                "entity_type": row.type,
            }
            try:
                abbreviation_attributes["entity_type"] = (
                    bke_taxonomy.AbbreviationEntityType(row.type)
                )
            except Exception as e:
                print(f"Error processing row {row}: {e} in Abbreviation file.")
                continue
            abbrev_ids = []
            # check if value is Nan
            if row.primary_identifier:
                abbrev_ids.append(row.primary_identifier)
            if row.secondary_identifier:
                abbrev_ids.append(row.secondary_identifier)
            entity_type = abbreviation_attributes.get("entity_type")
            if entity_type == bke_taxonomy.AbbreviationEntityType.gene:
                abbreviation_attributes["denotes_gene_annotation"] = abbrev_ids
            elif entity_type == bke_taxonomy.AbbreviationEntityType.cell_type:
                abbreviation_attributes["denotes_cell_type"] = abbrev_ids
            elif entity_type == bke_taxonomy.AbbreviationEntityType.anatomical:
                abbreviation_attributes["denotes_parcellation_term"] = abbrev_ids
            else:
                print(
                    f"Warning: Unknown Abbreviation entity type: '{entity_type}' when parsing abbreviation file."
                )
            abbreviation_object = generate_object(
                bke_taxonomy.Abbreviation, abbreviation_attributes
            )
            self.abbreviations[abbreviation_object.term] = abbreviation_object

    def parse_cell_type_set(self, df):
        """
        Parses a DataFrame to create and populate CellTypeSet objects based on the provided data.

        Args:
            df (pandas.DataFrame): A DataFrame containing cell type set information.
                Expected columns include 'name', 'label', 'description', and 'order'.
        """
        for row in df.itertuples():
            # define CellTypeSet
            cell_type_set_attributes = {
                "name": row.name,
                "accession_id": row.label,
                "description": row.description,
                "order": row.order,
            }
            if row.name == "Neighborhood":
                cell_type_set_attributes["contains_taxon"] = list(
                    self.neighborhood_ctt.keys()
                )
            elif row.name == "Class":
                cell_type_set_attributes["contains_taxon"] = list(
                    self.class_ctt.keys()
                )  # Updated to use keys()
            elif row.name == "Subclass":
                cell_type_set_attributes["contains_taxon"] = list(
                    self.subclass_ctt.keys()
                )  # Updated to use keys()
            elif row.name == "Group":
                cell_type_set_attributes["contains_taxon"] = list(
                    self.group_ctt.keys()
                )  # Updated to use keys()
            else:
                print(
                    f"Warning: Unknown CellTypeSet name: '{row.name}' when parsing description file."
                )
            # get self.row.name_ctt
            cell_type_set = generate_object(
                bke_taxonomy.CellTypeSet, cell_type_set_attributes
            )
            self.cell_type_sets.setdefault(cell_type_set.id, cell_type_set)

    def _helper_parse_cell_type_taxon_attributes(self, row, attribute_suffix):
        """
        Helper function to parse cell type taxon attributes from a row.

        Args:
            row (pd.Series): A row from the DataFrame.
            attribute_suffix (str): The suffix to append to the attribute names.

        Returns:
            dict: A dictionary of attributes for CellTypeTaxon.
        """
        cell_type_taxon_attribute_names = {
            "accession": "accession_id",
            "display_order": "order",
            "tokens": "has_abbreviation",
            "CL_ID": "xref",
        }
        attributes = {"name": row.get(attribute_suffix)}

        for key, model_value in cell_type_taxon_attribute_names.items():
            data_key = key + "_" + attribute_suffix.lower()
            if data_key in row:
                if key == "tokens":
                    tokens = row.get(data_key).split("|")
                    attributes[model_value] = [
                        self.abbreviations[token].id
                        for token in tokens
                        if token in self.abbreviations
                    ]
                elif key == "CL_ID":
                    attributes[model_value] = (
                        [row.get(data_key)] if pd.notna(row.get(data_key)) else None
                    )
                else:
                    attributes[model_value] = row.get(data_key)
        if attribute_suffix == 'Group':
            spatial_region_columns = ['spatial_regional_proportions', 'spatial_proportions_marmoset', 'spatial_proportions_macaque', 'spatial_proportions_human']
            for sr in spatial_region_columns:
                if sr in row and pd.notna(row[sr]):
                    print(f"Parsing spatial proportions for column: {sr}")
                    proportions = {}
                    for item in row[sr].split(","):
                        region, value = item.split(":")
                        region = region.strip()
                        value = value.strip()
                        print(f"Region: {region}, Value: {value}")
                        if bke_taxonomy.Region[region] in bke_taxonomy.Region:
                            proportions[bke_taxonomy.Region[region].value] = float(value)
                        else:
                            print(f"Warning: Unknown region '{region}' in spatial proportions.")
                            print(row[sr])
                    print(row)
                    print(proportions)
                    spatial_region_object = generate_object(bke_taxonomy.SpatialProportions, proportions)
                    self.spatial_proportions[spatial_region_object.id] = spatial_region_object
                    attributes[sr] = spatial_region_object.id
            curated_markers_columns = ['curated_markers_to_primates', 'curated_markers_to_mouse']
            for cm in curated_markers_columns:
                if cm in row and pd.notna(row[cm]):
                    markers = [marker.strip() for marker in row[cm].split(",")]
                    #! IN THE FUTURE, QUERY KG FOR GENE'S BKBIT ID
                    attributes[cm] = markers
        return attributes


def generate_object(cls, attributes: dict):
    """
    Generate an object of the specified class with the given attributes.

    Args:
        cls (type): The class to instantiate.
        attributes (dict): A dictionary containing the attributes for the object.

    Returns:
        object: An instance of the specified class with the provided attributes.
    """
    # Generate a unique object ID and add it to the attributes
    object_id = generate_object_id(attributes)
    attributes["id"] = object_id
    return cls(**attributes)


def generate_object_id(attributes: dict):
    """
    Generate a unique object ID based on the provided attributes.
    Args:
        attributes (dict): A dictionary containing the attributes of the object.
    Returns:
        str: The generated object ID.
    """
    # Sort the attributes by keys and convert to a consistent JSON string
    # print(attributes)
    BKBIT_OBJECT_ID_PREFIX = "urn:bkbit:"
    normalized_attributes = json.dumps(attributes, sort_keys=True)
    object_id = hashlib.sha256(normalized_attributes.encode()).hexdigest()
    return BKBIT_OBJECT_ID_PREFIX + object_id


@click.command()
## ARGUMENTS ##
@click.argument("annotation_file", type=click.Path(exists=True))
@click.argument("abbreviation_file", type=click.Path(exists=True))
@click.argument("description_file", type=click.Path(exists=True))

## OPTIONS ##
# Option: Output file path
@click.option(
    "--output_file",
    "-o",
    required=False,
    type=click.Path(),
    default="HMBA_BG_taxonomy.jsonld",
    show_default=True,
    help="The output file path.",
)
# Option: Output format: jsonld or turtle
@click.option(
    "--output_format",
    "-f",
    required=False,
    type=click.Choice(["jsonld", "turtle"]),
    default="jsonld",
    show_default=True,
    help="The output format.",
)
def taxonomy2jsonld(
    annotation_file, abbreviation_file, description_file, output_file, output_format
):
    # create BKETaxonomy instance
    hmba_bg = BKETaxonomy()

    # read abbreviation file
    abbreviation_df = pd.read_csv(abbreviation_file)
    # replace NaN values with empty strings
    abbreviation_df.fillna("", inplace=True)
    # process abbreviations
    hmba_bg.parse_abbreviations(abbreviation_df)

    # read annotation file
    hmba_df = pd.read_csv(annotation_file)
    # process each row individually
    for _, curr_row in hmba_df.iterrows():
        # parse Neighborhood columns for this row
        neighborhood_taxon = hmba_bg.parse_taxonomy_level(
            curr_row.iloc[40:47], "Neighborhood", parent_id=None
        )
        # parse Class columns for this row
        class_taxon = hmba_bg.parse_taxonomy_level(
            curr_row.iloc[33:40], "Class", parent_id=neighborhood_taxon
        )
        # parse Subclass columns for this row
        subclass_taxon = hmba_bg.parse_taxonomy_level(
            curr_row.iloc[26:33], "Subclass", parent_id=class_taxon
        )
        # parse Group columns for this row
        hmba_bg.parse_taxonomy_level(
            curr_row.iloc[0:26], "Group", parent_id=subclass_taxon
        )

    # read description file
    hmba_cell_type_set_df = pd.read_csv(description_file)
    hmba_bg.parse_cell_type_set(hmba_cell_type_set_df)

    # save objects to json files
    with open(output_file, "w", encoding="utf-8") as f:
        # use json_dumper to serialize objects
        data = []
        for i in hmba_bg.group_ctt.values():
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.subclass_ctt.values():
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.class_ctt.values():
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.neighborhood_ctt.values():
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.display_colors.values():
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.abbreviations.values():
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.cell_type_sets.values():
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.spatial_proportions.values():
            data.append(json.loads(json_dumper.dumps(i)))
        output = {
            "@context": "https://raw.githubusercontent.com/brain-bican/models/refs/heads/main/jsonld-context-autogen/bke_taxonomy.context.jsonld",
            "@graph": data,
        }
        json.dump(output, f, indent=4)


if __name__ == "__main__":
    taxonomy2jsonld()
