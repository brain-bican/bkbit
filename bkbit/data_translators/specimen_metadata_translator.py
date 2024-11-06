import csv
import click

def extract_specimen_ids(csv_file_path):
    """
    Reads a CSV file and prints the 'Specimen ID' column to the command line.

    Parameters:
    - csv_file_path: str, path to the input CSV file.
    """
    with open(csv_file_path, 'r', encoding='utf-8') as csv_file:
        reader = csv.DictReader(csv_file)
        
        # Ensure 'Specimen ID' column exists in the CSV
        if 'Specimen ID' not in reader.fieldnames:
            raise ValueError("The CSV file does not contain the 'Specimen ID' column.")
        
        # Print 'Specimen ID' values to the command line
        for row in reader:
            specimen_id = row['Specimen ID']
            if specimen_id.startswith("LA"):
                print(specimen_id)

@click.command
@click.argument('specimen_metadata_file_path')

def list_library_aliquot(specimen_metadata_file_path):
    """
    Extracts and prints all the Library Aliquot NHash IDs from Data Catalog's specimen metadata file.

    Args:
        specimen_metadata_file_path (str): Path to the specimen metadata file.
    """
    extract_specimen_ids(specimen_metadata_file_path)

if __name__ == '__main__':  
    list_library_aliquot()