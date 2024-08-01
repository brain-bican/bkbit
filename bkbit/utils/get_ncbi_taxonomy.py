"""
This script downloads a zip file containing taxonomic data from a given URL, extracts and processes 
the content of the 'names.dmp' file in memory, and saves the parsed data into JSON files. The script
includes three main functions:

1. download_and_extract_zip_in_memory(url):
    Downloads a zip file from the given URL and extracts the content of the 'names.dmp' file in memory.

2. parse_dmp_content(dmp_content):
    Parses the content of a DMP file and extracts taxonomic information into dictionaries.

3. process_and_save_taxdmp_in_memory(url, output_dir):
    Downloads and processes the taxdump file from the given URL, and saves the parsed data into 
    separate JSON files in the specified output directory.

Usage:
    The script can be executed as a standalone program. Modify the URL and output directory as needed.
"""

import json
import zipfile
import io
import os
import requests


def download_and_extract_zip_in_memory(url):
    """
    Downloads a zip file from the given URL and extracts the content of the 'names.dmp' file in memory.

    Args:
        url (str): The URL of the zip file to download.

    Returns:
        str: The content of the 'names.dmp' file as a string.

    Raises:
        requests.exceptions.HTTPError: If the file download fails with a non-200 status code.
    """
    # Download the file
    response = requests.get(url, timeout=30)
    if response.status_code == 200:
        # Unzip the file in memory
        with zipfile.ZipFile(io.BytesIO(response.content)) as z:
            # Extract names.dmp file content into memory
            with z.open("names.dmp") as names_dmp_file:
                names_dmp_content = names_dmp_file.read().decode("utf-8")
                return names_dmp_content
    else:
        raise requests.exceptions.HTTPError(
            f"Failed to download file, status code: {response.status_code}"
        )


def parse_dmp_content(dmp_content):
    """
    Parses the content of a DMP file and extracts taxonomic information.

    Args:
        dmp_content (str): The content of the DMP file.

    Returns:
        tuple: A tuple containing three dictionaries:
            - taxid_to_scientific_name: A dictionary mapping taxonomic IDs to scientific names.
            - taxid_to_common_name: A dictionary mapping taxonomic IDs to common names.
            - scientific_name_to_taxid: A dictionary mapping scientific names to taxonomic IDs.
    """
    taxid_to_scientific_name = {}
    taxid_to_common_name = {}
    scientific_name_to_taxid = {}

    for line in dmp_content.strip().split("\n"):
        # Split the line by the delimiter '|'
        parts = line.strip().split("|")

        # Remove leading and trailing whitespace from each part
        parts = [part.strip() for part in parts]
        # Taxonomy names file (names.dmp):
        #   tax_id-- the id of node associated with this name
        #   name_txt-- name itself
        #   unique name-- the unique variant of this name if name not unique
        #   name class-- (synonym, common name, ...)
        taxid = parts[0]
        name = parts[1]
        unique_name = parts[2]
        name_class = parts[3]

        # Create a dictionary with the parsed data
        if name_class == "scientific name" and taxid not in taxid_to_scientific_name:
            if unique_name:
                taxid_to_scientific_name[taxid] = unique_name
                scientific_name_to_taxid[unique_name] = taxid
            else:
                taxid_to_scientific_name[taxid] = name
                scientific_name_to_taxid[name] = taxid
        elif name_class == "genbank common name" and taxid not in taxid_to_common_name:
            taxid_to_common_name[taxid] = name
    return taxid_to_scientific_name, taxid_to_common_name, scientific_name_to_taxid


def process_and_save_taxdmp_in_memory(url, output_dir):
    """
    Downloads and processes the taxdump file from the given URL,
    and saves the parsed data into separate JSON files in the specified output directory.

    Args:
        url (str): The URL of the taxdump file to download and process.
        output_dir (str): The directory where the parsed data will be saved.

    Returns:
        None
    """
    # Ensure the output directory exists
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Step 1: Download and unzip the folder in memory
    names_dmp_content = download_and_extract_zip_in_memory(url)

    # Step 2: Parse the names.dmp content
    taxid_to_scientific_name, taxid_to_common_name, scientific_name_to_taxid = (
        parse_dmp_content(names_dmp_content)
    )

    # Step 3: Save the dictionaries to files
    with open(
        os.path.join(output_dir, "taxid_to_scientific_name.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(taxid_to_scientific_name, f, indent=4)

    with open(
        os.path.join(output_dir, "taxid_to_common_name.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(taxid_to_common_name, f, indent=4)

    with open(
        os.path.join(output_dir, "scientific_name_to_taxid.json"), "w", encoding="utf-8"
    ) as f:
        json.dump(scientific_name_to_taxid, f, indent=4)


if __name__ == "__main__":
    URL = "https://ftp.ncbi.nih.gov/pub/taxonomy/taxdmp.zip"
    process_and_save_taxdmp_in_memory(URL, "ncbi_taxonomy")
