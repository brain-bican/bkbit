"""
Module for parsing and processing specimen data using BICAN models and NIMP API endpoints. This module provides functionality to:

1. Parse nhash IDs for specimens from the NIMP API, either in a top-down (descendants) or bottom-up (ancestors) fashion.
2. Generate BICAN objects based on the parsed specimen data.
3. Serialize the extracted information into JSON-LD format for further use.
4. Check if values belong to a specific enumeration set.

Classes:
    SpecimenPortal: A class responsible for handling the parsing and generation of BICAN objects for specimen data.

Functions:
    get_field_type: Determines if an annotation is multivalued and returns the field type.
    generate_bican_object: Generates a BICAN object based on the provided data and parent relationships.
    parse_nhash_id_bottom_up: Parses ancestors of the provided nhash ID, generating BICAN objects.
    parse_nhash_id_top_down: Parses descendants of the provided nhash ID, generating BICAN objects.
    serialize_to_jsonld: Serializes the generated BICAN objects into JSON-LD format.
    specimen2jsonld: Command-line function for parsing nhash IDs and serializing the result into JSON-LD format.

Usage:
    The module can be run as a standalone script using the command-line interface with the appropriate arguments and options:

    ```
    python specimen_portal.py <nhash_id> [-d]
    ```

    This script will parse the nhash ID and serialize the generated data into JSON-LD format, with the option to parse descendants or ancestors.

Example:
    ```
    python specimen_portal.py "DO-GICE7463" -d
    ```

    This will parse the descendants of the specimen identified by the nhash ID and save the result as a JSON-LD file.

Dependencies:
    - json
    - os
    - click
    - tqdm
    - multiprocessing.Pool
    - bkbit.models.library_generation
    - bkbit.utils.nimp_api_endpoints (get_data, get_ancestors, get_descendants)
"""

import json
from enum import Enum
import os
from multiprocessing import Pool
from tqdm import tqdm
import click
from bkbit.models import library_generation as lg
from bkbit.utils.nimp_api_endpoints import get_data, get_ancestors, get_descendants
from bkbit.utils.generate_bkbit_id import generate_object_id

CATEGORY_TO_CLASS = {
    "Library Pool": lg.LibraryPool,
    "Library Aliquot": lg.LibraryAliquot,
    "Library": lg.Library,
    "Amplified cDNA": lg.AmplifiedCdna,
    "Barcoded Cell Sample": lg.BarcodedCellSample,
    "Enriched Cell Sample": lg.EnrichedCellSample,
    "Dissociated Cell Sample": lg.DissociatedCellSample,
    "Tissue": lg.TissueSample,
    "Donor": lg.Donor,
    "Specimen Dissected ROI": lg.DissectionRoiPolygon,
    "Slab": lg.BrainSlab,
}
JWT_TOKEN_OS_VAR_NAME = "jwt_token"
CONTEXT = "https://raw.githubusercontent.com/brain-bican/models/main/jsonld-context-autogen/library_generation.context.jsonld"


class SpecimenPortal:
    """
    The SpecimenPortal class is responsible for parsing and generating BICAN objects for specimen data
    by traversing through nodes (ancestors or descendants) based on nhash IDs. It provides utilities to
    recursively parse node relationships and convert the data into a JSON-LD format.

    Attributes:
        jwt_token (str): The authentication token used to access the specimen data.
        generated_objects (dict): A dictionary that stores generated BICAN objects, keyed by nhash IDs.

    Methods:
        get_field_type(annotation, collected_annotations=None):
            Static method that determines whether a field is multivalued and returns the type of the field.

        parse_nhash_id_bottom_up(nhash_id):
            Parses ancestors of the provided nhash_id, starting from the node and moving upwards to the root (Donor).

        parse_nhash_id_top_down(nhash_id):
            Parses descendants of the provided nhash_id, starting from the node and moving downwards to the leaves (Library Pool).

        generate_bican_object(data, was_derived_from=None):
            Generates a BICAN object based on the provided data and parent relationships.

        serialize_to_jsonld(exclude_none=True, exclude_unset=False):
            Serializes the generated objects into JSON-LD format for further use or storage.

        parse_single_nashid(jwt_token, nhash_id, descendants, save_to_file=False):
            Parses a single nhash ID and optionally saves the result to a JSON-LD file.

        parse_multiple_nashids(jwt_token, file_path, descendants):
            Parses multiple nhash IDs from a file and saves the results to JSON-LD files.

    Static Methods:
        __check_valueset_membership(enum_type, nimp_value):
            Checks if a given value belongs to a specified enum.
    """
    def __init__(self, jwt_token):
        self.jwt_token = jwt_token
        self.generated_objects = {}

    @staticmethod
    def get_field_type(annotation, collected_annotations=None):
        """
        Determines the field type based on the provided annotation.

        Args:
            annotation: The annotation to determine the field type for.
            collected_annotations: A dictionary to collect annotations encountered during recursion.

        Returns:
            A tuple containing a boolean indicating if the field is multivalued and the selected field type.
        """
        is_multivalued = False
        primitive_types = {str, int, float, bool}
        selected_type = None

        if hasattr(annotation, "__args__"):
            arguments = annotation.__args__
            for arg in arguments:
                if arg != type(None):
                    nested_multivalued, nested_annotations = (
                        SpecimenPortal.get_field_type(arg, collected_annotations)
                    )
                    is_multivalued = is_multivalued or nested_multivalued
                    # Prioritize primitive types in case of Union
                    if selected_type is None or (
                        selected_type not in primitive_types
                        and nested_annotations in primitive_types
                    ):
                        selected_type = nested_annotations

            # Check if the original annotation is a List or other multivalued type
            if getattr(annotation, "_name", None) in {"List", "Set", "Tuple"}:
                is_multivalued = True
        else:
            return False, annotation

        return is_multivalued, selected_type

    def parse_nhash_id_bottom_up(self, nhash_id: str):
        """
        Parses the given nhash_id from bottom to top, retrieving ancestors and generating respective BICAN objects.

        Args:
            nhash_id (str): The nhash_id to parse.

        Returns:
            None: If there is an error retrieving ancestors or generating objects.

        Raises:
            ValueError: If there is an error retrieving ancestors or generating objects.

        """
        # Traverse the nodes all the way to the root (Donor)
        try:
            ancestors = get_ancestors(nhash_id, self.jwt_token)
            if "error" in ancestors:
                raise ValueError(ancestors["error"])
        except ValueError as e:
            print(f"ValueError retrieving ancestors for '{nhash_id}': {e}")
            return
        except Exception as e:
            print(f"Unexpected error retrieving ancestors for '{nhash_id}': {e}")
            return
        for curr_nhash_id, curr_value in tqdm(
            ancestors.get("data", {}).items(),
            desc="Processing ancestors and generating respective BICAN objects for NHash ID: "
            + nhash_id,
            unit="ancestor",
        ):
            try:
                curr_data = get_data(curr_nhash_id, self.jwt_token).get("data")
                parents = curr_value.get("edges", {}).get("has_parent")
                generated_object = self.generate_bican_object(curr_data, parents)
                if generated_object is not None:
                    self.generated_objects[curr_nhash_id] = generated_object
            except ValueError as e:
                print(f"ValueError generating object for '{curr_nhash_id}': {e}")
                continue
            except Exception as e:
                print(f"Unexpected error generating object for '{curr_nhash_id}': {e}")
                continue
        for obj in self.generated_objects.values():
            if hasattr(obj, "was_derived_from") and obj.was_derived_from is not None:
                if type(obj.was_derived_from) is str:
                    if obj.was_derived_from not in self.generated_objects:
                        obj.was_derived_from = None
                    else:
                        obj.was_derived_from = self.generated_objects[obj.was_derived_from].id
                else:    
                    updated_parents = []
                    for parent in obj.was_derived_from:
                        if parent in self.generated_objects:
                            updated_parents.append(self.generated_objects[parent].id)
                    obj.was_derived_from = updated_parents

    def parse_nhash_id_top_down(self, nhash_id: str):
        """
        Parses the given nhash_id in a top-down manner, traversing the nodes all the way to the leaves (Library Pool).

        Args:
            nhash_id (str): The nhash_id to be parsed.

        Returns:
            None: If an error occurs while retrieving descendants or generating objects.

        Raises:
            ValueError: If an error occurs while retrieving descendants.
            Exception: If an unexpected error occurs while retrieving descendants or generating objects.
        """
        # Traverse the nodes all the way to the leaves (Library Pool)
        try:
            descendants = get_descendants(nhash_id, self.jwt_token)
            if "error" in descendants:
                raise ValueError(descendants["error"])
        except ValueError as e:
            print(f"ValueError retrieving descendants for '{nhash_id}': {e}")
            return
        except Exception as e:
            print(f"Unexpected error retrieving descendants for '{nhash_id}': {e}")
            return
        for curr_nhash_id in tqdm(
            descendants.get("data", {}).keys(),
            desc="Processing descendants and generating respective BICAN objects for NHash ID: "
            + nhash_id,
            unit="descendant",
        ):
            try:
                curr_data = get_data(curr_nhash_id, self.jwt_token).get("data")
                ancestors = get_ancestors(curr_nhash_id, self.jwt_token).get("data", {})
                parents = (
                    ancestors.get(curr_nhash_id).get("edges", {}).get("has_parent")
                )
                generated_object = self.generate_bican_object(curr_data, parents)
                if generated_object is not None:
                    self.generated_objects[curr_nhash_id] = generated_object
            except ValueError as e:
                print(f"ValueError generating object for '{curr_nhash_id}': {e}")
                continue
            except Exception as e:
                print(f"Unexpected error generating object for '{curr_nhash_id}': {e}")
                continue

    #@classmethod
    def generate_bican_object(self, data, was_derived_from: list[str] = None):
        """
        Generate a Bican object based on the provided data.

        Parameters:
            data (dict): The data retrieved from the NIMP portal.
            was_derived_from (list): A list of parent NHash IDs.

        Returns:
            The generated Bican object.

        Raises:
            None.

        """
        category = data.get("category")
        bican_class = CATEGORY_TO_CLASS.get(category)
        if bican_class is None:
            raise ValueError(f"Unsupported category: {category}.")

        assigned_attributes = {}
        for schema_field_name, schema_field_metadata in bican_class.__fields__.items():
            nimp_field_name = (
                schema_field_metadata.json_schema_extra.get("linkml_meta", {})
                .get("local_names", {})
                .get("NIMP", {})
                .get("local_name_value", schema_field_name)
            )
            multivalued, field_type = SpecimenPortal.get_field_type(
                schema_field_metadata.annotation
            )
            required = schema_field_metadata.is_required()
            #! handle multivalued fields
            if nimp_field_name == "id":
                #! might want to check if "id" is provided otherwise raise error
                if assigned_attributes.get(schema_field_name) is not None:
                    assigned_attributes[schema_field_name].append("NIMP:" + str(data.get("id")))
                else:
                    assigned_attributes[schema_field_name] = ["NIMP:" + str(data.get("id"))]
                continue
            if nimp_field_name == "was_derived_from" and was_derived_from is not None:
                if multivalued:
                    # Prefix each string with "NIMP:" and assign the list
                    assigned_attributes[schema_field_name] = [value for value in was_derived_from]
                else:
                    # Prefix the single string with "NIMP:" and assign it
                    assigned_attributes[schema_field_name] = was_derived_from[0]
                continue
            data_value = data.get("record", {}).get(nimp_field_name)
            if data_value is None:
                assigned_attributes[schema_field_name] = schema_field_metadata.default
            elif field_type is str:
                if multivalued:
                    assigned_attributes[schema_field_name] = [
                        str(item) for item in data_value
                    ]
                else:
                    assigned_attributes[schema_field_name] = str(data_value)
            elif field_type is int:
                assigned_attributes[schema_field_name] = int(float(data_value))
            elif field_type is float:
                assigned_attributes[schema_field_name] = float(data_value)
            elif field_type is bool:
                assigned_attributes[schema_field_name] = bool(data_value)
            elif type(field_type) is type(Enum):
                assigned_attributes[schema_field_name] = (
                    SpecimenPortal.__check_valueset_membership(field_type, data_value)
                )

            # check if the field is required; if missing raise an error
            if assigned_attributes[schema_field_name] is None and required:
                raise ValueError(f"Missing required field: {schema_field_name}")
        assigned_attributes["id"] = generate_object_id(assigned_attributes)
        return bican_class(**assigned_attributes)

    @staticmethod
    def __check_valueset_membership(enum_type, nimp_value):
        """
        Check if the given value belongs to the specified enum.

        Parameters:
            enum_type(Enum): The enum class
            nimp_value: The value to check for membership in the enum.

        Returns:
            The enum member if the value belongs to the enum, None otherwise.
        """
        for member in enum_type:
            if member.value == nimp_value:
                return member
        return None

    def serialize_to_jsonld(
        self, exclude_none: bool = True, exclude_unset: bool = False
    ):
        """
        Serialize the object and write it to the specified output file.

        Parameters:
            output_file (str): The path of the output file.

        Returns:
            None
        """

        data = []
        for obj in self.generated_objects.values():
            # data.append(obj.to_dict(exclude_none=exclude_none, exclude_unset=exclude_unset))
            data.append(obj.__dict__)
        output_data = {
            "@context": CONTEXT,
            "@graph": data,
        }
        return json.dumps(output_data, indent=2)


def parse_single_nashid(jwt_token, nhash_id, descendants, save_to_file=False):
    """
    Parse a single nashid using the SpecimenPortal class.

    Parameters:
    - jwt_token (str): The JWT token for authentication.
    - nhash_id (str): The nashid to parse.
    - descendants (bool): The direction of parsing. True for descendants, False for ancestors.
    - save_to_file (bool): Whether to save the parsed data to a file. Default is False.

    Returns:
    - None

    Raises:
    - None
    """
    sp_obj = SpecimenPortal(jwt_token)
    if descendants == False:
        sp_obj.parse_nhash_id_bottom_up(nhash_id)
    else:
        sp_obj.parse_nhash_id_top_down(nhash_id)
    if save_to_file:
        with open(f"{nhash_id}.jsonld", "w") as f:
            f.write(sp_obj.serialize_to_jsonld())
    else:
        print(sp_obj.serialize_to_jsonld())


def parse_multiple_nashids(jwt_token, file_path, descendants):
    """
    Parse multiple nashids from a file.

    Args:
        jwt_token (str): The JWT token.
        file_path (str): The path to the file containing the nashids.
        descendants (bool): The direction of parsing. True for descendants, False for ancestors.

    Returns:
        list: A list of results from parsing each nashid.

    """
    with open(file_path, "r") as file:
        nhashids = [line.strip() for line in file.readlines()]
    with Pool() as pool:
        results = pool.starmap(
            parse_single_nashid,
            [(jwt_token, nhash_id, descendants, True) for nhash_id in nhashids],
        )
    return results


@click.command()
##ARGUMENTS##
# Argument #1: The nhash id of the record to retrieve.
@click.argument("nhash_id")

##OPTIONS##
# Option #1: Which direction to parse the nhash id. Default is ancestors.
@click.option('--descendants', '-d', is_flag=True, help='Parse the given nhash_id and all of its children down to Library Pool.')

def specimen2jsonld(nhash_id: str, descendants: bool):
    """
    Convert the specimen portal data to JSON-LD format.

    Args:
        nhash_id (str): The nhash ID of the specimen.
        descendants (bool): Which direction to parse the nhash id. Default is ancestors.

    Raises:
        ValueError: If JWT token is missing or empty.

    Returns:
        None
    """
    jwt_token = os.getenv(JWT_TOKEN_OS_VAR_NAME)
    if not jwt_token or jwt_token == "":
        raise ValueError("JWT token is required")
    if os.path.isfile(nhash_id):
        parse_multiple_nashids(jwt_token, nhash_id, descendants)
    else:
        parse_single_nashid(jwt_token, nhash_id, descendants)


if __name__ == "__main__":
    # example inputs: 'DO-GICE7463','LP-LOMHPL202182'
    specimen2jsonld()
