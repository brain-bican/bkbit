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

#### Requirements
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