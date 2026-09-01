#!/usr/bin/env python
"""Macaque atlas lineage diagram for a single donor.

Default target donor is ``DO-IJUP7054``. The script:

1. Pulls every descendant of the donor from the NIMP Specimen Portal.
2. Auto-discovers the NIMP record field carrying the Barcoded Cell Sample tag
   (e.g. ``HMBA_Macaque_Atlas_BN_BF``), the Tissue Sample Structure field, and
   the Tissue Structure Acronym field. Discovery uses value matching against
   known atlas strings — no need to hard-code NIMP field names.
3. Filters:

   - **Libraries** kept if any upstream Barcoded Cell Sample carries the tag
     ``HMBA_Macaque_Atlas_BN_BF``.
   - **Sections** kept if their upstream Tissue's structure equals
     ``basal nuclei (basal ganglia)``.

4. Colors kept libraries (and their upstream ribbons) by tissue structure,
   using the HOMBA anatomy palette scraped from
   https://alleninstitute.github.io/CCF-MAP/docs/HOMBA_ontology_v1.html at
   runtime, falling back to a curated palette for the six expected structures.
5. Renders a Sankey lineage as interactive Plotly HTML **and** a static PNG.

Run locally (needs the ``jwt_token`` env var):

    export jwt_token=...   # NIMP Personal API Token
    python scripts/macaque_atlas_diagram.py

Optional flags::

    --donor DO-IJUP7054
    --out-dir ./out
    --bcs-tag HMBA_Macaque_Atlas_BN_BF
    --section-structure "basal nuclei (basal ganglia)"
    --skip-png       # skip static PNG (avoids kaleido dependency)
    --cache-dir ./_nimp_cache   # cache raw NIMP responses to disk

Optional deps: ``plotly`` (HTML), ``kaleido`` (PNG), ``beautifulsoup4`` (better
HOMBA scrape). All are optional — the script degrades gracefully.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Set, Tuple

import requests
from tqdm import tqdm

# Reuse the existing thin NIMP client so this script stays in step with the
# rest of bkbit rather than duplicating URL/token handling.
from bkbit.utils.nimp_api_endpoints import (
    get_ancestors,
    get_data,
    get_descendants,
)


DEFAULT_DONOR = "DO-IJUP7054"
DEFAULT_BCS_TAG = "HMBA_Macaque_Atlas_BN_BF"
DEFAULT_SECTION_STRUCTURE = "basal nuclei (basal ganglia)"

# NIMP raw-record field names. These are the "local_name_value" NIMP names
# for the corresponding schema slots; they are the source of truth. Auto-
# discovery below runs on top of these only as a sanity-check / fallback
# when a field is genuinely missing on the record shape.
DEFAULT_BCS_TAG_FIELD = "barcoded_cell_sample_tag_local_name"
DEFAULT_TISSUE_STRUCTURE_FIELD = "structure"          # schema slot: tissue_sample_structure
DEFAULT_TISSUE_ACRONYM_FIELD = "tissue_structure_acronym"

# Expected library-side structures per the task; used both to seed field
# auto-discovery and as the fallback color-map keys.
EXPECTED_LIBRARY_STRUCTURES = [
    "body of caudate",
    "septal nuclei",
    "head of caudate",
    "putamen",
    "caudate nucleus",
    "globus pallidus",
]

# Section-structure presets. The canonical "basal nuclei (basal ganglia)"
# phrase doesn't appear on any record for DO-IJUP7054; the tissues carry
# substructure names instead. The preset expands to the canonical basal-
# ganglia parts (plus septal nuclei, which is basal forebrain territory but
# is present in this donor's substructures).
SECTION_STRUCTURE_PRESETS = {
    "basal-nuclei": [
        "caudate nucleus",
        "head of caudate",
        "body of caudate",
        "tail of caudate",
        "putamen",
        "globus pallidus",
        "external segment of globus pallidus",
        "internal segment of globus pallidus",
        "nucleus accumbens",
        "septal nuclei",
        "lateral septal complex",
    ],
}

# The pipeline stage order we lay out left→right on the Sankey. Every
# category the NIMP graph might carry is listed here so unknown categories
# (like "Section") can slot in without a schema change.
STAGE_ORDER = [
    "Donor",
    "Slab",
    "Tissue",
    "Section",              # rendered immediately after Tissue per feedback
    "Specimen Dissected ROI",
    "Dissociated Cell Sample",
    "Enriched Cell Sample",
    "Barcoded Cell Sample",
    "Amplified cDNA",
    "Library",
    "Library Aliquot",
]

HOMBA_URL = "https://github.com/AllenInstitute/CCF-MAP/releases/latest/download/HOMBA.csv"

# In columns with more than this many nodes, per-node labels are suppressed
# (still shown on hover). Overridable via --label-cap.
_LABEL_CAP = 12


# ---------------------------------------------------------------------------
# NIMP fetch with on-disk cache
# ---------------------------------------------------------------------------

def _cache_path(cache_dir: Optional[Path], kind: str, key: str) -> Optional[Path]:
    if cache_dir is None:
        return None
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", key)
    return cache_dir / f"{kind}_{safe}.json"


_CACHE_STATS = {"hit": 0, "miss": 0}
_OFFLINE = False


def _cached(cache_dir: Optional[Path], kind: str, key: str, fetch):
    p = _cache_path(cache_dir, kind, key)
    if p is not None and p.exists():
        _CACHE_STATS["hit"] += 1
        return json.loads(p.read_text())
    if _OFFLINE:
        raise SystemExit(
            f"--offline set but cache miss for {kind}={key!r}. Rerun without "
            f"--offline to populate the cache first."
        )
    _CACHE_STATS["miss"] += 1
    payload = fetch()
    if p is not None:
        p.write_text(json.dumps(payload))
    return payload


def fetch_descendants(donor: str, jwt: str, cache_dir: Optional[Path]) -> Dict:
    return _cached(cache_dir, "descendants", donor,
                   lambda: get_descendants(donor, jwt, nhash_only=True))


def fetch_data(nhash_id: str, jwt: str, cache_dir: Optional[Path]) -> Dict:
    return _cached(cache_dir, "data", nhash_id,
                   lambda: get_data(nhash_id, jwt))


def fetch_ancestors(nhash_id: str, jwt: str, cache_dir: Optional[Path]) -> Dict:
    """Only needed to find each library's parent chain when parents don't
    come back in the descendants payload."""
    return _cached(cache_dir, "ancestors", nhash_id,
                   lambda: get_ancestors(nhash_id, jwt, nhash_only=True))


# ---------------------------------------------------------------------------
# Field auto-discovery
# ---------------------------------------------------------------------------

def _iter_scalar_fields(record: Dict) -> Iterable[Tuple[str, str]]:
    """Yield (field_name, string_token) for every field on a NIMP record, with
    ``{"name": ..., "desc": ...}``-shaped values unwrapped to their name."""
    for k, v in record.items():
        for token in _flatten_field_value(v):
            yield k, token


def summarize_bcs_tag_values(nodes: Dict[str, Dict], bcs_tag_field: str) -> Dict[str, int]:
    """Distinct values seen on ``bcs_tag_field`` across every BCS record, with
    counts. Values are flattened through ``_flatten_field_value`` so
    dict-shaped tags print as their ``name`` rather than the wrapper dict.
    """
    counts: Dict[str, int] = defaultdict(int)
    for node in nodes.values():
        if node.get("category") != "Barcoded Cell Sample":
            continue
        record = node.get("record") or {}
        for token in _flatten_field_value(record.get(bcs_tag_field)):
            counts[token] += 1
    return dict(counts)


def discover_fields(nodes: Dict[str, Dict], bcs_tag: str,
                    section_structure: str) -> Dict[str, str]:
    """Given every fetched node, discover which raw-record field carries
    each thing we filter on.

    Returns a dict with keys:
      - ``bcs_tag_field``       : the NIMP field on a Barcoded Cell Sample record
                                  that holds values like ``HMBA_Macaque_Atlas_BN_BF``
      - ``tissue_structure_field`` : the field on a Tissue that equals values
                                     like ``basal nuclei (basal ganglia)`` or
                                     ``putamen``
      - ``tissue_acronym_field``   : the field on a Tissue that holds acronyms
                                     (BCd, HCd, Pu, Cd, GP, LSX ...)
    """
    known_structure_values = {
        section_structure.lower(),
        *(s.lower() for s in EXPECTED_LIBRARY_STRUCTURES),
    }
    known_acronyms = {
        "bcd", "hcd", "cd", "pu", "gp", "gpe", "gpi", "lsx", "sep", "bn",
    }

    votes: Dict[str, Dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for node in nodes.values():
        category = node.get("category")
        record = node.get("record") or {}
        for field, value in _iter_scalar_fields(record):
            v_lower = value.lower().strip()
            if category == "Barcoded Cell Sample" and value == bcs_tag:
                votes["bcs_tag_field"][field] += 1
            if category == "Tissue" and v_lower in known_structure_values:
                votes["tissue_structure_field"][field] += 1
            if category == "Tissue" and v_lower in known_acronyms:
                votes["tissue_acronym_field"][field] += 1

    discovered = {}
    for key, field_counts in votes.items():
        best = max(field_counts.items(), key=lambda kv: kv[1])[0]
        discovered[key] = best
    return discovered


# ---------------------------------------------------------------------------
# HOMBA color palette
# ---------------------------------------------------------------------------

# Curated fallback keyed on the six structures the task expects. These are
# neutral placeholders; the runtime scrape below overrides them when
# available.
FALLBACK_STRUCTURE_COLORS = {
    "caudate nucleus":   "#4E9F3D",
    "head of caudate":   "#66C266",
    "body of caudate":   "#8FDC7A",
    "putamen":           "#2E7D32",
    "globus pallidus":   "#F4A261",
    "septal nuclei":     "#8E7CC3",
    "basal nuclei (basal ganglia)": "#5D9CEC",
}


def fetch_homba_colors() -> Dict[str, str]:
    """Fetch the HOMBA ontology CSV and return {lower(name-or-acronym): #RRGGBB}.

    The Allen CCF-MAP release ships a canonical CSV with columns
    HOMBA_name / HOMBA_abbreviation / r / g / b (0-255 ints), plus a DHBA
    name and acronym per row. We index all four labels at the same hex
    color so a lookup by either the structure name or its acronym hits.

    Empty on failure; callers fall back to ``FALLBACK_STRUCTURE_COLORS``.
    """
    import csv
    import io

    try:
        # requests follows the GitHub release-asset redirect chain transparently.
        resp = requests.get(HOMBA_URL, timeout=30, allow_redirects=True)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] could not fetch HOMBA CSV ({HOMBA_URL}): {exc}")
        return {}

    palette: Dict[str, str] = {}
    reader = csv.DictReader(io.StringIO(resp.text))
    for row in reader:
        try:
            r = int(row.get("r") or 0)
            g = int(row.get("g") or 0)
            b = int(row.get("b") or 0)
        except ValueError:
            continue
        hex_color = f"#{r:02X}{g:02X}{b:02X}"
        for key_field in ("HOMBA_name", "HOMBA_abbreviation", "DHBA_name", "DHBA_acronym"):
            label = (row.get(key_field) or "").strip().lower()
            if label:
                palette.setdefault(label, hex_color)
    return palette


def resolve_structure_color(structure: Optional[str],
                            acronym: Optional[str],
                            homba: Dict[str, str]) -> str:
    """Pick the best color for a tissue structure/acronym pair."""
    candidates: List[str] = []
    for v in (structure, acronym):
        if v:
            candidates.append(v.lower().strip())
    for c in candidates:
        if c in homba:
            return homba[c]
    for c in candidates:
        if c in FALLBACK_STRUCTURE_COLORS:
            return FALLBACK_STRUCTURE_COLORS[c]
        # loose containment ("head of caudate nucleus" vs "head of caudate")
        for known, color in FALLBACK_STRUCTURE_COLORS.items():
            if known in c or c in known:
                return color
    return "#9AA0A6"  # neutral gray for "unknown structure"


# ---------------------------------------------------------------------------
# Graph assembly
# ---------------------------------------------------------------------------

def _parents_from_ancestors_payload(payload: Dict, nhash_id: str) -> List[str]:
    data = payload.get("data") or {}
    node = data.get(nhash_id) or {}
    edges = node.get("edges") or {}
    return list(edges.get("has_parent") or [])


def build_graph(donor: str, jwt: str, cache_dir: Optional[Path]) -> Tuple[Dict[str, Dict], Dict[str, List[str]]]:
    """Fetch descendants of the donor, every raw record, and every parent edge.

    Returns (nodes, parents) where ``nodes[nhash] = record_dict`` and
    ``parents[nhash] = [parent_nhash, ...]``.

    NIMP's ``descendants`` endpoint does not populate ``has_parent`` edges,
    only the node list; ``get_ancestors`` does. We call ``get_ancestors``
    for each descendant to recover its immediate parents. All calls go
    through the on-disk cache.
    """
    print(f"Fetching descendants of {donor} ...")
    desc = fetch_descendants(donor, jwt, cache_dir)
    if "error" in desc:
        raise SystemExit(f"NIMP descendants error: {desc['error']}")

    nhash_ids = list((desc.get("data") or {}).keys())
    if donor not in nhash_ids:
        nhash_ids.insert(0, donor)

    nodes: Dict[str, Dict] = {}
    parents: Dict[str, List[str]] = {}
    for nhash in tqdm(nhash_ids, desc="Fetching NIMP records", unit="node"):
        try:
            data_payload = fetch_data(nhash, jwt, cache_dir)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] failed to fetch record for {nhash}: {exc}")
            continue
        node = data_payload.get("data")
        if node:
            nodes[nhash] = node

        # Parents: from get_ancestors(nhash)["data"][nhash]["edges"]["has_parent"].
        # Donor has no parents, so skip the call for it.
        if nhash == donor:
            parents[nhash] = []
            continue
        try:
            anc_payload = fetch_ancestors(nhash, jwt, cache_dir)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] failed to fetch ancestors for {nhash}: {exc}")
            parents[nhash] = []
            continue
        anc_data = (anc_payload.get("data") or {}).get(nhash) or {}
        edges = anc_data.get("edges") or {}
        parents[nhash] = list(edges.get("has_parent") or [])

    return nodes, parents


def upstream_closure(seed: Set[str], parents: Dict[str, List[str]]) -> Set[str]:
    """All ancestors (inclusive of the seeds themselves)."""
    keep: Set[str] = set()
    stack = list(seed)
    while stack:
        n = stack.pop()
        if n in keep:
            continue
        keep.add(n)
        stack.extend(parents.get(n, []))
    return keep


def build_children_map(parents: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """Invert parents: children[parent] = [child, child, ...]."""
    children: Dict[str, List[str]] = defaultdict(list)
    for child, ps in parents.items():
        for p in ps:
            children[p].append(child)
    return children


def downstream_closure(seed: Set[str], children: Dict[str, List[str]]) -> Set[str]:
    """All descendants (inclusive of the seeds themselves)."""
    keep: Set[str] = set()
    stack = list(seed)
    while stack:
        n = stack.pop()
        if n in keep:
            continue
        keep.add(n)
        stack.extend(children.get(n, []))
    return keep


def find_upstream_of_category(start: str, category: str,
                              nodes: Dict[str, Dict],
                              parents: Dict[str, List[str]]) -> List[str]:
    """BFS upstream from ``start``, collect nhashes whose category matches."""
    found: List[str] = []
    seen: Set[str] = set()
    stack = [start]
    while stack:
        n = stack.pop()
        if n in seen:
            continue
        seen.add(n)
        node = nodes.get(n) or {}
        if node.get("category") == category:
            found.append(n)
        stack.extend(parents.get(n, []))
    return found


# ---------------------------------------------------------------------------
# Filtering per task
# ---------------------------------------------------------------------------

def filter_libraries_by_bcs_tag(nodes: Dict[str, Dict],
                                parents: Dict[str, List[str]],
                                bcs_tag: str,
                                bcs_tag_field: str) -> List[str]:
    tagged_bcs = {
        n for n, node in nodes.items()
        if node.get("category") == "Barcoded Cell Sample"
        and _record_field_matches(node, bcs_tag_field, bcs_tag)
    }
    kept = []
    for n, node in nodes.items():
        if node.get("category") != "Library":
            continue
        upstream = upstream_closure({n}, parents)
        if upstream & tagged_bcs:
            kept.append(n)
    return kept


def filter_sections_by_tissue_structure(nodes: Dict[str, Dict],
                                        parents: Dict[str, List[str]],
                                        target_structures: List[str],
                                        tissue_structure_field: str,
                                        section_category: str = "Section") -> List[str]:
    targets_l = {s.lower().strip() for s in target_structures}

    def _tissue_matches(node: Dict) -> bool:
        tokens = _flatten_field_value((node.get("record") or {}).get(tissue_structure_field))
        return any(t.lower().strip() in targets_l for t in tokens)

    matching_tissues = {
        n for n, node in nodes.items()
        if node.get("category") == "Tissue" and _tissue_matches(node)
    }
    kept = []
    for n, node in nodes.items():
        if node.get("category") != section_category:
            continue
        upstream = upstream_closure({n}, parents)
        if upstream & matching_tissues:
            kept.append(n)
    return kept


def _flatten_field_value(value) -> List[str]:
    """Turn any NIMP field value into the list of comparable string tokens it
    represents.

    NIMP occasionally wraps a scalar as ``{"name": "...", "desc": "..."}`` (see
    the barcoded_cell_sample_tag_local_name field). We treat the ``name`` /
    ``value`` / ``id`` / ``local_name`` / ``label`` keys of such a dict as the
    real value, and recurse into lists.
    """
    tokens: List[str] = []
    if value is None:
        return tokens
    if isinstance(value, dict):
        for key in ("name", "value", "id", "local_name", "label"):
            if key in value:
                tokens.extend(_flatten_field_value(value[key]))
                return tokens
        # Fall back to the whole stringified dict.
        tokens.append(str(value))
        return tokens
    if isinstance(value, list):
        for item in value:
            tokens.extend(_flatten_field_value(item))
        return tokens
    tokens.append(str(value))
    return tokens


def _record_field_matches(node: Dict, field: Optional[str], target: str) -> bool:
    if not field:
        return False
    record = node.get("record") or {}
    value = record.get(field)
    target_l = target.lower().strip()
    return any(t.lower().strip() == target_l for t in _flatten_field_value(value))


def _record_field_value(node: Dict, field: Optional[str]) -> Optional[str]:
    if not field:
        return None
    record = node.get("record") or {}
    tokens = _flatten_field_value(record.get(field))
    if not tokens:
        return None
    return ", ".join(tokens)


def library_tissue_structure(library_nhash: str,
                             nodes: Dict[str, Dict],
                             parents: Dict[str, List[str]],
                             tissue_structure_field: str,
                             tissue_acronym_field: str) -> Tuple[Optional[str], Optional[str]]:
    """Return (structure, acronym) from the nearest upstream Tissue."""
    for t in find_upstream_of_category(library_nhash, "Tissue", nodes, parents):
        node = nodes[t]
        structure = _record_field_value(node, tissue_structure_field)
        acronym = _record_field_value(node, tissue_acronym_field)
        if structure or acronym:
            return structure, acronym
    return None, None


# ---------------------------------------------------------------------------
# Sankey rendering (Plotly)
# ---------------------------------------------------------------------------

def build_sankey(kept_nodes: Set[str],
                 nodes: Dict[str, Dict],
                 parents: Dict[str, List[str]],
                 library_colors: Dict[str, str],
                 section_color: str,
                 section_category: str,
                 kept_library_ancestors: Dict[str, Set[str]],
                 kept_section_ancestors: Dict[str, Set[str]],
                 kept_library_descendants: Optional[Dict[str, Set[str]]] = None,
                 ) -> Dict:
    """Build the Plotly Sankey ``data`` dict.

    Each node's color follows the same rule as its ribbons: nodes reachable
    from a kept library inherit that library's structure color; nodes reachable
    from a kept section get ``section_color``; a node visited by both gets a
    neutral blend.
    """
    # Node → color decision.
    lib_color_of: Dict[str, str] = {}
    sec_color_of: Dict[str, str] = {}
    for lib, ancestors in kept_library_ancestors.items():
        color = library_colors.get(lib, "#9AA0A6")
        for a in ancestors:
            lib_color_of.setdefault(a, color)
    if kept_library_descendants:
        for lib, descendants in kept_library_descendants.items():
            color = library_colors.get(lib, "#9AA0A6")
            for d in descendants:
                lib_color_of.setdefault(d, color)
    for sec, ancestors in kept_section_ancestors.items():
        for a in ancestors:
            sec_color_of.setdefault(a, section_color)

    def node_color(n: str) -> str:
        in_lib = n in lib_color_of
        in_sec = n in sec_color_of
        if in_lib and in_sec:
            return "#B39DDB"  # blended purple for the shared donor/slab spine
        if in_lib:
            return lib_color_of[n]
        if in_sec:
            return sec_color_of[n]
        return "#CFCFCF"

    stage_of = {cat: i for i, cat in enumerate(STAGE_ORDER)}

    # Per-column vertical ordering: library nodes first (sort key 0), section
    # nodes below (sort key 1) so the section track sits under the library
    # flow — "section comes after library" in reading order.
    def _lane(n: str) -> int:
        in_lib = n in lib_color_of
        in_sec = n in sec_color_of
        if in_lib and in_sec:
            return 0   # keep shared spine at the top with libraries
        return 1 if in_sec else 0

    ordered_nodes = sorted(
        kept_nodes,
        key=lambda n: (stage_of.get(nodes[n].get("category"), 99), _lane(n), n),
    )
    idx_of = {n: i for i, n in enumerate(ordered_nodes)}

    # Deterministic x per stage so column-header annotations can share the
    # same formula and land dead-center on each column.
    stages_used = sorted({stage_of.get(nodes[n].get("category"), 99) for n in ordered_nodes})
    stage_x: Dict[int, float] = {}
    if stages_used:
        n_stages = max(len(stages_used) - 1, 1)
        # Plotly clamps node x to (0, 1) exclusive; use a tiny inset.
        for i, s in enumerate(stages_used):
            stage_x[s] = 0.02 + (0.96 * i / n_stages)
    node_x = [stage_x.get(stage_of.get(nodes[n].get("category"), 99), 0.5)
              for n in ordered_nodes]

    # Column density: used later for legend sizing, and to compute an
    # explicit per-node y (see below).
    label_cap = int(_LABEL_CAP)
    col_counts_by_stage: Dict[int, int] = defaultdict(int)
    for n in ordered_nodes:
        col_counts_by_stage[stage_of.get(nodes[n].get("category"), 99)] += 1

    # Explicit y per node: fill each column top-to-bottom so a small column
    # (Donor=1) sits at the top while a big column (Section=53) spans the
    # full vertical range. Without this Plotly centers each column, which
    # leaves a big empty band above Donor and pushes Section past the
    # bottom of the plot area.
    col_seen: Dict[int, int] = defaultdict(int)
    node_y: List[float] = []
    for n in ordered_nodes:
        stage_idx = stage_of.get(nodes[n].get("category"), 99)
        total = col_counts_by_stage[stage_idx]
        pos = col_seen[stage_idx]
        col_seen[stage_idx] += 1
        # Offset by 0.5 so single-node columns sit at y=0.5 (center),
        # multi-node columns spread evenly across (near-)full height.
        node_y.append((pos + 0.5) / total if total > 0 else 0.5)

    def _short(label: str, limit: int = 22) -> str:
        return label if len(label) <= limit else label[: limit - 1] + "…"

    # All per-node labels are suppressed in the rendered chart per feedback;
    # column headers carry the category + count and full IDs stay in the
    # hover tooltip. label_cap is retained for the label-cap hint text.
    node_labels = []
    node_colors = []
    node_hover = []
    for n in ordered_nodes:
        node = nodes[n]
        category = node.get("category", "?")
        label = (node.get("record") or {}).get("name") or n
        node_labels.append("")
        node_colors.append(node_color(n))
        node_hover.append(f"<b>{label}</b><br>{category}<br>{n}")

    src, tgt, val, link_colors = [], [], [], []
    for child in ordered_nodes:
        for parent in parents.get(child, []):
            if parent not in idx_of:
                continue
            src.append(idx_of[parent])
            tgt.append(idx_of[child])
            val.append(1)
            # Ribbon color follows the *child* — reads downstream so kept
            # library branches carry their structure hue back up.
            link_colors.append(_rgba(node_color(child), 0.55))

    # Track the busiest column so the caller can size the figure to fit,
    # and remember the ordered list of stages present so the renderer can
    # add column headers.
    max_column = max(col_counts_by_stage.values()) if col_counts_by_stage else 1
    stages_present: List[Tuple[str, int]] = []
    for stage_idx in sorted(col_counts_by_stage.keys()):
        # Find the human-readable category name for this stage index.
        cat = next((c for c, i in stage_of.items() if i == stage_idx), None)
        if cat is None:
            continue
        stages_present.append((cat, col_counts_by_stage[stage_idx]))

    return {
        "node": {
            "label": node_labels,
            "color": node_colors,
            "customdata": node_hover,
            "hovertemplate": "%{customdata}<extra></extra>",
            "x": node_x,
            "y": node_y,
            "pad": 6,
            "thickness": 14,
            "line": {"color": "#3d3d3d", "width": 0.3},
        },
        "link": {
            "source": src,
            "target": tgt,
            "value": val,
            "color": link_colors,
        },
        # Sidecar for the renderer, popped before Plotly sees the dict.
        "_max_column": max_column,
        "_n_nodes": len(ordered_nodes),
        "_stages_present": stages_present,
        "_label_cap": label_cap,
        "_stage_x": stage_x,
    }


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


def render_sankey(sankey_data: Dict, donor: str, out_dir: Path, skip_png: bool,
                  legend_entries: Optional[List[Tuple[str, str]]] = None,
                  n_libs: int = 0, n_secs: int = 0) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        raise SystemExit(
            "plotly is required for rendering. Install with `pip install plotly` "
            "(and `pip install kaleido` if you want the static PNG)."
        )

    # Auto-size: ~18px per node in the tallest column, floored at 900, capped
    # at 6000 to keep the browser happy. Width scales with the number of stages.
    max_col = sankey_data.pop("_max_column", 20)
    n_nodes = sankey_data.pop("_n_nodes", 0)
    stages_present: List[Tuple[str, int]] = sankey_data.pop("_stages_present", [])
    label_cap = sankey_data.pop("_label_cap", _LABEL_CAP)
    stage_x_map: Dict[int, float] = sankey_data.pop("_stage_x", {})
    # 28px per node in the tallest column, plus generous top+bottom padding
    # (headers ~120, legend row ~140) so nothing gets clipped.
    height = max(1200, min(8000, 28 * max_col + 320))
    width = 2200

    # Bigger pad + smaller node font gives label text room to breathe.
    sankey_data["node"]["pad"] = 18
    sankey_data["node"]["thickness"] = 16

    fig = go.Figure(data=[go.Sankey(
        arrangement="fixed",
        textfont=dict(family="Inter, system-ui, sans-serif", size=10, color="#222"),
        **sankey_data,
    )])

    subtitle = (f"{n_libs} libraries | {n_secs} sections | "
                f"{n_nodes} lineage nodes")

    # Title / subtitle are placed via update_layout.title so they get their
    # own reserved band above the plot and never overlap column headers.
    annotations: List[dict] = []

    # Column headers with per-stage counts. Kept short so they don't crowd
    # the title band above.
    # Column headers use the exact same per-stage x we assigned to each node,
    # so they land dead-center on their column. Sankey node.x is in [0,1] of
    # the plot area; we map it into paper coordinates using the layout
    # margins (l=30, r=30, width=2200).
    stage_of = {cat: i for i, cat in enumerate(STAGE_ORDER)}
    plot_left = 30 / 2200
    plot_right = 1 - (30 / 2200)
    plot_span = plot_right - plot_left
    for cat, count in stages_present:
        sx = stage_x_map.get(stage_of.get(cat, 99))
        if sx is None:
            continue
        # sx is inset by 0.02 into the plot area; convert to paper x.
        x_paper = plot_left + sx * plot_span
        annotations.append(dict(
            text=f"<b>{cat}</b><br><span style='color:#777;font-size:10px'>"
                 f"n={count}</span>",
            x=x_paper, y=1.005, xref="paper", yref="paper",
            xanchor="center", yanchor="bottom", showarrow=False,
            font=dict(size=11, color="#333"),
        ))

    # Structure-color legend along the bottom in a horizontal row, so the
    # Sankey area sits directly under the header instead of sharing space
    # with a vertical left-side legend.
    legend_shapes: List[dict] = []
    if legend_entries:
        annotations.append(dict(
            text="<b>Library structure:</b>",
            x=0.005, y=-0.02, xref="paper", yref="paper",
            xanchor="left", yanchor="top", showarrow=False,
            font=dict(size=12, color="#333"),
        ))
        # Layout as: [swatch] label   [swatch] label ...  wrapped every 6.
        # Swatches are drawn as native SVG <rect> via Plotly shapes rather
        # than using the U+25A0 glyph, so an email preview that mis-decodes
        # UTF-8 as Latin-1 still renders them correctly (the ■ character
        # was becoming 'â–' in some clients). Labels stay in plain black
        # and are lowercased for uniform casing.
        entries_per_row = 6
        for i, (label, color) in enumerate(legend_entries):
            row = i // entries_per_row
            col = i % entries_per_row
            x_swatch = 0.08 + col * 0.15
            y_top = -0.023 - row * 0.02
            swatch_w = 0.012
            swatch_h = 0.018
            legend_shapes.append(dict(
                type="rect",
                xref="paper", yref="paper",
                x0=x_swatch, x1=x_swatch + swatch_w,
                y0=y_top - swatch_h, y1=y_top,
                fillcolor=color,
                line=dict(color=color, width=0),
            ))
            annotations.append(dict(
                text=f"<span style='color:#111'>{label}</span>",
                x=x_swatch + swatch_w + 0.006,
                y=y_top - swatch_h / 2,
                xref="paper", yref="paper",
                xanchor="left", yanchor="middle", showarrow=False,
                font=dict(size=11),
            ))

    fig.update_layout(
        title=dict(
            text=(f"<b>Macaque atlas lineage - {donor}</b>"
                  f"<br><span style='font-size:12px;color:#555'>{subtitle}</span>"),
            x=0.005, xanchor="left",
            y=0.985, yanchor="top",
            font=dict(family="Inter, system-ui, sans-serif", size=18, color="#111"),
        ),
        annotations=annotations,
        shapes=legend_shapes,
        font=dict(family="Inter, system-ui, sans-serif", size=11),
        paper_bgcolor="white",
        plot_bgcolor="white",
        # Diagram sits directly under the header; legend lives in the
        # reserved bottom margin.
        margin=dict(l=30, r=30, t=120, b=140),
        height=height,
        width=width,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{donor}_lineage.html"
    fig.write_html(str(html_path), include_plotlyjs="cdn")
    print(f"Wrote {html_path}  ({width}x{height})")

    # Static outputs: SVG (vector — always emit) and optionally PNG.
    try:
        svg_path = out_dir / f"{donor}_lineage.svg"
        fig.write_image(str(svg_path), format="svg")
        print(f"Wrote {svg_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] could not write SVG (install `kaleido`): {exc}")

    if skip_png:
        return
    try:
        png_path = out_dir / f"{donor}_lineage.png"
        fig.write_image(str(png_path), scale=2)
        print(f"Wrote {png_path}")
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] could not write PNG (install `kaleido`): {exc}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main(argv: Optional[List[str]] = None) -> None:
    global _OFFLINE, _LABEL_CAP
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--donor", default=DEFAULT_DONOR)
    p.add_argument("--bcs-tag", default=DEFAULT_BCS_TAG)
    p.add_argument("--section-structure", default=DEFAULT_SECTION_STRUCTURE)
    p.add_argument("--section-structure-in",
                   help="Comma-separated list of tissue structures; a section is "
                        "kept if any upstream tissue's structure is in this set. "
                        "Overrides --section-structure when set. Useful when "
                        "'basal nuclei (basal ganglia)' isn't literally on any "
                        "tissue but its substructures are.")
    p.add_argument("--section-preset", choices=sorted(SECTION_STRUCTURE_PRESETS.keys()),
                   help=("Named substructure set; equivalent to a canned "
                         "--section-structure-in. Currently: basal-nuclei "
                         "(caudate parts, putamen, globus pallidus segments, "
                         "septal nuclei, nucleus accumbens)."))
    p.add_argument("--section-category", default="Section",
                   help="NIMP category name for Sections (default: 'Section')")
    p.add_argument("--bcs-tag-field", default=DEFAULT_BCS_TAG_FIELD,
                   help=("NIMP record field on Barcoded Cell Sample holding the "
                         "tag (default: barcoded_cell_sample_tag_local_name)."))
    p.add_argument("--tissue-structure-field", default=DEFAULT_TISSUE_STRUCTURE_FIELD,
                   help="NIMP record field on Tissue for structure (default: structure).")
    p.add_argument("--tissue-acronym-field", default=DEFAULT_TISSUE_ACRONYM_FIELD,
                   help="NIMP record field on Tissue for structure acronym "
                        "(default: tissue_structure_acronym).")
    p.add_argument("--out-dir", type=Path, default=Path("./out"))
    p.add_argument("--cache-dir", type=Path, default=Path("./_nimp_cache"),
                   help="Cache NIMP responses on disk to speed up reruns "
                        "(default: ./_nimp_cache).")
    p.add_argument("--no-cache", action="store_true",
                   help="Disable disk cache; always hit NIMP.")
    p.add_argument("--offline", action="store_true",
                   help="Serve everything from --cache-dir; error on any cache "
                        "miss instead of calling NIMP. Assumes a prior online run "
                        "populated the cache.")
    p.add_argument("--skip-png", action="store_true")
    p.add_argument("--label-cap", type=int, default=_LABEL_CAP,
                   help="In columns with more than this many nodes, per-node "
                        f"labels are suppressed and the full ID stays on hover "
                        f"(default: {_LABEL_CAP}). Set to a big number to force "
                        "labels on every node.")
    args = p.parse_args(argv)

    jwt = os.environ.get("jwt_token")
    if not jwt and not args.offline:
        raise SystemExit("Set the `jwt_token` env var to your NIMP Personal API Token, "
                         "or pass --offline to work from --cache-dir only.")
    if args.offline and args.no_cache:
        raise SystemExit("--offline is incompatible with --no-cache.")

    _OFFLINE = args.offline
    _LABEL_CAP = args.label_cap
    cache_dir = None if args.no_cache else args.cache_dir
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)
        existing = sum(1 for _ in cache_dir.glob("*.json"))
        print(f"NIMP cache dir: {cache_dir}  ({existing} entries on disk, "
              f"offline={args.offline})")

    nodes, parents = build_graph(args.donor, jwt or "", cache_dir)
    print(f"Fetched {len(nodes)} records under {args.donor}  "
          f"(cache hit={_CACHE_STATS['hit']}, miss={_CACHE_STATS['miss']})")

    # Report categories we saw — makes it easy to spot 'Section' etc.
    cats = defaultdict(int)
    for n in nodes.values():
        cats[n.get("category", "?")] += 1
    print("Category counts:")
    for c, n in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"  {c:30s} {n}")

    discovered = discover_fields(nodes, args.bcs_tag, args.section_structure)

    # Resolve each field: CLI/default first, auto-discovery only fills in when
    # the CLI-selected field is genuinely absent from every record.
    def _pick(cli_value: str, discovered_key: str, sample_category: str) -> str:
        cli_hit = any(
            cli_value in ((n.get("record") or {}).keys())
            for n in nodes.values()
            if n.get("category") == sample_category
        )
        if cli_hit:
            return cli_value
        fallback = discovered.get(discovered_key)
        if fallback:
            print(f"[info] '{cli_value}' not present on any {sample_category} record; "
                  f"auto-discovery falling back to '{fallback}'.")
            return fallback
        return cli_value

    bcs_tag_field = _pick(args.bcs_tag_field, "bcs_tag_field", "Barcoded Cell Sample")
    tissue_structure_field = _pick(args.tissue_structure_field, "tissue_structure_field", "Tissue")
    tissue_acronym_field = _pick(args.tissue_acronym_field, "tissue_acronym_field", "Tissue")

    print("Using NIMP fields:")
    print(f"  bcs_tag_field            -> {bcs_tag_field}")
    print(f"  tissue_structure_field   -> {tissue_structure_field}")
    print(f"  tissue_acronym_field     -> {tissue_acronym_field}")
    if discovered:
        print("Auto-discovery report (value-matched):")
        for k, v in discovered.items():
            print(f"  {k:28s} -> {v}")

    kept_libs = filter_libraries_by_bcs_tag(
        nodes, parents, args.bcs_tag, bcs_tag_field)

    if args.section_structure_in:
        section_targets = [s.strip() for s in args.section_structure_in.split(",") if s.strip()]
        print(f"[info] section filter set to structure IN {section_targets}")
    elif args.section_preset:
        section_targets = list(SECTION_STRUCTURE_PRESETS[args.section_preset])
        print(f"[info] section filter using preset {args.section_preset!r}: "
              f"{section_targets}")
    elif args.section_structure != DEFAULT_SECTION_STRUCTURE:
        # User explicitly asked for a single structure other than the default
        # (which doesn't exist on any record — see below).
        section_targets = [args.section_structure]
    else:
        # The task's literal 'basal nuclei (basal ganglia)' isn't on any
        # Tissue record; fall back to the basal-nuclei substructure preset
        # so a plain `python scripts/macaque_atlas_diagram.py` gets sections
        # for this donor instead of silently returning zero. Override with
        # --section-structure / --section-structure-in / --section-preset.
        section_targets = list(SECTION_STRUCTURE_PRESETS["basal-nuclei"])
        print(f"[info] no section flag given; defaulting to preset 'basal-nuclei' "
              f"since the literal {DEFAULT_SECTION_STRUCTURE!r} isn't on any "
              f"Tissue record. Override with --section-structure=<value>, "
              f"--section-structure-in=<comma list>, or --section-preset.")
    kept_secs = filter_sections_by_tissue_structure(
        nodes, parents, section_targets,
        tissue_structure_field, args.section_category)

    # Section-side diagnostics.
    total_sections = sum(1 for n in nodes.values()
                         if n.get("category") == args.section_category)
    targets_l = {s.lower().strip() for s in section_targets}
    matching_tissues = [
        n for n, node in nodes.items()
        if node.get("category") == "Tissue"
        and any(
            t.lower().strip() in targets_l
            for t in _flatten_field_value((node.get("record") or {}).get(tissue_structure_field))
        )
    ]
    print(f"Section-side filter: category={args.section_category!r}, "
          f"structures={section_targets} -> "
          f"{total_sections} total sections, "
          f"{len(matching_tissues)} matching tissues, "
          f"kept {len(kept_secs)} sections")
    if total_sections == 0:
        cats = sorted({n.get("category", "?") for n in nodes.values()})
        print(f"[warn] no records matched --section-category={args.section_category!r}. "
              f"Categories seen: {cats}. Override with --section-category=<name>.")
    elif matching_tissues == []:
        target_l = args.section_structure.lower().strip()
        hits: Dict[Tuple[str, str], int] = defaultdict(int)
        for node in nodes.values():
            record = node.get("record") or {}
            category = node.get("category", "?")
            for field, tokens in ((k, _flatten_field_value(v)) for k, v in record.items()):
                for t in tokens:
                    if t.lower().strip() == target_l:
                        hits[(category, field)] += 1
        if hits:
            print(f"[hint] value {args.section_structure!r} was found elsewhere:")
            for (category, field), count in sorted(hits.items(), key=lambda kv: -kv[1]):
                print(f"  n={count:4d}  {category} . {field}")
            print("       -> re-run with --section-category and/or "
                  "--tissue-structure-field pointing at the (category, field) "
                  "above.")
        else:
            print(f"[hint] value {args.section_structure!r} was not found on ANY "
                  "record. The task's phrase may be idiomatic for the "
                  "basal-nuclei substructures. Try re-running with e.g. "
                  "--section-structure=putamen (repeat per structure) or ask "
                  "for --section-structure-in=<comma list>.")

    if not kept_secs and total_sections > 0:
        struct_counts: Dict[str, int] = defaultdict(int)
        for n, node in nodes.items():
            if node.get("category") != args.section_category:
                continue
            for a in upstream_closure({n}, parents):
                anode = nodes.get(a) or {}
                if anode.get("category") != "Tissue":
                    continue
                for token in _flatten_field_value((anode.get("record") or {}).get(tissue_structure_field)):
                    struct_counts[token] += 1
        print(f"[warn] no sections kept. Distinct upstream-tissue structures "
              f"seen on field {tissue_structure_field!r}:")
        for value, count in sorted(struct_counts.items(), key=lambda kv: -kv[1])[:40]:
            print(f"  n={count:4d}  {value!r}")
        if not struct_counts:
            print("  (none — Sections have no upstream Tissue, or the "
                  "--tissue-structure-field is empty on those tissues)")

    if not kept_libs:
        seen = summarize_bcs_tag_values(nodes, bcs_tag_field)
        print(f"\n[warn] no libraries matched --bcs-tag={args.bcs_tag!r} on field "
              f"{bcs_tag_field!r}. Distinct tag values on BCS records:")
        for value, count in sorted(seen.items(), key=lambda kv: -kv[1])[:40]:
            print(f"  n={count:4d}  {value!r}")
        if not seen:
            print("  (none — try --bcs-tag-field to point at a different NIMP field)")

    print(f"Kept {len(kept_libs)} libraries and {len(kept_secs)} sections")
    if not kept_libs and not kept_secs:
        raise SystemExit("Nothing to draw. Check --bcs-tag and --section-structure.")

    homba = fetch_homba_colors()
    print(f"HOMBA palette entries: {len(homba)}")

    library_colors: Dict[str, str] = {}
    library_summary = defaultdict(list)  # structure -> [lib nhash, ...]
    for lib in kept_libs:
        structure, acronym = library_tissue_structure(
            lib, nodes, parents,
            tissue_structure_field,
            tissue_acronym_field,
        )
        color = resolve_structure_color(structure, acronym, homba)
        library_colors[lib] = color
        key = structure or acronym or "unknown"
        library_summary[key].append(lib)
    print("Library structure summary:")
    for k, libs in sorted(library_summary.items(), key=lambda kv: -len(kv[1])):
        print(f"  {k:40s} n={len(libs)}  color={library_colors[libs[0]]}")

    section_color = "#4C6EF5"  # single color per task

    children = build_children_map(parents)

    # Libraries: upstream chain to Donor + downstream to Library Aliquot.
    # Sections: upstream chain only (nothing biologically downstream of a
    # Section in this schema). Library Pool is intentionally excluded per
    # spec — the diagram ends at Library Aliquot.
    kept_library_ancestors = {lib: upstream_closure({lib}, parents) for lib in kept_libs}
    kept_library_descendants = {lib: downstream_closure({lib}, children) for lib in kept_libs}
    kept_section_ancestors = {sec: upstream_closure({sec}, parents) for sec in kept_secs}

    excluded_cats = {"Library Pool"}
    kept_nodes: Set[str] = set()
    for s in kept_library_ancestors.values():
        kept_nodes |= {n for n in s if (nodes.get(n) or {}).get("category") not in excluded_cats}
    for s in kept_library_descendants.values():
        kept_nodes |= {n for n in s if (nodes.get(n) or {}).get("category") not in excluded_cats}
    for s in kept_section_ancestors.values():
        kept_nodes |= {n for n in s if (nodes.get(n) or {}).get("category") not in excluded_cats}
    # Trim the per-library descendant sets too so build_sankey doesn't try
    # to color a Library Pool node we've already dropped from kept_nodes.
    for lib, desc in kept_library_descendants.items():
        kept_library_descendants[lib] = {
            n for n in desc if (nodes.get(n) or {}).get("category") not in excluded_cats
        }

    # Report downstream reach so we can see whether we hit Library Aliquot.
    downstream_cat_counts: Dict[str, int] = defaultdict(int)
    for s in kept_library_descendants.values():
        for n in s:
            downstream_cat_counts[(nodes.get(n) or {}).get("category", "?")] += 1
    print("Downstream of kept libraries:")
    for cat in ("Library", "Library Aliquot"):
        print(f"  {cat:20s} {downstream_cat_counts.get(cat, 0)}")

    sankey = build_sankey(
        kept_nodes, nodes, parents,
        library_colors=library_colors,
        section_color=section_color,
        section_category=args.section_category,
        kept_library_ancestors=kept_library_ancestors,
        kept_section_ancestors=kept_section_ancestors,
        kept_library_descendants=kept_library_descendants,
    )
    # Build legend from what actually got rendered — one entry per distinct
    # structure that colored at least one library, plus the sections entry.
    legend_seen = {}
    for lib in kept_libs:
        c = library_colors.get(lib, "#9AA0A6")
        structure, _ = library_tissue_structure(
            lib, nodes, parents, tissue_structure_field, tissue_acronym_field)
        key = structure or "unknown structure"
        legend_seen.setdefault(key, c)
    if kept_secs:
        legend_seen["Basal Nuclei"] = section_color
    legend_entries = sorted(legend_seen.items(), key=lambda kv: kv[0])

    render_sankey(sankey, args.donor, args.out_dir, args.skip_png,
                  legend_entries=legend_entries,
                  n_libs=len(kept_libs), n_secs=len(kept_secs))


if __name__ == "__main__":
    main()
