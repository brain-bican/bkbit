.. _ait_taxonomy:

Cell Type Taxonomy (AIT h5ad)
------------------------------

Overview
.........

Generate JSON-LD files for a cell type taxonomy stored in `Allen Institute Taxonomy (AIT)
<https://github.com/AllenInstitute/AllenInstituteTaxonomy/blob/main/docs/schema.md>`_
format, an AnnData ``.h5ad`` file. The objects follow the BICAN ``cell_taxonomy`` model.

Only the metadata of the file is read (``uns``, a few ``obs`` columns, the ``var`` index and
the keys/shapes of ``X``, ``raw.X`` and ``obsm``); expression matrices are never loaded.
Because of that, the H5AD file can also be a URL (``http(s)://`` or ``s3://``), in which
case only the bytes that are needed are fetched. Reading URLs requires the ``remote`` extra:

.. code-block:: bash

    $ pip install 'bkbit[remote]'

Each JSON-LD file will contain:

=====================  ==============================================================
Object                 Source in the AIT file
=====================  ==============================================================
1 CellTypeTaxonomy     ``uns`` (title, schema_version, hierarchy, mode, filter, ...)
CellTypeSet objects    one per annotation level in ``uns['hierarchy']`` (e.g. Class)
CellTypeTaxon objects  one per distinct value of each annotation level
1 ClusterSet           the ``cluster_id`` level
Cluster objects        one per ``cluster_id`` value
ExpressionMatrix       ``X`` (normalized) and ``raw.X`` (raw counts), when present
Embedding objects      one per ``obsm['X_*']`` entry
Cell objects           one per cell in ``obs`` (only with ``--include_cells``)
=====================  ==============================================================

Taxon data the ``cell_taxonomy`` model has no slot for is expressed with the
``bke_taxonomy`` model, and the output then lists both models' JSON-LD contexts:

- ``color_hex_<level>`` -> a DisplayColor per taxon (``is_color_for_taxon``), all in one
  ColorPalette for the taxonomy
- ``tokens_<level>`` (e.g. ``STRd|D2 Matrix MSN``) -> an Abbreviation per token; the
  taxon lists them in ``has_abbreviation``

AIT files store only the abbreviation tokens. To add their meaning and the entities they
denote, pass ``--abbreviation_file`` with a CSV in the format used by ``taxonomy2jsonld``
(columns ``token``, ``meaning``, ``type`` = ``cell_type``/``gene``/``anatomical``,
``primary_identifier``, ``secondary_identifier``).

Columns without a level suffix describe the finest annotation level (``Group`` in HMBA):

- ``curated_markers`` -> ``curated_markers_to_primates`` (``curated_markers_to_mouse`` for
  mouse taxonomies, i.e. ``organism_ontology_term_id`` is ``NCBITaxon:10090``)
- ``literature_name_short`` -> ``synonym``
- ``literature_name_long`` -> ``full_name``

Each CellTypeTaxon links to its parent taxon at the next broader level (``has_parent``)
and records the number of cells it contains. Its accession ID, display order and CL term
are read from per-level columns that follow the HMBA naming convention:
``accession_<level>``, ``display_order_<level>`` and ``CL:ID_<level>`` (level in lower
case). These columns are read from ``uns['cluster_info']`` when it lists every annotation
level, and from ``obs`` otherwise. Values that are not CL IDs (e.g. ``PR 2579``) are
skipped with a warning.

If the file defines several taxonomy modes, ``--mode`` selects one; cells flagged by
``uns['filter'][mode]`` are left out of the cell counts, and clusters with no remaining
cells are left out entirely.

Command Line
.............

``bkbit ait2jsonld``
,,,,,,,,,,,,,,,,,,,,,

    .. code-block:: bash

        $ bkbit ait2jsonld [OPTIONS] H5AD_FILE

Options
,,,,,,,,

    ``-o, --output_file <output_file>``
        Output file path. Prints to stdout if not given.

    ``-f, --output_format <jsonld|turtle>``
        Output format. Default: ``jsonld``.

    ``-m, --mode <mode>``
        Taxonomy mode to translate. Defaults to ``uns['mode']``.

    ``-a, --taxonomy_accession <accession>``
        Accession ID to assign to the taxonomy (AIT files do not store one).

    ``-b, --abbreviation_file <csv>``
        Meaning (and denoted entities) of the abbreviation tokens.

    ``--include_cells``
        Also generate a Cell object for every cell. Taxonomies routinely hold millions of
        cells, so the output can be very large.

    ``--include_variables``
        List every gene of the ``var`` index in ``ExpressionMatrix.has_variable``.

Arguments
,,,,,,,,,,

    ``H5AD_FILE``
        Required argument. Local path or URL of the AIT ``.h5ad`` file.

Examples
.........

Example 1: HMBA basal ganglia taxonomy, read directly from S3
,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,,

.. code-block:: bash

    $ pip install 'bkbit[remote]'

    $ bkbit ait2jsonld -o marmoset_bg_taxonomy.jsonld \
        'https://released-taxonomies-802451596237-us-west-2.s3.us-west-2.amazonaws.com/HMBA/BasalGanglia/BICAN_05072025_pre-print_release/Marmoset_HMBA_basalganglia_AIT_pre-print.h5ad'

Example 2: Python
,,,,,,,,,,,,,,,,,,

.. code-block:: python

    from bkbit.data_translators.ait_taxonomy_translator import AITTaxonomy

    taxonomy = AITTaxonomy("Human_HMBA_basalganglia_AIT_pre-print.h5ad").parse()
    taxonomy.cell_type_taxa[("Subclass", "STR D1 MSN")]  # CellTypeTaxon object
    taxonomy.serialize_to_jsonld("human_bg_taxonomy.jsonld")
