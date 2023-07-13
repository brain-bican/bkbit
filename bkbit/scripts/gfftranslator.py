## IMPORTS ##

import pandas as pd
import os
import csv
import json
import hashlib
import uuid
import urllib.parse
from bkbit.models import kbmodel

## GLOBAL VARIABLES ##
taxon_scientific_name = {'9606': 'Homo sapiens', '10090': 'Mus musculus'}
taxon_common_name = {'9606': 'human', '10090': 'house mouse'}

prefix_map = {"NCBITaxon": "http://purl.obolibrary.org/obo/NCBITaxon_", "NCBIGene": "http://identifiers.org/ncbigene/", "ENSEMBL": "http://identifiers.org/ensembl/", "NCBIAssembly": "https://www.ncbi.nlm.nih.gov/assembly/"}
## FUNCTIONS ##

def parse_data(df, authority, label, taxon_local_unique_id, version, gene_id_prefix, output_dir):
    """Generates a .csv file in which the columns are a subset of the GeneAnnotation class attributes. 
    Parameters: 
    df (pandas.DataFrame): 
    label (str):
    taxon_local_unique_id (str):
    version (str):
    gene_id_prefix (str):

    """
    # filter the dataframe to only genes
    pred = [x in ['gene','ncRNA_gene','pseudogene'] for x in df['type'] ]
    df_gene = df[pred].copy(deep=True)
    ngene = len(df_gene)
    print("-- number of genes = %d" % ngene)

    # break attributes into components #
    print("-- parse attributes")
    count = 0
    for gindex, grow in df_gene.iterrows() :
        # split attribute string by semicolon
        astr = grow['attributes']
        arr = astr.split(';')
        # break each component into label-value pair and put into a dictionary
        adict = {}
        attribute_set = set()
        for att in arr :
            apart = att.split('=')
            adict[apart[0]] = apart[1]
            attribute_set.add(apart[0])

        print(f'SET OF KEYS: {adict.keys()}')
        # add as columns in the dataframe
        for x in adict :
            df_gene.loc[gindex,x] = adict[x]
        count += 1

        if count % 10000 == 0 :
            print(count,ngene)
    print('SET OF ATTRIBUTES: ', attribute_set)
    print("--------DATAFRAME ------- \n", df_gene.columns.values)

    # break database crossreference into components #
    if authority == 'NCBI' :
        print("-- parse db crossreference")
        # break Dbxref into its components
        count = 0
        for gindex, grow in df_gene.iterrows() :

            # split Dbxref string by semicolon
            astr = grow['Dbxref']
            arr = astr.split(',')

            # break each component into label-value pair and put into a dictionary
            adict = {}
            for att in arr :
                apart = att.split(':',1)
                adict[apart[0]] = apart[1]

            # add as columns in the dataframe
            for x in adict :
                df_gene.loc[gindex,x] = adict[x]
            count += 1

            if count % 10000 == 0 :
                print(count,ngene)

    # prepare output dataframe
    print("-- prepare output dataframe and file")
    
    df_gene['genome_annotation_label'] = label
    df_gene['gene_identifier_prefix'] = gene_id_prefix
    df_gene['taxon_unique_identifier'] = taxon_local_unique_id

    # authority specific mapping and transforms
    if authority == 'NCBI' :
        out_cols = ['genome_annotation_label','gene_identifier_prefix','GeneID','Name','description','gene_biotype', 'taxon_unique_identifier']
    elif authority == 'Ensembl':
        #out_cols = ['genome_annotation_label','gene_identifier_prefix','gene_id','Name','description','biotype', 'taxon_unique_identifier']
        out_cols = ['genome_annotation_label','gene_identifier_prefix','gene_id','Name','description','biotype', 'taxon_unique_identifier']

    # ATTRIBUTES FOR GENE ANNOTATION OBJECT:
    cols = ['genome_annotation_label','gene_identifier_prefix','gene_local_unique_identifier','name','description', 'gene_biotype', 'taxon_unique_identifier']

    # create output dataframe
    out_df = df_gene[out_cols]
    out_df.columns = cols

    fname = 'gene_annotation_%s-%s-%s.csv' % (authority, str(taxon_local_unique_id), str(version))
    file = os.path.join(output_dir, fname)
    out_df.to_csv(file, index=False)


def create_gene_annotation_objects(file, genomeAnnot, orgTaxon):
    """Initializes GeneAnnotation objects using data from .csv file.

    Parameters:
    file (str): path to .csv file containing gene data.
    orgTaxon (OrganismTaxon): reference to organism taxon object.
    genomeAnn (GenomeAnnotation): reference to genome annotation object.

    Returns:
    AnnotationCollection: AnnotationCollection object containing list of initialized GeneAnnotation objects.
    
    """
    with open(file=file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        translatedannots = []
        for row in reader:
            #print(f'***GENEID: {row["gene_local_unique_identifier"]}')
            myannotation = kbmodel.GeneAnnotation(id = row['gene_identifier_prefix'].upper().replace('ENE', 'ene') + ':' + row['gene_local_unique_identifier'],
                                        symbol = row['name'],
                                        name = row['name'],
                                        description = f'"{urllib.parse.unquote(row["description"])}"',
                                        referenced_in = genomeAnnot, # referenced_in:[GenomeAnnotation]
                                        molecular_type = kbmodel.BioType.protein_coding if row['gene_biotype'] == 'protein_coding' else kbmodel.BioType.noncoding, 
                                        source_id = row['gene_local_unique_identifier'],
                                        in_taxon = [orgTaxon], # in_taxon:[OrganismTaxon]
                                        in_taxon_label = taxon_scientific_name[row['taxon_unique_identifier']]
                                        )
            #print(f'GeneAnnotation: {myannotation}')
            translatedannots.append(myannotation)
    #return kbmodel.AnnotationCollection(annotations=translatedannots)
    return translatedannots


def serialize_annotation_collection(annotations, outfile):
    """Serializes the annotation collection object to a JSON file.

    Parameters:  
    annotations (list): list of initialized classes from kbmodel
    outfile (str): path to output file

    """
    with open(outfile, 'w') as f:
        output_arr = []
        #for g in annotations.annotations:
        for g in annotations:
            #output_arr.append(g.dict(exclude_none=True))
            output_arr.append(g.dict())
        f.write(json.dumps(output_arr, indent=2))

def gff_to_gene_annotation(input_fname, data_dir, output_dir, genome_assembly_fname):
    """Converts GFF file(s) to GeneAnnotation objects and serializes them to a JSON file.

    Parameters:
    gff_files_path (str): path .csv that contains GFF file(s)
    output_dir (str): path to output directory

    """

    genomeAssemblyObjects = generate_genome_assembly(os.path.join(data_dir,genome_assembly_fname))
    orgTaxonObjects = {}
    genomeAnnotObjects = []
    geneAnnotObjects = []
    checkSumObjects = []
    
    # GENERATE GENOME ASSEMBLY OBJECT #
    genomeAssemblyObjects = generate_genome_assembly(os.path.join(data_dir,genome_assembly_fname))

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(data_dir,input_fname), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            print(f"AUTHORITY: {row['authority']}, LABEL: {row['label']}, TAXON_LOCAL_UNIQUE_ID: {row['taxon_local_unique_identifier']}, VERSION: {row['version']}, GENE_ID_PREFIX: {row['gene_identifier_prefix']}, URL: {row['url']}")
            gene_name = ''.join(row['url'].split('/')[-1].split('.')[0:-2])
            print("GENE NAME: ", gene_name)
            if os.path.isfile(data_dir + '/' + gene_name + '.csv'):
                print(f"Data from url is already downloaded and saved here: {data_dir + '/' + gene_name + '.csv'}")
                df = pd.read_csv(data_dir + '/' + gene_name + '.csv') 
            else:
                print(f"Downloading and saving data from url here: {data_dir + '/' + gene_name + '.csv'}")
                gffcols = ['seqid','source','type','start','end','score','strand','phase','attributes'] # gff columns
                df = pd.read_csv(row['url'], sep='\t', comment = "#", header=None, names=gffcols)
                df.to_csv(data_dir + '/' + gene_name + '.csv', index=False)

            # LOAD GFF FILE AND SAVE TO CSV #
            fname = 'gene_annotation_%s-%s-%s.csv' % (row['authority'], str(row['taxon_local_unique_identifier']), str(row['version']))
            file = os.path.join(output_dir, fname)
            if not os.path.isfile(file):
                parse_data(df, row['authority'], row['label'], row['taxon_local_unique_identifier'], row['version'], row['gene_identifier_prefix'], output_dir)
            print(f'Parsed DF containing GeneAnnotation class attribute values is saved here: {file}')

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
                        
            # GENERATE ORGANISM TAXON OBJECT #
            if row['taxon_local_unique_identifier'] not in orgTaxonObjects:
                orgTaxonObjects[row['taxon_local_unique_identifier']] = kbmodel.OrganismTaxon(id = 'NCBITaxon:' + str(row['taxon_local_unique_identifier']), full_name = taxon_scientific_name[row['taxon_local_unique_identifier']], name = taxon_common_name[row['taxon_local_unique_identifier']],  iri = prefix_map['NCBITaxon'] + row['taxon_local_unique_identifier'])
            curr_org_taxon = orgTaxonObjects[row['taxon_local_unique_identifier']]

            # GENERATE GENOME ANNOTATION OBJECT #
            curr_digest_256 = generate_digest('sha256', df)
            checkSumObjects.append(curr_digest_256)
            curr_genome_annot = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + row['label'].upper(), digest=[curr_digest_256], content_url = [row['url']], reference_assembly = genomeAssemblyObjects[row['assembly_local_unique_identifier'].strip()], version = row['version'], in_taxon = [curr_org_taxon], in_taxon_label = taxon_scientific_name[row['taxon_local_unique_identifier']], description = row['description'])
            #print(f'GenomeAnnotation object is created: {curr_genome_annot}')
            genomeAnnotObjects.append(curr_genome_annot)

            annotations = create_gene_annotation_objects(file, curr_genome_annot, curr_org_taxon)
            geneAnnotObjects.extend(annotations)
            # output_ser = os.path.join(output_dir, gene_name +'.json')
            # serialize_annotation_collection(annotations.annotations, output_ser)
            # print(f'Serialized GeneAnnotation objects saved here: {output_ser}')

#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
            
    orgTaxon_file = os.path.join(output_dir, 'organismTaxon.json')
    genomeAnnot_file = os.path.join(output_dir, 'genomeAnnotation.json')
    genomeAssem_file = os.path.join(output_dir, 'genomeAssembly.json')
    geneAnnot_file = os.path.join(output_dir, 'geneAnnotation.json')
    checkSum_file = os.path.join(output_dir, 'checksum.json')

    serialize_annotation_collection(list(orgTaxonObjects.values()), orgTaxon_file)
    serialize_annotation_collection(genomeAnnotObjects, genomeAnnot_file)
    serialize_annotation_collection(list(genomeAssemblyObjects.values()), genomeAssem_file)
    serialize_annotation_collection(checkSumObjects, checkSum_file)
    serialize_annotation_collection(geneAnnotObjects, geneAnnot_file)
    
    


def generate_genome_assembly(file_path):
    if not os.path.isfile(file_path):
        print(f"{file_path} does not exist.")
    # cols = identifier_prefix, local_unique_identifier, taxon_identifier_prefix, taxon_local_unique_identifier, version, label, description
    df = pd.read_csv(file_path) 
    genomeAssemblyObjects = {}
    for row in df.itertuples(index=False):
        id = row.local_unique_identifier.strip()
        if row.local_unique_identifier not in genomeAssemblyObjects:
            currOrgTaxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:' + str(row.taxon_local_unique_identifier), full_name = taxon_scientific_name[str(row.taxon_local_unique_identifier)], name = taxon_common_name[str(row.taxon_local_unique_identifier)],  iri = prefix_map['NCBITaxon'] + str(row.taxon_local_unique_identifier))

            genomeAssemblyObjects[id] = kbmodel.GenomeAssembly(id = "NCBIAssembly:" + id, in_taxon = [currOrgTaxon], in_taxon_label = taxon_scientific_name[str(row.taxon_local_unique_identifier)],  version = row.version, label = row.label, description = row.description)
    print(f"GenomeAssembly objects are created: {genomeAssemblyObjects}")
    return genomeAssemblyObjects


def generate_digest(hash, data):
    # Generate a UUID version 4
    uuid_value = uuid.uuid4()

    # Construct a URN with the UUID
    urn = f"urn:uuid:{uuid_value}"
    
    # Create a Checksum object
    data_bytes = data.to_csv().encode('utf-8') 
    if hash == 'sha256':
        digest = hashlib.sha256(data_bytes).hexdigest()
        return kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.SHA256, value = digest)
    elif hash == 'md5':
        digest = hashlib.md5(data_bytes).hexdigest()
        return kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.MD5, value = digest)
    elif hash == 'sha1':
        digest = hashlib.sha1(data_bytes).hexdigest()
        return kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.SHA1, value = digest)


def gtf_to_gene_annotation(fname, data_dir, output_dir,taxon_id, label, authority):
    gffcols = ['seqid','source','type','start','end','score','strand','phase','attributes'] # gff columns
    df = pd.read_csv(os.join(data_dir, fname), sep='\t', comment = "#", header=None, names=gffcols)
    df.to_csv(data_dir + '/' + fname + '.csv', index=False)


if __name__ == '__main__':
    pass
    