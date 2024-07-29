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

genome_annotation_translator uses annoated genome data in GFF3 format to generate respective data objects representing genes, genome assemblies, and organisms. 

## Command Line
### gen-geneannotation
```python
gen-geneannotation [OPTIONS] GFF3_URL 
```

#### Requirements
<span style="color: red;">-a, --assembly_accession</span> <br> 
ID assigned to the genomic assembly used in the GFF3 file. <br>
<b>*Note*</b>: Must be provided when using ENSEMBL GFF3 files

<span style="color: red;">-s, --assembly_strain</span> <br>
Specific strain of the organism associated with the GFF3 file.

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