# linkml_trimmer.py

## Description
linkml_trimmer returns a trimmed version of a linkml model; only the given input list of classes, slots, and enumerations remain in the model.

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


# add_dunderMethods_genomeAnnotation.py 

## Description:
add_dunderMethods_genomeAnnotation adds 3 dunder methods to the GeneAnnotation class in the genome_annotation model.
1. \_\_ne\_\_ : compares two GeneAnnotation objects based on a sub-selection of attributes and returns True if they are not equivalent.
2. \_\_eq\_\_ : compares two GeneAnnotation objects based on a sub-selection of attributes and returns True if they are equivalent.
3. \_\_hash\_\_ : returns the hash of a GeneAnnotation object. 

## Notes
1. These dunder methods need to be added to models/genome_annotation.py if using genome_annotation_translator.py. 