import re

# Read the file
file_path = "../models/genome_annotation.py"
with open(file_path, "r") as file:
    content = file.read()

# Find the GeneAnnotation class
pattern = r"class GeneAnnotation\(Gene\):\s+\"\"\"\n    An annotation describing the location, boundaries, and functions of  individual genes within a genome annotation.\n    \"\"\""
match = re.search(pattern, content)

if match:
    # Add the function to the class
    updated_content = content.replace(match.group(), match.group() + "\n    def __ne__(self, other):\n        return (self.description != other.description) or (self.molecular_type != other.molecular_type)\n    ")
    updated_content = updated_content.replace(match.group(), match.group() + "\n    def __eq__(self, other):\n        return (self.description == other.description) and (self.molecular_type == other.molecular_type)\n    ")
    updated_content = updated_content.replace(match.group(), match.group() + "\n\n    def __hash__(self):\n        return hash(tuple([self.id, self.name, self.molecular_type, self.description]))\n    ")

    # Write the updated content back to the file
    with open(file_path, "w") as file:
        file.write(updated_content)
else:
    print("GeneAnnotation class not found in the file.")

