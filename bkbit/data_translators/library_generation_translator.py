import json
from enum import Enum
import os
from multiprocessing import Pool
from tqdm import tqdm
import click
from bkbit.models import library_generation as lg
from bkbit.utils.nimp_api_endpoints import get_data, get_ancestors, get_descendants

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

    def parse_nhash_id_bottom_up(self, nhash_id):
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

    def parse_nhash_id_top_down(self, nhash_id):
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

    @classmethod
    def generate_bican_object(cls, data, was_derived_from: list[str] = None):
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
                assigned_attributes[schema_field_name] = "NIMP:" + str(data.get("id"))
                continue
            if nimp_field_name == "was_derived_from" and was_derived_from is not None:
                if multivalued:
                    assigned_attributes[schema_field_name] = was_derived_from
                else:
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
                # if schema_field_name == "id":
                #     assigned_attributes[schema_field_name] = "NIMP:" + str(data.get("id"))
                # elif multivalued:
                #     assigned_attributes[schema_field_name] = [str(item) for item in data_value]
                # else:
                #     assigned_attributes[schema_field_name] = str(data_value)
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


def __parse_single_nashid(jwt_token, nhash_id, direction, save_to_file=False):
    """
    Parse a single nashid using the SpecimenPortal class.

    Parameters:
    - jwt_token (str): The JWT token for authentication.
    - nhash_id (str): The nashid to parse.
    - direction (str): The direction of parsing. Can be "toDonor" or any other value.
    - save_to_file (bool): Whether to save the parsed data to a file. Default is False.

    Returns:
    - None

    Raises:
    - None
    """
    sp_obj = SpecimenPortal(jwt_token)
    if direction == "toDonor":
        sp_obj.parse_nhash_id_bottom_up(nhash_id)
    else:
        sp_obj.parse_nhash_id_top_down(nhash_id)
    if save_to_file:
        with open(f"{nhash_id}.jsonld", "w") as f:
            f.write(sp_obj.serialize_to_jsonld())
    else:
        print(sp_obj.serialize_to_jsonld())


def __parse_multiple_nashids(jwt_token, file_path, direction):
    """
    Parse multiple nashids from a file.

    Args:
        jwt_token (str): The JWT token.
        file_path (str): The path to the file containing the nashids.
        direction (str): The direction of the parsing.

    Returns:
        list: A list of results from parsing each nashid.

    """
    with open(file_path, "r") as file:
        nhashids = [line.strip() for line in file.readlines()]
    with Pool() as pool:
        results = pool.starmap(
            __parse_single_nashid,
            [(jwt_token, nhash_id, direction, True) for nhash_id in nhashids],
        )
    return results


@click.command()
##ARGUMENTS##
# Argument #1: The nhash id of the record to retrieve.
@click.argument("nhash_id")

##OPTIONS##
# Option #1: The JWT token for authentication to NIMP Portal.
@click.option(
    "--jwt_token",
    "-j",
    required=False,
    default=os.getenv(JWT_TOKEN_OS_VAR_NAME),
    help="The JWT token for authentication to NIMP Portal. Can either provide the JWT token directly or use the environment variable",
)
# Option #2: Which direction to parse the nhash id. Default is bottom-up.
@click.option(
    "--direction",
    "-d",
    type=click.Choice(["toDonor", "toLibraryPool"]),
    default="toDonor",
    help="The direction to parse the NHash ID. Default is toDonor.",
)
def specimenportal2jsonld(nhash_id: str, jwt_token: str, direction: str = "toDonor"):
    """
    Convert the specimen portal data to JSON-LD format.

    Args:
        nhash_id (str): The nhash ID of the specimen.
        jwt_token (str): The JWT token for authentication.
        direction (str, optional): The direction of conversion. Defaults to "toDonor".

    Raises:
        ValueError: If JWT token is missing or empty.

    Returns:
        None
    """
    if not jwt_token or jwt_token == "":
        raise ValueError("JWT token is required")
    if os.path.isfile(nhash_id):
        __parse_multiple_nashids(jwt_token, nhash_id, direction)
    else:
        __parse_single_nashid(jwt_token, nhash_id, direction)


if __name__ == "__main__":
    # example inputs: 'DO-GICE7463','LP-LOMHPL202182'
    specimenportal2jsonld()
