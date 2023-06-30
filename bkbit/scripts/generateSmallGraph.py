import json
import argparse

def generateSmallGraph(file_name, num_objects):
    # Initialize an empty list to store the combined dictionaries
    combined_data = []

    # Iterate over each JSON file
    with open(file_name, "r") as file:
        data = json.load(file)
        combined_data.extend(data)

    # Create a dictionary with the @context and @graph
    output_data = {
        "@context": "https://raw.githubusercontent.com/atlaskb/models/main/jsonld-context-autogen/kbmodel.context.jsonld",
        "@graph": combined_data[:num_objects]
    }

    # Write the combined dictionaries to a new JSON file
    with open("small_graph_" + str(num_objects) + "_" + file_name.split('/')[-1] + "ld", "w") as outfile:
        json.dump(output_data, outfile, indent=2)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Create a graph based on a subset of single json data file.')
    parser.add_argument('--file_name', '-f', type=str, required=True, help='Path to json file.')
    parser.add_argument('--num_objects', '-n', type=int, default=15, help='Number of GeneAnnotation objects to include in the graph.')
    args = parser.parse_args()
    generateSmallGraph(args.file_name, args.num_objects)