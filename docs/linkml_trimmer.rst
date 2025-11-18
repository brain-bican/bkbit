.. _linkml_trimmer:

LinkML Schema Trimmer
----------------------

Overview
.........
Generate a trimmed version of a LinkML schema by only including a specific subset of classes, slots, and enums.


Command Line
.............

``bkbit linkml-trimmer``
,,,,,,,,,,,,,,,,,,,,,,,,

    .. code-block:: bash
        
        $ bkbit linkml-trimmer [OPTIONS] SCHEMA

Options
,,,,,,,

    ``-c, --classes <classes>``        
        List of 'classes' to include in the trimmed schema.

        **Note**: Classes must be separated by commas and enclosed in quotes.
    ``-s, --slots <slots>``
        List of 'slots' to include in the trimmed schema.

        **Note**: Slots must be separated by commas and enclosed in quotes.

    ``-e, --enums <enums>``
        List of 'enums' to include in the trimmed schema.

        **Note**: Enums must be separated by commas and enclosed in quotes.
    ``-i, --schema_id <schema_id>``
        Updated schema id for trimmed schema.
    ``-n, --schema_name <schema_name>``
        Updated schema name for trimmed schema.
    ``-t, --schema_title <schema_title>``
        Updated schema title for trimmed schema.
    ``-v, --schema_version <schema_version>``
        Updated schema version for trimmed schema.
    
Arguments
,,,,,,,,,

    ``SCHEMA``
        **Type**: str | Path | SchemaDefinition
           


Examples
.........

Example 1: Trim Schema (Local File): 
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    $ bkbit linkml-trimmer --classes "gene, genome, organism taxon, thing with taxon, material sample, procedure, entity, activity, named thing, relative frequency analysis result" biolink-model.yaml > bican-biolink.yaml


Example 2: Trim Schema (URL): 
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    $ bkbit linkml-trimmer --classes "gene, genome, organism taxon, thing with taxon, material sample, procedure, entity, activity, named thing, relative frequency analysis result" "https://raw.githubusercontent.com/biolink/biolink-model/refs/heads/master/biolink-model.yaml" > bican-biolink.yaml