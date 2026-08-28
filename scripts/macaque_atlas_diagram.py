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

# The pipeline stage order we lay out left→right on the Sankey. Every
# category the NIMP graph might carry is listed here so unknown categories
# (like "Section") can slot in without a schema change.
STAGE_ORDER = [
    "Donor",
    "Slab",
    "Section",              # inferred category, see --section-structure
    "Tissue",
    "Specimen Dissected ROI",
    "Dissociated Cell Sample",
    "Enriched Cell Sample",
    "Barcoded Cell Sample",
    "Amplified cDNA",
    "Library",
    "Library Aliquot",
    "Library Pool",
]

HOMBA_URL = "https://alleninstitute.github.io/CCF-MAP/docs/HOMBA_ontology_v1.html"


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
    """Best-effort scrape of anatomy → hex color from the HOMBA ontology page.

    Returns a dict keyed by lowercase structure name and acronym. Empty on
    failure; callers should fall back to ``FALLBACK_STRUCTURE_COLORS``.
    """
    try:
        resp = requests.get(HOMBA_URL, timeout=15)
        resp.raise_for_status()
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] could not fetch HOMBA ontology page: {exc}")
        return {}

    html = resp.text
    palette: Dict[str, str] = {}

    # Try BeautifulSoup for a cleaner row walk if it's available.
    try:
        from bs4 import BeautifulSoup  # type: ignore

        soup = BeautifulSoup(html, "html.parser")
        for row in soup.find_all("tr"):
            cells = row.find_all(["td", "th"])
            hex_color: Optional[str] = None
            texts: List[str] = []
            for cell in cells:
                style = cell.get("style", "") or ""
                m = re.search(r"background(?:-color)?:\s*#([0-9A-Fa-f]{6})", style)
                if m:
                    hex_color = "#" + m.group(1).upper()
                # Also handle plain-text hex codes in a cell.
                cell_text = cell.get_text(" ", strip=True)
                if hex_color is None:
                    m2 = re.match(r"^#[0-9A-Fa-f]{6}$", cell_text)
                    if m2:
                        hex_color = cell_text.upper()
                if cell_text:
                    texts.append(cell_text)
            if hex_color and texts:
                for label in texts:
                    key = label.lower().strip()
                    if key and not key.startswith("#"):
                        palette.setdefault(key, hex_color)
    except ImportError:
        # Fall back to a coarse regex over <tr>...</tr> blocks.
        for row in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.DOTALL | re.IGNORECASE):
            m = re.search(r"background(?:-color)?:\s*#([0-9A-Fa-f]{6})", row)
            if not m:
                continue
            hex_color = "#" + m.group(1).upper()
            for td in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row, flags=re.DOTALL | re.IGNORECASE):
                text = re.sub(r"<[^>]+>", " ", td)
                text = re.sub(r"\s+", " ", text).strip().lower()
                if text and not text.startswith("#"):
                    palette.setdefault(text, hex_color)

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
    """Fetch descendants of the donor and every raw record.

    Returns (nodes, parents) where ``nodes[nhash] = record_dict`` and
    ``parents[nhash] = [parent_nhash, ...]``.
    """
    print(f"Fetching descendants of {donor} ...")
    desc = fetch_descendants(donor, jwt, cache_dir)
    if "error" in desc:
        raise SystemExit(f"NIMP descendants error: {desc['error']}")

    # descendants payload gives us has_parent edges directly for every node
    # in the payload. Save an ancestors round-trip per node.
    parents: Dict[str, List[str]] = {}
    for nhash, info in (desc.get("data") or {}).items():
        parents[nhash] = list(((info or {}).get("edges") or {}).get("has_parent") or [])

    # Always include the donor itself.
    nhash_ids = list(parents.keys())
    if donor not in parents:
        parents[donor] = []
        nhash_ids.insert(0, donor)

    nodes: Dict[str, Dict] = {}
    for nhash in tqdm(nhash_ids, desc="Fetching NIMP records", unit="node"):
        try:
            payload = fetch_data(nhash, jwt, cache_dir)
        except Exception as exc:  # noqa: BLE001
            print(f"[warn] failed to fetch {nhash}: {exc}")
            continue
        node = payload.get("data")
        if node:
            nodes[nhash] = node
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
                                        target_structure: str,
                                        tissue_structure_field: str,
                                        section_category: str = "Section") -> List[str]:
    matching_tissues = {
        n for n, node in nodes.items()
        if node.get("category") == "Tissue"
        and _record_field_matches(node, tissue_structure_field, target_structure)
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
                 kept_section_ancestors: Dict[str, Set[str]]) -> Dict:
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
    ordered_nodes = sorted(
        kept_nodes,
        key=lambda n: (stage_of.get(nodes[n].get("category"), 99), n),
    )
    idx_of = {n: i for i, n in enumerate(ordered_nodes)}

    node_labels = []
    node_colors = []
    node_hover = []
    for n in ordered_nodes:
        node = nodes[n]
        category = node.get("category", "?")
        label = (node.get("record") or {}).get("name") or n
        node_labels.append(f"{label}")
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

    return {
        "node": {
            "label": node_labels,
            "color": node_colors,
            "customdata": node_hover,
            "hovertemplate": "%{customdata}<extra></extra>",
            "pad": 12,
            "thickness": 16,
            "line": {"color": "#3d3d3d", "width": 0.3},
        },
        "link": {
            "source": src,
            "target": tgt,
            "value": val,
            "color": link_colors,
        },
    }


def _rgba(hex_color: str, alpha: float) -> str:
    h = hex_color.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha:.2f})"


def render_sankey(sankey_data: Dict, donor: str, out_dir: Path, skip_png: bool) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError:
        raise SystemExit(
            "plotly is required for rendering. Install with `pip install plotly` "
            "(and `pip install kaleido` if you want the static PNG)."
        )

    fig = go.Figure(data=[go.Sankey(**sankey_data)])
    fig.update_layout(
        title=dict(
            text=f"Macaque atlas lineage · {donor}",
            x=0.02, xanchor="left", font=dict(size=18),
        ),
        font=dict(family="Inter, system-ui, sans-serif", size=11),
        paper_bgcolor="white",
        plot_bgcolor="white",
        margin=dict(l=20, r=20, t=60, b=20),
        height=900,
        width=1600,
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    html_path = out_dir / f"{donor}_lineage.html"
    fig.write_html(str(html_path), include_plotlyjs="cdn")
    print(f"Wrote {html_path}")

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
    p = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    p.add_argument("--donor", default=DEFAULT_DONOR)
    p.add_argument("--bcs-tag", default=DEFAULT_BCS_TAG)
    p.add_argument("--section-structure", default=DEFAULT_SECTION_STRUCTURE)
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
    args = p.parse_args(argv)

    jwt = os.environ.get("jwt_token")
    if not jwt and not args.offline:
        raise SystemExit("Set the `jwt_token` env var to your NIMP Personal API Token, "
                         "or pass --offline to work from --cache-dir only.")
    if args.offline and args.no_cache:
        raise SystemExit("--offline is incompatible with --no-cache.")

    global _OFFLINE
    _OFFLINE = args.offline
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
    kept_secs = filter_sections_by_tissue_structure(
        nodes, parents, args.section_structure,
        tissue_structure_field, args.section_category)

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

    kept_library_ancestors = {lib: upstream_closure({lib}, parents) for lib in kept_libs}
    kept_section_ancestors = {sec: upstream_closure({sec}, parents) for sec in kept_secs}
    kept_nodes: Set[str] = set()
    for s in kept_library_ancestors.values():
        kept_nodes |= s
    for s in kept_section_ancestors.values():
        kept_nodes |= s

    sankey = build_sankey(
        kept_nodes, nodes, parents,
        library_colors=library_colors,
        section_color=section_color,
        section_category=args.section_category,
        kept_library_ancestors=kept_library_ancestors,
        kept_section_ancestors=kept_section_ancestors,
    )
    render_sankey(sankey, args.donor, args.out_dir, args.skip_png)


if __name__ == "__main__":
    main()
