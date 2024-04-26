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
                     'donor': pb.Donor}

class SpecimenPortal:
    def __init__(self, jwt_token, bican_to_nimp_file_path):
        self.headers = {'Authorization': f'Bearer {jwt_token}'}
        self.generated_objects = {}
        self.bican_to_nimp_mapping, self.bican_slots_per_class = self.create_bican_to_nimp_mapping(bican_to_nimp_file_path)
    
    def create_bican_to_nimp_mapping(self, csv_file):
        """
        Creates a mapping dictionary from a CSV file, where the keys are 'LinkML Slot or Attribute Name'
        and the values are 'NIMP Variable Name'.

        Args:
            csv_file (str): The path to the CSV file.

        Returns:
            dict: A dictionary mapping 'LinkML Slot or Attribute Name' to 'NIMP Variable Name'.
        """
        mapping = {}
        bican_slots_per_class = defaultdict(set)
        with open(csv_file, 'r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            for row in reader:
                bican_name = row['SubGroup/LinkML Class Name'].lower() + '_' + row['LinkML Slot or Attribute Name'].lower() #! standardize the key
                nimp_name = row['NIMP Variable Name']
                mapping[bican_name] = nimp_name
                bican_slots_per_class[row['SubGroup/LinkML Class Name'].lower()].add(row['LinkML Slot or Attribute Name'].lower()) #! standardize the key and value
        return mapping, bican_slots_per_class

   
    def get_data(self, nhash_id):
        '''
        Retrieve information of any record with a NHash ID in the system. 

        Parameters:
        - nhash_id (str): The NHash ID of the record to retrieve.

        Returns:
        - dict: The JSON response containing the information of the record.

        Raises:
        - requests.exceptions.HTTPError: If there is an error retrieving the data.
        '''
        
        response = requests.get(f'{API_URL_PREFIX}{INFO_URL_SUFFIX}{nhash_id}', headers=self.headers) #TODO: add timeout
        if response.status_code == 200:
            return response.json()
        
        raise requests.exceptions.HTTPError(f'Error getting data for NHash ID = {nhash_id}. Status Code: {response.status_code}')

    def get_ancestors(self, nhash_id, nhash_only=True, depth=1):
        '''
        Retrieve information of all ancestors of a record with a NHash ID. 

        '''
        response = requests.get(f'{API_URL_PREFIX}{ANCESTORS_URL_SUFFIX}{nhash_id}{NHASH_ONLY_SUFFIX}{nhash_only}', headers=self.headers) #TODO: add timeout
        if response.status_code == 200:
            return response.json()
        
        raise requests.exceptions.HTTPError(f'Error getting data for NHash ID = {nhash_id}. Status Code: {response.status_code}')

    def get_parent(self, nhash_id):
        '''
        Retrieve information of a record’s parents with a NHash ID. 
        '''
        response = requests.get(f'{API_URL_PREFIX}{PARENTS_URL_SUFFIX}{nhash_id}', headers=self.headers) #TODO: add timeout
        if response.status_code == 200:
            return response.json()
        
        raise requests.exceptions.HTTPError(f'Error getting data for NHash ID = {nhash_id}. Status Code: {response.status_code}')

    def generate_bican_object(self, nhash_id:str, was_derived_from: list[str]=None):
        #TODO: 1. Add name to bican_to_nimp_mapping
        #TODO: 2. check if NHash ID is not found
        data = self.get_data(nhash_id).get('data')
        category = data.get('category').replace(' ', '').lower()
        bican_class = CATEGORY_TO_CLASS.get(category)
        bican_object = bican_class(id='NIMP:'+ nhash_id)
        # handle was_derived_from attribute. type of this attribute can either be Optional[str] or Optional[List[str]]
        if 'List' in bican_class.__annotations__['was_derived_from']:
            bican_object.was_derived_from = [f"NIMP:{item}" for item in was_derived_from]
        else:
            bican_object.was_derived_from = f"NIMP:{was_derived_from[0]}" if was_derived_from else None
        class_attributes = self.bican_slots_per_class.get(category) 
        if class_attributes is not None:
            for attribute in self.bican_slots_per_class.get(category):   
                if (category + '_' + attribute) in self.bican_to_nimp_mapping:
                    bican_attribute_type = bican_class.__annotations__[attribute]
                    value = data.get('record').get(self.bican_to_nimp_mapping[category + '_' + attribute])
                    if value is not None and type(value) != bican_attribute_type:
                        if 'str' in bican_attribute_type:
                            value = str(value)
                        elif 'int' in bican_attribute_type:
                            value = int(float(value))
                        elif 'float' in bican_attribute_type:
                            value = float(value)
                        elif 'bool' in bican_attribute_type:
                            value = bool(value)
                        elif 'AmplifiedCdnaRnaAmplificationPassFail' in bican_attribute_type:
                            value = self.__check_valueset_membership('AmplifiedCdnaRnaAmplificationPassFail', value)
                        elif 'BarcodedCellSampleTechnique' in bican_attribute_type:
                            value = self.__check_valueset_membership('BarcodedCellSampleTechnique', value)
                        elif 'DissociatedCellSampleCellPrepType' in bican_attribute_type:
                            value = self.__check_valueset_membership('DissociatedCellSampleCellPrepType', value)
                        elif 'DissociatedCellSampleCellLabelBarcode' in bican_attribute_type:
                            value = self.__check_valueset_membership('DissociatedCellSampleCellLabelBarcode', value)
                        elif 'LibraryTechnique' in bican_attribute_type:
                            value = self.__check_valueset_membership('LibraryTechnique', value)
                        elif 'LibraryPrepPassFail' in bican_attribute_type:
                            value = self.__check_valueset_membership('LibraryPrepPassFail', value)
                        elif 'LibraryR1R2Index' in bican_attribute_type:
                            value = self.__check_valueset_membership('LibraryR1R2Index', value)
                        else:
                            #print(f'Attribute {attribute} of class {category} is of type {bican_attribute_type} which is not supported.')
                            value = None
                    bican_object.__setattr__(attribute, value)
        return bican_object

    def __check_valueset_membership(self, enum_name, nimp_value):
        enum = pb.__dict__.get(enum_name)
        if enum is not None:
            valueset = {m.value: m for m in enum}
            return valueset.get(nimp_value)
        return None

    def parse_nhash_id(self, nhash_id):
        ancestor_tree = self.get_ancestors(nhash_id).get('data')
        stack = [nhash_id]
        while stack:
            current_nhash_id = stack.pop()
            if current_nhash_id not in self.generated_objects:
                parents = ancestor_tree.get(current_nhash_id).get('edges').get('has_parent')
                bican_object = self.generate_bican_object(current_nhash_id, parents)
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

    # NOTE: DEFINE THE FOLLOWING FUNCTIONS AS NEEDED #
    def get_children(self, nhash_id, nhash_only=True):
        '''
        Retrieve information of a record’s children with a NHash ID. 
        '''
        pass

    def get_descendants(self, nhash_id, nhash_only=True, id_only=True):
        '''
        Retrieve information of all descendants of a record with a NHash ID. 
        '''
        pass

if __name__ == '__main__':
    temp = SpecimenPortal('eyJhbGciOiJIUzI1NiJ9.eyJ1c2VyX2lkIjoxMTAsImV4cCI6MTcxNDE3Mzk5NH0.NZd07OqzhRImLcffPxcojEUO6W6rqxRFHrvgdPMbmg8', 'bican_to_nimp_slots.csv')
    #temp.generate_bican_object('LI-DDFMNG372245')
    temp.parse_nhash_id('LP-CVFLMQ819998')    
    temp.serialize_to_jsonld('output_LP-CVFLMQ819998_20240426.jsonld')