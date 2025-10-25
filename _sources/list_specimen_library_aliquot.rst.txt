.. _list_specimen_library_aliquot:

Specimen Library Aliquot List
-----------------------------

Overview
.........
Generates a list of Library Aliquot NHash IDs from an overall specimen list retrieved from the Brain Knowledge Platform. 

Retrieve Specimen Metadata from Brain Knowledge Platform 
.......................................................

- Step 1: Go to `Brain Knowledge Platform <https://knowledge.brain-map.org/>`_

- Step 2: Navigate to 'Data/Projects' tab on the top right menu

- Step 3: Filter by 'Specimen Type' specifically "Library Aliquot"

- Step 4: Click on specific project i.e. "BICAN Rapid Release Inventory: Single cell transcriptomics and epigenomics"

- Step 5: Click on 'BROWSE SPECIMENS' button

- Step 6: Click on download icon (arrow pointing down) on top menu bar and select 'Metadata'

The input file manifest must be in CSV format.

Required columns:

        - Specimen ID	

Optional columns:

        - Project ID
        - Library ALiquot NHash ID
        - Subject NHash ID


Command Line
.............

``bkbit list-library-aliquot``
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    $ bkbit list-library-aliquot SPECIMEN_METADATA_CSV

**Arguments**

    ``SPECIMEN_METADATA_CSV``
        Required argument

Examples
.........

Example 1: Save list of library aliquots to file
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # Run list-library-aliquot command 
    $ bkbit list-library-aliquot SpecimenMetadata.csv > library_aliquot_list.txt