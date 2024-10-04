.. _specimen_file_manifest:

Specimen File Manifest
----------------------

Overview
.........

Generates a JSON-LD file containing specimen file data using the BICAN Library Generation Schema. 

Command Line
.............

``bkbit filemanifest2jsonld``
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    $ bkbit filemanifest2jsonld [OPTIONS] FILE_MANIFEST_CSV

**Options**

    ``--list_library_aliquots``
        A boolean flag that, when provided, generates a list of unique library aliquots contained in the given file manifest and saves output in file called 'file_manifest_library_aliquots.txt'. 
        If this flag is not set (DEFAULT), then only the JSON-LD output will be generated.

**Arguments**

    ``FILE_MANIFEST_CSV``
        Required argument. 
        FILE_MANIFEST_CSV can be optained from Brain Knowledge Platform and **must** contains the following columns:

            - Project ID	
            - Specimen ID	
            - File Name	
            - Checksum	
            - File Type	
            - Archive	
            - Archive URI

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
    LP-123
    LP-345