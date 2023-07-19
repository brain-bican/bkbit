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

taxon_scientific_name = {'9606': 'Homo sapiens', '10090': 'Mus musculus', '9544': 'Macaca mulatta', '9483': 'Callithrix jacchus'}
taxon_common_name = {'9606': 'human', '10090': 'mouse', '9544': 'rhesus macaque', '9483': 'common marmoset'}
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
        cols = ['genome_annotation_label','gene_identifier_prefix','gene_local_unique_identifier','name','description', 'gene_biotype', 'taxon_unique_identifier']

    elif authority == 'Ensembl':
        out_cols = ['genome_annotation_label','gene_identifier_prefix','gene_id','Name','description','biotype', 'taxon_unique_identifier']
        cols = ['genome_annotation_label','gene_identifier_prefix','gene_local_unique_identifier','name','description', 'gene_biotype', 'taxon_unique_identifier']

    elif authority == 'GENCODE':
        out_cols = ['genome_annotation_label','gene_identifier_prefix','gene_id','gene_name','gene_type', 'taxon_unique_identifier']
        cols = ['genome_annotation_label','gene_identifier_prefix','gene_local_unique_identifier','name', 'gene_biotype', 'taxon_unique_identifier']

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
    [GeneAnnotation]: list of created GeneAnnotation objects using data from .csv file.
    
    """
    with open(file=file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        header = reader.fieldnames
        has_description = False
        if 'description' in header:
            has_description = True
        translatedannots = []
        for row in reader:
            myannotation = kbmodel.GeneAnnotation(id = row['gene_identifier_prefix'].upper().replace('ENE', 'ene') + ':' + row['gene_local_unique_identifier'].split('.')[0],
                                        symbol = row['name'],
                                        name = row['name'],
                                        referenced_in = genomeAnnot,
                                        molecular_type = kbmodel.BioType.protein_coding if row['gene_biotype'] == 'protein_coding' else kbmodel.BioType.noncoding, 
                                        source_id = row['gene_local_unique_identifier'].split('.')[0],
                                        in_taxon = [orgTaxon], 
                                        in_taxon_label = taxon_scientific_name[row['taxon_unique_identifier']]
                                        )
            if has_description:
                myannotation.description = urllib.parse.unquote(row["description"])
            translatedannots.append(myannotation)
    return translatedannots


def serialize_annotation_collection(annotations, outfile):
    """Serializes the annotation collection object to a JSON file.

    Parameters:  
    annotations (list): list of initialized classes from kbmodel
    outfile (str): path to output file

    """
    with open(outfile, 'w') as f:
        output_arr = []
        for g in annotations:
            #output_arr.append(g.dict(exclude_none=True))
            output_arr.append(g.dict())
        f.write(json.dumps(output_arr, indent=2))

def gff_to_gene_annotation(input_fname, data_dir, output_dir, genome_assembly_fname):
    """Converts GFF file(s) to GeneAnnotation objects and serializes them to a JSON file.

    Parameters:
    input_fname (str): name of csv file containing gff files
    data_dir (str): path to directory containing input file
    output_dir (str): path to output directory where generated files will be saved
    genome_assembly_fname (str): name of csv file containing genome assembly data

    """


    # orgTaxonObjects = {}
    # genomeAnnotObjects = []
    # geneAnnotObjects = []
    # checkSumObjects = []

    # GENERATE GENOME ASSEMBLY OBJECTS #
    genomeAssemblyObjects = generate_genome_assembly(os.path.join(data_dir,genome_assembly_fname)) 

    # ITERATE THROUGH GFF FILES #
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    with open(os.path.join(data_dir,input_fname), newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            fileObjects = []
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
            # if row['taxon_local_unique_identifier'] not in orgTaxonObjects:
            #     orgTaxonObjects[row['taxon_local_unique_identifier']] = kbmodel.OrganismTaxon(id = 'NCBITaxon:' + str(row['taxon_local_unique_identifier']), full_name = taxon_scientific_name[row['taxon_local_unique_identifier']], name = taxon_common_name[row['taxon_local_unique_identifier']],  iri = prefix_map['NCBITaxon'] + row['taxon_local_unique_identifier'])
            # curr_org_taxon = orgTaxonObjects[row['taxon_local_unique_identifier']]
            curr_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:' + str(row['taxon_local_unique_identifier']), full_name = taxon_scientific_name[row['taxon_local_unique_identifier']], name = taxon_common_name[row['taxon_local_unique_identifier']],  iri = prefix_map['NCBITaxon'] + row['taxon_local_unique_identifier'])

            # GENERATE CHECKCSUM OBJECT #
            curr_digest_256 = generate_digest('sha256', df)
            #checkSumObjects.append(curr_digest_256)

            # GENERATE GENOME ANNOTATION OBJECT #
            curr_genome_annot = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + row['label'].upper(), digest=[curr_digest_256], content_url = [row['url']], reference_assembly = genomeAssemblyObjects[row['assembly_local_unique_identifier'].strip()], version = row['version'], in_taxon = [curr_org_taxon], in_taxon_label = taxon_scientific_name[row['taxon_local_unique_identifier']], description = row['description'], authority = row['authority'].upper())
            #print(f'GenomeAnnotation object is created: {curr_genome_annot}')
            #genomeAnnotObjects.append(curr_genome_annot)
            
            # GENERATE GENE ANNOTATION OBJECT #
            annotations = create_gene_annotation_objects(file, curr_genome_annot, curr_org_taxon)
            #geneAnnotObjects.extend(annotations)

            # COMBINE ALL GENERATED OBJECTS RELATED TO THIS GFF FILE:
            fileObjects.append(genomeAssemblyObjects[row['assembly_local_unique_identifier'].strip()])
            fileObjects.append(curr_genome_annot)
            fileObjects.append(curr_org_taxon)
            fileObjects.append(curr_digest_256) 
            fileObjects.extend(annotations)
            output_ser = os.path.join(output_dir, gene_name +'.json')
            serialize_annotation_collection(fileObjects, output_ser)
            print(f'Serialized GeneAnnotation objects saved here: {output_ser}')


#--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------#
            
    # orgTaxon_file = os.path.join(output_dir, 'organismTaxon.json')
    # genomeAnnot_file = os.path.join(output_dir, 'genomeAnnotation.json')
    # genomeAssem_file = os.path.join(output_dir, 'genomeAssembly.json')
    # geneAnnot_file = os.path.join(output_dir, 'geneAnnotation.json')
    # checkSum_file = os.path.join(output_dir, 'checksum.json')

    # serialize_annotation_collection(list(orgTaxonObjects.values()), orgTaxon_file)
    # serialize_annotation_collection(genomeAnnotObjects, genomeAnnot_file)
    # serialize_annotation_collection(list(genomeAssemblyObjects.values()), genomeAssem_file)
    # serialize_annotation_collection(checkSumObjects, checkSum_file)
    # serialize_annotation_collection(geneAnnotObjects, geneAnnot_file)
    
    


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
            currGenomeAssem = kbmodel.GenomeAssembly(id = "NCBIAssembly:" + id, in_taxon = [currOrgTaxon], in_taxon_label = taxon_scientific_name[str(row.taxon_local_unique_identifier)],  version = row.version, name = row.label)
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


if __name__ == '__main__':
    pass
    