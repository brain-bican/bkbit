## IMPORTS ##
import pandas as pd
import os
import csv
import json
from bkbit.models import kbmodel

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
        out_cols = ['genome_annotation_label','gene_identifier_prefix','gene_id','Name','description','biotype', 'taxon_unique_identifier']

    # ATTRIBUTES FOR GENE ANNOTATION OBJECT:
    cols = ['genome_annotation_label','gene_identifier_prefix','gene_local_unique_identifier','name','description', 'gene_biotype', 'taxon_unique_identifier']

    # create output dataframe
    out_df = df_gene[out_cols]
    out_df.columns = cols

    fname = 'gene_annotation_%s-%s-%s.csv' % (authority, str(taxon_local_unique_id), str(version))
    file = os.path.join(output_dir, fname)
    out_df.to_csv(file, index=False)


def create_gene_annotation_objects(file):
    """Initializes GeneAnnotation objects using data from .csv file.

    Parameters:
    file (str): path to .csv file containing gene data.

    Returns:
    AnnotationCollection: AnnotationCollection object containing list of initialized GeneAnnotation objects.
    
    """
    taxon_uri = {'9606': 'NCBITaxon:9606', '10090': 'NCBITaxon:10090'}
    taxon_name = {'9606': 'Homo sapiens', '10090': 'Mus musculus'}
    with open(file=file, newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        translatedannots = []
        for row in reader:
            myannotation = kbmodel.GeneAnnotation(id = row['gene_identifier_prefix'].upper().replace('ENE', 'ene') + ':' + row['gene_local_unique_identifier'],
                                        symbol = row['name'],
                                        name = row['name'],
                                        description = row['description'],
                                        referenced_in = row['genome_annotation_label'],
                                        molecular_type = row['gene_biotype'] if row['gene_biotype'] == 'protein_coding' else 'noncoding', #TODO: confirm if noncoding for the rest of the values or parse them as new enum values)
                                        source_id = row['gene_local_unique_identifier'],
                                        in_taxon = [kbmodel.OrganismTaxon(id=taxon_uri[row['taxon_unique_identifier']])],
                                        in_taxon_label = taxon_name[row['taxon_unique_identifier']]
                                        )
            translatedannots.append(myannotation)
    return kbmodel.AnnotationCollection(annotations=translatedannots)


def serialize_annotation_collection(annotations, outfile):
    """Serializes the annotation collection object to a JSON file.

    Parameters:  
    annotations (AnnotationCollection): AnnotationCollection object containing list of initialized GeneAnnotation objects.
    outfile (str): path to output file

    """
    with open(outfile, 'w') as f:
        output_arr = []
        for g in annotations.annotations:
            output_arr.append(g.dict(exclude_none=True))
        f.write(json.dumps(output_arr, indent=2))
        print(f'Serialized AnnotationCollection object saved here: {outfile}')


def gff_to_gene_annotation(input_fname, data_dir, output_dir):
    """Converts GFF file(s) to GeneAnnotation objects and serializes them to a JSON file.

    Parameters:
    gff_files_path (str): path .csv that contains GFF file(s)
    output_dir (str): path to output directory

    """
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

            fname = 'gene_annotation_%s-%s-%s.csv' % (row['authority'], str(row['taxon_local_unique_identifier']), str(row['version']))
            file = os.path.join(output_dir, fname)
            if not os.path.isfile(file):
                parse_data(df, row['authority'], row['label'], row['taxon_local_unique_identifier'], row['version'], row['gene_identifier_prefix'], output_dir)
            print(f'Parsed DF containing GeneAnnotation class attribute values is saved here: {file}')
            
            annotations = create_gene_annotation_objects(file)
            output_ser = os.path.join(output_dir, gene_name +'.json')
            serialize_annotation_collection(annotations, output_ser)

if __name__ == '__main__':
    rev = '20230412_subset_genome_annotation'

    # check if directories exist and create them if they don't

    # data_dir is the path where the .csv containing the .gff files exists
    data_dir = '../source-data/' + rev 
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)

    # output_dir is the path where all the generated files will be saved
    output_dir = '../source-data/' + rev + '/output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    gff_to_gene_annotation(data_dir, output_dir)



