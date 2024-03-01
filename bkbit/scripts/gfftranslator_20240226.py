from collections import defaultdict
import re
import hashlib
import uuid
import logging
import urllib
import os
from bkbit.models import kbmodel

logging.basicConfig(filename='gff3_translator.log', format='%(levelname)s: %(message)s (%(asctime)s)', datefmt='%m/%d/%Y %I:%M:%S %p', level=logging.INFO)
logger = logging.getLogger(__name__)


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


class Gff3():
    generate_methods = {}
    def __init__(self, gff_file, taxon_id, assembly_id, assembly_version, assembly_label, genome_label:str, genome_version:str, genome_authority:str, hash_functions:list[str], assembly_strain=None): #!logger=logger <- do we need to add this
        self.gff_file = gff_file #! should this be a file path or a url?
        self.logger = logger
        self.taxon_id = taxon_id #* Note: we might be able to remove this
        self.authority = self.assign_authority_type(genome_authority)
        #TODO: maybe allow the inputs to be optional at initialization and then set them later
        self.organism_taxon = self.generate_organism_taxon(taxon_id)
        self.genome_assembly = self.generate_genome_assembly(assembly_id, assembly_version, assembly_label, assembly_strain)
        self.checksums = self.generate_digest(hash_functions)
        self.genome_annotation = self.generate_genome_annotation(genome_label, genome_version)
        self.gene_annotations = dict()
        
        
    def generate_organism_taxon(self, taxon_id:str):
        """
        Generates an organism taxon object based on the provided taxon ID.

        Args:
            taxon_id (str): The taxon ID of the organism.

        Returns:
            kbmodel.OrganismTaxon: The generated organism taxon object.
        """
        self.logger.debug('Generating organism taxon')
        return kbmodel.OrganismTaxon(id = TAXON_PREFIX + ':' + taxon_id,
                                     full_name = TAXON_SCIENTIFIC_NAME[taxon_id],
                                     name = TAXON_COMMON_NAME[taxon_id],
                                     iri = PREFIX_MAP[TAXON_PREFIX] + taxon_id)
    
    def assign_authority_type(self, authority:str):
        """
        Assigns the authority type based on the given authority string.

        Args:
            authority (str): The authority string to be assigned.

        Returns:
            kbmodel.AuthorityType: The corresponding authority type.

        Raises:
            Exception: If the authority is not supported. Only NCBI and Ensembl authorities are supported.
        """
        self.logger.debug('Assigning authority type')
        if authority.upper() == kbmodel.AuthorityType.NCBI.value:
            return kbmodel.AuthorityType.NCBI
        if authority.upper() == kbmodel.AuthorityType.ENSEMBL.value:
            return kbmodel.AuthorityType.ENSEMBL
        logger.critical('Authority %s is not supported. Please use NCBI or Ensembl.', authority)
        raise ValueError(f'Authority {self.authority} is not supported. Please use NCBI or Ensembl.')

    def generate_genome_assembly(self, assembly_id:str, assembly_version:str, assembly_label:str, assembly_strain:str=None):
        self.logger.debug('Generating genome assembly')
        return kbmodel.GenomeAssembly(id = ASSEMBLY_PREFIX + ":" + assembly_id, 
                                                     in_taxon = [self.organism_taxon.id],
                                                     in_taxon_label = self.organism_taxon.full_name,
                                                     version = assembly_version,
                                                     name = assembly_label,
                                                     strain = assembly_strain)

    def generate_genome_annotation(self, genome_label:str, genome_version:str):
        self.logger.info('Generating genome annotation')
        return kbmodel.GenomeAnnotation(id = BICAN_ANNOTATION_PREFIX + genome_label.upper(), 
                                                    digest = [checksum.id for checksum in self.checksums], 
                                                    content_url = [self.gff_file], 
                                                    reference_assembly = self.genome_assembly.id, 
                                                    version = genome_version, 
                                                    in_taxon = [self.organism_taxon.id], 
                                                    in_taxon_label = self.organism_taxon.full_name, 
                                                    description = self.authority.value + ' ' + self.organism_taxon.full_name + ' Annotation Release ' + genome_version, # Format for description: <authority> <TAXON_SCIENTIFIC_NAME> Annotation Release <version>; i.e. NCBI Homo sapiens Annotation Release 110
                                                    authority = self.authority)
    
    def generate_digest(self, hash_functions:list[str]) -> list[kbmodel.Checksum]:
        checksums = []
        # gff_data = requests.get(url).content #! only needed if data is provided in url  
        gff_data = self.gff_file.encode('utf-8')
        # Generate a UUID version 4
        uuid_value = uuid.uuid4()

        # Construct a URN with the UUID
        urn = f"urn:uuid:{uuid_value}"
        for hash_type in hash_functions: 

            hash_type = hash_type.strip().upper()
            # Create a Checksum object
            if hash_type == 'SHA256':
                digest = hashlib.sha256(gff_data).hexdigest()
                checksums.append(kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.SHA256, value = digest))
            elif hash_type == 'MD5':
                digest = hashlib.md5(gff_data).hexdigest()
                checksums.append(kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.MD5, value = digest))
            elif hash_type == 'SHA1':
                digest = hashlib.sha1(gff_data).hexdigest()
                checksums.append(kbmodel.Checksum(id = urn, checksum_algorithm = kbmodel.DigestType.SHA1, value = digest))
            else:
                #raise ValueError(f'Hash algorithm {hash} is not supported. Please use SHA256, MD5, or SHA1.')
                #! Check if this error message works correctly 
                logger.error('Hash algorithm %s is not supported. Please use SHA256, MD5, or SHA1.', hash_type)
        return checksums
    
    def parse(self, feature_filter):
        curr_line_num = 0
        if not os.path.isfile(self.gff_file):
            raise FileNotFoundError(f'File {self.gff_file} does not exist.')
        with open(self.gff_file, 'r') as file:
            for line_raw in file:
                curr_line_num += 1
                line_strip = line_raw.strip()
                if curr_line_num == 1 and not line_strip.startswith('##gff-version 3'):
                    logger.critical('Line %s: ##gff-version 3" missing from the first line.', curr_line_num)
                elif len(line_strip) == 0: # blank line
                    continue
                elif line_strip.startswith('##'): #TODO: parse more metadata
                    pass
                elif line_strip.startswith('#'): #TODO: parse more metadata
                    pass
                else: # line may be a feature or unknown
                    tokens = list(map(str.strip, line_raw.split('\t')))
                    if len(tokens) != 9:
                        logger.warning('Line %s: Features are expected 9 columns, found %s.', curr_line_num, len(tokens))
                    if tokens[2] in feature_filter: # only look at rows that have a type that is included in feature_filter
                        attributes = self.__merge_values(tuple(a.split('=')for a in tokens[8].split(';')))
                        logger.info(attributes)
                        #TODO: Write cleaner code that calls respective generate function based on the authority automatically
                        if self.genome_annotation.authority == kbmodel.AuthorityType.ENSEMBL:
                            gene_annotation = self.generate_ensembl_gene_annotation(attributes, curr_line_num)
                            if gene_annotation is not None:
                                self.gene_annotations[gene_annotation] = gene_annotation
                        elif self.genome_annotation.authority == kbmodel.AuthorityType.NCBI:
                            gene_annotation = self.generate_ncbi_gene_annotation(attributes, curr_line_num)
                            if gene_annotation is not None:
                                self.gene_annotations[gene_annotation.id] = gene_annotation


    def generate_ensembl_gene_annotation(self, attributes, curr_line_num):
        if 'gene_id' in attributes:
            if len(attributes['gene_id']) != 1:
                logger.error('Line %s: No GeneAnnotation object created for this row due to more than one gene_id provided.', curr_line_num)
                return
        else:
            logger.error('Line %s: No GeneAnnotation object created for this row due to missing gene_id attribute.', curr_line_num)
            return
        stable_id = attributes['gene_id'].pop().split('.')[0]

        # Check and validate the name attribute
        name = None
        if 'Name' in attributes:
            if len(attributes['Name']) != 1:
                logger.warning('Line %s: name not set for this row\'s GeneAnnotation object due to more than one name provided.', curr_line_num)
            else:
                name = attributes['Name'].pop()
        else:
            logger.warning('Line %s: name not set for this row\'s GeneAnnotation object due to missing name attribute.', curr_line_num)
       
        # Check and validate the description attribute
        description = None
        if 'description' in attributes:
            if len(attributes['description']) != 1:
                logger.warning('Line %s: description not set for this row\'s GeneAnnotation object due to more than one description provided.', curr_line_num)
            else:
                description = re.sub(r" \[Source.*?\]", "",  urllib.parse.unquote(attributes['description'].pop()))
        else:
            logger.warning('Line %s: description not set for this row\'s GeneAnnotation object due to missing description attribute.', curr_line_num)
        
        # Check and validate the biotype attribute
        biotype = None
        if 'biotype' in attributes:
            if len(attributes['biotype']) != 1:
                logger.warning('Line %s: biotype not set for this row\'s GeneAnnotation object due to more than one biotype provided.', curr_line_num)
            else:
                biotype = attributes['biotype'].pop()
        else:
            logger.warning('Line %s: biotype not set for this row\'s GeneAnnotation object due to missing biotype attribute.', curr_line_num)

        gene_annotation = kbmodel.GeneAnnotation(id = ENSEMBL_GENE_ID_PREFIX + ':' + stable_id, 
                                                 source_id = stable_id,
                                                 symbol = name,
                                                 name = name,
                                                 description = description,
                                                 molecular_type = biotype,
                                                 referenced_in = self.genome_annotation.id,
                                                 in_taxon = [self.organism_taxon.id],
                                                 in_taxon_label = self.organism_taxon.full_name)
        # handle duplicates
        if gene_annotation not in self.gene_annotations:
            return gene_annotation
        return None

    
    def generate_ncbi_gene_annotation(self, attributes, curr_line_num):
        logger.info('In Generate NCBI GA')
        stable_id = None
        if 'Dbxref' in attributes:
            logger.info(attributes['Dbxref'])
            dbxref = {t.strip() for s in attributes['Dbxref'] for t in s.split(',')}
            logger.info(dbxref)
            geneid_values = set()
            for reference in dbxref:
                k,v = reference.split(':',1)
                if k == 'GeneID':
                    geneid_values.add(v) #! do we want to compare the stable ids? so 123.1 and 123.2 are the same?
            if len(geneid_values) == 1:
                stable_id = geneid_values.pop().split('.')[0]
        else:
            logger.error('Line %s: No GeneAnnotation object created for this row due to missing dbxref attribute.', curr_line_num)
            return

        if not stable_id:
            logger.error('Line %s: No GeneAnnotation object created for this row due to number of GeneIDs provided in dbxref attribute is not equal to one.', curr_line_num)
            return

        # Check and validate the name attribute
        name = None
        if 'Name' in attributes:
            if len(attributes['Name']) != 1 :
                logger.warning('Line %s: name not set for this row\'s GeneAnnotation object due to more than one name provided.', curr_line_num)
            else:
                value = attributes['Name'].pop()
                if value.find(',') != -1:
                    logger.warning('Line %s: name not set for this row\'s GeneAnnotation object due to value of name attribute containing ",".', curr_line_num)
                else:
                    name = value     
        else:
            logger.warning('Line %s: name not set for this row\'s GeneAnnotation object due to missing name attribute.', curr_line_num)
       
        # Check and validate the description attribute
        description = None
        if 'description' in attributes:
            if len(attributes['description']) != 1:
                logger.warning('Line %s: description not set for this row\'s GeneAnnotation object due to more than one description provided.', curr_line_num)
            else:
                description = urllib.parse.unquote(attributes['description'].pop())
        else:
            logger.warning('Line %s: description not set for this row\'s GeneAnnotation object due to missing description attribute.', curr_line_num)
        
        # Check and validate the biotype attribute
        biotype = None
        if 'gene_biotype' in attributes:
            if len(attributes['gene_biotype']) != 1:
                logger.warning('Line %s: molecular_type is not set for this row\'s GeneAnnotation object due to more than one biotype provided.', curr_line_num)
            else:
                value = attributes['gene_biotype'].pop()
                if value.find(',') != -1:
                    logger.warning('Line %s: biotype not set for this row\'s GeneAnnotation object due to value of gene_biotype attribute containing ",".', curr_line_num)
                else:
                    biotype = value
        else:
            logger.warning('Line %s: molecular_type is not set for this row\'s GeneAnnotation object due to missing biotype attribute.', curr_line_num)

        # Parse synonyms
        synonyms = []
        if 'gene_synonym' in attributes:
            synonyms = list({t.strip() for s in attributes['gene_synonym'] for t in s.split(',')})
            synonyms.sort() #note: this is not required, but it makes the output more predictable therefore easier to test
        else:
            logger.warning('Line %s: synonym is not set for this row\'s GeneAnnotation object due to missing gene_synonym attribute.', curr_line_num)

        gene_annotation = kbmodel.GeneAnnotation(id = NCBI_GENE_ID_PREFIX + ':' + stable_id,
                                                 source_id = stable_id,
                                                 symbol = name,
                                                 name = name,
                                                 description = description,
                                                 molecular_type = biotype,
                                                 referenced_in = self.genome_annotation.id,
                                                 in_taxon = [self.organism_taxon.id],
                                                 in_taxon_label = self.organism_taxon.full_name,
                                                 synonym = synonyms)
        if gene_annotation.id in self.gene_annotations:
            if gene_annotation != self.gene_annotations[gene_annotation.id]:
                return self.__resolve_ncbi_gene_annotation(gene_annotation, curr_line_num)
            if name != self.gene_annotations[gene_annotation.id].name:
                logger.warning('Line %s: GeneAnnotation object with id %s already exists with a different name.', curr_line_num, stable_id)
                return None
        
        return gene_annotation
   
   
    def __resolve_ncbi_gene_annotation(self, new_gene_annotation, curr_line_num):
        existing_gene_annotation = self.gene_annotations[new_gene_annotation.id]
        if existing_gene_annotation.description is None and new_gene_annotation.description is not None:
            return new_gene_annotation
        if existing_gene_annotation.description is not None and new_gene_annotation.description is None:
            return None
        if existing_gene_annotation.molecular_type is None and new_gene_annotation.molecular_type is not None:
            return new_gene_annotation
        if existing_gene_annotation.molecular_type is not None and new_gene_annotation.molecular_type is None:
            return None
        if existing_gene_annotation.molecular_type == "noncoding" and new_gene_annotation.molecular_type  != "noncoding":
            return new_gene_annotation
        if existing_gene_annotation.molecular_type != "noncoding" and new_gene_annotation.molecular_type  == "noncoding":
            return None
        logger.critical('Line %s: Unable to resolve duplicates for GeneID: %s.', curr_line_num, new_gene_annotation.id)
        raise ValueError("Can not resolve duplicates")
        # return None

    def __merge_values(self, t):
        result = defaultdict(set)
        for lst in t:
            key = lst[0].strip()
            value = lst[1:]
            for e in value:
                result[key].add(e.strip())
        return result


    def serialize(self):
        pass

if __name__ == "__main__":
    pass
