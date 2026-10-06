# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

bkbit (Brain Knowledge Base Interaction Toolkit) is a Python library for working with BICAN (Brain Initiative Cell Atlas Network) Knowledgebase Data Models. It contains Pydantic versions of the BICAN models along with tools for data translation, model conversion, and model editing.

## Development Setup

```bash
# Install in editable mode with all dependencies
pip install -e .[all]

# Install newer schemasheets version (temporary fix)
pip install git+https://github.com/linkml/schemasheets
```

## Commands

### Testing
```bash
# Run all tests
pytest

# Run a specific test file
pytest bkbit/tests/test_specimen_portal_translator.py

# Run a specific test
pytest bkbit/tests/test_specimen_portal_translator.py::test_library_pool
```

### Linting and Formatting
```bash
# Format with black
black .

# Run pre-commit hooks
pre-commit run --all-files
```

### CLI Usage
The package provides a CLI tool `bkbit` with multiple subcommands:
- `bkbit specimen2jsonld` - Generate BICAN objects from Specimen Portal data
- `bkbit gff2jsonld` - Generate genome annotation objects from GFF3 files
- `bkbit taxonomy2jsonld` - Generate taxonomy objects from HMBA annotations
- `bkbit ait2jsonld` - Generate Cell Taxonomy objects from an AIT `.h5ad` (local or remote)
- `bkbit schema2model` - Convert spreadsheets to LinkML YAML models
- `bkbit yaml2cvs` - Convert YAML to CSV
- `bkbit linkml-trimmer` - Trim LinkML models
- `bkbit download-ncbi-taxonomy` - Optionally pre-download the full NCBI taxonomy (see below)

## Architecture

### Core Modules

**`bkbit/models/`** - Pydantic model definitions generated from LinkML schemas:
- `library_generation.py` - Library generation workflow models
- `genome_annotation.py` - Genome annotation models
- `anatomical_structure.py` - Anatomical structure models

**`bkbit/data_translators/`** - Convert external data sources to BICAN model instances:
- `library_generation_translator.py` - Specimen Portal to BICAN objects (specimen2jsonld)
- `genome_annotation_translator.py` - GFF3 files to genome annotation objects (gff2jsonld)
- `HMBA_annotation_translator.py` - HMBA taxonomy annotations (taxonomy2jsonld)
- `ait_taxonomy_translator.py` - AIT `.h5ad` taxonomies to Cell Taxonomy JSON-LD (ait2jsonld)
- `specimen_metadata_translator.py` - Specimen metadata handling

**`bkbit/model_converters/`** - Tools for converting between formats:
- `sheets_converter.py` - Google Sheets/TSV to LinkML YAML (schema2model)
- `yaml2sheet_converter.py` - YAML to CSV conversion

**`bkbit/model_editors/`** - Tools for modifying LinkML models:
- `linkml_trimmer.py` - Trims LinkML models to include only specified classes/slots/enums
- `add_dunderMethods_genomeAnnotation.py` - Adds __eq__, __ne__, __hash__ to GeneAnnotation

**`bkbit/utils/`** - Shared utilities:
- `ncbi_taxonomy_cache.py` - NCBI taxonomy name lookups (see NCBI Taxonomy Data below)
- `ncbi_taxonomy_data/` - Bundled taxonomy subset + the script that rebuilds it
- `get_ncbi_taxonomy.py` - Thin CLI wrapper for pre-fetching the full taxonomy
- `nimp_api_endpoints.py` - Specimen Portal API endpoints
- `setup_logger.py` - Logging configuration

### External Dependencies
- **LinkML** - Schema definition language for the models
- **Schemasheets** - Spreadsheet to LinkML conversion
- **Click** - CLI framework

### NCBI Taxonomy Data

`gff2jsonld` resolves organism names through `bkbit/utils/ncbi_taxonomy_cache.py`, which
serves lookups from two layers and requires no setup after `pip install`:

1. **Bundled subset** (`bkbit/utils/ncbi_taxonomy_data/taxonomy_subset.json.gz`, ~575KB) -
   every taxon with a GenBank common name (~30k), which covers all BICAN organisms.
   Offline, loads in milliseconds.
2. **Full NCBI taxonomy** - downloaded on demand only if a lookup misses the subset, and
   cached in a per-user cache directory (never in `site-packages`).

Rules to preserve when touching this code:
- **Never load taxonomy data at import time.** The previous version read the maps in the
  `Gff3` class body, so a missing cache broke every `bkbit` subcommand, including `--help`.
- **Never write runtime data into the installed package.** `site-packages` may be read-only
  and is wiped on upgrade.

To regenerate the bundled subset for a newer taxonomy dump:
```bash
bkbit download-ncbi-taxonomy
python -m bkbit.utils.ncbi_taxonomy_data.build_subset   # commit the resulting .json.gz
```

### AIT taxonomy translation (`ait2jsonld`)

Reads an Allen Institute Taxonomy `.h5ad` and emits Cell Taxonomy JSON-LD.

Rules to preserve when touching this code:

- **Field locations are never hardcoded.** Every slot in
  `bkbit/models/cell_taxonomy.yaml` carries an `ait_location` annotation saying
  where its value lives in the file; the translator resolves those through
  `SchemaView`. Changing the source spreadsheet changes behaviour with no code
  edit. Where a declared location cannot be honoured the translator may fall
  back, but the deviation is always written to the run report, never applied
  silently.
- **The annotations are read from the generated pydantic model**, not from a
  LinkML YAML. linkml's pydantic generator preserves them under each field's
  `json_schema_extra["linkml_meta"]`, so `bkbit/models/cell_taxonomy.py` is a
  complete source (verified against SchemaView: the same 52 (class, slot)
  pairs, identical values, and identical cardinality on all 732 shared keys).
  That means `ait2jsonld` needs **no extra artifact** — the model arrives by
  the models repo's `push_model_to_bkbit.yaml` workflow like every other.
- **It therefore depends on that model being current.** The annotations were
  added 2026-10-01; against an older `cell_taxonomy.py` nothing resolves, so
  `load_locations()` raises instead of silently emitting an empty graph.
- **ids come from `generate_object_id`,** like every other translator. The
  class name is deliberately not hashed -- see
  `bkbit/tests/test_ait_taxonomy_translator.py`.
- **`h5py` and `anndata` are imported lazily.** `cli.py` imports this module to
  register the command, so a module-scope import would make a stale environment
  break every subcommand including `--help` -- the same failure mode recorded
  for the NCBI taxonomy cache above. They are declared dependencies; the guard
  exists so a partial install degrades to one failing command.
- **Remote files are read over HTTP range requests** (`fsspec` + `h5py`), never
  downloaded; `X`, `raw` and `layers` are never materialised. A 332 GB file is
  routine. `--cache DIR` keeps a local block cache across runs.

```bash
bkbit ait2jsonld https://.../Human_LGN_SMART_seq_04042025.h5ad \
    --species Human --out Human_LGN.jsonld --report Human_LGN.report.json
```

### Environment Variables
- `jwt_token` - Specimen Portal Personal API Token (required for specimen2jsonld)
- `BKBIT_DATA_DIR` - Overrides the cache directory for the downloaded full NCBI taxonomy
- `BKBIT_NO_DOWNLOAD` - If set, a taxonomy lookup that misses the bundled subset raises
  instead of downloading (useful in CI/air-gapped runs)
