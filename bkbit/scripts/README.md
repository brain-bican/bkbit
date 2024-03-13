# linkml_trimmer.py

linkml_trimmer returns a trimmed version of a linkml model. 
## Usage

```python
# Step 1: import YamlTrimmer
from bkbit.scripts.linkml_trimmer import YamlTrimmer

# Step 2: initialize YamlTrimmer Object with a linkml model 
trimmed_model = YamlTrimmer(path_to_linkml_model)

# Step 3: define the classes, slots, and enums that should be included in the trimmed model
classes = [...] # List of classes to keep
slots = [...] # List of slots to keep
enums = [...] # List of enums to keep

# Step 4: call the trim_model function with the selected classes/slots/enums 
# Note: only classes is a required parameter. slots and enums are optional 
trimmed_model.trim_model(classes, slots, enums)

# Step 5: call the serialize function to produce trimmed linkml model 
trimmed_model.serialize()
```

## Notes

1. To produce bican_biolink.yaml call trim_model with classes = ['gene', 'genome', 'organism taxon', 'thing with taxon', 'material sample', 'procedure', 'entity', 'activity', 'named thing']

# specimen_portal_translator.py

specimen_portal_translator retrieves data from the Specimen Portal using the NIMP API and then generates respective data classes using classes defined in purple_boxes.py. 

## Usage 

```python
# Step 1: import specimen
from bkbit.scripts.specimen_portal_translator import SpecimenPortal

# Step 2: initialize SpecimenPortal object with Personal API Token
sp = SpecimenPortal(...)

# Step 3: Retrieve data corresponding to a resource by its NHash ID:
lib_aliquot_raw = sp.get_data('LA-XCYXZJ339245CIBDEK773733')

# Step 4: Generate Library Aliquot Object
sp.generate_library_aliquot(lib_aliquot_raw)
```