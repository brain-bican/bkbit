# specimen2jsonld

<b>*specimen2jsonld*</b> generates BICAN objects for specimen record(s) and its respective ancestors or descendants using data from the [Specimen Portal](https://brain-specimenportal.org/). 

## Docs

### Command Line
#### bkbit specimen2jsonld

```python
bkbit specimen2jsonld [OPTIONS] NHASH_ID_OR_FILE
```

#### Options
<span style="color: red;">-d, --descendants</span> <br> 
&emsp;Generate BICAN objects for the given NHASH_ID and all of its descendants. <br>

#### Arguments
<span style="color: red;">NHASH_ID_OR_FILE</span> <br> 
&emsp;Required argument. Provide either a nhash_id of a record or a file containing nhash_id(s).<br>

### Examples
#### Example 1: Parse a <b>single</b> record and its ancestors 
```python
# Install bkbit 
pip install bkbit

# Set SpecimenPortal Personal API Token
export jwt_token='specimen_portal_personal_api_token'

# Run specimen2jsonld command 
bkbit specimen2jsonld 'LP-CVFLMQ819998' > output.jsonld
```

#### Example 2: Parse a <b>single</b> containing record(s) and its descendants  
```python
# Install bkbit 
pip install bkbit

# Set SpecimenPortal Personal API Token
export jwt_token='specimen_portal_personal_api_token'

# Run specimen2jsonld command. Important: include 'descendants' flag
bkbit specimen2jsonld -d 'DO-GICE7463' > output.jsonld
```

#### Example 3: Parse a <b>file</b> containing record(s) and their respective ancestors 
```python
# Install bkbit 
pip install bkbit

# Set SpecimenPortal Personal API Token
export jwt_token='specimen_portal_personal_api_token'

# Contents of input file 
cat input_nhash_ids.txt

LA-TZWCWB265559FVVNTS329147
LA-IAXCCV360563HBFKKM103455
LA-JFCEST535498UIPMOH349083

# Run specimen2jsonld command 
bkbit specimen2jsonld input_nhash_ids.txt 

# Expected output 
ls .

LA-TZWCWB265559FVVNTS329147.jsonld
LA-IAXCCV360563HBFKKM103455.jsonld
LA-JFCEST535498UIPMOH349083.jsonld
```


#### Example 4: Parse a <b>file</b> containing record(s) and their respective descendants 
```python
# Install bkbit 
pip install bkbit

# Set SpecimenPortal Personal API Token
export jwt_token='specimen_portal_personal_api_token'

# Contents of input file 
cat input_nhash_ids.txt

DO-XIQQ6047
DO-WFFF3774
DO-RMRL6873

# Run specimenjsonld command. Important: include 'descendants' flag
bkbit specimen2jsonld -d input_nhash_ids.txt 

# Expected output 
ls .

DO-XIQQ6047.jsonld
DO-WFFF3774.jsonld
DO-RMRL6873.jsonld
# genome_annotation_translator.py

## Overview
genome_annotation_translator uses annotated genome data in GFF3 format to generate respective data objects representing genes, genome assemblies, and organisms. All data object are defined in the [Genome Annotation Schema](https://brain-bican.github.io/models/index_genome_annotation/).<br>
Each jsonld file will contain:
- GeneAnnotation objects
- 1 GenomeAnnotation object
- 1 GenomeAssembly object
- 1 OrganismTaxon object
- 1 Checksum object



## Command Line
### gen-geneannotation
```python
gen-geneannotation [OPTIONS] GFF3_URL 
```

#### Options
<span style="color: red;">-a, --assembly_accession</span> <br> 
&emsp;ID assigned to the genomic assembly used in the GFF3 file. <br>
&emsp;<b>*Note*</b>: Must be provided when using ENSEMBL GFF3 files

<span style="color: red;">-s, --assembly_strain</span> <br>
&emsp;Specific strain of the organism associated with the GFF3 file.

<span style="color: red;">-l, --log_level</span> <br>
&emsp;Logging level. <br>
&emsp;DEFAULT:<br>
&emsp;&emsp;'WARNING'<br>
&emsp;OPTIONS:<br>
&emsp;&emsp;DEBUG | INFO | WARNING | ERROR | CRITICIAL 

<span style="color: red;">-f, --log_to_file</span> <br>
&emsp;Log to a file instead of the console. <br>
&emsp;DEFAULT:<br>
&emsp;&emsp;False <br>

## Examples
#### Example 1: NCBI GFF3 File 

```python
pip install bkbit

gen-geneannotation 'https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/106/GCF_000003025.6_Sscrofa11.1/GCF_000003025.6_Sscrofa11.1_genomic.gff.gz' > output.jsonld
```

#### Example 2: ENSEMBL GFF3 File 

```python
pip install bkbit

# genome_annotation_translator.py

## Overview
genome_annotation_translator uses annotated genome data in GFF3 format to generate respective data objects representing genes, genome assemblies, and organisms. All data object are defined in the [Genome Annotation Schema](https://brain-bican.github.io/models/index_genome_annotation/).<br>
Each jsonld file will contain:
- GeneAnnotation objects
- 1 GenomeAnnotation object
- 1 GenomeAssembly object
- 1 OrganismTaxon object
- 1 Checksum object



## Command Line
### gen-geneannotation
```python
gen-geneannotation [OPTIONS] GFF3_URL 
```

#### Options
<span style="color: red;">-a, --assembly_accession</span> <br> 
&emsp;ID assigned to the genomic assembly used in the GFF3 file. <br>
&emsp;<b>*Note*</b>: Must be provided when using ENSEMBL GFF3 files

<span style="color: red;">-s, --assembly_strain</span> <br>
&emsp;Specific strain of the organism associated with the GFF3 file.

<span style="color: red;">-l, --log_level</span> <br>
&emsp;Logging level. <br>
&emsp;DEFAULT:<br>
&emsp;&emsp;'WARNING'<br>
&emsp;OPTIONS:<br>
&emsp;&emsp;DEBUG | INFO | WARNING | ERROR | CRITICIAL 

<span style="color: red;">-f, --log_to_file</span> <br>
&emsp;Log to a file instead of the console. <br>
&emsp;DEFAULT:<br>
&emsp;&emsp;False <br>

## Examples
#### Example 1: NCBI GFF3 File 

```python
pip install bkbit

gen-geneannotation 'https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/106/GCF_000003025.6_Sscrofa11.1/GCF_000003025.6_Sscrofa11.1_genomic.gff.gz' > output.jsonld
```

#### Example 2: ENSEMBL GFF3 File 

```python
pip install bkbit

gen-geneannotation -a 'GCF_003339765.1' 'https://ftp.ensembl.org/pub/release-104/gff3/macaca_mulatta/Macaca_mulatta.Mmul_10.104.gff3.gz' > output.jsonld
```

# BKE Taxonomy 
## Mapping Data to LinkML Schema


| Class Name | Slots in Schema (`x` if they can be found in the data)| Slots Missing in Schema |
|------------|-----------------------------------------------------|------------------------------|
| `CellTypeTaxon`    | - [x] id <br> - [x] accession_id <br> - [x] name <br> - [x] order <br> - [x] description <br> - [x] number_of_cells <br> - [ ] part_of_taxonomy <br> - [ ] contains_cluster <br> - [ ] has_parent |
| `ObservationRow`   | - [ ] part_of_matrix <br> - [ ] represented_in <br> - [ ] was_derived_from | - [ ] label
| `ObservationMatrix`| - [ ] represented_by <br> - [ ] has_variable <br> - [ ] was_derived_from   | - [ ] url
| `MatrixFile`       |                                                                            | - [ ] url
| `DisplayColor`     | - [x] id <br> - [x] color_hex_triplet <br> - [ ] part_of_palette <br> - [ ] is_color_for |
| `ColorPalette`     | - [x] id <br> - [x] name <br> - [x] description <br> - [ ] is_palette_for |
| `ClusterSet`       | - [x] id <br> - [x] created_at <br> - [x] accession_id <br> - [x] name <br> - [x] description <br> - [ ] was_generated_by <br> - [ ] was_derived_from <br> - [ ] is_revision_of |
| `Cluster`          | - [x] id <br> - [x] accession_id <br> - [x] name <br> - [x] number_of_observations <br> - [ ] part_of_set <br> - [ ] contains_observation <br> - [ ] contains_sample |
| `CellTypeTaxonomy`   | - [x] id <br> - [x] created_at <br> - [x] accession_id <br> - [x] name <br> - [x] description <br> - [ ] was_generated_by <br> - [ ] was_derived_from <br> - [ ] is_revision_of |
| `CellTypeSet`        | - [x] id <br> - [x] accession_id <br> - [x] name <br> - [x] description <br> - [x] type <br> - [x] order <br> - [ ] part_of_taxonomy <br> - [ ] contains_taxon <br> - [ ] has_parent <br> - [ ] has_abbreviation |
| `Abbreviation`       | - [x] id <br> - [x] term <br> - [x] meaning <br> - [x] entity_type <br> - [ ] denotes |

## Topological Sort of Classes
1.  DisplayColor  
2.  ColorPalette  
3.  CellTypeSet  
4.  CellTypeTaxon  
5.  CellTypeTaxonomy  
6.  Cluster  
7.  Abbreviation  
8.  CellTypeTaxonomyCreationProcess  
9.  ObservationRow  
10. ParcellationTerm  
11. ClusterSet  
12. ClusteringProcess  
13. ObservationMatrix  
14. ObservationMatrixCreationProcess  
15. MatrixFile  
16. gene annotation  
17. CellSpecimen  


