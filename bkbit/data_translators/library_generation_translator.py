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
    - bkbit.models.donor
    - bkbit.utils.nimp_api_endpoints (get_data, get_ancestors, get_descendants)
"""

import json
from enum import Enum
from functools import lru_cache
import inspect
from typing import get_origin
import os
from multiprocessing import Pool
from tqdm import tqdm
import click
from linkml_runtime.dumpers import json_dumper
from bkbit.models import library_generation as lg
from bkbit.models import donor
from bkbit.utils.nimp_api_endpoints import get_data, get_ancestors, get_descendants
from bkbit.utils.generate_bkbit_id import generate_object_id
from bkbit.utils.serialize_to_ttl import convert_jsonld_to_ttl


CATEGORY_TO_CLASS = {
    "Library Pool": lg.LibraryPool,
    "Library Aliquot": lg.LibraryAliquot,
    "Library": lg.Library,
    "Amplified cDNA": lg.AmplifiedCdna,
    "Barcoded Cell Sample": lg.BarcodedCellSample,
    "Enriched Cell Sample": lg.EnrichedCellSample,
    "Dissociated Cell Sample": lg.DissociatedCellSample,
    "Tissue": lg.TissueSample,
    # Donor is defined in its own model; library_generation only keeps a stub of it
    "Donor": donor.Donor,
    "ROI": lg.DissectionRoiPolygon,
    "Slab": lg.BrainSlab,
}


def _normalize_resource_type(resource_type):
    """NIMP resource types are spelled both "Library Aliquot" and "LibraryAliquot"."""
    return resource_type.replace(" ", "").casefold()


@lru_cache(maxsize=None)
def derived_classes(category):
    """
    Classes with no NIMP record of their own whose slots declare (via
    NIMP_resource_type) that their values come from a record of `category`,
    e.g. DigitalAsset.content_url <- Library Aliquot.nemo_aliquot_fastq_public_url.

    Returns:
        A tuple of (class, {slot name: NIMP field name}) pairs.
    """
    wanted = _normalize_resource_type(category)
    nimp_classes = set(CATEGORY_TO_CLASS.values())
    found = []
    for module in (lg, donor):
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__ or cls in nimp_classes:
                continue
            if not hasattr(cls, "model_fields"):
                continue
            slots = {}
            for slot_name, field in cls.model_fields.items():
                local_names = (field.json_schema_extra or {}).get(
                    "linkml_meta", {}
                ).get("local_names", {})
                resource_type = local_names.get("NIMP_resource_type", {}).get(
                    "local_name_value"
                )
                variable_name = local_names.get("NIMP_variable_name", {}).get(
                    "local_name_value"
                )
                if resource_type and variable_name and (
                    _normalize_resource_type(resource_type) == wanted
                ):
                    slots[slot_name] = variable_name
            if slots:
                found.append((cls, slots))
    return tuple(found)


JWT_TOKEN_OS_VAR_NAME = "jwt_token"
NIMP_PREFIX = "NIMP:"
CONTEXT = [
    "https://raw.githubusercontent.com/brain-bican/models/main/jsonld-context-autogen/library_generation.context.jsonld",
    "https://raw.githubusercontent.com/brain-bican/models/main/jsonld-context-autogen/donor.context.jsonld",
]


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

        resolve_parent_references():
            Replaces parent NHash IDs in was_derived_from with the generated parents' ids.

        generate_bican_object(data, was_derived_from=None):
            Generates a BICAN object based on the provided data and parent relationships.

        generate_derived_objects(data, nhash_id):
            Generates the objects NIMP has no record for (e.g. DigitalAsset) from the record they derive from.

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
            # (typing.List as well as builtin list[...], which the models now use)
            if get_origin(annotation) in {list, set, tuple}:
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
                    self.generated_objects.update(
                        self.generate_derived_objects(curr_data, curr_nhash_id)
                    )
            except ValueError as e:
                print(f"ValueError generating object for '{curr_nhash_id}': {e}")
                continue
            except Exception as e:
                print(f"Unexpected error generating object for '{curr_nhash_id}': {e}")
                continue
        self.resolve_parent_references()

    def resolve_parent_references(self):
        """
        Replace the parent NHash IDs in was_derived_from with the ids of the
        generated parent objects, so the output never references raw NIMP IDs.

        A parent that was not generated in this run (e.g. the parent of the
        starting node when parsing descendants) has no object to point to and
        is dropped.
        """
        for obj in self.generated_objects.values():
            if getattr(obj, "was_derived_from", None) is None:
                continue
            if isinstance(obj.was_derived_from, str):
                parent = self.generated_objects.get(obj.was_derived_from)
                obj.was_derived_from = parent.id if parent is not None else None
            else:
                updated_parents = [
                    self.generated_objects[parent].id
                    for parent in obj.was_derived_from
                    if parent in self.generated_objects
                ]
                obj.was_derived_from = updated_parents or None

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
                    self.generated_objects.update(
                        self.generate_derived_objects(curr_data, curr_nhash_id)
                    )
            except ValueError as e:
                print(f"ValueError generating object for '{curr_nhash_id}': {e}")
                continue
            except Exception as e:
                print(f"Unexpected error generating object for '{curr_nhash_id}': {e}")
                continue
        self.resolve_parent_references()

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
            local_names = schema_field_metadata.json_schema_extra.get(
                "linkml_meta", {}
            ).get("local_names", {})
            # Models declare the NIMP field under NIMP_variable_name; older ones used NIMP
            nimp_field_name = (
                local_names.get("NIMP_variable_name")
                or local_names.get("NIMP")
                or {}
            ).get("local_name_value", schema_field_name)
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
            assigned_attributes[schema_field_name] = SpecimenPortal.convert_value(
                schema_field_metadata, data_value
            )
            # xref holds NIMP NHash IDs; write them as NIMP: CURIEs
            if schema_field_name == "xref" and assigned_attributes[schema_field_name]:
                assigned_attributes[schema_field_name] = [
                    value if value.startswith(NIMP_PREFIX) else NIMP_PREFIX + value
                    for value in assigned_attributes[schema_field_name]
                ]

            # check if the field is required; if missing raise an error
            if assigned_attributes[schema_field_name] is None and required:
                raise ValueError(f"Missing required field: {schema_field_name}")
        assigned_attributes["id"] = generate_object_id(assigned_attributes)
        return bican_class(**assigned_attributes)

    def generate_derived_objects(self, data, nhash_id):
        """
        Generate the objects that NIMP has no record for but that the model
        declares are filled from this record (see `derived_classes`).

        An object is only generated if at least one of its declared values is
        present, so an aliquot without a FASTQ URL yields no DigitalAsset.

        Parameters:
            data (dict): The NIMP record the values are read from.
            nhash_id (str): NHash ID of that record; recorded as was_derived_from.

        Returns:
            A dict of the generated objects, keyed "<nhash_id>/<class name>".
        """
        derived = {}
        record = data.get("record", {})
        for bican_class, slots in derived_classes(data.get("category")):
            assigned_attributes = {
                slot_name: SpecimenPortal.convert_value(
                    bican_class.model_fields[slot_name], record.get(nimp_field_name)
                )
                for slot_name, nimp_field_name in slots.items()
            }
            if all(value is None for value in assigned_attributes.values()):
                continue
            if "was_derived_from" in bican_class.model_fields:
                assigned_attributes["was_derived_from"] = nhash_id
            assigned_attributes["id"] = generate_object_id(assigned_attributes)
            derived[f"{nhash_id}/{bican_class.__name__}"] = bican_class(
                **assigned_attributes
            )
        return derived

    @staticmethod
    def convert_value(field_metadata, data_value):
        """
        Convert a NIMP value to the type of the given model field.

        Parameters:
            field_metadata (FieldInfo): The pydantic field the value is for.
            data_value: The value from the NIMP record.

        Returns:
            The converted value, or the field's default if the value is missing.
        """
        multivalued, field_type = SpecimenPortal.get_field_type(
            field_metadata.annotation
        )
        # NIMP may return a single value for a multivalued slot (e.g. Donor.xref)
        if multivalued and data_value is not None and not isinstance(data_value, list):
            data_value = [data_value]
        if data_value is None:
            return field_metadata.default
        if field_type is str:
            if multivalued:
                return [str(item) for item in data_value]
            return str(data_value)
        if field_type is int:
            return int(float(data_value))
        if field_type is float:
            return float(data_value)
        if field_type is bool:
            return bool(data_value)
        if type(field_type) is type(Enum):
            return SpecimenPortal.__check_valueset_membership(field_type, data_value)
        return None

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
        # NIMP capitalises some values the model keeps lowercase (e.g. sex "Female" vs "female")
        if isinstance(nimp_value, str):
            for member in enum_type:
                if isinstance(member.value, str) and member.value.casefold() == nimp_value.casefold():
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
            data.append(json.loads(json_dumper.dumps(obj)))
        output_data = {
            "@context": CONTEXT,
            "@graph": data,
        }
        return json.dumps(output_data, indent=2)


def parse_single_nashid(jwt_token, nhash_id, descendants, output_format, save_to_file=False):
    """

    Parameters:
    - jwt_token (str): The JWT token for authentication.
    - nhash_id (str): The nashid to parse.
    - descendants (bool): The direction of parsing. True for descendants, False for ancestors.
    - output_format (str): The output format. Either "jsonld" or "turtle".
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
    jsonld_output = sp_obj.serialize_to_jsonld()
    if output_format == "jsonld":
        if save_to_file:
            with open(f"{nhash_id}.jsonld", "w") as f:
                f.write(jsonld_output)
        else:
            print(jsonld_output)
    elif output_format == "turtle":
        turtle_output = convert_jsonld_to_ttl(jsonld_output)
        if save_to_file:
            with open(f"{nhash_id}.ttl", "w") as f:
                f.write(turtle_output)
        else:
            print(turtle_output)

def parse_multiple_nashids(jwt_token, file_path, descendants, output_format):
    """
    Parse multiple nashids from a file.

    Args:
        jwt_token (str): The JWT token.
        file_path (str): The path to the file containing the nashids.
        descendants (bool): The direction of parsing. True for descendants, False for ancestors.
        output_format (str): The output format. Either "jsonld" or "turtle".

    Returns:
        list: A list of results from parsing each nashid.

    """
    with open(file_path, "r") as file:
        nhashids = [line.strip() for line in file.readlines()]
    with Pool() as pool:
        results = pool.starmap(
            parse_single_nashid,
            [(jwt_token, nhash_id, descendants, output_format, True) for nhash_id in nhashids],
        )
    return results


@click.command()
##ARGUMENTS##
# Argument #1: The nhash id of the record to retrieve.
@click.argument("nhash_id")

##OPTIONS##
# Option #1: Which direction to parse the nhash id. Default is ancestors.
@click.option('--descendants', '-d', is_flag=True, help='Parse the given nhash_id and all of its children down to Library Pool.')

# Option #2: Output format: jsonld or turtle
@click.option(
    "--output_format",
    "-o",
    required=False,
    type=click.Choice(["jsonld", "turtle"]),
    default="jsonld",
    show_default=True,
    help="The output format.",
)
def specimen2jsonld(nhash_id: str, descendants: bool, output_format: str):
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
        parse_multiple_nashids(jwt_token, nhash_id, descendants, output_format)
    else:
        parse_single_nashid(jwt_token, nhash_id, descendants, output_format)


if __name__ == "__main__":
    # example inputs: 'DO-GICE7463','LP-LOMHPL202182'
    specimen2jsonld()
