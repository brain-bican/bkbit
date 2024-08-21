import json
from enum import Enum
import requests
from bkbit.models import library_generation_auto as lg

API_URL_PREFIX = "https://brain-specimenportal.org/api/v1/nhash_ids/"
INFO_URL_SUFFIX = "info?id="
ANCESTORS_URL_SUFFIX = "ancestors?id="
DESCENDANTS_URL_SUFFIX = "descendants?id="
PARENTS_URL_SUFFIX = "parents?id="
NHASH_ONLY_SUFFIX = "&nhash_only="


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

class SpecimenPortal:
    def __init__(self, jwt_token):
        self.jwt_token = jwt_token
        self.generated_objects = {}
        self.og_objects = {}
        
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
                    nested_multivalued, nested_annotations = SpecimenPortal.get_field_type(arg, collected_annotations)
                    is_multivalued = is_multivalued or nested_multivalued
                    # Prioritize primitive types in case of Union
                    if selected_type is None or (selected_type not in primitive_types and nested_annotations in primitive_types):
                        selected_type = nested_annotations

            # Check if the original annotation is a List or other multivalued type
            if getattr(annotation, "_name", None) in {"List", "Set", "Tuple"}:
                is_multivalued = True
        else:
            return False, annotation

        return is_multivalued, selected_type

    @staticmethod
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

    @staticmethod
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

    @staticmethod
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
            timeout=10,  # This is an appropriate timeout value.
        )
        if response.status_code == 200:
            return response.json()

        raise requests.exceptions.HTTPError(
            f"Error getting data for NHash ID = {nhash_id}. Status Code: {response.status_code}"
        )
    
    def parse_nhash_id_bottom_up(self, nhash_id):
        # Traverse the nodes all the way to the root (Donor)
        ancestors = SpecimenPortal.get_ancestors(nhash_id, self.jwt_token).get(
            "data", {}
        )
        for curr_nhash_id, curr_value in ancestors.items():
            curr_data = SpecimenPortal.get_data(curr_nhash_id, self.jwt_token).get(
                "data"
            )
            parents = curr_value.get("edges",{}).get("has_parent")
            generated_object = self.generate_bican_object(curr_data, parents)
            if generated_object is not None:
                self.generated_objects[curr_nhash_id] = generated_object
            
    def parse_nhash_id_top_down(self, nhash_id):
        # Traverse the nodes all the way to the leaves (Library Pool)
        descendants = SpecimenPortal.get_descendants(nhash_id, self.jwt_token).get(
            "data"
        )
        for curr_nhash_id in descendants.keys():
            curr_data = SpecimenPortal.get_data(curr_nhash_id, self.jwt_token).get(
                "data"
            )
            ancestors = SpecimenPortal.get_ancestors(curr_nhash_id, self.jwt_token).get(
                "data", {}
            )
            parents = ancestors.get(curr_nhash_id).get("edges",{}).get("has_parent")
            generated_object = self.generate_bican_object(curr_data, parents)
            if generated_object is not None:
                self.generated_objects[curr_nhash_id] = generated_object


    # def parse_nhash_id_og(self, nhash_id):
    #     ancestor_tree = SpecimenPortal.get_ancestors(nhash_id, self.jwt_token).get(
    #         "data"
    #     )
    #     stack = [nhash_id] #! why not just set the stack to data.key()?
    #     while stack:
    #         current_nhash_id = stack.pop()
    #         if current_nhash_id not in self.og_objects:
    #             parents = (
    #                 ancestor_tree.get(current_nhash_id,{}).get("edges",{}).get("has_parent")
    #             )
    #             data = SpecimenPortal.get_data(current_nhash_id, self.jwt_token).get(
    #                 "data"
    #             )
    #             bican_object = self.generate_bican_object(data, parents)
    #             if bican_object is not None:
    #                 self.og_objects[current_nhash_id] = bican_object
    #             if parents is not None:
    #                 stack.extend(parents)

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

        assigned_attributes = {}
        for schema_field_name, schema_field_metadata in bican_class.__fields__.items():
            nimp_field_name = schema_field_metadata.json_schema_extra.get("linkml_meta", {}).get("local_names", {}).get("NIMP", {}).get("local_name_value", schema_field_name)
            multivalued, field_type = SpecimenPortal.get_field_type(schema_field_metadata.annotation)
            required = schema_field_metadata.is_required()
            #! handle multivalued fields
            #! handle was_derived_from
            if nimp_field_name == "id":
                #! might want to check if "id" ia provided otherwise raise error
                assigned_attributes[schema_field_name] = "NIMP:" + str(data.get("id"))
                continue
            data_value = data.get("record", {}).get(nimp_field_name)
            if data_value is None:
                assigned_attributes[schema_field_name] = schema_field_metadata.default
            elif field_type is str:
                if schema_field_name == "id":
                    assigned_attributes[schema_field_name] = "NIMP:" + str(data.get("id"))
                elif multivalued:
                    assigned_attributes[schema_field_name] = [str(item) for item in data_value]
                else:
                    assigned_attributes[schema_field_name] = str(data_value)
            elif field_type is int:
                assigned_attributes[schema_field_name] = int(float(data_value))
            elif field_type is float:
                assigned_attributes[schema_field_name] = float(data_value)
            elif field_type is bool:
                assigned_attributes[schema_field_name] = bool(data_value)
            elif type(field_type) is type(Enum):
                assigned_attributes[schema_field_name] = SpecimenPortal.__check_valueset_membership(field_type, data_value)

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
        self, output_file: str, exclude_none: bool = True, exclude_unset: bool = False
    ):
        """
        Serialize the object and write it to the specified output file.

        Parameters:
            output_file (str): The path of the output file.

        Returns:
            None
        """
        with open(output_file, "w", encoding="utf-8") as f:
            data = []
            for obj in self.generated_objects.values():
                # data.append(obj.to_dict(exclude_none=exclude_none, exclude_unset=exclude_unset))
                data.append(obj.__dict__)
            output_data = {
                "@context": "https://raw.githubusercontent.com/brain-bican/models/main/jsonld-context-autogen/library_generation.context.jsonld",
                "@graph": data,
            }
            f.write(json.dumps(output_data, indent=2))

if __name__ == "__main__":
    temp = SpecimenPortal('eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMTAsImV4cCI6MTcyNDE5NjU2Nn0.Mo-NzIJDXuz6ASABTZa1KUjCth_MM_yPbYxxnpS-DcA')
    temp.parse_nhash_id_bottom_up('LP-LOMHPL202182')
    temp.parse_nhash_id_og('LP-LOMHPL202182')
    print("ARE THEY THE SAME:")
    print(temp.og_objects == temp.generated_objects)
    #temp.parse_nhash_id_top_down('DO-GICE7463')
    #temp.parse_nhash_id_top_down('TI-DPXF326597')
    temp.serialize_to_jsonld("output_temp_aug20.jsonld")