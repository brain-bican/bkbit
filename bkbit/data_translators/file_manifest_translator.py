import click
import csv
import json
import os
from multiprocessing import Pool

class digitalObject:
    def __init__(self, file_name, checksum, file_type, archive, archive_uri, project_id):
        self.file_name = file_name
        self.checksum = checksum
        self.file_type = file_type
        self.archive = archive
        self.archive_uri = archive_uri
        self.project_id = project_id

def process_row(row):
    
    """Function to process each row and return a digitalObject instance and the Specimen ID."""
    # print(f"processing row in process: {os.getpid()}")  
    obj = digitalObject(
        file_name=row['File Name'],
        checksum=row['Checksum'],
        file_type=row['File Type'],
        archive=row['Archive'],
        archive_uri=row['Archive URI'],
        project_id=row['Project ID']
    )
    return obj, row['Specimen ID']

def process_csv(file_path):
    digital_objects = []
    specimen_ids = set()

    # Read CSV file and gather all rows
    with open(file_path, mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = [row for row in reader]

    # Use multiprocessing to process rows in parallel
    with Pool() as pool:
        results = pool.map(process_row, rows)

    # Collect results
    for obj, specimen_id in results:
        digital_objects.append(obj)
        specimen_ids.add(specimen_id)

    return digital_objects, specimen_ids

@click.command()
##ARGUMENTS##
# Argument #1: The path to the file manifest CSV file.  
@click.argument('file_manifest_path')

##OPTIONS##
# Option #1: List all library aliquots in the file manifest.
@click.option('--list_library_aliquots', is_flag=True, help='List all library aliquots in the file manifest.')  

def filemanifest2jsonld(file_manifest_path: str, list_library_aliquots: bool):
    digital_objects, specimen_ids = process_csv(file_manifest_path)
    # print(f"Processed {len(digital_objects)} digital objects")
    # print(f"Unique Specimen IDs: {specimen_ids}")
    # print(f"Number of unique Specimen IDs: {len(specimen_ids)}")
    # print(f"Number of unique PIDs: {len(PID)}")
    if list_library_aliquots:
        with open('file_manifest_library_aliquots.txt', 'w') as f:
            for specimen_id in specimen_ids:
                f.write(f"{specimen_id}\n")
    serialized_objects = [obj.__dict__ for obj in digital_objects]
    print(json.dumps(serialized_objects, indent=2))


if __name__ == "__main__":
    filemanifest2jsonld()
