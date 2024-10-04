.. _datatranslators:

Data Translators
======

Annotated Genome Data
----------------------
Generate JSON-LD files for annotated genes from a given GFF3 file. Currently GFF3 files from ENSEMBL and NCBI are supported.

Each JSON-LD file will contain:

- GeneAnnotation objects
- 1 GenomeAnnotation object
- 1 GenomeAssembly object
- 1 OrganismTaxon object
- 1 Checksum object

Command Line 
.............

``bkbit gff2jsonld``
,,,,,,,,,,,,,,,,,,,,,

    .. code-block:: bash

        $ bkbit gff2jsonld [OPTIONS] GFF3_URL

Options
,,,,,,,,

    ``-a, --assembly_accession``
        ID assigned to the genomic assembly used in the GFF3 file.
        **Note: Must be provided when using ENSEMBL GFF3 files**

    ``-s, --assembly_strain``
        Specific strain of the organism associated with the GFF3 file.

    ``-l, --log_level``
        Logging level.

        Default:
            WARNING
        Options:
            DEBUG | INFO | WARNING | ERROR | CRITICIAL

    ``-f, --log_to_file``
        Log to a file instead of the console.

        Default:
            FALSE

Arguments
,,,,,,,,

    ``GFF3_URL``
        URL to the GFF3 file.

Examples 
.........

Example 1: NCBI GFF3 file
,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    $ bkbit gff2jsonld 'https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/106/GCF_000003025.6_Sscrofa11.1/GCF_000003025.6_Sscrofa11.1_genomic.gff.gz' > output.jsonld


Example 2: ENSEMBL GFF3 file
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    $ bkbit gff2jsonld -a 'GCF_003339765.1' 'https://ftp.ensembl.org/pub/release-104/gff3/macaca_mulatta/Macaca_mulatta.Mmul_10.104.gff3.gz' > output.jsonld


Specimen Data
----------------------
Generate JSON-LD files for specimens, subjects, and their repective ancestors or descendants. Data is retrieved from the `BICAN Specimen Portal <https://brain-specimenportal.org/>`_. 

Command Line 
.............

``bkbit specimen2jsonld``
,,,,,,,,,,,,,,,,,,,,,

    .. code-block:: bash

        $ bkbit specimen2jsonld [OPTIONS] NHASH_ID_OR_FILE

Options
,,,,,,,,

    ``-d, --decendants``
        A boolean flag that, when provided, generates BICAN objects for the given NHASH_ID and all of its descendants. 
        If this flag is not set (DEFAULT), then the ancestors will be processed.

Arguments
,,,,,,,,

    ``NHASH_ID_OR_FILE``
        The NHASH_ID of the specimen or a file containing a list of NHASH_IDs. 
        If a file is provided, the file should contain one NHASH_ID per line.

Environment Variables 
.............

jwt_token
,,,,,,,,,

    You **must** set the SpecimenPortal Personal API Token as an environment variable before running ``bkbit specimen2jsonld``. Once set, the token will be used to authenticate with the Specimen Portal API and retrieve the specimen metadata.

    .. code-block:: bash

        $ export jwt_token=specimen_portal_personal_api_token


Examples 
.........

Example 1: Parse a single record and its ancestors
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # Run specimen2jsonld command 
    $ bkbit specimen2jsonld 'LP-CVFLMQ819998' > output.jsonld

Example 2: Parse a single record and its descendants
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # Run specimen2jsonld command. Important: include '--descendants' flag
    $ bkbit specimen2jsonld -d 'DO-GICE7463' > output.jsonld

Example 3: Parse a file containing record(s) and their respective ancestors
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # Contents of input file 
    $ cat input_nhash_ids.txt
    LA-TZWCWB265559FVVNTS329147
    LA-IAXCCV360563HBFKKM103455
    LA-JFCEST535498UIPMOH349083

    # Run specimen2jsonld command 
    $ bkbit specimen2jsonld input_nhash_ids.txt 

    # Expected output 
    $ ls .
    LA-TZWCWB265559FVVNTS329147.jsonld
    LA-IAXCCV360563HBFKKM103455.jsonld
    LA-JFCEST535498UIPMOH349083.jsonld

Example 4: Parse a file containing record(s) and their respective descendants
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # Contents of input file 
    $ cat input_nhash_ids.txt
    DO-XIQQ6047
    DO-WFFF3774
    DO-RMRL6873

    # Run specimenjsonld command. Important: include '--descendants' flag
    $ bkbit specimen2jsonld -d input_nhash_ids.txt 

    # Expected output 
    $ ls .
    DO-XIQQ6047.jsonld
    DO-WFFF3774.jsonld
    DO-RMRL6873.jsonld

Structured Anatomical Data
----------------------------



