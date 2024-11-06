.. _specimen_metadata:

Specimen Metadata
----------------------

Overview
.........

Generate JSON-LD files for specimens, subjects, and their repective ancestors or descendants. Data is retrieved from the `BICAN Specimen Portal <https://brain-specimenportal.org/>`_. 

Command Line 
.............

``bkbit specimen2jsonld``
,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    $ bkbit specimen2jsonld [OPTIONS] NHASH_ID_OR_FILE

**Options**

    ``-d, --decendants``
        A boolean flag that, when provided, generates BICAN objects for the given NHASH_ID and all of its descendants. 
        If this flag is not set (DEFAULT), then the ancestors will be processed.

**Arguments**

    ``NHASH_ID_OR_FILE``
        The NHASH_ID of the specimen or a file containing a list of NHASH_IDs. 
        If a file is provided, the file should contain one NHASH_ID per line.

Environment Variables 
.............

jwt_token
,,,,,,,,,

Token is used to authenticate with the Specimen Portal API and retrieve the specimen metadata.

.. note::
    You **must** set the Specimen Portal Personal API Token as an environment variable **before** running ``bkbit specimen2jsonld``. 

.. code-block:: bash

    $ export jwt_token=specimen_portal_personal_api_token

Examples 
.........

Example 1: Parse a single record and its ancestors
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash
    
    # If first time running specimen2jsonld or if token is expired, set jwt_token environment variable
    $ export jwt_token=specimen_portal_personal_api_token

    # Run specimen2jsonld command 
    $ bkbit specimen2jsonld 'LP-CVFLMQ819998' > output.jsonld

Example 2: Parse a single record and its descendants
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # If first time running specimen2jsonld or if token is expired, set jwt_token environment variable
    $ export jwt_token=specimen_portal_personal_api_token

    # Run specimen2jsonld command. Important: include '--descendants' flag
    $ bkbit specimen2jsonld -d 'DO-GICE7463' > output.jsonld

Example 3: Parse a file containing record(s) and their respective ancestors
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # If first time running specimen2jsonld or if token is expired, set jwt_token environment variable
    $ export jwt_token=specimen_portal_personal_api_token

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

    # If first time running specimen2jsonld or if token is expired, set jwt_token environment variable
    $ export jwt_token=specimen_portal_personal_api_token

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

