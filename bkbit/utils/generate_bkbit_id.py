"""Module for generating unique BKBit object IDs using SHA-256 hashing."""

import json
import hashlib

BKBIT_OBJECT_ID_PREFIX = "urn:bkbit:"

def generate_object_id(attributes:dict):
    """
    Generate a unique object ID based on the provided attributes.
    Args:
        attributes (dict): A dictionary containing the attributes of the object.
    Returns:
        str: The generated object ID.
    """
    # Sort the attributes by keys and convert to a consistent JSON string
    #print(attributes)
    normalized_attributes = json.dumps(attributes, sort_keys=True)
    object_id = hashlib.sha256(normalized_attributes.encode()).hexdigest()
    return BKBIT_OBJECT_ID_PREFIX + object_id
