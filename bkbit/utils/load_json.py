import json

def load_json(file_path):
    """
    Load a JSON file from the given file path.

    Args:
        file_path (str): The path to the JSON file.

    Returns:
        dict: The contents of the JSON file as a dictionary.

    Raises:
        FileNotFoundError: If the file does not exist.
        JSONDecodeError: If the file is not a valid JSON.

    """
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)