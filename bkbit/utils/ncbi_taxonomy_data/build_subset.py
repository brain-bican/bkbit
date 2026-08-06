"""
Rebuilds the NCBI taxonomy subset that is bundled inside the bkbit wheel.

The full NCBI taxonomy (~2.6M taxa, ~230MB of JSON) is far too large to ship on
PyPI, but bkbit only ever needs a scientific name, a common name, and a taxon id
for the organism a GFF3 file belongs to. Every taxon that carries a GenBank
common name (~30k of them, which covers every organism anyone realistically
runs an annotation pipeline for) fits in well under 1MB gzipped, so that subset
is bundled and used as the fast, offline path. Anything outside the subset falls
back to the full download managed by `bkbit.utils.ncbi_taxonomy_cache`.

Usage (maintainers only, not part of the runtime path):

    bkbit download-ncbi-taxonomy            # build the full cache first
    python -m bkbit.utils.ncbi_taxonomy_data.build_subset

Commit the regenerated `taxonomy_subset.json.gz` alongside any release that
should pick up a newer taxonomy dump.
"""

import gzip
import json
from datetime import date
from pathlib import Path
from typing import Optional

from bkbit.utils.ncbi_taxonomy_cache import (
    BUNDLED_SUBSET_FILENAME,
    NCBI_TAXON_URL,
    SUBSET_FORMAT_VERSION,
    full_cache_paths,
)


def build_subset(
    cache_dir: Optional[Path] = None, output_path: Optional[Path] = None
) -> Path:
    """
    Builds the bundled subset from a fully downloaded taxonomy cache.

    Args:
        cache_dir: Directory holding the full taxonomy cache. Defaults to the
            cache directory `bkbit.utils.ncbi_taxonomy_cache` resolves to.
        output_path: Where to write the gzipped subset. Defaults to the bundled
            location inside this package.

    Returns:
        Path: The path the subset was written to.
    """
    paths = full_cache_paths(cache_dir)
    missing = [str(p) for p in paths.values() if not p.exists()]
    if missing:
        raise FileNotFoundError(
            "Full taxonomy cache is incomplete; run 'bkbit download-ncbi-taxonomy' "
            f"first. Missing: {', '.join(missing)}"
        )

    with paths["scientific"].open(encoding="utf-8") as f:
        taxid_to_scientific_name = json.load(f)
    with paths["common"].open(encoding="utf-8") as f:
        taxid_to_common_name = json.load(f)

    # A taxon is only usable by the translator if it has both names, so the
    # subset is exactly the intersection of the two maps.
    taxa = {
        taxid: [taxid_to_scientific_name[taxid], common_name]
        for taxid, common_name in taxid_to_common_name.items()
        if taxid in taxid_to_scientific_name
    }

    payload = {
        "format": SUBSET_FORMAT_VERSION,
        "source": NCBI_TAXON_URL,
        "built": date.today().isoformat(),
        "taxa": taxa,
    }

    if output_path is None:
        output_path = Path(__file__).parent / BUNDLED_SUBSET_FILENAME
    blob = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    with gzip.open(output_path, "wb", compresslevel=9) as f:
        f.write(blob)

    print(
        f"Wrote {len(taxa)} taxa to {output_path} ({output_path.stat().st_size} bytes)"
    )
    return output_path


if __name__ == "__main__":
    build_subset()
