"""Module that converts JSON-LD data to Turtle (TTL) format."""

from rdflib import Graph
from rdflib.exceptions import ParserError

def convert_jsonld_to_ttl(jsonld_data):
    """
    Converts JSON-LD data to Turtle (TTL) format.

    Args:
        jsonld_data (str): A string containing JSON-LD formatted data.

    Returns:
        str: The converted data in Turtle format if successful, otherwise None.

    Raises:
        Prints an error message if parsing or conversion fails due to ParserError, ValueError, or SyntaxError.
    """
    g = Graph()
    try:
        g.parse(data=jsonld_data, format="json-ld")
        return g.serialize(format="turtle")
    except (ParserError, ValueError, SyntaxError) as e:
        return f"Error during conversion: {e}"
