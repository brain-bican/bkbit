.. _specimen_file_manifest:

Specimen Digital File Manifest
----------------------

Overview
.........

Generates a JSON-LD file containing digital asset objects using the BICAN Library Generation Schema. 


Retrieve Specimen File Manifest from Brain Knowledge Platform
......................................................

- Step 1: Go to `Brain Knowledge Platform <https://knowledge.brain-map.org/>`_

- Step 2: Navigate to 'Data/Projects' tab on the top right menu

- Step 3: Filter by 'Specimen Type' specifically "Library Aliquot"

- Step 4: Click on specific project i.e. "BICAN Rapid Release Inventory: Single cell transcriptomics and epigenomics"

- Step 5: Click on 'BROWSE SPECIMENS' button

- Step 6: Click on download icon (arrow pointing down) on top menu bar and select 'File Manifest'

The input file manifest must be in CSV format and contain the following columns:

        - Project ID	
        - Specimen ID	
        - File Name	
        - Checksum	
        - File Type	
        - Archive	
        - Archive URI

Command Line
.............

``bkbit filemanifest2jsonld``
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    $ bkbit filemanifest2jsonld [OPTIONS] FILE_MANIFEST_CSV

**Options**

    ``-l, --list_library_aliquots``
        A boolean flag that, when provided, generates a list of unique library aliquots contained in the given file manifest and saves output in file called 'file_manifest_library_aliquots.txt'. 
        If this flag is not set (DEFAULT), then only the JSON-LD output will be generated.

**Arguments**

    ``FILE_MANIFEST_CSV``
        Required argument

Examples
.........

Example 1: Only generate JSON-LD output
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # Run filemanifest2jsonld command 
    $ bkbit filemanifest2jsonld file_manifest.csv > output.jsonld

Example 2: Generate JSON-LD output and list of library aliquots
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # Run filemanifest2jsonld command 
    $ bkbit filemanifest2jsonld --list_library_aliquots file_manifest.csv > output.jsonld

    # Generated output files 
    $ ls .
    output.jsonld
    file_manifest_library_aliquots.txt

    # Contents of file_manifest_library_aliquots.txt
    $ cat file_manifest_library_aliquots.txt
    LA-123
    LA-345