from collections import defaultdict
import csv
import json
from enum import Enum
import typing
import requests
from typing import get_origin, get_args
from bkbit.models import library_generation_auto as lg

BICAN_TO_NIMP_FILE_PATH = "../utils/bican_to_nimp_slots.csv"
API_URL_PREFIX = "https://brain-specimenportal.org/api/v1/nhash_ids/"
INFO_URL_SUFFIX = "info?id="
ANCESTORS_URL_SUFFIX = "ancestors?id="
PARENTS_URL_SUFFIX = "parents?id="
NHASH_ONLY_SUFFIX = "&nhash_only="
# CATEGORY_TO_CLASS = {
#     "librarypool": lg.LibraryPool,
#     "libraryaliquot": lg.LibraryAliquot,
#     "library": lg.Library,
#     "amplifiedcdna": lg.AmplifiedCdna,
#     "barcodedcellsample": lg.BarcodedCellSample,
#     "enrichedcellsample": lg.EnrichedCellSample,
#     "dissociatedcellsample": lg.DissociatedCellSample,
#     "tissue": lg.TissueSample,
#     "donor": lg.Donor,
#     "specimendissectedroi": lg.DissectionRoiPolygon,
#     "slab": lg.BrainSlab,
# }

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
        
    @staticmethod
    def get_field_type(annotation, collected_annotations=None):
 
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





    # def get_field_type(annotation):
    #     primitive_types = {str, int, float, bool}
    #     is_multivalued = False
    #     resolved_type = None

    #     def resolve_to_primitive(arg):
    #         if hasattr(arg, "__args__"):
    #             for nested_arg in arg.__args__:
    #                 primitive = resolve_to_primitive(nested_arg)
    #                 if primitive in primitive_types:
    #                     return primitive
    #         return arg if arg in primitive_types else None

    #     if hasattr(annotation, "__args__"):
    #         for arg in annotation.__args__:
    #             resolved_primitive = resolve_to_primitive(arg)
    #             if resolved_primitive:
    #                 resolved_type = resolved_primitive
    #                 break

    #         # Check if the original annotation is a List, Set, Tuple, or other multivalued type
    #         if getattr(annotation, "_name", None) in {"List", "Set", "Tuple"}:
    #             is_multivalued = True
    #     else:
    #         resolved_type = resolve_to_primitive(annotation)

    #     return is_multivalued, resolved_type


    # def get_field_type(annotation, collected_annotations=None):
    #     if collected_annotations is None:
    #         collected_annotations = set()
        
    #     is_multivalued = False
        
    #     if hasattr(annotation, "__args__"):
    #         arguments = annotation.__args__
    #         for arg in arguments:
    #             if arg != type(None):
    #                 nested_multivalued, nested_annotations = SpecimenPortal.get_field_type(arg, collected_annotations)
    #                 is_multivalued = is_multivalued or nested_multivalued
    #                 collected_annotations.update(nested_annotations)
            
    #         # Check if the original annotation is a List or other multivalued type
    #         if getattr(annotation, "_name", None) in {"List", "Set", "Tuple"}:
    #             is_multivalued = True
    #     else:
    #         collected_annotations.add(annotation)
        
    #     return is_multivalued, collected_annotations

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
    
    def parse_nhash_id(self, nhash_id):
        ancestor_tree = SpecimenPortal.get_ancestors(nhash_id, self.jwt_token).get(
            "data"
        )
        stack = [nhash_id]
        while stack:
            current_nhash_id = stack.pop()
            if current_nhash_id not in self.generated_objects:
                parents = (
                    ancestor_tree.get(current_nhash_id).get("edges").get("has_parent")
                )
                data = SpecimenPortal.get_data(current_nhash_id, self.jwt_token).get(
                    "data"
                )
                bican_object = self.generate_bican_object(data, parents)
                if bican_object is not None:
                    self.generated_objects[current_nhash_id] = bican_object
                if parents is not None:
                    stack.extend(parents)


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
            data_value = data.get("record", {}).get(nimp_field_name) #! Check if accesses the correct info
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
            else:
                #print(f"VALUE NOT SET: id={data.get('id')}, field={schema_field_name}, value={data_value}")
                pass

            #! check if the field is required; if missing raise an error
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
    temp = SpecimenPortal('eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMTAsImV4cCI6MTcyNDE1MjY5OX0.GIelY0ZUjYCz1w8OjCwMIPgwiYy1GrQAYrMIVynjCjY')
    #temp.parse_nhash_id('LP-LOMHPL202182')
    temp.parse_nhash_id('DO-GICE7463')
    #temp.parse_nhash_id('TI-DPXF326597')
    temp.serialize_to_jsonld("output_temp_aug19.jsonld")


        # if "List" in bican_class.__annotations__["was_derived_from"]:
        #     bican_object.was_derived_from = [
        #         f"NIMP:{item}" for item in was_derived_from
        #     ]
        # else:
        #     bican_object.was_derived_from = (
        #         f"NIMP:{was_derived_from[0]}" if was_derived_from else None
        #     )
        # class_attributes = SpecimenPortal.bican_slots_per_class.get(bican_category)
        # if class_attributes is not None:
        #     for attribute in class_attributes:
        #         if (
        #             bican_category + "_" + attribute
        #         ) in SpecimenPortal.bican_to_nimp_attribute_mapping:
        #             bican_attribute_type = bican_class.__annotations__[attribute]
        #             value = data.get("record").get(
        #                 SpecimenPortal.bican_to_nimp_attribute_mapping[
        #                     bican_category + "_" + attribute
        #                 ]
        #             )
        #             if value is not None and type(value) != bican_attribute_type:
        #                 if (
        #                     "AmplifiedCdnaRnaAmplificationPassFail"
        #                     in bican_attribute_type
        #                 ):
        #                     value = SpecimenPortal.__check_valueset_membership(
        #                         "AmplifiedCdnaRnaAmplificationPassFail", value
        #                     ) 
        #                 elif "BarcodedCellSampleTechnique" in bican_attribute_type:
        #                     value = SpecimenPortal.__check_valueset_membership(
        #                         "BarcodedCellSampleTechnique", value
        #                     )
        #                 elif (
        #                     "DissociatedCellSampleCellPrepType" in bican_attribute_type
        #                 ):
        #                     value = SpecimenPortal.__check_valueset_membership(
        #                         "DissociatedCellSampleCellPrepType", value
        #                     )
        #                 elif (
        #                     "DissociatedCellSampleCellLabelBarcode"
        #                     in bican_attribute_type
        #                 ):
        #                     value = SpecimenPortal.__check_valueset_membership(
        #                         "DissociatedCellSampleCellLabelBarcode", value
        #                     )
        #                 elif "LibraryTechnique" in bican_attribute_type:
        #                     value = SpecimenPortal.__check_valueset_membership(
        #                         "LibraryTechnique", value
        #                     )
        #                 elif "LibraryPrepPassFail" in bican_attribute_type:
        #                     value = SpecimenPortal.__check_valueset_membership(
        #                         "LibraryPrepPassFail", value
        #                     )
        #                 elif "LibraryR1R2Index" in bican_attribute_type:
        #                     value = SpecimenPortal.__check_valueset_membership(
        #                         "LibraryR1R2Index", value
        #                     )
        #                 elif "Sex" in bican_attribute_type:
        #                     value = SpecimenPortal.__check_valueset_membership(
        #                         "Sex", value
        #                     )
        #                 elif "AgeAtDeathReferencePoint" in bican_attribute_type:
        #                     value = SpecimenPortal.__check_valueset_membership(
        #                         "AgeAtDeathReferencePoint", value
        #                     )
        #                 elif "AgeAtDeathUnit" in bican_attribute_type:
        #                     value = SpecimenPortal.__check_valueset_membership(
        #                         "AgeAtDeathUnit", value
        #                     )
        #                 elif "str" in bican_attribute_type:
        #                     if "List" in bican_attribute_type:
        #                         pass
        #                     else:
        #                         value = str(value)
        #                 elif "int" in bican_attribute_type:
        #                     value = int(float(value))
        #                 elif "float" in bican_attribute_type:
        #                     value = float(value)
        #                 elif "bool" in bican_attribute_type:
        #                     value = bool(value)
        #                 else:
        #                     value = None
        #             bican_object.__setattr__(attribute, value)
        # return bican_object

#     @staticmethod
#     def __check_valueset_membership(enum_name, nimp_value):
#         """
#         Check if the given value belongs to the specified enum.

#         Parameters:
#             enum_name (str): The name of the enum to check.
#             nimp_value: The value to check for membership in the enum.

#         Returns:
#             The enum member if the value belongs to the enum, None otherwise.
#         """
#         enum = lg.__dict__.get(enum_name)
#         if enum is not None:
#             valueset = {m.value: m for m in enum}
#             return valueset.get(nimp_value)
#         return None



#     def serialize_to_jsonld(
#         self, output_file: str, exclude_none: bool = True, exclude_unset: bool = False
#     ):
#         """
#         Serialize the object and write it to the specified output file.

#         Parameters:
#             output_file (str): The path of the output file.

#         Returns:
#             None
#         """
#         with open(output_file, "w", encoding="utf-8") as f:
#             data = []
#             for obj in self.generated_objects.values():
#                 # data.append(obj.to_dict(exclude_none=exclude_none, exclude_unset=exclude_unset))
#                 data.append(obj.__dict__)
#             output_data = {
#                 "@context": "https://raw.githubusercontent.com/brain-bican/models/main/jsonld-context-autogen/library_generation.context.jsonld",
#                 "@graph": data,
#             }
#             f.write(json.dumps(output_data, indent=2))


# if __name__ == "__main__":
#     print(get_types_helper(lg.BrainSlab.__fields__['was_derived_from'].annotation))   
#     print(get_types_helper(lg.Donor.__fields__['age_at_death_unit'].annotation))
#     print(get_types_helper(lg.Donor.__fields__['in_taxon'].annotation))

# if __name__ == "__main__":
#     get_types_helper(lg.BrainSlab.__fields__['was_derived_from'].annotation)
    ## EXAMPLE #1 ##
    # sp = SpecimenPortal(
    #     "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMTAsImV4cCI6MTcxNTc1NzUzN30.2CsWyCHwtOAd4NnOUMinhgtTk86z0ydh0T5__rfh824"
    # )
    # sp.parse_nhash_id('AC-ATDJAH472237')

    ## EXAMPLE #2 ##
    # token = "eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMTAsImV4cCI6MTcxNTc1NzUzN30.2CsWyCHwtOAd4NnOUMinhgtTk86z0ydh0T5__rfh824"
    # sp = SpecimenPortal(
    #     token
    # )
    # LIMIT = 10
    # with open("example_library_pool_data.csv", "r", encoding="utf-8") as file:
    #     reader = csv.DictReader(file)
    #     row_number = 1
    #     for row in reader:
    #         print(f'Processing LP: {row["NHash ID"]}')
    #         sp.parse_nhash_id(row["NHash ID"])
    #         sp.serialize_to_jsonld("output_" + row["NHash ID"] + ".jsonld")
    #         if row_number == LIMIT:
    #             break
    #         row_number += 1