"""Utilities for querying the BrainKB knowledge graph SPARQL endpoint."""

import requests
from typing import List
from urllib.parse import quote


QUERY_SERVICE_URL = "https://queryservice.brainkb.org/query/sparql/"


def get_bkbit_ids_by_xref(
    xref: str,
    bearer_token: str,
    graph_name: str,
    timeout: int = 30
) -> List[str]:
    """
    Query the BrainKB knowledge graph to retrieve bkbit IDs using an xref value.

    This function searches for entities in the knowledge graph that have the specified
    xref value and returns all associated bkbit IDs (stored in the 'id' attribute).

    Parameters:
        xref (str): The cross-reference identifier to search for (e.g., "CL:4030043", "NCBITaxon:9823")
        bearer_token (str): The bearer token for authentication
        graph_name (str): The named graph to query (e.g., "https://apitesting.com/")
        timeout (int): Request timeout in seconds. Default is 30.

    Returns:
        List[str]: List of bkbit IDs (URN format) that have the specified xref.
                   Returns an empty list if no matches are found.

    Raises:
        requests.exceptions.HTTPError: If there is an error querying the endpoint
        requests.exceptions.RequestException: For other request-related errors
    """
    # Construct SPARQL query to find all entities with the specified xref
    sparql_query = f"""
    PREFIX biolink: <https://w3id.org/biolink/vocab/>
    PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>

    SELECT ?id WHERE {{
        GRAPH <{graph_name}> {{
            ?id biolink:xref "{xref}"^^xsd:anyURI .
        }}
    }}
    """

    # URL encode the SPARQL query
    encoded_query = quote(sparql_query)

    # Construct the full URL
    url = f"{QUERY_SERVICE_URL}?sparql_query={encoded_query}"

    # Set up headers with bearer token
    headers = {
        "Authorization": f"Bearer {bearer_token}",
        "Accept": "application/json"
    }

    try:
        # Make the request
        response = requests.get(url, headers=headers, timeout=timeout)
        response.raise_for_status()

        # Parse the response
        result = response.json()

        # Extract all bkbit IDs from SPARQL results
        bindings = result.get("results", {}).get("bindings", [])

        # Collect all IDs
        bkbit_ids = []
        for binding in bindings:
            id_value = binding.get("id", {}).get("value")
            if id_value:
                bkbit_ids.append(id_value)

        return bkbit_ids

    except requests.exceptions.HTTPError as e:
        raise requests.exceptions.HTTPError(
            f"Error querying BrainKB for xref = {xref}. Status Code: {e.response.status_code}, Response: {e.response.text}"
        )
    except requests.exceptions.RequestException as e:
        raise requests.exceptions.RequestException(
            f"Error making request to BrainKB SPARQL endpoint: {str(e)}"
        )
