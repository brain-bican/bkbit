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