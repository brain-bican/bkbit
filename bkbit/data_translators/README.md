# specimen_portal_translator.py

specimen_portal_translator retrieves data from the Specimen Portal using the NIMP API and then generates respective data classes using classes defined in library_generation.py. 

## Usage 

```python

# Step 0: Download Mapping Data bkbit.utils.bican_to_nimp_slots.csv and set correct path in specimen_portal_translator.py line 7

# Step 1: Import specimen_portal_translator
from bkbit.scripts.specimen_portal_translator import SpecimenPortal

# Step 2: Retrieve Personal API Token from SpecimenPortal
token = ... 

# Step 3: Initialize SpecimenPortal instance
sp = SpecimenPortal(token)

# Step 4: Generate respective BICAN data objects for provided nhash_id and its ancestors:
nhash_id = ... # i.e. nhashid = 'LP-CVFLMQ819998'
sp.parse_nhash_id(nhash_id)

# Step 5: Serialize BICAN data objects to jsonld 
output_file_name = ... # i.e. output_file_name = output_LP-CVFLMQ819998.jsonld
sp.serialize_to_jsonld(output_file_name)
```