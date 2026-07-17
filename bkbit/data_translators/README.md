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
&emsp;&emsp;DEBUG | INFO | WARNING | ERROR | CRITICAL 

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
&emsp;&emsp;DEBUG | INFO | WARNING | ERROR | CRITICAL 

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

# ait_taxonomy_parser.py

## Overview
`ait_taxonomy_parser` reads **Allen Institute Taxonomy (AIT)** files distributed in
`.h5ad` ([AnnData](https://anndata.readthedocs.io)) format — for example the BICAN /
HMBA basal-ganglia taxonomies produced with the
[`scrattch`](https://alleninstitute.github.io/scrattch/) toolkit — and extracts the
cell-type taxonomy into plain Python objects (pandas DataFrames) or a CSV.

It reads **only** the small taxonomy/metadata groups and never loads the expression
matrix, so it works on multi-GB files and can read them directly from an
`https://` / `s3://` URL without downloading the whole file.

## How the parser works

An `.h5ad` file is really an **HDF5 container** — a tree of "groups" (folders):

```
X, layers, raw     ← cell × gene expression matrices (this is ~all of the file size)
obs                ← per-cell table (can be millions of rows)
var                ← per-gene table
uns                ← unstructured metadata  ← the taxonomy lives here
obsm, obsp, ...    ← embeddings, graphs
```

The taxonomy is a tiny fraction of the file, so the parser opens the container and
reaches into only the small groups — it never touches `X`.

1. **Open the file (local or remote).** For a URL, `h5py` + `fsspec` read just the
   HDF5 internal index and then fetch **only the specific byte ranges** for the
   groups actually accessed, using HTTP range requests. That is why a 100+ GB file
   can be "read" in seconds without downloading it — the bytes making up `X` are
   never requested. Files are opened read-only; the parser never modifies them.

2. **Read the taxonomy definition from `uns`.**
   - `uns/hierarchy` is a small dict of level → position
     (e.g. `Neighborhood:0, Class:1, Subclass:2, Group:3, cluster_id:4`), sorted to
     give the level order from root to leaf.
   - `uns/cluster_info` is the taxonomy table: one row per leaf cluster with its
     full ancestor path plus per-level accessions, colors, and CL ontology IDs.

   Decoding is done with anndata's `read_elem`, which honors each group's
   `encoding-type` attribute — e.g. reconstructing categorical columns (stored as
   `categories` + integer `codes` in HDF5) back into real string values.

3. **Read the rest of `uns`, plus `obs`/`var`.** `obs` is optional (`load_obs`)
   because it is the one large metadata group; taxonomy work skips it by default.

4. **Build in-memory views** (no further file access): ordered `levels`, the
   `cluster_info` DataFrame, a `.edges()` view of parent→child tree edges, a
   `.summary()` printout, and `.to_csv()` to persist the taxonomy table.

## Dependencies
`anndata`, `h5py`, and (for remote URLs) `fsspec` + `aiohttp`.

## Command Line
```python
python -m bkbit.data_translators.ait_taxonomy_parser PATH_OR_URL [OPTIONS]
```

#### Options
<span style="color: red;">--no-obs</span> <br>
&emsp;Skip the large per-cell `obs` table; read only the taxonomy definition
(`uns` + `cluster_info`). Recommended when reading remote files. <br>

<span style="color: red;">--out CSV</span> <br>
&emsp;Write the leaf-cluster taxonomy table (`cluster_info`) to this CSV path. <br>

## Examples
#### Example 1: Summarize a taxonomy from a remote URL (no download)
```python
python -m bkbit.data_translators.ait_taxonomy_parser \
  'https://.../Marmoset_HMBA_basalganglia_AIT_pre-print.h5ad' --no-obs
```

#### Example 2: Export the taxonomy table to CSV
```python
python -m bkbit.data_translators.ait_taxonomy_parser \
  'https://.../Human_HMBA_basalganglia_AIT_pre-print.h5ad' \
  --no-obs --out Human_taxonomy.csv
```

#### Example 3: Use as a library
```python
from bkbit.data_translators.ait_taxonomy_parser import AITTaxonomy

tax = AITTaxonomy.from_file(path_or_url, load_obs=False)
print(tax.summary())
tax.levels            # ['Neighborhood', 'Class', 'Subclass', 'Group', 'cluster_id']
tax.cluster_info      # pandas DataFrame, one row per leaf cluster
tax.edges()           # list of (parent_level, parent, child_level, child) tree edges
tax.to_csv('taxonomy.csv')
```