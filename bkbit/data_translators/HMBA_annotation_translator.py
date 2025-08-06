import pkg_resources
from bkbit.models import bke_taxonomy
import json
import hashlib
import pandas as pd
import json

class BKETaxonomy: 
    def __init__(self):
        self.abbreviations = {}
        self.group_ctt = {}
        self.subclass_ctt = {}
        self.class_ctt = {}
        self.neighborhood_ctt = {}
        self.display_colors = {}
    def parse_group(self, df):
        """
        Parse the group data from the DataFrame and generate CellTypeTaxon and DisplayColor objects.
        
        Args:
            df (pd.DataFrame): DataFrame containing group data with columns:
                - name
                - accession_group
                - display_order_group
                - color_hex_group
        Returns:
            list: A list of generated CellTypeTaxon and DisplayColor objects.
        """
        generated_group_objects = []
        for row in df.itertuples():

            # define CellTypeTaxon
            #? Should literature support be added as content_url?
            #? Should literature_name_short and literature_name_long be added as xref?
            #! columns not processed and contain data: embedding_set, CL:ID_group, curated_markers, literature_support, literature_name_short, literature_name_long
            group_ctt_attributes = _helper_parse_cell_type_taxon_attributes(row, "Group")
            group_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, group_ctt_attributes)

            # define DisplayColor 
            group_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row.color_hex_group, "is_color_for_taxon": group_cell_type_taxon.id})
            generated_group_objects.extend([group_cell_type_taxon, group_display_color])

        return generated_group_objects



    def parse_subclass(self, df):
        """
        Parse the subclass data from the DataFrame and generate CellTypeTaxon and DisplayColor objects.
        
        Args:
            df (pd.DataFrame): DataFrame containing subclass data with columns:
                - Subclass
                - accession_subclass
                - display_order_subclass
                - color_hex_subclass
        Returns:
            list: A list of generated CellTypeTaxon and DisplayColor objects.
        """
        generated_subclass_objects = []
        for row in df.itertuples():
            # define CellTypeTaxon
            subclass_ctt_attributes = _helper_parse_cell_type_taxon_attributes(row, "Subclass")
            subclass_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, subclass_ctt_attributes)

            # define DisplayColor
            subclass_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row.color_hex_subclass, "is_color_for_taxon": subclass_cell_type_taxon.id})
            generated_subclass_objects.extend([subclass_cell_type_taxon, subclass_display_color])

        return generated_subclass_objects

    def parse_class(self, df):
        """
        Parse the class data from the DataFrame and generate CellTypeTaxon and DisplayColor objects.
        
        Args:
            df (pd.DataFrame): DataFrame containing class data with columns:
                - Class
                - accession_class
                - display_order_class
                - color_hex_class
        Returns:
            list: A list of generated CellTypeTaxon and DisplayColor objects.
        """
        generated_class_objects = []
        for row in df.itertuples():
            # define CellTypeTaxon
            class_ctt_attributes = _helper_parse_cell_type_taxon_attributes(row, "Class")
            class_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, class_ctt_attributes)

            # define DisplayColor
            class_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row.color_hex_class, "is_color_for_taxon": class_cell_type_taxon.id})
            generated_class_objects.extend([class_cell_type_taxon, class_display_color])

        return generated_class_objects

    def parse_neighborhood(self, df):
        """
        Parse the neighborhood data from the DataFrame and generate CellTypeTaxon and DisplayColor objects.
        
        Args:
            df (pd.DataFrame): DataFrame containing neighborhood data with columns:
                - Neighborhood
                - accession_neighborhood
                - display_order_neighborhood
                - color_hex_neighborhood
        Returns:
            list: A list of generated CellTypeTaxon and DisplayColor objects.
        """
        generated_neighborhood_objects = []
        for row in df.itertuples():
            # define CellTypeTaxon
            neighborhood_ctt_attributes = _helper_parse_cell_type_taxon_attributes(row, "Neighborhood")
            neighborhood_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, neighborhood_ctt_attributes)

            # define DisplayColor
            neighborhood_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row.color_hex_neighborhood, "is_color_for_taxon": neighborhood_cell_type_taxon.id})
            generated_neighborhood_objects.extend([neighborhood_cell_type_taxon, neighborhood_display_color])

        return generated_neighborhood_objects

    def parse_abbreviation(self, df):
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

        Returns:
            dict: A dictionary where keys are abbreviation terms (str) and values 
            are abbreviation objects generated using `bke_taxonomy.Abbreviation`.
        """
        abbreviations = dict()
        for row in df.itertuples():
            # define Abbreviation
            xref = []
            if row.primary_identifier:
                xref.append(row.primary_identifier)
            if row.secondary_identifier:
                xref.append(row.secondary_identifier)
            abbreviation_attributes = {"term": row.token, "meaning": row.abbreviation_meaning, "entity_type": row.type, "xref": xref}
            abbreviation_object = generate_object(bke_taxonomy.Abbreviation, abbreviation_attributes)
            abbreviations[abbreviation_object.term] = abbreviation_object
        return abbreviations


def _helper_parse_cell_type_taxon_attributes(row, attribute_suffix):
    """
    Helper function to parse cell type taxon attributes from a row.
    
    Args:
        row (pd.Series): A row from the DataFrame.
        attribute_suffix (str): The suffix to append to the attribute names.
    
    Returns:
        dict: A dictionary of attributes for CellTypeTaxon.
    """
    cell_type_taxon_attribute_names = {"accession": "accession_id", "display_order":"order"}
    attributes = {"name": getattr(row, attribute_suffix)}
    
    for key, model_value in cell_type_taxon_attribute_names.items():
        data_key = key + "_" + attribute_suffix.lower()
        if data_key in row._fields:
            attributes[model_value] = getattr(row, data_key)
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
    # open HMBA consensus annotation file
    hmba_annotation_file = pkg_resources.resource_filename("bkbit", "data/HMBA_BG_consensus_annotation.csv")
    hmba_df = pd.read_csv(hmba_annotation_file)

    # parse Group columns
    group_ctt_objects = parse_group(hmba_df.iloc[:,:21])
    #print group_ctt_object in readable format
    # print in json format
    for i in group_ctt_objects:
        print(i)

    # parse Subclass columns
    subclass_ctt_objects = parse_subclass(hmba_df.iloc[:,21:28])
    # print in json format
    for i in subclass_ctt_objects:
        print(i)

    # parse Class columns
    class_ctt_objects = parse_class(hmba_df.iloc[:,28:34])
    # print in json format
    for i in class_ctt_objects:
        print(i)
        
    # parse Neighborhood columns
    neighborhood_ctt_objects = parse_neighborhood(hmba_df.iloc[:,34:41])
    # print in json format
    for i in neighborhood_ctt_objects:
        print(i)