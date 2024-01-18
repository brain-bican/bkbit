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

## GLOBAL VARIABLES ##

taxon_scientific_name = {'9606': 'Homo sapiens', '10090': 'Mus musculus', '9544': 'Macaca mulatta', '9483': 'Callithrix jacchus'}
taxon_common_name = {'9606': 'human', '10090': 'mouse', '9544': 'rhesus macaque', '9483': 'common marmoset'}
prefix_map = {"NCBITaxon": "http://purl.obolibrary.org/obo/NCBITaxon_", "NCBIGene": "http://identifiers.org/ncbigene/", "ENSEMBL": "http://identifiers.org/ensembl/", "NCBIAssembly": "https://www.ncbi.nlm.nih.gov/assembly/"}
genome_annotation_input_file_column_names = {'authority_identifier_prefix', 'assembly_local_unique_identifier', 'label', 'taxon_identifier_prefix', 'taxon_local_unique_identifier', 'authority', 'version', 'gene_identifier_prefix', 'description', 'url'}

## FUNCTIONS ##

def gff_to_gene_annotation(input_fname, data_dir, output_dir, genome_assembly_fname):
    """Converts GFF file(s) to GeneAnnotation objects and serializes them to a JSON file.

    Parameters:
    input_fname (str): name of csv file containing gff files
    data_dir (str): path to directory containing input file
    output_dir (str): path to output directory where generated files will be saved
    genome_assembly_fname (str): name of csv file containing genome assembly data

    """
     #! TODO: ADD option for user to give hash algorithm

    # GENERATE GENOME ASSEMBLY OBJECTS #
    #! TODO: Validate column names for genome assembly 
    genomeAssemblyObjects = generate_genome_assembly(os.path.join(data_dir,genome_assembly_fname)) 

    # ITERATE THROUGH ALL GFF3 FILES PROVIDED IN CSV #
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(data_dir,input_fname), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        
        # Check if column names match expected column names
        validate_column_names(reader.fieldnames, genome_annotation_input_file_column_names)
        
        for row in reader:
            filter_and_parse_gff3(**row, data_dir=data_dir, output_dir=output_dir, genomeAssemblyObjects=genomeAssemblyObjects)
            

def filter_and_parse_gff3(authority_identifier_prefix, assembly_local_unique_identifier, label, taxon_identifier_prefix, taxon_local_unique_identifier, authority, version, gene_identifier_prefix, description, url, data_dir, output_dir, genomeAssemblyObjects, feature_type_filter=['gene', 'pseudogene', 'ncRNA_gene']):
    print(f"AUTHORITY: {authority}, LABEL: {label}, TAXON_LOCAL_UNIQUE_ID: {taxon_local_unique_identifier}, VERSION: {version}, GENE_ID_PREFIX: {gene_identifier_prefix}, URL: {url}")
    gene_name = ''.join(url.split('/')[-1].split('.')[0:-2])
    print("GENE NAME: ", gene_name)

    if os.path.isfile(data_dir + '/' + gene_name + '.csv'):
        print(f"Data from url is already downloaded and saved here: {data_dir + '/' + gene_name + '.csv'}")
        df = pd.read_csv(data_dir + '/' + gene_name + '.csv') 
    else:
        print(f"Downloading and saving data from url here: {data_dir + '/' + gene_name + '.csv'}")
        gffcols = ['seqid','source','type','start','end','score','strand','phase','attributes'] # gff3 file column names
        df = pd.read_csv(url, sep='\t', comment = "#", header=None, names=gffcols)
        df.to_csv(data_dir + '/' + gene_name + '.csv', index=False)

    # FILTER FOR GENE FEATURES #
    pred = [x in feature_type_filter for x in df['type']]
    df_gene = df[pred].copy(deep=True)
    print(f'LENGTH OF DATAFRAME AFTER FILTERING FOR GENES: {len(df_gene)}')
    df_gene.to_csv(data_dir + '/' + gene_name + '_genefilter.csv', index=False) 

    # STORES ALL GENERATED OBJECTS RELATED TO THIS GFF3 FILE #
    fileObjects = []

    # GENERATE ORGANISM TAXON OBJECT #
    curr_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:' + str(taxon_local_unique_identifier), full_name = taxon_scientific_name[taxon_local_unique_identifier], name = taxon_common_name[taxon_local_unique_identifier],  iri = prefix_map['NCBITaxon'] + taxon_local_unique_identifier)

    # GENERATE CHECKSUM OBJECT #
    curr_digest_256 = generate_digest('sha256', requests.get(url).content)

    # GENERATE GENOME ANNOTATION OBJECT #
    if authority.strip().upper() == kbmodel.AuthorityType.NCBI.value:
        authority_type = kbmodel.AuthorityType.NCBI
    elif authority.strip().upper() == kbmodel.AuthorityType.ENSEMBL.value:
        authority_type = kbmodel.AuthorityType.ENSEMBL
    else:
        raise Exception(f'Authority {authority} is not supported. Please use NCBI or Ensembl.')
    curr_genome_annot = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + label.upper(), 
                                                    digest = [curr_digest_256.id], 
                                                    content_url = [url], 
                                                    reference_assembly = genomeAssemblyObjects[assembly_local_unique_identifier.strip()].id, 
                                                    version = version, 
                                                    in_taxon = [curr_org_taxon.id], 
                                                    in_taxon_label = taxon_scientific_name[taxon_local_unique_identifier], 
                                                    description = authority_type.value + ' ' + taxon_scientific_name[taxon_local_unique_identifier] + ' Annotation Release ' + version.strip(), # Format for description: <authority> <taxon_scientific_name> Annotation Release <version>; i.e. NCBI Homo sapiens Annotation Release 110
                                                    authority = authority_type
                                                )
    
    # GENERATE GENE ANNOTATION OBJECT #
    curr_gene_annots = generate_gene_annotations(df_gene, curr_genome_annot, curr_org_taxon, gene_identifier_prefix, taxon_local_unique_identifier)
    print(f'NUMBER OF GENE ANNOTATIONS: {len(curr_gene_annots)}')

    # COMBINE ALL GENERATED OBJECTS RELATED TO THIS GFF FILE #
    fileObjects.append(genomeAssemblyObjects[assembly_local_unique_identifier.strip()])
    fileObjects.append(curr_genome_annot)
    fileObjects.append(curr_org_taxon)
    fileObjects.append(curr_digest_256) 
    fileObjects.extend(curr_gene_annots)
    output_ser = os.path.join(output_dir, gene_name +'.json')
    serialize_annotation_collection(fileObjects, output_ser)
    print(f'Serialized GeneAnnotation objects saved here: {output_ser}')

def generate_gene_annotations(df, genomeAnnot, orgTaxon, gene_identifier_prefix, taxon_id):
    """Creates a gene annotation object for every row in the provided dataframe.

    Parameters:
    df (pandas.DataFrame): dataframe containing gene annotations and respective metadata
    genomeAnnot (GenomeAnnotation): reference to GenomeAnnotation object 
    orgTaxon (OrganismTaxon): reference to OrganismTaxon object 
    gene_identifier_prefix (str): gene identifier 
    taxon_id (str): taxon id 

    Returns:
    gene_annotations.values() (List[GeneAnnotations]): list of gene annotations created

    """
    gene_annotations = dict()

    for row in df.itertuples():
        attributes = dict([x.split('=') for x in row.attributes.split(';')])
        description = urllib.parse.unquote(attributes.get("description"))
        #! TODO: strip and lower gene_identifier_prefix
        if gene_identifier_prefix == 'ncbigene':
            db_xref = dict([x.split(':', 1) for x in attributes['Dbxref'].split(',')]) if 'Dbxref' in attributes else {}
            stable_id = db_xref['GeneID'].split('.')[0]
            id = gene_identifier_prefix.upper().replace('ENE', 'ene') + ':' + stable_id 
            source_id = stable_id
            molecular_type = kbmodel.BioType.protein_coding if attributes.get('gene_biotype') == 'protein_coding' else kbmodel.BioType.noncoding
            synonym = attributes.get('gene_synonym').split(',')
        elif gene_identifier_prefix == 'ensembl':
            description = re.sub(r"\[source .*?\]", "", description)
            stable_id = attributes['gene_id'].split('.')[0]
            id = gene_identifier_prefix.upper() + ':' + stable_id 
            source_id = stable_id
            molecular_type = kbmodel.BioType.protein_coding if attributes.get('biotype') == kbmodel.BioType.protein_coding.value else kbmodel.BioType.noncoding
            synonym = None

        # CHECK FOR DUPLICATE GENE IDS #
        if source_id in gene_annotations:
            if (gene_annotations[source_id].name != attributes.get('Name')):
                raise Exception(f'GeneID {source_id} has multiple names.')
            if (gene_annotations[source_id].molecular_type != molecular_type):
                gene_annotations[source_id].molecular_type = kbmodel.BioType.noncoding
        else:
            curr_gene_annot = kbmodel.GeneAnnotation(id = id, symbol = attributes.get('Name'), name = attributes.get('Name'), referenced_in = genomeAnnot.id, 
                                                     molecular_type = molecular_type, source_id = source_id, in_taxon = [orgTaxon.id], 
                                                     in_taxon_label = taxon_scientific_name[taxon_id], description = description, synonym = synonym)
            gene_annotations[source_id] = curr_gene_annot
    return gene_annotations.values()


def generate_genome_assembly(file_path):
    ''' Creates GenomeAssembly objects from the given file path. 
    Parameters:
    file_path (str): Path to the file containing the genome assembly data.

    Returns: 
    [GeneomeAssembly]: list of GenomeAssembly objects created from the given file path

    '''
    df = pd.read_csv(file_path) 
    genomeAssemblyObjects = {}
    for row in df.itertuples(index=False):
        id = row.local_unique_identifier.strip()
        if row.local_unique_identifier not in genomeAssemblyObjects:
            currOrgTaxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:' + str(row.taxon_local_unique_identifier), full_name = taxon_scientific_name[str(row.taxon_local_unique_identifier)], name = taxon_common_name[str(row.taxon_local_unique_identifier)],  iri = prefix_map['NCBITaxon'] + str(row.taxon_local_unique_identifier))
            currGenomeAssem = kbmodel.GenomeAssembly(id = "NCBIAssembly:" + id, 
                                                     in_taxon = [currOrgTaxon.id], 
                                                     in_taxon_label = taxon_scientific_name[str(row.taxon_local_unique_identifier)],
                                                     version = str(row.version), 
                                                     name = row.label)
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
    # Generate a UUID version 4
    uuid_value = uuid.uuid4()

    # Construct a URN with the UUID
    urn = f"urn:uuid:{uuid_value}"
    
    #! TODO: ADD else statement in case user has given an invalid hash 
   
    # Create a Checksum object
    if hash == 'sha256':
        digest = hashlib.sha256(data).hexdigest()
        return kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.SHA256, value = digest)
    elif hash == 'md5':
        digest = hashlib.md5(data).hexdigest()
        return kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.MD5, value = digest)
    elif hash == 'sha1':
        digest = hashlib.sha1(data).hexdigest()
        return kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.SHA1, value = digest)


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