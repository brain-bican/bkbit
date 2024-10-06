.. _spreadsheet_converter:

Spreadsheet to LinkML Schema
=============================

Overview
.........
Create a yaml linkml model from set of spreadsheets. It can use either tsv files or Google Sheet as an input.

The default behavior is to run the converter starting with tsv files, specifying their paths as arguments, for example, model_spreadsheets/*tsv.

If ``--gsheet`` option is used, the converter starts from downloading spreadsheets  from Google Sheets.
The argument must be a YAML file that has ``gsheet_id`` and a list of ``sheets``  with ``gid`` (a unique identifier for each individual sheet) 
and ``name`` (optionally) that will be used as a name of the downloaded TSV file (if not available ``gid`` wil be used).

Command Line
.............

``bkbit schema2model``
,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    $ bkbit schema2model [OPTIONS] SPREADSHEETS

**Options**

    ``-o, --output <output>``
        Path for the yaml output file.

    ``-t, --template <template>``
        Optional template yaml file with standard classes that will be added to the model.

    ``--gsheet, --no-gsheet``
        Using Google Sheet as a source. If True, the arguments MUST be a yaml file with gsheet_id
        and gid of all the sheets.

        Default:
            False

    ``--gsheet-download-dir <gsheet_download_dir>`` 
        Path used to download Google Sheets. If not specified a default directory will be created.

    ``--fix_tsv, --no-fix_tsv``
        Fixing known issues with tsv files from Google Sheets. 
        
        Default:
            True
    
    ``--fix_tsv_save, --no-fix_tsv_save``
        Keeping the fixed files, relevant only if fix_tsv is True  
        
        Default: 
            False

    ``--repair, --no-repair``
        Standard Linkml auto-repair schema
        
        Default:
            True
    ``--fix_bican_model, --no-fix_bican_model``
        Automated repair specifically for the BICAN YAML model  
        
        Default:
            True

**Arguments**
    
        ``SPREADSHEETS``
            Required argument
  
Examples
.........

Example 1: Schema defined in tsv files
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # Run schema2model command 
    $ bkbit schema2model -o model.yaml source_model/spreadsheets/*.tsv

Example 2: Schema defined in Google Sheets
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    # Run schema2model command 
    $ bkbit schema2model -o model.yaml  --gsheet --gsheet-download-dir source_model/spreadsheets  source_model/gsheet.yaml