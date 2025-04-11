from collections import defaultdict

import pandas as pd
import pyarrow.parquet as pq
from tqdm import tqdm
from multiprocessing import Pool
from bkbit.models import bke_taxonomy_full as bke_tax
from bkbit.utils.generate_bkbit_id import generate_object_id

LOCAL_NAME_SOURCE = "allen"
DEPENDENCIES = {
    "Abbreviation": ["GeneAnnotation", "ParcellationTerm"],
    "CellTypeSet": ["CellTypeTaxonomy", "CellTypeTaxon", "Abbreviation", "CellTypeSet"],  # self-dependency
    "CellTypeTaxon": ["CellTypeTaxonomy", "Cluster", "Abbreviation", "CellTypeTaxon"],    # self-dependency
    "CellTypeTaxonomy": ["CellTypeTaxonomyCreationProcess", "ClusterSet", "CellTypeTaxonomy"],  # self-dependency
    "CellTypeTaxonomyCreationProcess": ["ClusterSet"],
    "Cluster": ["ClusterSet", "ObservationRow", "CellSpecimen"],
    "ClusteringProcess": ["ObservationMatrix"],
    "ClusterSet": ["ClusteringProcess", "ObservationMatrix", "ClusterSet"],  # self-dependency
    "ColorPalette": ["CellTypeTaxonomy"],
    "DisplayColor": ["ColorPalette", "CellTypeTaxon", "CellTypeSet"],
    "ObservationMatrix": ["ObservationMatrixCreationProcess", "MatrixFile", "GeneAnnotation", "CellSpecimen"],
    "ObservationRow": ["ObservationMatrix", "MatrixFile", "CellSpecimen"],
    "ObservationMatrixCreationProcess": [],  # no dependencies
    "MatrixFile": [],  # no dependencies
    "CellSpecimen": [],  # no dependencies
    "GeneAnnotation": [],  # no dependencies
    "ParcellationTerm": []  # no dependencies
}

processed_classes = set()

    # Decorator to check dependencies and prompt user if unmet
def require_dependencies(class_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            unmet = [dep for dep in DEPENDENCIES.get(class_name, []) if dep not in processed_classes]
            if unmet:
                print(f"\n⚠️  The following dependencies for '{class_name}' have not been processed locally: {unmet}")
                proceed = input("Do you want to continue anyway? (y/N): ").strip().lower()
                if proceed != "y":
                    print(f"❌ Skipping {class_name}.")
                    return
            print(f"✔ Processing {class_name}...")
            result = func(*args, **kwargs)
            processed_classes.add(class_name)
            return result
        return wrapper
    return decorator

class Taxonomy:
    def __init__(self):
        self.relations = pd.DataFrame()
        self.xref_to_bkbit_id = {}

    def read_relationships(self, file_path):
        """Read relationship data from a parquet file and store in relations dictionary."""
        df = pd.read_parquet(file_path, engine="pyarrow").set_index(
            ["subject_id", "predicate", "object_type"]
        )
        df = df.sort_index()
        self.relations = df

    def get_relations(self, subject_id, predicate, object_type):
        """Retrieve relations for a given subject ID and predicate from the taxonomy."""
        try:
            rows = self.relations.loc[subject_id, predicate, object_type]
        except KeyError:
            print(f"KeyError: {subject_id}, {predicate}, {object_type}")
            return None
        return rows
    
    def _get_attributes(self, file_path, class_name):
        """Parse attributes from a parquet file and return a dictionary of attributes."""
        df = pd.read_parquet(file_path)
        all_object_attributes = []
        for _, row in df.iterrows():
            row_attributes = {}
            for (
                schema_field_name,
                schema_field_metadata,
            ) in class_name.__fields__.items():
                data_field_name = (
                    schema_field_metadata.json_schema_extra.get("linkml_meta", {})
                    .get("local_names", {})
                    .get(LOCAL_NAME_SOURCE, {})
                    .get("local_name_value", schema_field_name)
                )
                linkml_range = schema_field_metadata.json_schema_extra.get(
                    "linkml_meta", {}
                ).get("range", "string")
                multivalued = schema_field_metadata.json_schema_extra.get(
                    "linkml_meta", {}
                ).get("multivalued", False)
                print(
                    f"Processing {schema_field_name} ({data_field_name}) with range {linkml_range} and multivalued {multivalued}"
                )
                if data_field_name in row: 
                    #! TODO: What if references are provided in the data? We need to then use xref_to_bkbit_id
                    #! TODO: Check to see if the type of the data matches the range
                    #! TODO: Check to see if the type of the data is a class or a primitive
                    if schema_field_name == "xref":
                        row_attributes[schema_field_name] = [LOCAL_NAME_SOURCE + ":" + str(row[data_field_name])]
                    elif multivalued:
                        row_attributes[schema_field_name] = row[data_field_name].split(",")
                    else:
                        row_attributes[schema_field_name] = row[data_field_name]
                # elif relations := self.get_relations(
                #     source_id, data_field_name, linkml_range
                # ):
                #     row_attributes[schema_field_name] = self.xref_to_bkbit_id.get(
                #         relations["object"], relations["object"]
                #     )
                #     #! TODO: If the object is not found in local xref_to_bkbit_id, check the KG

            all_object_attributes.append(row_attributes)
        return all_object_attributes
    
    def parse(self, class_name, file_path):
        """Parse data from a parquet file and return a dictionary of objects."""

        #class_object = CLASS_NAME_MAPPING.get(class_name)
        class_object = bke_tax.__dict__.get(class_name)
        if class_object is None:
            raise ValueError(f"Unknown class name: {class_name}")
        all_object_attributes = self._get_attributes(file_path, class_object)
        for attributes in all_object_attributes:
            attributes["id"] = generate_object_id(attributes)
            self._append_attr(class_name, class_object(**attributes))            
            self.xref_to_bkbit_id[attributes["xref"][0]] = attributes["id"]

    def _append_attr(self, attr_name, item):
        if not hasattr(self, attr_name) or getattr(self, attr_name) is None:
            setattr(self, attr_name, [])
        getattr(self, attr_name).append(item)