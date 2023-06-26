# gfftranslator.py

gfftranslator.py is a Python script that generates GeneAnnotation objects from data stored in .gff files.  

## Usage

```python
from gfftranslator import gff_to_gene_annotation

# input_fname is the name of the input .csv file 
# Note: example input data can be found on Allen Teams under Knowledge Graph files. "20230412_subset_genome_annotation.csv" 
input_fname = 'XXX.csv'

# data_dir is the directory path where the input .csv file exists
data_dir = ' XXX/XXX/'

# output_dir is the directory path where all of the generated output files will be saved 
# Note: if output_dir does not exist, gff_to_gene_annotation will create the directory
output_dir = 'XXX/XXX/'

gff_to_gene_annotation(input_fname, data_dir, output_dir)
```

## Notes

1. Input csv file  
a. Each row in the csv file contains a url to the .gff file as well as additional attributes to describe the dataset. The csv file must contain the following columns: authority, label, taxon_local_unique_identifier, version, gene_identifier_prefix, url. 
2. Generated files  
a. For each .gff file 3 files will be generated: (i) The raw data downloaded from the url provided will be saved as a csv file in the 'data_dir' directory provided. (ii) The parsed and cleaned data will be saved as a csv file in the 'output_dir' directory provided. (iii) The initialized GeneAnnotation objects will be saved as a list of json dictionaries in a json file in the 'output_dir' directory provided. 
