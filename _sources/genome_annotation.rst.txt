.. _genome_annotation:

Annotated Genome Data
----------------------

Overview
.........

Generate JSON-LD files for annotated genes from a given GFF3 file. Currently GFF3 files from ENSEMBL and NCBI are supported.

Each JSON-LD file will contain:

- GeneAnnotation objects
- 1 GenomeAnnotation object
- 1 GenomeAssembly object
- 1 OrganismTaxon object
- 1 Checksum object

NCBI Taxonomy Data
...................

No setup is required before running ``bkbit gff2jsonld``. A taxonomy subset covering every
organism with a GenBank common name ships inside the ``bkbit`` package, so organism names
resolve offline for all supported species.

If a GFF3 file references a taxon outside that subset, ``bkbit`` downloads the full NCBI
taxonomy once and caches it in a per-user cache directory. To do that download up front
instead of mid-run - for example when building a container image or running air-gapped -
use the optional command:

.. code-block:: bash

    $ bkbit download-ncbi-taxonomy

Set ``BKBIT_DATA_DIR`` to control where the cache is stored, or ``BKBIT_NO_DOWNLOAD`` to
make an out-of-subset lookup raise an error instead of downloading.

Command Line
.............

``bkbit gff2jsonld``
,,,,,,,,,,,,,,,,,,,,,

    .. code-block:: bash

        $ bkbit gff2jsonld [OPTIONS] GFF3_URL

Options
,,,,,,,,

    ``-a, --assembly_accession <assembly_accession>``
        ID assigned to the genomic assembly used in the GFF3 file.

    .. note::
        Must be provided when using ENSEMBL GFF3 files

    ``-s, --assembly_strain <assembly_strain>``
        Specific strain of the organism associated with the GFF3 file.

    ``-l, --log_level <log_level>``
        Logging level.

        Default:
            WARNING
        Options:
            DEBUG | INFO | WARNING | ERROR | CRITICAL

    ``-f, --log_to_file``
        Log to a file instead of the console.

        Default:
            False

    ``-o, --output_format <output_format>``
        Output format for the serialized data.
        
        Default:
            jsonld
        Options:
            jsonld | turtle
Arguments
,,,,,,,,,,,

    ``GFF3_URL``
        Required argument

Examples 
.........

Example 1: NCBI GFF3 file
,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # Run gff2jsonld command
    $ bkbit gff2jsonld 'https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/106/GCF_000003025.6_Sscrofa11.1/GCF_000003025.6_Sscrofa11.1_genomic.gff.gz' > output.jsonld


Example 2: ENSEMBL GFF3 file
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # Run gff2jsonld command
    $ bkbit gff2jsonld -a 'GCF_003339765.1' 'https://ftp.ensembl.org/pub/release-104/gff3/macaca_mulatta/Macaca_mulatta.Mmul_10.104.gff3.gz' > output.jsonld
