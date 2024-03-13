import requests
from bkbit.models import purple_boxes as pb
#from bkbit.models import kbmodel220231002 as pb

API_URL_PREFIX = 'https://brain-specimenportal.org/api/v1/nhash_ids/'
INFO_URL_SUFFIX = 'info?id='

class SpecimenPortal:
    def __init__(self, jwt_token):
        self.jwt_token = jwt_token
        self.library_aliquots = {}
   
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
        headers = {'Authorization': f'Bearer {self.jwt_token}'}
        response = requests.get(f'{API_URL_PREFIX}{INFO_URL_SUFFIX}{nhash_id}', headers=headers) #TODO: add timeout
        if response.status_code == 200:
            return response.json()
        
        raise requests.exceptions.HTTPError(f'Error getting data for NHash ID = {nhash_id}. Status Code: {response.status_code}')

    def get_parent(self, nhash_id):
        '''
        Retrieve information of a record’s parents with a NHash ID. 
        '''
        pass

    def get_children(self, nhash_id, nhash_only=True):
        '''
        Retrieve information of a record’s children with a NHash ID. 
        '''
        pass

    def get_all_ancestors(self, nhash_id, nhash_only=True, id_only=True):
        '''
        Retrieve information of all ancestors of a record with a NHash ID. 
        '''
        pass

    def get_all_descendants(self, nhash_id, nhash_only=True, id_only=True):
        '''
        Retrieve information of all descendants of a record with a NHash ID. 
        '''
        pass

    
    def generate_library_aliquot(self, attributes: dict):
        '''
        Generate a library aliquot.

        Parameters:
        - attributes (dict): A dictionary containing the attributes of the library aliquot.

        Returns:
        - lib_aliquot (pb.LibraryAliquot): The generated library aliquot object.

        Raises:
        - ValueError: If the NHash ID is not found in the attributes.
        '''
        nhash_id = attributes.get('data').get('id')
        if nhash_id is None:
            raise ValueError('NHash ID not found in attributes.')
        local_name = attributes.get('data').get('record').get('library_aliquot_local_name')
        lib_aliquot = pb.LibraryAliquot(id = 'bican:'+ nhash_id, name = local_name)

        self.library_aliquots[nhash_id] = lib_aliquot
        return lib_aliquot
