import itertools
import pkg_resources
from bkbit.models import bke_taxonomy
import json
import hashlib
import pandas as pd
import json
from collections import defaultdict
from linkml_runtime.dumpers import json_dumper
class BKETaxonomy: 
    def __init__(self):
        self.abbreviations = {}
        self.group_ctt = []
        self.subclass_ctt = []
        self.class_ctt = []
        self.neighborhood_ctt = []
        self.display_colors = []
        self.cell_type_sets = {}
    def parse_group(self, row):
        """
        Parse the group data from a pandas Series (row) and generate CellTypeTaxon and DisplayColor objects.
        
        Args:
            row (pd.Series): Series containing group data with columns:
                - Group
                - accession_group
                - display_order_group
                - color_hex_group
        """
        # define CellTypeTaxon
        #? Should literature support be added as content_url?
        #? Should literature_name_short and literature_name_long be added as xref?
        #! columns not processed and contain data: embedding_set, curated_markers, literature_support, literature_name_short, literature_name_long
        group_ctt_attributes = self._helper_parse_cell_type_taxon_attributes(row, "Group")
        group_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, group_ctt_attributes)
        self.group_ctt.append(group_cell_type_taxon)

        # define DisplayColor
        group_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row["color_hex_group"], "is_color_for_taxon": group_cell_type_taxon.id})
        self.display_colors.append(group_display_color)
        
        return group_cell_type_taxon.id

    def parse_subclass(self, row, parent_id):
        """
        Parse the subclass data from the DataFrame and generate CellTypeTaxon and DisplayColor objects.
        
        Args:
            df (pd.DataFrame): DataFrame containing subclass data with columns:
                - Subclass
                - accession_subclass
                - display_order_subclass
                - color_hex_subclass
        """
        # define CellTypeTaxon
        subclass_ctt_attributes = self._helper_parse_cell_type_taxon_attributes(row, "Subclass")
        # add parent attribute

        subclass_ctt_attributes['has_parent'] = parent_id
        subclass_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, subclass_ctt_attributes)
        self.subclass_ctt.append(subclass_cell_type_taxon)

        # define DisplayColor
        subclass_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row.color_hex_subclass, "is_color_for_taxon": subclass_cell_type_taxon.id})
        self.display_colors.append(subclass_display_color)            
        
        return subclass_cell_type_taxon.id
    
    def parse_class(self, row, parent_id):
        """
        Parse the class data from the DataFrame and generate CellTypeTaxon and DisplayColor objects.
        
        Args:
            df (pd.DataFrame): DataFrame containing class data with columns:
                - Class
                - accession_class
                - display_order_class
                - color_hex_class
        """
        # define CellTypeTaxon
        class_ctt_attributes = self._helper_parse_cell_type_taxon_attributes(row, "Class")
        class_ctt_attributes['has_parent'] = parent_id
        class_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, class_ctt_attributes)
        self.class_ctt.append(class_cell_type_taxon)

        # define DisplayColor
        class_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row.color_hex_class, "is_color_for_taxon": class_cell_type_taxon.id})
        self.display_colors.append(class_display_color)       
       
        return class_cell_type_taxon.id

    def parse_neighborhood(self, row, parent_id):
        """
        Parse the neighborhood data from the DataFrame and generate CellTypeTaxon and DisplayColor objects.
        
        Args:
            df (pd.DataFrame): DataFrame containing neighborhood data with columns:
                - Neighborhood
                - accession_neighborhood
                - display_order_neighborhood
                - color_hex_neighborhood
        """

        # define CellTypeTaxon
        neighborhood_ctt_attributes = self._helper_parse_cell_type_taxon_attributes(row, "Neighborhood")
        neighborhood_ctt_attributes['has_parent'] = parent_id
        neighborhood_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, neighborhood_ctt_attributes)
        self.neighborhood_ctt.append(neighborhood_cell_type_taxon)

        # define DisplayColor
        neighborhood_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row.color_hex_neighborhood, "is_color_for_taxon": neighborhood_cell_type_taxon.id})
        self.display_colors.append(neighborhood_display_color)

        return neighborhood_cell_type_taxon.id

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
            abbreviation_attributes = {"term": row.token, "meaning": row.meaning, "entity_type": row.type}

            abbrev_ids = []
            # check if value is Nan
            if row.primary_identifier:
                abbrev_ids.append(row.primary_identifier)
            if row.secondary_identifier:
                abbrev_ids.append(row.secondary_identifier)
            entity_type = abbreviation_attributes.get("entity_type")
            if entity_type == "gene":
                abbreviation_attributes["denotes_gene_annotation"] = abbrev_ids
            elif entity_type == "cell_type":
                abbreviation_attributes["denotes_cell_type"] = abbrev_ids
            elif entity_type == "anatomical":
                abbreviation_attributes["denotes_parcellation_term"] = abbrev_ids
            else:
                print(f"Unknown entity type: {entity_type}")
            abbreviation_object = generate_object(bke_taxonomy.Abbreviation, abbreviation_attributes)
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
            cell_type_set_attributes = {"name": row.name, "accession_id": row.label, "description": row.description, "order": row.order}
            if row.name == "Neighborhood":
                cell_type_set_attributes["contains_taxon"] = [i.id for i in self.neighborhood_ctt]
            elif row.name == "Class":
                cell_type_set_attributes["contains_taxon"] = [i.id for i in self.class_ctt]
            elif row.name == "Subclass":
                cell_type_set_attributes["contains_taxon"] = [i.id for i in self.subclass_ctt]
            elif row.name == "Group":
                cell_type_set_attributes["contains_taxon"] = [i.id for i in self.group_ctt]
            else:
                print(f"Unknown CellTypeSet name: {row.name}")
            # get self.row.name_ctt
            cell_type_set = generate_object(bke_taxonomy.CellTypeSet, cell_type_set_attributes)
            self.cell_type_sets[cell_type_set.id] = cell_type_set

    def _helper_parse_cell_type_taxon_attributes(self, row, attribute_suffix):
        """
        Helper function to parse cell type taxon attributes from a row.
        
        Args:
            row (pd.Series): A row from the DataFrame.
            attribute_suffix (str): The suffix to append to the attribute names.
        
        Returns:
            dict: A dictionary of attributes for CellTypeTaxon.
        """
        cell_type_taxon_attribute_names = {"accession": "accession_id", "display_order":"order", "tokens": "has_abbreviation", "CL_ID": "xref"}
        attributes = {"name": row.get(attribute_suffix)}
        
        for key, model_value in cell_type_taxon_attribute_names.items():
            data_key = key + "_" + attribute_suffix.lower()
            if data_key in row:
                if key == "tokens":
                    tokens = row.get(data_key).split("|")
                    attributes[model_value] = [self.abbreviations[token].id for token in tokens if token in self.abbreviations]
                elif key == "CL_ID":
                    attributes[model_value] = [row.get(data_key)] if pd.notna(row.get(data_key)) else None
                else:
                    attributes[model_value] = row.get(data_key)
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

def generate_object_id(attributes:dict):
    """
    Generate a unique object ID based on the provided attributes.
    Args:
        attributes (dict): A dictionary containing the attributes of the object.
    Returns:
        str: The generated object ID.
    """
    # Sort the attributes by keys and convert to a consistent JSON string
    #print(attributes)
    BKBIT_OBJECT_ID_PREFIX = "urn:bkbit:"
    normalized_attributes = json.dumps(attributes, sort_keys=True)
    object_id = hashlib.sha256(normalized_attributes.encode()).hexdigest()
    return BKBIT_OBJECT_ID_PREFIX + object_id

if __name__ == "__main__":
    # create BKETaxonomy instance
    hmba_bg = BKETaxonomy()
    
    # open HMBA abbreviation meaning file
    abbreviation_meaning_file = pkg_resources.resource_filename("bkbit", "data/HMBA_BG_abbrev_meanings.csv")
    abbreviation_df = pd.read_csv(abbreviation_meaning_file)
    # replace NaN values with empty strings
    abbreviation_df.fillna("", inplace=True)
    # parse abbreviations
    hmba_bg.parse_abbreviations(abbreviation_df)

    # open HMBA consensus annotation file
    hmba_annotation_file = pkg_resources.resource_filename("bkbit", "data/HMBA_BG_consensus_annotation.csv")
    hmba_df = pd.read_csv(hmba_annotation_file)
    
    # process each row individually
    for _, curr_row in hmba_df.iterrows():        
        # parse Group columns for this row
        group_taxon = hmba_bg.parse_group(curr_row.iloc[0:21])
        # parse Subclass columns for this row
        subclass_taxon = hmba_bg.parse_subclass(curr_row.iloc[21:28], parent_id=group_taxon)
        # parse Class columns for this row
        class_taxon = hmba_bg.parse_class(curr_row.iloc[28:34], parent_id=subclass_taxon)
        # parse Neighborhood columns for this row
        neighborhood_taxon = hmba_bg.parse_neighborhood(curr_row.iloc[34:41], parent_id=class_taxon)

    # parse CellTypeSet columns
    # hmba_cell_type_set_file = pkg_resources.resource_filename("bkbit", "data/HMBA_BG_descriptions.csv")
    # hmba_cell_type_set_df = pd.read_csv(hmba_cell_type_set_file)
    # hmba_bg.parse_cell_type_set(hmba_cell_type_set_df)
    # save objects to json files
    with open(pkg_resources.resource_filename("bkbit", "data/HMBA_BG_taxonomy.jsonld"), "w") as f:
        # use json_dumper to serialize objects
        data = []
        for i in hmba_bg.group_ctt:
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.subclass_ctt:
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.class_ctt:
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.neighborhood_ctt:
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.display_colors:
            data.append(json.loads(json_dumper.dumps(i)))
        for i in hmba_bg.abbreviations.values():
            data.append(json.loads(json_dumper.dumps(i)))
        output = output_data = {
            "@context": "https://raw.githubusercontent.com/brain-bican/models/refs/heads/main/jsonld-context-autogen/bke_taxonomy.context.jsonld",
            "@graph": data,
        }
        json.dump(output, f, indent=4)

    # with open(pkg_resources.resource_filename("bkbit", "data/HMBA_BG_display_colors.json"), "w") as f:
    #     json.dump(hmba_bg.display_colors, f, indent=4, default=lambda o: o.__dict__)
    # with open(pkg_resources.resource_filename("bkbit", "data/HMBA_BG_abbreviations.json"), "w") as f:
    #     json.dump(hmba_bg.abbreviations, f, indent=4, default=lambda o: o.__dict__)
    #     json.dump(hmba_bg.display_colors, f, indent=4, default=lambda o: o.__dict__)
    # with open(pkg_resources.resource_filename("bkbit", "data/HMBA_BG_abbreviations.json"), "w") as f:
    #     json.dump(hmba_bg.abbreviations, f, indent=4, default=lambda o: o.__dict__)