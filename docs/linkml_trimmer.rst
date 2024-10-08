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
        
        $ bkbit linkml-trimmer [OPTIONS] CLASSES SCHEMA

Options
,,,,,,,

    ``-s, --slots <slots>``
        List of 'slots' to include in the trimmed schema.

        **Note: Slots must be separated by commas and enclosed in quotes.**

    ``-e, --enums <enums>``
        List of 'enums' to include in the trimmed schema.

        **Note: Enums must be separated by commas and enclosed in quotes.**
    
Arguments
,,,,,,,,,

    ``CLASSES``
        Required argument

        List of 'classes' to include in the trimmed schema.

        **Note: Classes must be separated by commas and enclosed in quotes.**

    ``SCHEMA``
        Required argument


Examples
.........

Example 1: Trim `Biolink Schema <https://biolink.github.io/biolink-model/>`_
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    $ classes =  ['gene', 'genome', 'organism taxon', 'thing with taxon', 'material sample', 'procedure', 'entity', 'activity', 'named thing']
    $ bkbit classes biolink.yaml > bican-biolink.yaml