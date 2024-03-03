## IMPORTS ##

import pandas as pd
import os
import csv
import json
import requests
import hashlib
import uuid
import urllib.parse
import re
from bkbit.models import kbmodel
#from mappings import *

## CONSTANTS ##

TAXON_SCIENTIFIC_NAME = {'9606': 'Homo sapiens', '10090': 'Mus musculus', '9544': 'Macaca mulatta', '9483': 'Callithrix jacchus'}
TAXON_COMMON_NAME = {'9606': 'human', '10090': 'mouse', '9544': 'rhesus macaque', '9483': 'common marmoset'}
PREFIX_MAP = {"NCBITaxon": "http://purl.obolibrary.org/obo/NCBITaxon_", "NCBIGene": "http://identifiers.org/ncbigene/", "ENSEMBL": "http://identifiers.org/ensembl/", "NCBIAssembly": "https://www.ncbi.nlm.nih.gov/assembly/"}
GENOME_ANNOTATION_FILE_COLUMN_NAMES = {'assembly_identifier_prefix', 'assembly_local_unique_identifier', 'label', 'taxon_identifier_prefix', 'taxon_local_unique_identifier', 'authority', 'version', 'gene_identifier_prefix', 'description', 'url'}
GENOME_ASSEMBLY_FILE_COLUMN_NAMES = {'identifier_prefix','local_unique_identifier','taxon_identifier_prefix','taxon_local_unique_identifier','version','strain','label'}
GFF3_FILE_COLUMN_NAMES = ['seqid','source','type','start','end','score','strand','phase','attributes']
NCBI_GENE_ID_PREFIX = 'NCBIGene'
ENSEMBL_GENE_ID_PREFIX = 'ENSEMBL'
TAXON_PREFIX = 'NCBITaxon'
ASSEMBLY_PREFIX = "NCBIAssembly"
BICAN_ANNOTATION_PREFIX = 'bican:annotation-'

## FUNCTIONS ##

def gff_to_gene_annotation(input_fname, data_dir, output_dir, genome_assembly_fname, hash_functions=['SHA256']):
    """Converts GFF file(s) to GeneAnnotation objects and serializes them to a JSON file.

    Parameters:
    input_fname (str): name of csv file containing gff files
    data_dir (str): path to directory containing input file
    output_dir (str): path to output directory where generated files will be saved
    genome_assembly_fname (str): name of csv file containing genome assembly data

    """
    # CHECK IF DATA DIRECTORY EXISTS #
    if not os.path.exists(data_dir):
        raise NotADirectoryError(f"Data directory {data_dir} does not exist.")
    
    # CHECK IF INPUT FILES EXIST #
    if not os.path.isfile(os.path.join(data_dir,input_fname)):
        raise FileNotFoundError(f"Input file {input_fname} does not exist in data directory {data_dir}.")
    if not os.path.isfile(os.path.join(data_dir,genome_assembly_fname)):
        raise FileNotFoundError(f"Genome assembly file {genome_assembly_fname} does not exist in data directory {data_dir}.")

    # GENERATE GENOME ASSEMBLY OBJECTS #
    genomeAssemblyObjects = generate_genome_assembly(os.path.join(data_dir,genome_assembly_fname)) 

    # CREATE OUTPUT DIRECTORY IF IT DOES NOT EXIST #
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # ITERATE THROUGH ALL GFF3 FILES PROVIDED IN INPUT CSV #
    with open(os.path.join(data_dir,input_fname), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Check if column names match expected column names
        column_names = [name.strip('\ufeff').strip() for name in reader.fieldnames]  # Remove invisible characters
        validate_column_names(column_names, GENOME_ANNOTATION_FILE_COLUMN_NAMES)
        
        for row in reader:
            row = {k.strip('\ufeff').strip(): v.strip('\ufeff').strip() for k, v in row.items()}
            filter_and_parse_gff3(**row, data_dir=data_dir, output_dir=output_dir, genomeAssemblyObjects=genomeAssemblyObjects, hash_functions=hash_functions)
            

def filter_and_parse_gff3(assembly_identifier_prefix, assembly_local_unique_identifier, label, taxon_identifier_prefix, taxon_local_unique_identifier, authority, version, gene_identifier_prefix, description, url, data_dir, output_dir, genomeAssemblyObjects, feature_type_filter=['gene', 'pseudogene', 'ncRNA_gene'], hash_functions=['SHA256']):
    """
    Filters and parses a GFF3 file, generates various objects, and serializes them.

    Parameters:
    assembly_identifier_prefix (str): The prefix for the assembly identifier.
    assembly_local_unique_identifier (str): The local unique identifier for the assembly.
    label (str): The label for the genome annotation.
    taxon_identifier_prefix (str): The prefix for the taxon identifier.
    taxon_local_unique_identifier (str): The local unique identifier for the taxon.
    authority (str): The authority for the genome annotation.
    version (str): The version of the genome annotation.
    gene_identifier_prefix (str): The prefix for the gene identifier.
    description (str): The description of the genome annotation.
    url (str): The URL of the GFF3 file.
    data_dir (str): The directory to store the downloaded data.
    output_dir (str): The directory to store the serialized objects.
    genomeAssemblyObjects (dict): A dictionary of genome assembly objects.
    feature_type_filter (list, optional): The list of feature types to filter for. Defaults to ['gene', 'pseudogene', 'ncRNA_gene'].
    hash_functions (list, optional): The list of hash functions to generate checksums. Defaults to ['SHA256'].

    """
    print(f"AUTHORITY: {authority}, LABEL: {label}, TAXON_LOCAL_UNIQUE_ID: {taxon_local_unique_identifier}, VERSION: {version}, GENE_ID_PREFIX: {gene_identifier_prefix}, URL: {url}")
    gene_name = ''.join(url.split('/')[-1].split('.')[0:-2])
    print("GENE NAME: ", gene_name)

    if os.path.isfile(data_dir + '/' + gene_name + '.csv'):
        print(f"Data from url is already downloaded and saved here: {data_dir + '/' + gene_name + '.csv'}")
        df = pd.read_csv(data_dir + '/' + gene_name + '.csv') 
    else:
        print(f"Downloading and saving data from url here: {data_dir + '/' + gene_name + '.csv'}")
        df = pd.read_csv(url, sep='\t', comment = "#", header=None, names=GFF3_FILE_COLUMN_NAMES)
        df.to_csv(data_dir + '/' + gene_name + '.csv', index=False)

    # FILTER FOR GENE FEATURES #
    pred = [x in feature_type_filter for x in df['type']]
    df_gene = df[pred].copy(deep=True)
    print(f'LENGTH OF DATAFRAME AFTER FILTERING FOR GENES: {len(df_gene)}')
    df_gene.to_csv(data_dir + '/' + gene_name + '_genefilter.csv', index=False) 

    # STORES ALL GENERATED OBJECTS RELATED TO THIS GFF3 FILE #
    fileObjects = []

    # GENERATE ORGANISM TAXON OBJECT #
    curr_org_taxon = kbmodel.OrganismTaxon(id = TAXON_PREFIX + ':' + str(taxon_local_unique_identifier), full_name = TAXON_SCIENTIFIC_NAME[taxon_local_unique_identifier], name = TAXON_COMMON_NAME[taxon_local_unique_identifier],  iri = PREFIX_MAP[TAXON_PREFIX] + taxon_local_unique_identifier)

    # GENERATE CHECKSUM OBJECT #
    digests = dict()
    for hash_function in hash_functions:
        curr_digest = generate_digest(hash_function, requests.get(url).content)
        digests[curr_digest.id] = curr_digest

    # CHECK IF AUTHORITY IS VALID #
    if authority.upper() == kbmodel.AuthorityType.NCBI.value:
        authority_type = kbmodel.AuthorityType.NCBI
    elif authority.upper() == kbmodel.AuthorityType.ENSEMBL.value:
        authority_type = kbmodel.AuthorityType.ENSEMBL
    else:
        raise Exception(f'Authority {authority} is not supported. Please use NCBI or Ensembl.')
    
    # GENERATE GENOME ANNOTATION OBJECT #
    curr_genome_annot = kbmodel.GenomeAnnotation(id = BICAN_ANNOTATION_PREFIX + label.upper(), 
                                                    digest = list(digests.keys()), 
                                                    content_url = [url], 
                                                    reference_assembly = genomeAssemblyObjects[assembly_local_unique_identifier].id, 
                                                    version = version, 
                                                    in_taxon = [curr_org_taxon.id], 
                                                    in_taxon_label = TAXON_SCIENTIFIC_NAME[taxon_local_unique_identifier], 
                                                    description = authority_type.value + ' ' + TAXON_SCIENTIFIC_NAME[taxon_local_unique_identifier] + ' Annotation Release ' + version, # Format for description: <authority> <TAXON_SCIENTIFIC_NAME> Annotation Release <version>; i.e. NCBI Homo sapiens Annotation Release 110
                                                    authority = authority_type
                                                )
    
    # GENERATE GENE ANNOTATION OBJECT #
    if authority_type.value == 'NCBI':
        curr_gene_annots = generate_ncbi_gene_annotation(df_gene, curr_genome_annot, curr_org_taxon, taxon_local_unique_identifier)
    else: 
        curr_gene_annots = generate_ensembl_gene_annotation(df_gene, curr_genome_annot, curr_org_taxon, taxon_local_unique_identifier)
    print(f'NUMBER OF GENE ANNOTATIONS: {len(curr_gene_annots)}')

    # COMBINE ALL GENERATED OBJECTS RELATED TO THIS GFF FILE #
    fileObjects.append(genomeAssemblyObjects[assembly_local_unique_identifier])
    fileObjects.append(curr_genome_annot)
    fileObjects.append(curr_org_taxon)
    fileObjects.extend(list(digests.values())) 
    fileObjects.extend(curr_gene_annots)
    output_ser = os.path.join(output_dir, gene_name +'.json')
    serialize_annotation_collection(fileObjects, output_ser)
    print(f'Serialized GeneAnnotation objects saved here: {output_ser}')


def generate_ensembl_gene_annotation(df, genomeAnnot, orgTaxon, taxon_id):
    """Creates a gene annotation object for every row in the provided dataframe.

    Parameters:
    df (pandas.DataFrame): dataframe containing gene annotations and respective metadata
    genomeAnnot (GenomeAnnotation): reference to GenomeAnnotation object 
    orgTaxon (OrganismTaxon): reference to OrganismTaxon object 
    taxon_id (str): taxon id 

    Returns:
    gene_annotations (List[GeneAnnotations]): list of gene annotations created

    """
    gene_annotations = []

    for row in df.itertuples():
        attributes = dict([x.split('=') for x in row.attributes.split(';')])
        description = attributes.get("description")
        if description is not None:
            description = urllib.parse.unquote(description)
            description = re.sub(r"\[source .*?\]", "", description)
        stable_id = attributes['gene_id'].split('.')[0]
        molecular_type = kbmodel.BioType.protein_coding if attributes.get('biotype') == kbmodel.BioType.protein_coding.value else kbmodel.BioType.noncoding


        curr_gene_annot = kbmodel.GeneAnnotation(id = ENSEMBL_GENE_ID_PREFIX + ':' + stable_id , symbol = attributes.get('Name'), name = attributes.get('Name'), referenced_in = genomeAnnot.id, 
                                                molecular_type = molecular_type, source_id = stable_id, in_taxon = [orgTaxon.id], 
                                                in_taxon_label = TAXON_SCIENTIFIC_NAME[taxon_id], description = description, synonym = None)
        gene_annotations.append(curr_gene_annot)
    return remove_ensembl_duplicates(gene_annotations)


def remove_ensembl_duplicates(gene_annotations):
    """
    Removes duplicates in a list of gene annotations based on [id, name, description, molecular_type]. 

    Parameters:
    gene_annotations (list): A list of gene annotations.

    Returns:
    list[GeneAnnotations]: A list of unique gene annotations.

    """
    #! LONG TERM TODO: make GeneAnnotation hashable so we can use set(). Add def __hash__(self) to GeneAnnotation class in kbmodel.py
    unique_annotations = dict()
    seen_annotations = set()

    for annotation in gene_annotations:
        annotation_key = (annotation.id, annotation.name, annotation.description, annotation.molecular_type)

        if annotation_key not in seen_annotations:
            unique_annotations[annotation.id] = annotation
            seen_annotations.add(annotation_key)
        else:
            try:
                unique_annotations.pop(annotation.id)
            except KeyError:
                pass
    print(f'NUMBER OF UNIQUE GENE ANNOTATIONS: {len(unique_annotations)}')
    return list(unique_annotations.values())
      

def generate_ncbi_gene_annotation(df, genomeAnnot, orgTaxon, taxon_id):
    """Creates a gene annotation object for every row in the provided dataframe.

    Parameters:
    df (pandas.DataFrame): dataframe containing gene annotations and respective metadata
    genomeAnnot (GenomeAnnotation): reference to GenomeAnnotation object 
    orgTaxon (OrganismTaxon): reference to OrganismTaxon object 
    taxon_id (str): taxon id 

    Returns:
    gene_annotations.values() (List[GeneAnnotations]): list of gene annotations created

    """
    gene_annotations = dict()
    
    for row in df.itertuples():
        attributes = dict([x.split('=') for x in row.attributes.split(';')])
        description = attributes.get("description")
        if description is not None:
            description = urllib.parse.unquote(description)
        db_xref = dict([x.split(':', 1) for x in attributes['Dbxref'].split(',')]) if 'Dbxref' in attributes else {}
        stable_id = db_xref['GeneID'].split('.')[0]
        molecular_type = kbmodel.BioType.protein_coding if attributes.get('gene_biotype') == 'protein_coding' else kbmodel.BioType.noncoding

        # CHECK FOR DUPLICATE GENE IDS #
        #! TODO: ASK IF SHOULD I CHECK IF 'NAME' IS CONSISTENT BETWEEN DUPLICATES?
        if stable_id in gene_annotations:
            gene_annotations[stable_id] = resolve_ncbi_duplicates(gene_annotations[stable_id], curr_gene_annot)
        else:
            curr_gene_annot = kbmodel.GeneAnnotation(id = NCBI_GENE_ID_PREFIX + ':' + stable_id, symbol = attributes.get('Name'), name = attributes.get('Name'), referenced_in = genomeAnnot.id, 
                                                     molecular_type = molecular_type, source_id = stable_id, in_taxon = [orgTaxon.id], 
                                                     in_taxon_label = TAXON_SCIENTIFIC_NAME[taxon_id], description = description, synonym = attributes.get('gene_synonym').split(','))
            gene_annotations[stable_id] = curr_gene_annot
    return gene_annotations.values()

def resolve_ncbi_duplicates(stored_annotation, curr_annotation):
    """
    Resolves duplicates between two GeneAnnotation objects with the same GeneID based on specific conditions.
    Conditions: Among all duplicates with the same GeneID, keep one record per GeneID using the following priority:
        1.	“description” is not NULL and “molecular_type” = ‘protein_coding’
        2.	“description” is not NULL and “molecular_type” = ‘noncoding’
        3.	“description” is NULL and “molecular_type” = ‘protein_coding’
        4.	“description” is NULL and “molecular_type” = ‘noncoding

    Parameters:
    stored_annotation (GeneAnnotation): The stored gene annotation object.
    curr_annotation (GeneAnnotation): The current gene annotation object.

    Returns:
    (GeneAnnotation): The gene annotation object with higher priority.

    """
    if stored_annotation.description is None and curr_annotation.description is not None:
        return curr_annotation
    elif stored_annotation.description is not None and curr_annotation.description is None:
        return stored_annotation
    elif stored_annotation.molecular_type == 'protein_coding' and curr_annotation.molecular_type == 'noncoding':
        return stored_annotation
    elif stored_annotation.molecular_type == 'noncoding' and curr_annotation.molecular_type == 'protein_coding':
        return curr_annotation
    else:
        return stored_annotation
    


def generate_genome_assembly(file_path):
    ''' Creates GenomeAssembly objects from the given file path. 
    Parameters:
    file_path (str): Path to the file containing the genome assembly data.

    Returns: 
    [GeneomeAssembly]: list of GenomeAssembly objects created from the given file path

    '''
    df = pd.read_csv(file_path) 
    validate_column_names(df.columns.tolist(), GENOME_ASSEMBLY_FILE_COLUMN_NAMES)
    genomeAssemblyObjects = {}
    for row in df.itertuples(index=False):
        id = row.local_unique_identifier.strip()
        if row.local_unique_identifier not in genomeAssemblyObjects:
            currOrgTaxon = kbmodel.OrganismTaxon(id = TAXON_PREFIX + ':' + str(row.taxon_local_unique_identifier), full_name = TAXON_SCIENTIFIC_NAME[str(row.taxon_local_unique_identifier)], name = TAXON_COMMON_NAME[str(row.taxon_local_unique_identifier)],  iri = PREFIX_MAP[TAXON_PREFIX] + str(row.taxon_local_unique_identifier))
            currGenomeAssem = kbmodel.GenomeAssembly(id = ASSEMBLY_PREFIX + ":" + id, 
                                                     in_taxon = [currOrgTaxon.id], 
                                                     in_taxon_label = TAXON_SCIENTIFIC_NAME[str(row.taxon_local_unique_identifier)],
                                                     version = str(row.version), 
                                                     name = row.label)
            #! LONG TERM TODO: DOUBLE CHECK IF THIS IS THE BEST WAY TO CHECK IF STRAIN IS PROVIDED
            if str(row.strain) != 'nan':
                currGenomeAssem.strain = row.strain
            genomeAssemblyObjects[id] = currGenomeAssem
    return genomeAssemblyObjects


def generate_digest(hash, data):
    '''Generates a Checksum object from the given hash and data.
    
    Parameters:
    hash (str): Hash algorithm to use. Currently supported: sha256, md5, sha1
    data (pandas.DataFrame): Data to be hashed

    Returns:
    Checksum: Checksum object containing the hash value of the given data

    '''
    hash = hash.strip().upper()

    # Generate a UUID version 4
    uuid_value = uuid.uuid4()

    # Construct a URN with the UUID
    urn = f"urn:uuid:{uuid_value}"
       
    # Create a Checksum object
    if hash == 'SHA256':
        digest = hashlib.sha256(data).hexdigest()
        return kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.SHA256, value = digest)
    elif hash == 'MD5':
        digest = hashlib.md5(data).hexdigest()
        return kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.MD5, value = digest)
    elif hash == 'SHA1':
        digest = hashlib.sha1(data).hexdigest()
        return kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.SHA1, value = digest)
    else:
        raise ValueError(f'Hash algorithm {hash} is not supported. Please use SHA256, MD5, or SHA1.')


def serialize_annotation_collection(annotations, outfile):
    """Serializes the annotation collection object to a JSON file.

    Parameters:  
    annotations (list): list of initialized classes from kbmodel
    outfile (str): path to output file

    """
    with open(outfile, 'w') as f:
        output_arr = []
        for g in annotations:
            output_arr.append(g.dict(exclude_none=True))
        f.write(json.dumps(output_arr, indent=2))


def validate_column_names(column_names, expected_names):
    #! LONG TERM TODO: ADD EXTRA PARAMETER FOR FILENAME FOR EXTRA CLARITY
    """Validates that the given column names match the expected column names.

    Parameters:
    column_names (list): list of column names
    expected_names (set): set of expected column names

    """
    if len(column_names) != len(expected_names):
        raise ValueError(f"Expected {len(expected_names)} columns, but found {len(column_names)} columns. Expected column names: {expected_names}")
    if set(column_names) != expected_names:
        raise ValueError(f"Expected column names: {expected_names}, but found: {column_names}.")


if __name__ == '__main__':
    pass