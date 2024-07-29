import re

# Read the file
file_path = "bkbit/models/genome_annotation.py"
with open(file_path, "r") as file:
    content = file.read()

# Define the patterns to check if the functions already exist
ne_pattern = r"def __ne__\(self, other\):"
eq_pattern = r"def __eq__\(self, other\):"
hash_pattern = r"def __hash__\(self\):"

# Find the GeneAnnotation class
class_pattern = r"class GeneAnnotation\(Gene\):\s+\"\"\"\n    An annotation describing the location, boundaries, and functions of  individual genes within a genome annotation.\n    \"\"\""
class_match = re.search(class_pattern, content)

if class_match:
    class_start = class_match.end()

    # Check if the functions already exist
    has_ne = re.search(ne_pattern, content[class_start:])
    has_eq = re.search(eq_pattern, content[class_start:])
    has_hash = re.search(hash_pattern, content[class_start:])

    # Add the functions only if they do not exist
    if not has_ne:
        content = content.replace(class_match.group(), class_match.group() + "\n    def __ne__(self, other):\n        return (self.description != other.description) or (self.molecular_type != other.molecular_type)\n    ")
    if not has_eq:
        content = content.replace(class_match.group(), class_match.group() + "\n    def __eq__(self, other):\n        return (self.description == other.description) and (self.molecular_type == other.molecular_type)\n    ")
    if not has_hash:
        content = content.replace(class_match.group(), class_match.group() + "\n\n    def __hash__(self):\n        return hash(tuple([self.id, self.name, self.molecular_type, self.description]))\n    ")

    # Write the updated content back to the file
    with open(file_path, "w") as file:
        file.write(content)
else:
    print("GeneAnnotation class not found in the file.")
