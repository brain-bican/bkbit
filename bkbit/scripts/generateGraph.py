import json
import glob
import os
import argparse

def generateGraph(dir_path, output_fname):
    # List all JSON files in the directory
    json_files = glob.glob(os.path.join(dir_path, "*.json"))

    # Initialize an empty list to store the combined dictionaries
    combined_data = []

    # Iterate over each JSON file
    for file_name in json_files:
        print(f"Reading {file_name}")
        with open(file_name, "r") as file:
            data = json.load(file)
            combined_data.extend(data)

    # Create a dictionary with the @context and @graph
    output_data = {
        "@context": "https://raw.githubusercontent.com/atlaskb/models/main/jsonld-context-autogen/kbmodel.context.jsonld",
        "@graph": combined_data
    }

    # Write the combined dictionaries to a new JSON file
    with open(output_fname, "w") as outfile:
        json.dump(output_data, outfile, indent=2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create a jsonld graph based on all the json files in a given directory.')
    parser.add_argument('--dir_path', '-d', type=str, required=True, help='Path to directory containing json files used to create jsonld graph. Note: all .json files in the directory will be used.')
    parser.add_argument('--output_fname', '-o', type=str, required=True, help='Name of file where graph will be saved. Must have extension .jsonld')
    args = parser.parse_args()
    generateGraph(args.dir_path, args.output_fname)