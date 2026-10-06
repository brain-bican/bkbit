#!/usr/bin/env python3
"""Refresh bkbit/models/cell_taxonomy.yaml from the models repo.

``ait2jsonld`` resolves every field location from the ``ait_location``
annotations on the cell_taxonomy LinkML schema. Those annotations exist only in
the LinkML source -- the generated pydantic model drops them -- so bkbit has to
carry the YAML as well as the .py.

The upstream source imports five sibling schemas (bican_biolink, bican_prov,
bican_core, genome_annotation, anatomical_structure). Shipping six files that
each have to stay in step with brain-bican/models would be a standing drift
hazard, so this writes a single self-contained schema with the import closure
merged in.

The .py and .context.jsonld next to it come from a different route -- the
models repo's push_model_to_bkbit.yaml workflow. This script does not touch
them; run that workflow to refresh those.

Usage:
    python scripts/refresh_cell_taxonomy_schema.py [path/to/models/linkml-schema/cell_taxonomy.yaml]
"""

import sys
from pathlib import Path

from linkml_runtime.dumpers import yaml_dumper
from linkml_runtime.utils.schemaview import SchemaView

DEST = Path(__file__).resolve().parents[1] / "bkbit" / "models" / "cell_taxonomy.yaml"
DEFAULT_SRC = (
    Path(__file__).resolve().parents[2]
    / "models"
    / "linkml-schema"
    / "cell_taxonomy.yaml"
)


def count_locations(sv: SchemaView) -> int:
    n = 0
    for cls in sv.all_classes().values():
        for container in (cls.slot_usage or {}, cls.attributes or {}):
            for su in container.values():
                if su.annotations and "ait_location" in su.annotations:
                    n += 1
    return n


def main() -> int:
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SRC
    if not src.is_file():
        print(f"error: source schema not found: {src}", file=sys.stderr)
        print(
            "Pass the path to brain-bican/models/linkml-schema/cell_taxonomy.yaml",
            file=sys.stderr,
        )
        return 1

    sv = SchemaView(str(src))
    before = count_locations(sv)
    sv.merge_imports()
    DEST.write_text(yaml_dumper.dumps(sv.schema))

    # A merge that silently dropped annotations would leave the translator
    # resolving nothing, so verify rather than assume.
    after = count_locations(SchemaView(str(DEST)))
    print(f"{src} -> {DEST}")
    print(f"  ait_location slots: {before} before merge, {after} after")
    if before != after:
        print("error: annotation count changed across the merge", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
