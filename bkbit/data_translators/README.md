# anatomical_structure_translator.py

## Overview
anatomical_structure_translator will create a single .jsonld file containing the objects generated from all the files in the “package” directory. All data objects are defined in the [Anatomical Structure Schema](https://brain-bican.github.io/models/index_anatomical_structure/)

## Command Line
### gen-geneannotation
```python
gen-anatomicalstructure path/to/csv_directory
```

## Required Format of Data
Each .csv must have the **specific column names** listed below in the **given order**.
## Required Format of Data
Each .csv must have the **specific column names** listed below in the **given order**.

| File Name                            | Column Names                                                                                                |
|--------------------------------------|-------------------------------------------------------------------------------------------------------------|
| anatomical_annotation_set        | label, name, description, revision_of, version, anatomical_space_label                                       |
| anatomical_space                | label, name, description, revision_of, version, image_dataset_label                                          |
| image_dataset                   | label, name, description, revision_of, version, x_direction, y_direction, z_direction, x_size, y_size, z_size, x_resolution, y_resolution, z_resolution, unit |
| parcellation_annotation          | internal_identifier, anatomical_annotation_set_label, voxel_count                                            |
| parcellation_annotation_term_map | internal_identifier, anatomical_annotation_set_label, parcellation_term_identifier, parcellation_term_set_label, parcellation_terminology_label |
| parcellation_atlas              | label, name, description, specialization_of, revision_of, version, anatomical_space_label, anatomical_annotation_set_label, parcellation_terminology_label |
| parcellation_color_assignment    | parcellation_color_scheme_label, parcellation_term_identifier, parcellation_terminology_label, color_hex_triplet |
| parcellation_color_scheme        | label, name, description, revision_of, version, parcellation_terminology_label                               |
| parcellation_term_set            | label, name, description, parcellation_terminology_label, parcellation_term_set_order, parcellation_parent_term_set_label |
| parcellation_term                | name, symbol, description, parcellation_term_set_label, parcellation_terminology_label, parcellation_term_identifier, parcellation_term_order, parcellation_parent_term_set_label, parcellation_parent_term_identifier |
| parcellation_terminology         | label, name, description, revision_of, version                                                               |


## Examples
#### Example 1 

```python
pip install bkbit

gen-anatomicalstructure path/to/package_dir > output.jsonld
```

