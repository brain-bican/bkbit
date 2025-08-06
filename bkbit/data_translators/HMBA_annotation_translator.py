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
        """
        for row in df.itertuples():

            # define CellTypeTaxon
            #? Should literature support be added as content_url?
            #? Should literature_name_short and literature_name_long be added as xref?
            #! columns not processed and contain data: embedding_set, CL:ID_group, curated_markers, literature_support, literature_name_short, literature_name_long
            group_ctt_attributes = self._helper_parse_cell_type_taxon_attributes(row, "Group")
            group_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, group_ctt_attributes)
            self.group_ctt[group_cell_type_taxon.id] = group_cell_type_taxon
            
            # define DisplayColor
            group_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row.color_hex_group, "is_color_for_taxon": group_cell_type_taxon.id})
            self.display_colors[group_display_color.id] = group_display_color

    def parse_subclass(self, df):
        """
        Parse the subclass data from the DataFrame and generate CellTypeTaxon and DisplayColor objects.
        
        Args:
            df (pd.DataFrame): DataFrame containing subclass data with columns:
                - Subclass
                - accession_subclass
                - display_order_subclass
                - color_hex_subclass
        """
        for row in df.itertuples():
            # define CellTypeTaxon
            subclass_ctt_attributes = self._helper_parse_cell_type_taxon_attributes(row, "Subclass")
            subclass_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, subclass_ctt_attributes)
            self.subclass_ctt[subclass_cell_type_taxon.id] = subclass_cell_type_taxon

            # define DisplayColor
            subclass_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row.color_hex_subclass, "is_color_for_taxon": subclass_cell_type_taxon.id})
            self.display_colors[subclass_display_color.id] = subclass_display_color            

    def parse_class(self, df):
        """
        Parse the class data from the DataFrame and generate CellTypeTaxon and DisplayColor objects.
        
        Args:
            df (pd.DataFrame): DataFrame containing class data with columns:
                - Class
                - accession_class
                - display_order_class
                - color_hex_class
        """
        for row in df.itertuples():
            # define CellTypeTaxon
            class_ctt_attributes = self._helper_parse_cell_type_taxon_attributes(row, "Class")
            class_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, class_ctt_attributes)
            self.class_ctt[class_cell_type_taxon.id] = class_cell_type_taxon

            # define DisplayColor
            class_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row.color_hex_class, "is_color_for_taxon": class_cell_type_taxon.id})
            self.display_colors[class_display_color.id] = class_display_color

    def parse_neighborhood(self, df):
        """
        Parse the neighborhood data from the DataFrame and generate CellTypeTaxon and DisplayColor objects.
        
        Args:
            df (pd.DataFrame): DataFrame containing neighborhood data with columns:
                - Neighborhood
                - accession_neighborhood
                - display_order_neighborhood
                - color_hex_neighborhood
        """
        for row in df.itertuples():
            # define CellTypeTaxon
            neighborhood_ctt_attributes = self._helper_parse_cell_type_taxon_attributes(row, "Neighborhood")
            neighborhood_cell_type_taxon = generate_object(bke_taxonomy.CellTypeTaxon, neighborhood_ctt_attributes)
            self.neighborhood_ctt[neighborhood_cell_type_taxon.id] = neighborhood_cell_type_taxon

            # define DisplayColor
            neighborhood_display_color = generate_object(bke_taxonomy.DisplayColor, {"color_hex_triplet":row.color_hex_neighborhood, "is_color_for_taxon": neighborhood_cell_type_taxon.id})
            self.display_colors[neighborhood_display_color.id] = neighborhood_display_color

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
            xref = []
            # check if value is Nan
            if row.primary_identifier:
                xref.append(row.primary_identifier)
            if row.secondary_identifier:
                xref.append(row.secondary_identifier)
            abbreviation_attributes = {"term": row.token, "meaning": row.meaning, "entity_type": row.type, "xref": xref}
            abbreviation_object = generate_object(bke_taxonomy.Abbreviation, abbreviation_attributes)
            self.abbreviations[abbreviation_object.term] = abbreviation_object

    def _helper_parse_cell_type_taxon_attributes(self, row, attribute_suffix):
        """
        Helper function to parse cell type taxon attributes from a row.
        
        Args:
            row (pd.Series): A row from the DataFrame.
            attribute_suffix (str): The suffix to append to the attribute names.
        
        Returns:
            dict: A dictionary of attributes for CellTypeTaxon.
        """
        cell_type_taxon_attribute_names = {"accession": "accession_id", "display_order":"order", "token": "has_abbreviation"}
        attributes = {"name": getattr(row, attribute_suffix)}
        
        for key, model_value in cell_type_taxon_attribute_names.items():
            data_key = key + "_" + attribute_suffix.lower()
            if data_key in row._fields:
                if key == "token":
                    tokens = getattr(row, data_key).split("|")
                    attributes[model_value] = [self.abbreviations[token].id for token in tokens if token in self.abbreviations]
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
    # parse Group columns
    hmba_bg.parse_group(hmba_df.iloc[:,:21])
    # parse Subclass columns
    hmba_bg.parse_subclass(hmba_df.iloc[:,21:28])
    # parse Class columns
    hmba_bg.parse_class(hmba_df.iloc[:,28:34])
    # parse Neighborhood columns
    hmba_bg.parse_neighborhood(hmba_df.iloc[:,34:41])
