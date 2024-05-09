import requests
from bkbit.models import purple_boxes as pb
import csv
import json
from collections import defaultdict
#from bkbit.models import purple_boxes_entire_biolink as pb

PURPLE_BOXES_MODEL = 'pb'
API_URL_PREFIX = 'https://brain-specimenportal.org/api/v1/nhash_ids/'
INFO_URL_SUFFIX = 'info?id='
ANCESTORS_URL_SUFFIX = 'ancestors?id='
PARENTS_URL_SUFFIX = 'parents?id='
NHASH_ONLY_SUFFIX = '&nhash_only='
CATEGORY_TO_CLASS = {'librarypool': pb.LibraryPool,
                     'libraryaliquot': pb.LibraryAliquot,
                     'library': pb.Library,
                     'amplifiedcdna': pb.AmplifiedCdna,
                     'barcodedcellsample': pb.BarcodedCellSample,
                     'enrichedcellsample': pb.EnrichedCellSample,
                     'dissociatedcellsample': pb.DissociatedCellSample,
                     'tissue': pb.TissueSample,
                     'donor': pb.Donor,
                     'specimendissectedroi': pb.DissectionRoiPolygon,
                     'slab': pb.BrainSlab}

class SpecimenPortal:
    @staticmethod
    def create_bican_to_nimp_mapping(csv_file):
        """
        Creates a mapping dictionary from a CSV file, where the keys are 'LinkML Slot or Attribute Name'
        and the values are 'NIMP Variable Name'.

        Args:
            csv_file (str): The path to the CSV file.

        Returns:
            dict: A dictionary mapping 'LinkML Slot or Attribute Name' to 'NIMP Variable Name'.
        """
        bican_to_nimp_attribute_mapping = {}
        nimp_to_bican_class_mapping = {}
        bican_slots_per_class = defaultdict(set)


        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                bican_name = row['SubGroup/LinkML Class Name'].lower() + '_' + row['LinkML Slot or Attribute Name'].lower() 
                nimp_name = row['NIMP Variable Name']
                bican_to_nimp_attribute_mapping[bican_name] = nimp_name
                nimp_to_bican_class_mapping[row['NIMP Category'].replace(' ', '').lower()] = row['SubGroup/LinkML Class Name'].lower()
                bican_slots_per_class[row['SubGroup/LinkML Class Name'].lower()].add(row['LinkML Slot or Attribute Name'].lower()) 
        return bican_to_nimp_attribute_mapping, nimp_to_bican_class_mapping, bican_slots_per_class

    bican_to_nimp_file_path = '../scripts/bican_to_nimp_slots.csv'
    bican_to_nimp_attribute_mapping, nimp_to_bican_class_mapping, bican_slots_per_class = create_bican_to_nimp_mapping(bican_to_nimp_file_path)
    
    def __init__(self, jwt_token):
        #self.headers = {'Authorization': f'Bearer {jwt_token}'}
        self.jwt_token = jwt_token
        self.generated_objects = {}
    
    
    @staticmethod
    def get_data(nhash_id, jwt_token):
        '''
        Retrieve information of any record with a NHash ID in the system. 

        Parameters:
        - nhash_id (str): The NHash ID of the record to retrieve.

        Returns:
        - dict: The JSON response containing the information of the record.

        Raises:
        - requests.exceptions.HTTPError: If there is an error retrieving the data.
        '''
        headers = {'Authorization': f'Bearer {jwt_token}'}
        response = requests.get(f'{API_URL_PREFIX}{INFO_URL_SUFFIX}{nhash_id}', headers=headers) #TODO: add timeout
        if response.status_code == 200:
            return response.json()
        
        raise requests.exceptions.HTTPError(f'Error getting data for NHash ID = {nhash_id}. Status Code: {response.status_code}')

    @staticmethod
    def get_ancestors(nhash_id, jwt_token, nhash_only=True, depth=1):
        '''
        Retrieve information of all ancestors of a record with a NHash ID. 

        '''
        headers = {'Authorization': f'Bearer {jwt_token}'}

        response = requests.get(f'{API_URL_PREFIX}{ANCESTORS_URL_SUFFIX}{nhash_id}{NHASH_ONLY_SUFFIX}{nhash_only}', headers=headers) #TODO: add timeout
        if response.status_code == 200:
            return response.json()
        
        raise requests.exceptions.HTTPError(f'Error getting data for NHash ID = {nhash_id}. Status Code: {response.status_code}')

    @classmethod
    def generate_bican_object(cls, data, was_derived_from: list[str]=None):
        #TODO: 2. check if NHash ID is not found
        #data = self.get_data(nhash_id).get('data')
        nhash_id = data.get('id')
        category = data.get('category').replace(' ', '').lower()
        bican_category = cls.nimp_to_bican_class_mapping.get(category)
        print(f'Category: {category}, Bican Category: {bican_category}')
        if bican_category is None:
            return None
        bican_class = CATEGORY_TO_CLASS.get(category)
        bican_object = bican_class(id='NIMP:'+ nhash_id)
        # handle was_derived_from attribute. type of this attribute can either be Optional[str] or Optional[List[str]]
        if 'List' in bican_class.__annotations__['was_derived_from']:
            bican_object.was_derived_from = [f"NIMP:{item}" for item in was_derived_from]
        else:
            bican_object.was_derived_from = f"NIMP:{was_derived_from[0]}" if was_derived_from else None
        class_attributes = SpecimenPortal.bican_slots_per_class.get(bican_category)
        if class_attributes is not None:
            for attribute in class_attributes:   
                if (bican_category + '_' + attribute) in SpecimenPortal.bican_to_nimp_attribute_mapping:
                    bican_attribute_type = bican_class.__annotations__[attribute]
                    value = data.get('record').get(SpecimenPortal.bican_to_nimp_attribute_mapping[bican_category + '_' + attribute])
                    if value is not None and type(value) != bican_attribute_type:
                        if 'AmplifiedCdnaRnaAmplificationPassFail' in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership('AmplifiedCdnaRnaAmplificationPassFail', value)
                        elif 'BarcodedCellSampleTechnique' in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership('BarcodedCellSampleTechnique', value)
                        elif 'DissociatedCellSampleCellPrepType' in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership('DissociatedCellSampleCellPrepType', value)
                        elif 'DissociatedCellSampleCellLabelBarcode' in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership('DissociatedCellSampleCellLabelBarcode', value)
                        elif 'LibraryTechnique' in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership('LibraryTechnique', value)
                        elif 'LibraryPrepPassFail' in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership('LibraryPrepPassFail', value)
                        elif 'LibraryR1R2Index' in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership('LibraryR1R2Index', value)
                        elif 'Sex' in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership('Sex', value)
                        elif 'AgeAtDeathReferencePoint' in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership('AgeAtDeathReferencePoint', value)
                        elif 'AgeAtDeathUnit' in bican_attribute_type:
                            value = SpecimenPortal.__check_valueset_membership('AgeAtDeathUnit', value)
                        elif 'str' in bican_attribute_type:
                            if 'List' in bican_attribute_type:
                                pass
                            else:
                                value = str(value)
                        elif 'int' in bican_attribute_type:
                            value = int(float(value))
                        elif 'float' in bican_attribute_type:
                            value = float(value)
                        elif 'bool' in bican_attribute_type:
                            value = bool(value)
                        else:
                            #print(f'Attribute {attribute} of class {category} is of type {bican_attribute_type} which is not supported.')
                            value = None
                    bican_object.__setattr__(attribute, value)
        return bican_object

    @staticmethod
    def __check_valueset_membership(enum_name, nimp_value):
        enum = pb.__dict__.get(enum_name)
        if enum is not None:
            valueset = {m.value: m for m in enum}
            return valueset.get(nimp_value)
        return None

    def parse_nhash_id(self, nhash_id):
        ancestor_tree = SpecimenPortal.get_ancestors(nhash_id, self.jwt_token).get('data')
        stack = [nhash_id]
        while stack:
            current_nhash_id = stack.pop()
            if current_nhash_id not in self.generated_objects:
                parents = ancestor_tree.get(current_nhash_id).get('edges').get('has_parent')
                #bican_object = self.generate_bican_object(current_nhash_id, parents)
                data = SpecimenPortal.get_data(current_nhash_id, self.jwt_token).get('data')
                #print(f'Processing NHash ID: {current_nhash_id}')
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
                #data.append(obj.to_dict(exclude_none=exclude_none, exclude_unset=exclude_unset))
                data.append(obj.__dict__)
            output_data = {
                "@context": "https://raw.githubusercontent.com/djarecka/models_tests/main/purple_boxes.context.json",
                "@graph": data,
            }
            f.write(json.dumps(output_data, indent=2))


if __name__ == '__main__':
    # temp = SpecimenPortal('eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMTAsImV4cCI6MTcxNTI0NDgxNX0.-bB0KPxN93WGTFyWyGFXNv5mwqyPr2Cizz8-EtkTMxA')
    # #temp.generate_bican_object('LI-DDFMNG372245')
    # temp.parse_nhash_id('LP-CVFLMQ819998')
    # #temp.parse_nhash_id("AC-ATDJAH472237")
    # temp.serialize_to_jsonld('output_LP-CVFLMQ819998_20240508.jsonld')

    sp = SpecimenPortal('eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMTAsImV4cCI6MTcxNTI5MzcwMX0.xquqUIIFsPynRc25SfU2GMqpg2gatSfldyYlqRhql8k')
    with open('example_library_pool_data.csv', 'r', encoding='utf-8') as file:
        reader = csv.DictReader(file)
        count = 1
        for row in reader:
            print(f'Processing LP: {row["NHash ID"]}')
            sp.parse_nhash_id(row['NHash ID'])
            sp.serialize_to_jsonld('output_' + row["NHash ID"] + '.jsonld')
            if count > 10:
                break
        