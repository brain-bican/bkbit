from collections import defaultdict
import re
import hashlib
import uuid
import logging
import urllib
import os
import json
from bkbit.models import kbmodel

logging.basicConfig(
    filename="gff3_translator.log",
    format="%(levelname)s: %(message)s (%(asctime)s)",
    datefmt="%m/%d/%Y %I:%M:%S %p",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


## CONSTANTS ##

TAXON_SCIENTIFIC_NAME = {
    "9606": "Homo sapiens",
    "10090": "Mus musculus",
    "9544": "Macaca mulatta",
    "9483": "Callithrix jacchus",
}
TAXON_COMMON_NAME = {
    "9606": "human",
    "10090": "mouse",
    "9544": "rhesus macaque",
    "9483": "common marmoset",
}
PREFIX_MAP = {
    "NCBITaxon": "http://purl.obolibrary.org/obo/NCBITaxon_",
    "NCBIGene": "http://identifiers.org/ncbigene/",
    "ENSEMBL": "http://identifiers.org/ensembl/",
    "NCBIAssembly": "https://www.ncbi.nlm.nih.gov/assembly/",
}
NCBI_GENE_ID_PREFIX = "NCBIGene"
ENSEMBL_GENE_ID_PREFIX = "ENSEMBL"
TAXON_PREFIX = "NCBITaxon"
ASSEMBLY_PREFIX = "NCBIAssembly"
BICAN_ANNOTATION_PREFIX = "bican:annotation-"
GENOME_ANNOTATION_DESCRIPTION_FORMAT = (
    "{authority} {taxon_scientific_name} Annotation Release {genome_version}"
)
FEATURE_FILTER = ("gene", "pseudogene", "ncRNA_gene")
DEFAULT_HASH = "SHA256"


class Gff3:
    def __init__(
        self,
        gff_file,
        taxon_id,
        assembly_id,
        assembly_version,
        assembly_label,
        genome_label: str,
        genome_version: str,
        genome_authority: str,
        hash_functions: tuple[str],
        assembly_strain=None,
    ):
        """
        Initializes an instance of the GFFTranslator class.

        Parameters:
        - gff_file (str): The path to the GFF file.
        - taxon_id (int): The taxon ID of the organism.
        - assembly_id (str): The ID of the genome assembly.
        - assembly_version (str): The version of the genome assembly.
        - assembly_label (str): The label of the genome assembly.
        - genome_label (str): The label of the genome.
        - genome_version (str): The version of the genome.
        - genome_authority (str): The authority responsible for the genome.
        - hash_functions (tuple[str]): A list of hash functions to use for generating checksums.
        - assembly_strain (str, optional): The strain of the genome assembly. Defaults to None.
        """
        self.gff_file = gff_file
        self.logger = logger
        self.authority = self.assign_authority_type(genome_authority)
        self.organism_taxon = self.generate_organism_taxon(taxon_id)
        self.genome_assembly = self.generate_genome_assembly(
            assembly_id, assembly_version, assembly_label, assembly_strain
        )
        self.checksums = self.generate_digest(hash_functions)
        self.genome_annotation = self.generate_genome_annotation(
            genome_label, genome_version
        )
        self.gene_annotations = {}

    def generate_organism_taxon(self, taxon_id: str):
        """
        Generates an organism taxon object based on the provided taxon ID.

        Args:
            taxon_id (str): The taxon ID of the organism.

        Returns:
            kbmodel.OrganismTaxon: The generated organism taxon object.
        """
        self.logger.debug("Generating organism taxon")
        return kbmodel.OrganismTaxon(
            id=TAXON_PREFIX + ":" + taxon_id,
            full_name=TAXON_SCIENTIFIC_NAME[taxon_id],
            name=TAXON_COMMON_NAME[taxon_id],
            iri=PREFIX_MAP[TAXON_PREFIX] + taxon_id,
        )

    def assign_authority_type(self, authority: str):
        """
        Assigns the authority type based on the given authority string.

        Args:
            authority (str): The authority string to be assigned.

        Returns:
            kbmodel.AuthorityType: The corresponding authority type.

        Raises:
            Exception: If the authority is not supported. Only NCBI and Ensembl authorities are supported.
        """
        self.logger.debug("Assigning authority type")
        if authority.upper() == kbmodel.AuthorityType.NCBI.value:
            return kbmodel.AuthorityType.NCBI
        if authority.upper() == kbmodel.AuthorityType.ENSEMBL.value:
            return kbmodel.AuthorityType.ENSEMBL
        logger.critical(
            "Authority %s is not supported. Please use NCBI or Ensembl.", authority
        )
        raise ValueError(
            f"Authority {self.authority} is not supported. Please use NCBI or Ensembl."
        )

    def generate_genome_assembly(
        self,
        assembly_id: str,
        assembly_version: str,
        assembly_label: str,
        assembly_strain: str = None,
    ):
        """
        Generate a genome assembly object.

        Parameters:
        assembly_id (str): The ID of the assembly.
        assembly_version (str): The version of the assembly.
        assembly_label (str): The label of the assembly.
        assembly_strain (str, optional): The strain of the assembly. Defaults to None.

        Returns:
        kbmodel.GenomeAssembly: The generated genome assembly object.
        """
        self.logger.debug("Generating genome assembly")
        return kbmodel.GenomeAssembly(
            id=ASSEMBLY_PREFIX + ":" + assembly_id,
            in_taxon=[self.organism_taxon.id],
            in_taxon_label=self.organism_taxon.full_name,
            version=assembly_version,
            name=assembly_label,
            strain=assembly_strain,
        )

    def generate_genome_annotation(self, genome_label: str, genome_version: str):
        """
        Generates a genome annotation object.

        Args:
            genome_label (str): The label of the genome.
            genome_version (str): The version of the genome.

        Returns:
            kbmodel.GenomeAnnotation: The generated genome annotation.
        """
        self.logger.debug("Generating genome annotation")
        return kbmodel.GenomeAnnotation(
            id=BICAN_ANNOTATION_PREFIX + genome_label.upper(),
            digest=[checksum.id for checksum in self.checksums],
            content_url=[self.gff_file],
            reference_assembly=self.genome_assembly.id,
            version=genome_version,
            in_taxon=[self.organism_taxon.id],
            in_taxon_label=self.organism_taxon.full_name,
            description=GENOME_ANNOTATION_DESCRIPTION_FORMAT.format(
                authority=self.authority.value,
                taxon_scientific_name=self.organism_taxon.full_name,
                genome_version=genome_version,
            ),
            authority=self.authority,
        )

    def generate_digest(
        self, hash_functions: tuple[str] = DEFAULT_HASH
    ) -> list[kbmodel.Checksum]:
        """
        Generates checksum digests for the GFF file using the specified hash functions.

        Args:
            hash_functions (list[str]): A list of hash functions to use for generating the digests.

        Returns:
            list[kbmodel.Checksum]: A list of Checksum objects containing the generated digests.

        Raises:
            ValueError: If an unsupported hash algorithm is provided.

        """
        # gff_data = requests.get(url).content #* note: only needed if data is provided in url (from old version of gfftranslator)
        checksums = []
        gff_data = self.gff_file.encode("utf-8")

        # Generate a UUID version 4
        uuid_value = uuid.uuid4()

        # Construct a URN with the UUID
        urn = f"urn:uuid:{uuid_value}"
        for hash_type in hash_functions:

            hash_type = hash_type.strip().upper()
            # Create a Checksum object
            if hash_type == "SHA256":
                digest = hashlib.sha256(gff_data).hexdigest()
                checksums.append(
                    kbmodel.Checksum(
                        id=urn,
                        checksum_algorithm=kbmodel.DigestType.SHA256,
                        value=digest,
                    )
                )
            elif hash_type == "MD5":
                digest = hashlib.md5(gff_data).hexdigest()
                checksums.append(
                    kbmodel.Checksum(
                        id=urn, checksum_algorithm=kbmodel.DigestType.MD5, value=digest
                    )
                )
            elif hash_type == "SHA1":
                digest = hashlib.sha1(gff_data).hexdigest()
                checksums.append(
                    kbmodel.Checksum(
                        id=urn, checksum_algorithm=kbmodel.DigestType.SHA1, value=digest
                    )
                )
            else:
                logger.error(
                    "Hash algorithm %s is not supported. Please use SHA256, MD5, or SHA1.",
                    hash_type,
                )
        return checksums

    def parse(self, feature_filter: tuple[str] = FEATURE_FILTER):
        """
        Parses the GFF file and extracts gene annotations based on the provided feature filter.

        Args:
            feature_filter (tuple[str]): Tuple of feature types to include in the gene annotations.

        Raises:
            FileNotFoundError: If the GFF file does not exist.

        Returns:
            None
        """
        curr_line_num = 0
        if not os.path.isfile(self.gff_file):
            raise FileNotFoundError(f"File {self.gff_file} does not exist.")
        with open(self.gff_file, "r", encoding="utf-8") as file:
            for line_raw in file:
                curr_line_num += 1
                line_strip = line_raw.strip()
                if curr_line_num == 1 and not line_strip.startswith("##gff-version 3"):
                    logger.critical(
                        'Line %s: ##gff-version 3" missing from the first line.',
                        curr_line_num,
                    )
                elif len(line_strip) == 0:  # blank line
                    continue
                elif line_strip.startswith("##"):  # TODO: parse more metadata
                    pass
                elif line_strip.startswith("#"):  # TODO: parse more metadata
                    pass
                else:  # line may be a feature or unknown
                    tokens = list(map(str.strip, line_raw.split("\t")))
                    if len(tokens) != 9:
                        logger.warning(
                            "Line %s: Features are expected 9 columns, found %s.",
                            curr_line_num,
                            len(tokens),
                        )
                    if (
                        tokens[2] in feature_filter
                    ):  # only look at rows that have a type that is included in feature_filter
                        attributes = self.__merge_values(
                            tuple(a.split("=") for a in tokens[8].split(";"))
                        )
                        # TODO: Write cleaner code that calls respective generate function based on the authority automatically
                        if (
                            self.genome_annotation.authority
                            == kbmodel.AuthorityType.ENSEMBL
                        ):
                            gene_annotation = self.generate_ensembl_gene_annotation(
                                attributes, curr_line_num
                            )
                            if gene_annotation is not None:
                                self.gene_annotations[gene_annotation] = gene_annotation
                        elif (
                            self.genome_annotation.authority
                            == kbmodel.AuthorityType.NCBI
                        ):
                            gene_annotation = self.generate_ncbi_gene_annotation(
                                attributes, curr_line_num
                            )
                            if gene_annotation is not None:
                                self.gene_annotations[gene_annotation.id] = (
                                    gene_annotation
                                )

    def generate_ensembl_gene_annotation(self, attributes, curr_line_num):
        """
        Generates a GeneAnnotation object for Ensembl based on the provided attributes.

        Args:
            attributes (dict): A dictionary containing the attributes of the gene.
            curr_line_num (int): The line number of the current row in the input file.

        Returns:
            GeneAnnotation or None: The generated GeneAnnotation object if it is not a duplicate,
            otherwise None.

        Raises:
            None

        """
        stable_id = self.__get_attribute(attributes, "gene_id", curr_line_num)
        if stable_id:
            stable_id = stable_id.split(".")[0]

        # Check and validate the name attribute
        name = self.__get_attribute(attributes, "Name", curr_line_num)

        # Check and validate the description attribute
        description = self.__get_attribute(attributes, "description", curr_line_num)

        # Check and validate the biotype attribute
        biotype = self.__get_attribute(attributes, "biotype", curr_line_num)

        gene_annotation = kbmodel.GeneAnnotation(
            id=ENSEMBL_GENE_ID_PREFIX + ":" + stable_id,
            source_id=stable_id,
            symbol=name,
            name=name,
            description=description,
            molecular_type=biotype,
            referenced_in=self.genome_annotation.id,
            in_taxon=[self.organism_taxon.id],
            in_taxon_label=self.organism_taxon.full_name,
        )
        # handle duplicates
        if gene_annotation not in self.gene_annotations:
            return gene_annotation
        return None

    def generate_ncbi_gene_annotation(self, attributes, curr_line_num):
        """
        Generates a GeneAnnotation object for NCBI based on the provided attributes.

        Args:
            attributes (dict): A dictionary containing the attributes of the gene.
            curr_line_num (int): The line number of the current row in the input file.

        Returns:
            GeneAnnotation or None: The generated GeneAnnotation object if it is not a duplicate,
            otherwise None.

        Raises:
            None

        """
        stable_id = None
        if "Dbxref" in attributes:
            dbxref = {t.strip() for s in attributes["Dbxref"] for t in s.split(",")}
            geneid_values = set()
            for reference in dbxref:
                k, v = reference.split(":", 1)
                if k == "GeneID":
                    geneid_values.add(v.split(".")[0])
            if len(geneid_values) == 1:
                stable_id = geneid_values.pop()
        else:
            logger.error(
                "Line %s: No GeneAnnotation object created for this row due to missing dbxref attribute.",
                curr_line_num,
            )
            return None

        if not stable_id:
            logger.error(
                "Line %s: No GeneAnnotation object created for this row due to number of GeneIDs provided in dbxref attribute is not equal to one.",
                curr_line_num,
            )
            return None

        # Check and validate the name attribute
        name = self.__get_attribute(attributes, "Name", curr_line_num)

        # Check and validate the description attribute
        description = self.__get_attribute(attributes, "description", curr_line_num)

        # Check and validate the biotype attribute
        biotype = self.__get_attribute(attributes, "gene_biotype", curr_line_num)

        # Parse synonyms
        synonyms = []
        if "gene_synonym" in attributes:
            synonyms = list(
                {t.strip() for s in attributes["gene_synonym"] for t in s.split(",")}
            )
            synonyms.sort()  # note: this is not required, but it makes the output more predictable therefore easier to test
        else:
            logger.warning(
                "Line %s: synonym is not set for this row's GeneAnnotation object due to missing gene_synonym attribute.",
                curr_line_num,
            )

        gene_annotation = kbmodel.GeneAnnotation(
            id=NCBI_GENE_ID_PREFIX + ":" + stable_id,
            source_id=stable_id,
            symbol=name,
            name=name,
            description=description,
            molecular_type=biotype,
            referenced_in=self.genome_annotation.id,
            in_taxon=[self.organism_taxon.id],
            in_taxon_label=self.organism_taxon.full_name,
            synonym=synonyms,
        )
        if gene_annotation.id in self.gene_annotations:
            if gene_annotation != self.gene_annotations[gene_annotation.id]:
                return self.__resolve_ncbi_gene_annotation(
                    gene_annotation, curr_line_num
                )
            if name != self.gene_annotations[gene_annotation.id].name:
                logger.warning(
                    "Line %s: GeneAnnotation object with id %s already exists with a different name.",
                    curr_line_num,
                    stable_id,
                )
                return None
        return gene_annotation

    def __get_attribute(self, attributes, attribute_name, curr_line_num):
        """
        Get the value of a specific attribute from the given attributes dictionary.

        Args:
            attributes (dict): A dictionary containing attribute names and their values.
            attribute_name (str): The name of the attribute to retrieve.
            curr_line_num (int): The current line number for logging purposes.

        Returns:
            str or None: The value of the attribute if found, None otherwise.
        """
        value = None
        if attribute_name in attributes:
            if len(attributes[attribute_name]) != 1:
                logger.warning(
                    "Line %s: %s not set for this row's GeneAnnotation object due to more than one %s provided.",
                    curr_line_num,
                    attribute_name,
                    attribute_name,
                )
            elif attribute_name == "description":
                value = re.sub(
                    r"\s*\[Source.*?\]",
                    "",
                    urllib.parse.unquote(attributes["description"].pop()),
                )
            else:
                value = attributes[attribute_name].pop()
                if value.find(",") != -1:
                    logger.warning(
                        'Line %s: %s not set for this row\'s GeneAnnotation object due to value of %s attribute containing ",".',
                        curr_line_num,
                        attribute_name,
                        attribute_name,
                    )
                    value = None
        else:
            logger.warning(
                "Line %s: %s not set for this row's GeneAnnotation object due to missing %s attribute.",
                curr_line_num,
                attribute_name,
                attribute_name,
            )
        return value

    def __resolve_ncbi_gene_annotation(self, new_gene_annotation, curr_line_num):
        """
        Resolves conflicts between existing and new gene annotations based on certain conditions.

        Args:
            new_gene_annotation (GeneAnnotation): The new gene annotation to be resolved.
            curr_line_num (int): The current line number in the file.

        Returns:
            GeneAnnotation or None: The resolved gene annotation or None if it cannot be resolved.

        Raises:
            ValueError: If duplicates cannot be resolved.

        """
        existing_gene_annotation = self.gene_annotations[new_gene_annotation.id]
        if (
            existing_gene_annotation.description is None
            and new_gene_annotation.description is not None
        ):
            return new_gene_annotation
        if (
            existing_gene_annotation.description is not None
            and new_gene_annotation.description is None
        ):
            return None
        if (
            existing_gene_annotation.molecular_type is None
            and new_gene_annotation.molecular_type is not None
        ):
            return new_gene_annotation
        if (
            existing_gene_annotation.molecular_type is not None
            and new_gene_annotation.molecular_type is None
        ):
            return None
        if (
            existing_gene_annotation.molecular_type == kbmodel.BioType.noncoding.value
            and new_gene_annotation.molecular_type != kbmodel.BioType.noncoding.value
        ):
            return new_gene_annotation
        if (
            existing_gene_annotation.molecular_type != kbmodel.BioType.noncoding.value
            and new_gene_annotation.molecular_type == kbmodel.BioType.noncoding.value
        ):
            return None
        logger.critical(
            "Line %s: Unable to resolve duplicates for GeneID: %s.\nexisting gene: %s\nnew gene:      %s",
            curr_line_num,
            new_gene_annotation.id,
            existing_gene_annotation,
            new_gene_annotation,
        )
        return None

    def __merge_values(self, t):
        """
        Merge values from a list of lists into a dictionary of sets.

        Args:
            t (list): A list of lists containing key-value pairs.

        Returns:
            dict: A dictionary where each key maps to a set of values.

        """
        result = defaultdict(set)
        for lst in t:
            key = lst[0].strip()
            value = lst[1:]
            for e in value:
                result[key].add(e.strip())
        return result

    def serialize_to_jsonld(
        self, output_file: str, exclude_none: bool = True, exclude_unset: bool = False
    ):
        """
        Serialize the object and write it to the specified output file.

        Parameters:
            output_file (str): The path of the output file.

        Returns:
            None
        """
        with open(output_file, "w", encoding="utf-8") as f:
            data = [
                self.organism_taxon.dict(
                    exclude_none=exclude_none, exclude_unset=exclude_unset
                ),
                self.genome_assembly.dict(
                    exclude_none=exclude_none, exclude_unset=exclude_unset
                ),
                self.genome_annotation.dict(
                    exclude_none=exclude_none, exclude_unset=exclude_unset
                ),
            ]
            for ck in self.checksums:
                data.append(
                    ck.dict(exclude_none=exclude_none, exclude_unset=exclude_unset)
                )
            for ga in self.gene_annotations.values():
                data.append(
                    ga.dict(exclude_none=exclude_none, exclude_unset=exclude_unset)
                )

            output_data = {
                "@context": "https://raw.githubusercontent.com/atlaskb/models/main/jsonld-context-autogen/kbmodel.context.jsonld",
                "@graph": data,
            }
            f.write(json.dumps(output_data, indent=2))


if __name__ == "__main__":
    pass
