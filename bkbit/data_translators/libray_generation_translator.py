from collections import defaultdict
import csv
import json
import requests
from bkbit.models import library_generation as lg

BICAN_TO_NIMP_FILE_PATH = "../utils/bican_to_nimp_slots.csv"
API_URL_PREFIX = "https://brain-specimenportal.org/api/v1/nhash_ids/"
INFO_URL_SUFFIX = "info?id="
ANCESTORS_URL_SUFFIX = "ancestors?id="
PARENTS_URL_SUFFIX = "parents?id="
NHASH_ONLY_SUFFIX = "&nhash_only="
CATEGORY_TO_CLASS = {
    "librarypool": lg.LibraryPool,
    "libraryaliquot": lg.LibraryAliquot,
    "library": lg.Library,
    "amplifiedcdna": lg.AmplifiedCdna,
    "barcodedcellsample": lg.BarcodedCellSample,
    "enrichedcellsample": lg.EnrichedCellSample,
    "dissociatedcellsample": lg.DissociatedCellSample,
    "tissue": lg.TissueSample,
    "donor": lg.Donor,
    "specimendissectedroi": lg.DissectionRoiPolygon,
    "slab": lg.BrainSlab,
}


class SpecimenPortal:
    @staticmethod
    def create_bican_to_nimp_mapping(csv_file):
        """
        Creates a mapping dictionary from a CSV file, where the keys are 'LinkML Slot or Attribute Name'
        and the values are 'NIMP Variable Name'.

        Parameters:
            csv_file (str): The path to the CSV file.

        Returns:
            dict: A dictionary mapping 'LinkML Slot or Attribute Name' to 'NIMP Variable Name'.

        """
        bican_to_nimp_attribute_mapping = {}
        nimp_to_bican_class_mapping = {}
        bican_slots_per_class = defaultdict(set)

        with open(csv_file, "r", encoding="utf-8") as file:
            reader = csv.DictReader(file)
            for row in reader:
                bican_name = (
                    row["SubGroup/LinkML Class Name"].lower()
                    + "_"
                    + row["LinkML Slot or Attribute Name"].lower()
                )
                nimp_name = row["NIMP Variable Name"]
                bican_to_nimp_attribute_mapping[bican_name] = nimp_name
                nimp_to_bican_class_mapping[
                    row["NIMP Category"].replace(" ", "").lower()
                ] = row["SubGroup/LinkML Class Name"].lower()
                bican_slots_per_class[row["SubGroup/LinkML Class Name"].lower()].add(
                    row["LinkML Slot or Attribute Name"].lower()
                )
        return (
            bican_to_nimp_attribute_mapping,
            nimp_to_bican_class_mapping,
            bican_slots_per_class,
        )

    (
        bican_to_nimp_attribute_mapping,
        nimp_to_bican_class_mapping,
        bican_slots_per_class,
    ) = create_bican_to_nimp_mapping(BICAN_TO_NIMP_FILE_PATH)

    def __init__(self, jwt_token):
        self.jwt_token = jwt_token
        self.generated_objects = {}

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
    def get_ancestors(nhash_id, jwt_token, nhash_only=True, depth=1):
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
        # TODO: check if NHash ID is not found
        nhash_id = data.get("id")
        category = data.get("category").replace(" ", "").lower()
        bican_category = cls.nimp_to_bican_class_mapping.get(category)
        if bican_category is None:
            return None
        bican_class = CATEGORY_TO_CLASS.get(category)
        bican_object = bican_class(id="NIMP:" + nhash_id)
        # handle was_derived_from attribute. type of this attribute can either be Optional[str] or Optional[List[str]]
        if "List" in bican_class.__annotations__["was_derived_from"]:
            bican_object.was_derived_from = [
                f"NIMP:{item}" for item in was_derived_from
            ]
        else:
            bican_object.was_derived_from = (
                f"NIMP:{was_derived_from[0]}" if was_derived_from else None
            )
        class_attributes = SpecimenPortal.bican_slots_per_class.get(bican_category)
        if class_attributes is not None:
            for attribute in class_attributes:
                if (
                    bican_category + "_" + attribute
                ) in SpecimenPortal.bican_to_nimp_attribute_mapping:
                    bican_attribute_type = bican_class.__annotations__[attribute]
                    value = data.get("record").get(
                        SpecimenPortal.bican_to_nimp_attribute_mapping[
                            bican_category + "_" + attribute
                        ]
                    )
                    if value is not None and type(value) != bican_attribute_type:
                        if (
                            "AmplifiedCdnaRnaAmplificationPassFail"
                            in bican_attribute_type
                        ):
                            value = SpecimenPortal.__check_valueset_membership(
                                "AmplifiedCdnaRnaAmplificationPassFail", value
                            ) 
                        elif "BarcodedCellSampleTechnique" in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership(
                                "BarcodedCellSampleTechnique", value
                            )
                        elif (
                            "DissociatedCellSampleCellPrepType" in bican_attribute_type
                        ):
                            value = SpecimenPortal.__check_valueset_membership(
                                "DissociatedCellSampleCellPrepType", value
                            )
                        elif (
                            "DissociatedCellSampleCellLabelBarcode"
                            in bican_attribute_type
                        ):
                            value = SpecimenPortal.__check_valueset_membership(
                                "DissociatedCellSampleCellLabelBarcode", value
                            )
                        elif "LibraryTechnique" in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership(
                                "LibraryTechnique", value
                            )
                        elif "LibraryPrepPassFail" in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership(
                                "LibraryPrepPassFail", value
                            )
                        elif "LibraryR1R2Index" in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership(
                                "LibraryR1R2Index", value
                            )
                        elif "Sex" in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership(
                                "Sex", value
                            )
                        elif "AgeAtDeathReferencePoint" in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership(
                                "AgeAtDeathReferencePoint", value
                            )
                        elif "AgeAtDeathUnit" in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership(
                                "AgeAtDeathUnit", value
                            )
                        elif "str" in bican_attribute_type:
                            if "List" in bican_attribute_type:
                                pass
                            else:
                                value = str(value)
                        elif "int" in bican_attribute_type:
                            value = int(float(value))
                        elif "float" in bican_attribute_type:
                            value = float(value)
                        elif "bool" in bican_attribute_type:
                            value = bool(value)
                        else:
                            value = None
                    bican_object.__setattr__(attribute, value)
        return bican_object

    @staticmethod
    def __check_valueset_membership(enum_name, nimp_value):
        """
        Check if the given value belongs to the specified enum.

        Parameters:
            enum_name (str): The name of the enum to check.
            nimp_value: The value to check for membership in the enum.

        Returns:
            The enum member if the value belongs to the enum, None otherwise.
        """
        enum = lg.__dict__.get(enum_name)
        if enum is not None:
            valueset = {m.value: m for m in enum}
            return valueset.get(nimp_value)
        return None

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
    pass
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