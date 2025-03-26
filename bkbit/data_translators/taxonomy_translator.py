from collections import defaultdict

import pandas as pd
import pyarrow.parquet as pq

from bkbit.models import bke_taxonomy as bke_tax

class Taxonomy:
    def __init__(self):
        self.relations = {}
        self.display_colors = {}


    @staticmethod
    def generate_cell_type_taxon(file_path):
        """Read and return cell type taxonomy data from a parquet file."""
        table = pq.read_table(file_path)
        df = table.to_pandas()
        return df

    def read_relationships(self,file_path):
        """Read relationship data from parquet file and store in relations dictionary."""
        df = pd.read_parquet(file_path)
        relations = defaultdict(list)
        for _, row in df.iterrows():
            subject_id = row['subject_id']
            relations[subject_id].append(
                {
                    "predicate": row['predicate'],
                    "object_id": row['object_id'],
                    "subject_type": row['subject_type'],
                    "object_type": row['object_type']
                }
            )
        self.relations = relations
    def parse_display_color(self,file_path):
        """Parse display color data from a parquet file and return a dictionary of display colors."""
        display_colors = self._get_attributes(file_path, bke_tax.DisplayColor)

    @staticmethod
    def _get_attributes(file_path, class_name):
        """Parse attributes from a parquet file and return a dictionary of attributes."""
        df = pd.read_parquet(file_path)
        all_object_attributes = []
        for _, row in df.iterrows():
            row_attributes = {}
            for schema_field_name, schema_field_metadata in class_name.__fields__.items():
                data_field_name = schema_field_metadata.json_schema_extra.get("linkml_meta", {}).get("local_names", {}).get("bke", {}).get("local_name_value", schema_field_name)
                if data_field_name in row:
                    row_attributes[schema_field_name] = row[data_field_name]
            all_object_attributes.append(row_attributes)
        return all_object_attributes
   