"""
Module for downloading, parsing, and processing GFF3 files from NCBI and Ensembl repositories. This module provides functionality to:

1. Download a GFF3 file from a specified URL and calculate its checksums.
2. Parse the GFF3 file to extract gene annotations.
3. Generate various metadata objects such as organism taxon, genome assembly, and genome annotation.
4. Serialize the extracted information into JSON-LD format for further use.

Classes:
    Gff3: The Gff3 class is designed to handle the complete lifecycle of downloading, parsing, and processing GFF3 files from NCBI or Ensembl repositories. It extracts gene annotations and serializes the data into JSON-LD format.

Functions:
    gff2jsonld: The gff2jsonld function is responsible for creating GeneAnnotation objects from a provided GFF3 file and serializing the extracted information into the JSON-LD format.

Usage:
    The module can be run as a standalone script by executing it with appropriate arguments and options:
    
    ```
    python genome_annotation_translator.py <content_url> -a <assembly_accession> -s <assembly_strain> -l <log_level> -f
    ```
    
    The script will download the GFF3 file from the specified URL, parse it, and serialize the extracted information into JSON-LD format.

Example:
    ```
    python genome_annotation_translator.py "https://example.com/path/to/gff3.gz" -a "GCF_000001405.39" -s "strain_name" -l "INFO" -f True
    ```
    
Dependencies:
    - re
    - hashlib
    - tempfile
    - urllib
    - urllib.request
    - urllib.parse
    - os
    - json
    - datetime
    - collections.defaultdict
    - subprocess
    - gzip
    - tqdm
    - click
    - pkg_resources
    - bkbit.models.genome_annotation as ga
    - bkbit.utils.setup_logger as setup_logger
    - bkbit.utils.load_json as load_json    
"""

import re
import hashlib
import tempfile
import urllib
import urllib.request
from urllib.parse import urlparse
import os
import json
from datetime import datetime
from collections import defaultdict
import subprocess
import gzip
import sys
from tqdm import tqdm
import click
import pkg_resources
from bkbit.models import genome_annotation as ga
from bkbit.utils.setup_logger import setup_logger
from bkbit.utils.load_json import load_json



## CONSTANTS ##

PREFIX_MAP = {
    "NCBITaxon:": "http://purl.obolibrary.org/obo/NCBITaxon_",
    "NCBIGene:": "http://identifiers.org/ncbigene/",
    "ENSEMBL:": "http://identifiers.org/ensembl/",
    "NCBIAssembly:": "https://www.ncbi.nlm.nih.gov/assembly/",
}
NCBI_GENE_ID_PREFIX = "NCBIGene:"
ENSEMBL_GENE_ID_PREFIX = "ENSEMBL:"
TAXON_PREFIX = "NCBITaxon:"
ASSEMBLY_PREFIX = "NCBIAssembly:"
BICAN_ANNOTATION_PREFIX = "bican:annotation-"
BKBIT_OBJECT_ID_PREFIX = "urn:bkbit:"
GENOME_ANNOTATION_DESCRIPTION_FORMAT = (
    "{authority} {taxon_scientific_name} Annotation Release {genome_version}"
)
DEFAULT_FEATURE_FILTER = ("gene", "pseudogene", "ncRNA_gene")
DEFAULT_HASH = ("MD5",)
LOG_FILE_NAME = (
    "gff3_translator_" + datetime.now().strftime("%Y-%m-%d_%H:%M:%S") + ".log"
)
TAXON_DIR_PATH = "../utils/ncbi_taxonomy/"
SCIENTIFIC_NAME_TO_TAXONID_PATH = pkg_resources.resource_filename(__name__, TAXON_DIR_PATH + "scientific_name_to_taxid.json")
TAXON_SCIENTIFIC_NAME_PATH = pkg_resources.resource_filename(__name__, TAXON_DIR_PATH + "taxid_to_scientific_name.json")
TAXON_COMMON_NAME_PATH = pkg_resources.resource_filename(__name__, TAXON_DIR_PATH + "taxid_to_common_name.json")

class Gff3:
    """
    The Gff3 class is responsible for downloading, parsing, and processing of GFF3 files from NCBI and Ensembl repositories.

    Attributes:
        content_url (str): The URL of the GFF file.
        assembly_accession (str): The ID of the genome assembly.
        assembly_strain (str, optional): The strain of the genome assembly. Defaults to None.
        log_level (str): The logging level. Defaults to 'WARNING'.
        log_to_file (bool): Flag to log messages to a file. Defaults to False.

    Methods:
        __init__(content_url, assembly_accession=None, assembly_strain=None, log_level="WARNING", log_to_file=False):
            Initializes the Gff3 class with the provided parameters.

        parse_url():
            Parses the content URL and extracts information about the genome annotation.

        __download_gff_file():
            Downloads a GFF file from a given URL and calculates the MD5, SHA256, and SHA1 hashes.

        generate_organism_taxon(taxon_id):
            Generates an organism taxon object based on the provided taxon ID.

        assign_authority_type(authority):
            Assigns the authority type based on the given authority string.

        generate_genome_assembly(assembly_id, assembly_version, assembly_label, assembly_strain=None):
            Generates a genome assembly object based on the provided parameters.

        generate_genome_annotation(genome_label, genome_version):
            Generates a genome annotation object based on the provided parameters.

        generate_digest(hash_values, hash_functions=DEFAULT_HASH):
            Generates checksum digests for the GFF file using the specified hash functions.

        __get_line_count(file_path):
            Returns the line count of a file.

        parse(feature_filter=DEFAULT_FEATURE_FILTER):
            Parses the GFF file and extracts gene annotations based on the provided feature filter.

        generate_ensembl_gene_annotation(attributes, curr_line_num):
            Generates a GeneAnnotation object for Ensembl based on the provided attributes.

        generate_ncbi_gene_annotation(attributes, curr_line_num):
            Generates a GeneAnnotation object for NCBI based on the provided attributes.

        __get_attribute(attributes, attribute_name, curr_line_num):
            Retrieves the value of a specific attribute from the given attributes dictionary.

        __resolve_ncbi_gene_annotation(new_gene_annotation, curr_line_num):
            Resolves conflicts between existing and new gene annotations based on certain conditions.

        __merge_values(t):
            Merges values from a list of lists into a dictionary of sets.

        serialize_to_jsonld(exclude_none=True, exclude_unset=False):
            Serializes the object and either writes it to the specified output file or prints it to the CLI.
    """

    def __init__(
        self,
        content_url,
        assembly_accession=None,
        assembly_strain=None,
        log_level="WARNING",
        log_to_file=False,
    ):
        """
        Initializes an instance of the GFFTranslator class.

        Parameters:
        - content_url (str): The URL of the GFF file.
        - assembly_id (str): The ID of the genome assembly.
        - assembly_strain (str, optional): The strain of the genome assembly. Defaults to None.
        - hash_functions (tuple[str]): A tuple of hash functions to use for generating checksums. Defaults to ('MD5').
        """
        self.logger = setup_logger(LOG_FILE_NAME, log_level, log_to_file)
        try:
            self.scientific_name_to_taxonid = load_json(SCIENTIFIC_NAME_TO_TAXONID_PATH)
            self.taxon_scientific_name = load_json(TAXON_SCIENTIFIC_NAME_PATH)
            self.taxon_common_name = load_json(TAXON_COMMON_NAME_PATH)
        except FileNotFoundError as e:
            self.logger.critical("NCBI Taxonomy not downloaded. Run 'bkbit download-ncbi-taxonomy' command first." )
            print(e)
            sys.exit(2)

        self.content_url = content_url

        ## STEP 1: Parse the content URL to get metadata
        # Parse content_url to get metadata
        url_metadata = self.parse_url()
        if url_metadata is None:
            self.logger.critical(
                "The provided content URL is not supported. Please provide a valid URL."
            )
            raise ValueError(
                "The provided content URL is not supported. Please provide a valid URL."
            )

        # Define variables to store metadata
        (
            taxon_id,
            assembly_id,
            assembly_version,
            assembly_label,
            genome_label,
            genome_version,
        ) = (None, None, None, None, None, None)

        # Assign the authority type
        self.authority = url_metadata.get("authority")

        # Assign the taxon_id and assembly_id based on the authority
        if self.authority.value == ga.AuthorityType.NCBI.value:
            taxon_id = url_metadata.get("taxonid")
            assembly_id = url_metadata.get("assembly_accession")
        elif self.authority.value == ga.AuthorityType.ENSEMBL.value:
            taxon_id = self.scientific_name_to_taxonid.get(
                url_metadata.get("scientific_name").replace("_", " ")
            )
            if assembly_accession is None:
                self.logger.critical(
                    "The assembly ID is required for Ensembl URLs. Please provide the assembly ID."
                )
                raise ValueError(
                    "The assembly ID is required for Ensembl URLs. Please provide the assembly ID."
                )
            assembly_id = assembly_accession

        # Assign assembly_version, assembly_label, genome_version, and genome_label
        assembly_version = (
            assembly_id.split(".")[1] if len(assembly_id.split(".")) >= 1 else None
        )
        assembly_label = url_metadata.get("assembly_name")
        genome_version = url_metadata.get("release_version")
        genome_label = self.authority.value + "-" + taxon_id + "-" + genome_version

        ## STEP 2: Download the GFF file
        # Download the GFF file
        self.gff_file, hash_values = self.__download_gff_file()

        ## STEP 3: Generate the organism taxon, genome assembly, checksums, and genome annotation objects
        # Generate the organism taxon object
        self.organism_taxon = self.generate_organism_taxon(taxon_id)
        self.genome_assembly = self.generate_genome_assembly(
            assembly_id, assembly_version, assembly_label, assembly_strain
        )
        self.checksums = self.generate_digest(hash_values, DEFAULT_HASH)
        self.genome_annotation = self.generate_genome_annotation(
            genome_label, genome_version
        )

        self.gene_annotations = {}

    def parse_url(self):
        """
        Parses the content URL and extracts information about the genome annotation.

        Returns:
            A dictionary containing the following information:
            - 'authority': The authority type (NCBI or ENSEMBL).
            - 'taxonid': The taxon ID of the genome.
            - 'release_version': The release version of the genome annotation.
            - 'assembly_accession': The assembly accession of the genome.
            - 'assembly_name': The name of the assembly.
            - 'species': The species name (only for ENSEMBL URLs).
        """
        # Define regex patterns for NCBI and Ensembl URLs
        # NCBI : [assembly accession.version]_[assembly name]_[content type].[optional format]
        # ENSEMBL :  <species>.<assembly>.<_version>.gff3.gz -> organism full name, assembly name, genome version
        ncbi_pattern = r"/genomes/all/annotation_releases/(\d+)(?:/(\d+))?/(GCF_\d+\.\d+)[_-]([^/]+)/(GCF_\d+\.\d+)[_-]([^/]+)_genomic\.gff\.gz"
        ensembl_pattern = (
            r"/pub/release-(\d+)/gff3/([^/]+)/([^/.]+)\.([^/.]+)\.([^/.]+)\.gff3\.gz"
        )

        # Parse the URL to get the path
        parsed_url = urlparse(self.content_url)
        path = parsed_url.path

        # Determine if the URL is from NCBI or Ensembl and extract information
        if "ncbi" in parsed_url.netloc:
            ncbi_match = re.search(ncbi_pattern, path)
            if ncbi_match:
                return {
                    "authority": ga.AuthorityType.NCBI,
                    "taxonid": ncbi_match.group(1),
                    "release_version": (
                        ncbi_match.group(2)
                        if ncbi_match.group(2)
                        else ncbi_match.group(4)
                    ),
                    "assembly_accession": ncbi_match.group(3),
                    "assembly_name": ncbi_match.group(6),
                }

        elif "ensembl" in parsed_url.netloc:
            ensembl_match = re.search(ensembl_pattern, path)
            if ensembl_match:
                return {
                    "authority": ga.AuthorityType.ENSEMBL,
                    "release_version": ensembl_match.group(1),
                    "scientific_name": ensembl_match.group(3),
                    "assembly_name": ensembl_match.group(4),
                }

        # If no match is found, return None
        return None

    def __download_gff_file(self):
        """
        Downloads a GFF file from a given URL and calculates the MD5, SHA256, and SHA1 hashes.

        Returns:
            tuple: A tuple containing the path to the downloaded gzip file and a dictionary
            with the MD5, SHA256, and SHA1 hashes of the file.
        """
        response = urllib.request.urlopen(self.content_url)
        total_size = int(response.headers.get("content-length", 0))
        block_size = 1024  # 1 Kilobyte

        # Create hash objects
        md5_hash = hashlib.md5()
        sha256_hash = hashlib.sha256()
        sha1_hash = hashlib.sha1()

        # Create a temporary file for the gzip data
        with tempfile.NamedTemporaryFile(suffix=".gz", delete=False) as f_gzip:
            gzip_file_path = f_gzip.name

            # Create a progress bar
            progress_bar = tqdm(
                total=total_size,
                unit="iB",
                unit_scale=True,
                desc="Downloading GFF file",
            )

            # Read the file in chunks, write to the temporary file, and update the hash
            while True:
                data = response.read(block_size)
                if not data:
                    break
                f_gzip.write(data)
                md5_hash.update(data)
                sha256_hash.update(data)
                sha1_hash.update(data)
                progress_bar.update(len(data))

            progress_bar.close()

        # Return the path to the temporary file and the md5 hash
        return gzip_file_path, {
            "MD5": md5_hash.hexdigest(),
            "SHA256": sha256_hash.hexdigest(),
            "SHA1": sha1_hash.hexdigest(),
        }

    def generate_organism_taxon(self, taxon_id: str):
        """
        Generates an organism taxon object based on the provided taxon ID.

        Args:
            taxon_id (str): The taxon ID of the organism.

        Returns:
            ga.OrganismTaxon: The generated organism taxon object.
        """
        attributes = {"full_name": self.taxon_scientific_name[taxon_id], "name": self.taxon_common_name[taxon_id], "iri": PREFIX_MAP[TAXON_PREFIX] + taxon_id, "type": ["bican:OrganismTaxon"], "xref": [TAXON_PREFIX + taxon_id]}
        attributes["id"] = self.generate_object_id(attributes)
        return ga.OrganismTaxon(**attributes)

    def assign_authority_type(self, authority: str):
        """
        Assigns the authority type based on the given authority string.

        Args:
            authority (str): The authority string to be assigned.

        Returns:
            ga.AuthorityType: The corresponding authority type.

        Raises:
            Exception: If the authority is not supported. Only NCBI and Ensembl authorities are supported.
        """
        if authority.upper() == ga.AuthorityType.NCBI.value:
            return ga.AuthorityType.NCBI
        if authority.upper() == ga.AuthorityType.ENSEMBL.value:
            return ga.AuthorityType.ENSEMBL
        self.logger.critical(
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
        ga.GenomeAssembly: The generated genome assembly object.
        """
        attributes = {"in_taxon": [self.organism_taxon.id], "in_taxon_label": self.organism_taxon.full_name, "name": assembly_label, "version": assembly_version, "strain": assembly_strain, "type": ["bican:GenomeAssembly"], "xref": [ASSEMBLY_PREFIX + assembly_id]}
        attributes["id"] = self.generate_object_id(attributes)
        return ga.GenomeAssembly(**attributes)

    def generate_genome_annotation(self, genome_label: str, genome_version: str):
        """
        Generates a genome annotation object.

        Args:
            genome_label (str): The label of the genome.
            genome_version (str): The version of the genome.

        Returns:
            ga.GenomeAnnotation: The generated genome annotation.
        """
        attributes = {"digest": [checksum.id for checksum in self.checksums], "content_url": [self.content_url], "reference_assembly": self.genome_assembly.id, "version": genome_version, "in_taxon": [self.organism_taxon.id], "in_taxon_label": self.organism_taxon.full_name, "description": GENOME_ANNOTATION_DESCRIPTION_FORMAT.format(authority=self.authority.value, taxon_scientific_name=self.organism_taxon.full_name, genome_version=genome_version), "authority": self.authority, "type": ["bican:GenomeAnnotation"], "xref": [BICAN_ANNOTATION_PREFIX + genome_label.upper()]}
        attributes["id"] = self.generate_object_id(attributes)
        return ga.GenomeAnnotation(**attributes)

    def generate_digest(
        self,
        hash_values: dict,
        hash_functions: tuple[str] = DEFAULT_HASH,
    ) -> list[ga.Checksum]:
        """
        Generates checksum digests for the GFF file using the specified hash functions.

        Args:
            hash_functions (list[str]): A list of hash functions to use for generating the digests.

        Returns:
            list[ga.Checksum]: A list of Checksum objects containing the generated digests.

        Raises:
            ValueError: If an unsupported hash algorithm is provided.

        """
        checksums = []
        for hash_type in hash_functions:
            hash_type = hash_type.strip().upper()
            # Create a Checksum object
            if hash_type == ga.DigestType.SHA256.name:
                sha256_attributes = {"checksum_algorithm": ga.DigestType.SHA256, "value": hash_values.get("SHA256"), "type": ["bican:Checksum"]}
                sha256_attributes["id"] = self.generate_object_id(sha256_attributes)
                checksums.append(ga.Checksum(**sha256_attributes))
            elif hash_type == ga.DigestType.MD5.name:
                md5_attributes = {"checksum_algorithm": ga.DigestType.MD5, "value": hash_values.get("MD5"), "type": ["bican:Checksum"]}
                md5_attributes["id"] = self.generate_object_id(md5_attributes)
                checksums.append(ga.Checksum(**md5_attributes))
            elif hash_type == ga.DigestType.SHA1.name:
                sha1_attributes = {"checksum_algorithm": ga.DigestType.SHA1, "value": hash_values.get("SHA1"), "type": ["bican:Checksum"]}
                sha1_attributes["id"] = self.generate_object_id(sha1_attributes)
                checksums.append(ga.Checksum(**sha1_attributes))
            else:
                self.logger.error(
                    "Hash algorithm %s is not supported. Please use SHA256, MD5, or SHA1.",
                    hash_type,
                )
        return checksums

    def __get_line_count(self, file_path):
        """
        Get the line count of a file.

        Args:
            file_path (str): The path to the file.

        Returns:
            int: The number of lines in the file.
        """

        result = subprocess.run(
            ["wc", "-l", file_path], stdout=subprocess.PIPE, check=True
        )  # If check is True and the exit code was non-zero, it raises a CalledProcessError.
        # The CalledProcessError object will have the return code in the returncode attribute,
        # and output & stderr attributes if those streams were captured.
        output = result.stdout.decode().strip()
        line_count = int(output.split()[0])  # Extract the line count from the output
        return line_count

    def parse(self, feature_filter: tuple[str] = DEFAULT_FEATURE_FILTER):
        """
        Parses the GFF file and extracts gene annotations based on the provided feature filter.

        Args:
            feature_filter (tuple[str]): Tuple of feature types to include in the gene annotations.

        Raises:
            FileNotFoundError: If the GFF file does not exist.

        Returns:
            None
        """
        gff_file = self.gff_file
        if self.gff_file.endswith(".gz"):
            # Decompress the gzip file
            with gzip.open(self.gff_file, "rb") as f_in:
                # Create a temporary file to save the decompressed data
                with tempfile.NamedTemporaryFile(delete=False) as f_out:
                    # Copy the decompressed data to the temporary file
                    f_out.write(f_in.read())
                    gff_file = f_out.name

        if not os.path.isfile(gff_file):
            raise FileNotFoundError(f"File {gff_file} does not exist.")

        with open(gff_file, "r", encoding="utf-8") as file:
            curr_line_num = 1
            progress_bar = tqdm(
                total=self.__get_line_count(gff_file), desc="Parsing GFF3 File"
            )
            for line_raw in file:
                line_strip = line_raw.strip()
                if curr_line_num == 1 and not line_strip.startswith("##gff-version 3"):
                    self.logger.warning(
                        '"##gff-version 3" missing from the first line of the file. The given file may not be a valid GFF3 file.'
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
                        self.logger.warning(
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
                        if self.genome_annotation.authority == ga.AuthorityType.ENSEMBL:
                            gene_annotation = self.generate_ensembl_gene_annotation(
                                attributes, curr_line_num
                            )
                            if gene_annotation is not None:
                                self.gene_annotations[gene_annotation] = gene_annotation
                        elif self.genome_annotation.authority == ga.AuthorityType.NCBI:
                            gene_annotation = self.generate_ncbi_gene_annotation(
                                attributes, curr_line_num
                            )
                            if gene_annotation is not None:
                                self.gene_annotations[gene_annotation.id] = (
                                    gene_annotation
                                )
                progress_bar.update(1)
                curr_line_num += 1
            progress_bar.close()

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

        #! maybe remove type and add it as default directly in model
        attributes = {"source_id": stable_id, "symbol": name, "name": name, "description": description, "molecular_type": biotype, "referenced_in": self.genome_annotation.id, "in_taxon": [self.organism_taxon.id], "in_taxon_label": self.organism_taxon.full_name, "type": ["bican:GeneAnnotation"], "xref": [ENSEMBL_GENE_ID_PREFIX + stable_id]}
        #! add a try/catch incase the hash returns an error and log it
        attributes["id"] = self.generate_object_id(attributes)
        gene_annotation = ga.GeneAnnotation(**attributes)

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
            self.logger.error(
                "Line %s: No GeneAnnotation object created for this row due to missing dbxref attribute.",
                curr_line_num,
            )
            return None

        if not stable_id:
            self.logger.error(
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
            self.logger.debug(
                "Line %s: synonym is not set for this row's GeneAnnotation object due to missing gene_synonym attribute.",
                curr_line_num,
            )

        #! maybe remove type and add it as default directly in model
        attributes = {"source_id": stable_id, "symbol": name, "name": name, "description": description, "molecular_type": biotype, "referenced_in": self.genome_annotation.id, "in_taxon": [self.organism_taxon.id], "in_taxon_label": self.organism_taxon.full_name, "synonym": synonyms, "type": ["bican:GeneAnnotation"], "xref": [NCBI_GENE_ID_PREFIX + stable_id]}
        #! add a try/catch incase the hash returns an error and log it
        attributes["id"] = self.generate_object_id(attributes)
        gene_annotation = ga.GeneAnnotation(**attributes)

        if gene_annotation.id in self.gene_annotations:
            if gene_annotation != self.gene_annotations[gene_annotation.id]:
                return self.__resolve_ncbi_gene_annotation(
                    gene_annotation, curr_line_num
                )
            if name != self.gene_annotations[gene_annotation.id].name:
                self.logger.debug(
                    "Line %s: GeneAnnotation object with id %s already exists with a different name. Current name: %s, Existing name: %s",
                    curr_line_num,
                    stable_id,
                    name,
                    self.gene_annotations[gene_annotation.id].name,
                )
                return None
        return gene_annotation


    @staticmethod
    def generate_object_id(attributes:dict):
        """
        Generate a unique object ID based on the provided attributes.

        Args:
            attributes (dict): A dictionary containing the attributes of the object.

        Returns:
            str: The generated object ID.
        """
        # Sort the attributes by keys and convert to a consistent JSON string
        #print(attributes)
        normalized_attributes = json.dumps(attributes, sort_keys=True)
        object_id = hashlib.sha256(normalized_attributes.encode()).hexdigest()
        return BKBIT_OBJECT_ID_PREFIX + object_id


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
                self.logger.debug(
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
                    self.logger.debug(
                        'Line %s: %s not set for this row\'s GeneAnnotation object due to value of %s attribute containing ",".',
                        curr_line_num,
                        attribute_name,
                        attribute_name,
                    )
                    value = None
        else:
            self.logger.debug(
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
            GeneAnnotation or None: The resolved gene annotation or None if it cannot be resolved
                                    or None if the resolution is in favor of the existing gene
                                    annotation.

        Raises:
            ValueError: If duplicates cannot be resolved.

        """
        existing_gene_annotation = self.gene_annotations[new_gene_annotation.id]
        if (
            existing_gene_annotation.description is not None
            and new_gene_annotation.description is None
        ):
            return None
        if (
            existing_gene_annotation.description is None
            and new_gene_annotation.description is not None
        ):
            return new_gene_annotation
        if (
            existing_gene_annotation.molecular_type is not None
            and new_gene_annotation.molecular_type is None
        ):
            return None
        if (
            existing_gene_annotation.molecular_type is None
            and new_gene_annotation.molecular_type is not None
        ):
            return new_gene_annotation
        if existing_gene_annotation.molecular_type == ga.BioType.protein_coding.value:
            return None
        if new_gene_annotation.molecular_type == ga.BioType.protein_coding.value:
            return new_gene_annotation

        self.logger.error(
            "Line %s: Unable to resolve duplicates for GeneID: %s.\nexisting gene: %s\nnew gene: %s",
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
        self, exclude_none: bool = True, exclude_unset: bool = False
    ):
        """
        Serialize the object and either write it to the specified output file or print it to the CLI.

        Parameters:
            exclude_none (bool): Whether to exclude None values in the output.
            exclude_unset (bool): Whether to exclude unset values in the output.

        Returns:
            None
        """

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
            data.append(ck.dict(exclude_none=exclude_none, exclude_unset=exclude_unset))
        for ga in self.gene_annotations.values():
            data.append(ga.dict(exclude_none=exclude_none, exclude_unset=exclude_unset))

        output_data = {
            "@context": "https://raw.githubusercontent.com/brain-bican/models/main/jsonld-context-autogen/genome_annotation.context.jsonld",
            "@graph": data,
        }

        print(json.dumps(output_data, indent=2))


@click.command()
##ARGUEMENTS##
# Argument #1: The URL of the GFF file
@click.argument("content_url", type=str)

##OPTIONS##
# Option #1: The ID of the genome assembly
@click.option("assembly_accession", "-a", required=False, default=None, type=str)
# Option #2: The strain of the genome assembly
@click.option(
    "--assembly_strain",
    "-s",
    required=False,
    default=None,
    type=str,
    help="The strain of the genome assembly. Defaults to None.",
)
# Option #3: The log level
@click.option(
    "--log_level",
    "-l",
    required=False,
    default="WARNING",
    help="The log level. Defaults to WARNING.",
)
# Option #4: Log to file
@click.option(
    "--log_to_file",
    "-f",
    is_flag=True,
    help="Log to a file instead of the console.",
)
def gff2jsonld(content_url, assembly_accession, assembly_strain, log_level, log_to_file):
    '''
    Creates GeneAnnotation objects from a GFF3 file and serializes them to JSON-LD format.
    '''
    gff3 = Gff3(
        content_url, assembly_accession, assembly_strain, log_level, log_to_file
    )
    gff3.parse()
    gff3.serialize_to_jsonld()


if __name__ == "__main__":
    gff2jsonld()
