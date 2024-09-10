import inspect
import requests

API_URL_PREFIX = "https://brain-specimenportal.org/api/v1/nhash_ids/"
INFO_URL_SUFFIX = "info?id="
ANCESTORS_URL_SUFFIX = "ancestors?id="
DESCENDANTS_URL_SUFFIX = "descendants?id="
PARENTS_URL_SUFFIX = "parents?id="
NHASH_ONLY_SUFFIX = "&nhash_only="
DONORS_URL_SUFFIX = "donors"


def get_data(nhash_id, jwt_token):
    """
    Retrieve information of any record with a NHash ID in the system.

    Parameters:
        nhash_id (str): The NHash ID of the record to retrieve.
        jwt_token (str): The JWT token for authentication.

    Returns:
        dict: The JSON response containing the information of the record.

    Raises:
        requests.exceptions.HTTPError: If there is an error retrieving the data.

    """
    headers = {"Authorization": f"Bearer {jwt_token}"}
    response = requests.get(
        f"{API_URL_PREFIX}{INFO_URL_SUFFIX}{nhash_id}",
        headers=headers,
        timeout=10,  # ? is this an appropriate timeout value?
    )
    if response.status_code == 200:
        return response.json()

    raise requests.exceptions.HTTPError(
        f"Error getting data for NHash ID = {nhash_id}. Status Code: {response.status_code}"
    )

def get_ancestors(nhash_id, jwt_token, nhash_only=True, depth=None):
    """
    Retrieve information of all ancestors of a record with the given NHash ID.

    Parameters:
        nhash_id (str): The NHash ID of the record.
        jwt_token (str): The JWT token for authentication.
        nhash_only (bool): Flag indicating whether to retrieve only NHash IDs or complete record information. Default is True.
        depth (int): The depth of ancestors to retrieve. Default is 1.

    Returns:
        dict: The JSON response containing information of all ancestors.

    Raises:
        requests.exceptions.HTTPError: If there is an error getting data for the NHash ID.

    """
    headers = {"Authorization": f"Bearer {jwt_token}"}

    response = requests.get(
        f"{API_URL_PREFIX}{ANCESTORS_URL_SUFFIX}{nhash_id}{NHASH_ONLY_SUFFIX}{nhash_only}",
        headers=headers,
        timeout=10,  # This is an appropriate timeout value.
    )
    if response.status_code == 200:
        return response.json()

    raise requests.exceptions.HTTPError(
        f"Error getting data for NHash ID = {nhash_id}. Status Code: {response.status_code}"
    )

def get_descendants(nhash_id, jwt_token, nhash_only=True, depth=None):
    """
    Retrieve information of all descendents of a record with the given NHash ID.

    Parameters:
        nhash_id (str): The NHash ID of the record.
        jwt_token (str): The JWT token for authentication.
        nhash_only (bool): Flag indicating whether to retrieve only NHash IDs or complete record information. Default is True.
        depth (int): The depth of descendents to retrieve. Default is 1.

    Returns:
        dict: The JSON response containing information of all descendents.

    Raises:
        requests.exceptions.HTTPError: If there is an error getting data for the NHash ID.

    """
    headers = {"Authorization": f"Bearer {jwt_token}"}

    response = requests.get(
        f"{API_URL_PREFIX}{DESCENDANTS_URL_SUFFIX}{nhash_id}{NHASH_ONLY_SUFFIX}{nhash_only}",
        headers=headers,
        timeout=30,  # This is an appropriate timeout value.
    )
    if response.status_code == 200:
        return response.json()

    raise requests.exceptions.HTTPError(
        f"Error getting data for NHash ID = {nhash_id}. Status Code: {response.status_code}"
    )

def get_donor(jwt_token, donor_local_id=None, donor_nhash_id=None, age_of_death=None, ethnicity=None, race=None, sex=None, species=None):
    headers = {"Authorization": f"Bearer {jwt_token}"}
    # Create a dictionary of parameters to be sent in the request
    params = {}
    
    # Iterate through the function's parameters and add them to the params dictionary if they are not None
    for param_name in inspect.signature(get_donor).parameters.keys():
        if param_name in ['jwt_token']:  # Skip the non-optional parameters
            continue
        value = locals().get(param_name)
        if value is not None:
            params[param_name] = value
    
    # Make the request with the dynamically created params
    response = requests.get(API_URL_PREFIX + DONORS_URL_SUFFIX, headers=headers, params=params, timeout=10)
    if response.status_code == 200:
        return response.json()
    
    raise requests.exceptions.HTTPError(
        f"Error getting donor data. Status Code: {response.status_code}"
    )