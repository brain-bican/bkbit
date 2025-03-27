from collections import defaultdict

import pandas as pd
import pyarrow.parquet as pq
from tqdm import tqdm
from multiprocessing import Pool
from bkbit.models import bke_taxonomy as bke_tax
from bkbit.utils.generate_bkbit_id import generate_object_id


class Taxonomy:
    def __init__(self):
        self.relations = pd.DataFrame()
        self.display_colors = []
        self.xref_to_bkbit_id = {}

    @staticmethod
    def generate_cell_type_taxon(file_path):
        """Read and return cell type taxonomy data from a parquet file."""
        table = pq.read_table(file_path)
        df = table.to_pandas()
        return df

    @staticmethod
    def _process_row(row):
        relation = {
            "predicate": row["predicate"],
            "object_id": row["object"],
            "subject_type": row["subject_type"],
            "object_type": row["object_type"],
        }
        print(relation)
        return relation

    def read_relationships(self, file_path):
        """Read relationship data from a parquet file and store in relations dictionary."""
        df = pd.read_parquet(file_path, engine="pyarrow").set_index(
            ["subject_id", "predicate"]
        )
        self.relations = df

    def get_relations(self, subject_id, predicate):
        """Retrieve relations for a given subject ID and predicate from the taxonomy."""
        rows = self.relations.loc[subject_id, predicate]
        return rows

    def parse_display_color(self, file_path):
        """Parse display color data from a parquet file and return a dictionary of display colors."""
        display_colors = self._get_attributes(file_path, bke_tax.DisplayColor)
        for display_color in display_colors:
            display_color["id"] = generate_object_id(display_color)
            self.display_colors.append(bke_tax.DisplayColor(**display_color))
            self.xref_to_bkbit_id[display_color["xref"]] = display_color["id"]

    @staticmethod
    def _get_attributes(file_path, class_name):
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
                    .get("bke", {})
                    .get("local_name_value", schema_field_name)
                )
                if data_field_name in row:
                    row_attributes[schema_field_name] = row[data_field_name]
            all_object_attributes.append(row_attributes)
        return all_object_attributes
