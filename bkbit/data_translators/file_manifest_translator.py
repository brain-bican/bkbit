import uuid
import click
import csv
import json
from multiprocessing import Pool
from bkbit.models import library_generation as lg
CONTEXT = "https://raw.githubusercontent.com/brain-bican/models/main/jsonld-context-autogen/library_generation.context.jsonld"


def process_row(row):
    
    """Function to process each row and return a digitalObject instance and the Specimen ID."""
    # print(f"processing row in process: {os.getpid()}")  
    # File Name Format -> [Sample Name]_S[0-9]_L00[Lane Number]_[Read Type]_001.fastq.gz
    read_type = row['File Name'].split('.')[0].split('_')[-2]
    id = row['Archive'] + ':' + row['File Name']
    library_aliquot_nhashid = 'NIMP' + ":" + row['Specimen ID']
    # Generate Checksum Object
    uuid_value = uuid.uuid4()
    # Construct a URN with the UUID
    urn = f"urn:uuid:{uuid_value}"
    checksum_obj = lg.Checksum(id=urn, checksum_algorithm=lg.DigestType.MD5, value=row['Checksum'])

    digital_obj = lg.DigitalAsset(
        id = id,
        was_derived_from = library_aliquot_nhashid,
        name=row['File Name'],
        format=row['File Type'],
        data_type = read_type,
        content_url=[row['Archive URI']],
        digest = [urn]

    )
    return digital_obj, checksum_obj, row['Specimen ID']

def process_csv(file_path):
    digital_and_checksum_objects = []
    specimen_ids = set()

    # Read CSV file and gather all rows
    with open(file_path, mode='r') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = [row for row in reader]

    # Use multiprocessing to process rows in parallel
    with Pool() as pool:
        results = pool.map(process_row, rows)

    # Collect results
    for digital_obj, checksum_obj, specimen_id in results:
        digital_and_checksum_objects.append(digital_obj)
        digital_and_checksum_objects.append(checksum_obj)
        specimen_ids.add(specimen_id)

    return digital_and_checksum_objects, specimen_ids

def serialize_to_jsonld(objects):
    serialized_objects = [obj.__dict__ for obj in objects]
    output_data = {
            "@context": CONTEXT,
            "@graph": serialized_objects,
    }
    return json.dumps(output_data, indent=2)

@click.command()
##ARGUMENTS##
# Argument #1: The path to the file manifest CSV file.  
@click.argument('file_manifest_path')

##OPTIONS##
# Option #1: List all library aliquots in the file manifest.
@click.option('--list_library_aliquots', is_flag=True, help='List all library aliquots in the file manifest.')  

def filemanifest2jsonld(file_manifest_path: str, list_library_aliquots: bool):
    digital_and_checksum_objects, specimen_ids = process_csv(file_manifest_path)
    if list_library_aliquots:
        with open('file_manifest_library_aliquots.txt', 'w') as f:
            for specimen_id in specimen_ids:
                f.write(f"{specimen_id}\n")
    print(serialize_to_jsonld(digital_and_checksum_objects))


if __name__ == "__main__":
    filemanifest2jsonld()
