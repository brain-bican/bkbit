from collections import defaultdict

import pandas as pd
import pyarrow.parquet as pq

class Taxonomy:
    def __init__(self):
        self.relations = {}


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
