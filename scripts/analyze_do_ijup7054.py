#!/usr/bin/env python
"""Clean-slate analysis for donor DO-IJUP7054.

Steps:
1. Fetch every descendant of DO-IJUP7054 from NIMP (records + parent edges),
   caching each API response on disk so reruns are instant.
2. Filter Barcoded Cell Sample records whose
   ``barcoded_cell_sample_tag_local_name`` list contains any dict with
   ``name == 'HMBA_Macaque_Atlas_BN_BF'``.
3. For each filtered BCS walk upstream, collect every Tissue ancestor, and
   print the count of distinct Tissues.

Run:
    export jwt_token=<NIMP PAT>
    python scripts/analyze_do_ijup7054.py
"""

from __future__ import annotations

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Set

from tqdm import tqdm

from bkbit.utils.nimp_api_endpoints import get_ancestors, get_data, get_descendants


DONOR = "DO-IJUP7054"
TARGET_TAG = "HMBA_Macaque_Atlas_BN_BF"
CACHE_DIR = Path("./_nimp_cache")


# --- disk cache ----------------------------------------------------------

def _cache_path(kind: str, key: str) -> Path:
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", key)
    return CACHE_DIR / f"{kind}_{safe}.json"


def _cached(kind: str, key: str, fetch):
    p = _cache_path(kind, key)
    if p.exists():
        return json.loads(p.read_text())
    payload = fetch()
    p.write_text(json.dumps(payload))
    return payload


# --- step 1: fetch descendants + records + parent edges ------------------

def fetch_graph(jwt: str):
    print(f"Fetching descendants of {DONOR} ...")
    desc = _cached("descendants", DONOR,
                   lambda: get_descendants(DONOR, jwt, nhash_only=True))
    if "error" in desc:
        raise SystemExit(f"NIMP descendants error: {desc['error']}")

    nhash_ids = list((desc.get("data") or {}).keys())
    if DONOR not in nhash_ids:
        nhash_ids.insert(0, DONOR)

    nodes: Dict[str, Dict] = {}
    parents: Dict[str, List[str]] = {}
    for nh in tqdm(nhash_ids, desc="records + parents", unit="node"):
        data_payload = _cached("data", nh, lambda: get_data(nh, jwt))
        node = data_payload.get("data") or {}
        if node:
            nodes[nh] = node

        if nh == DONOR:
            parents[nh] = []
            continue
        anc_payload = _cached("ancestors", nh,
                              lambda: get_ancestors(nh, jwt, nhash_only=True))
        anc_data = (anc_payload.get("data") or {}).get(nh) or {}
        parents[nh] = list((anc_data.get("edges") or {}).get("has_parent") or [])
    return nodes, parents


# --- step 2: filter BCS by tag -------------------------------------------

def bcs_matches_tag(node: Dict, target_name: str) -> bool:
    """barcoded_cell_sample_tag_local_name is a list of {name, desc} dicts.
    Return True if any element's 'name' == target_name."""
    if node.get("category") != "Barcoded Cell Sample":
        return False
    record = node.get("record") or {}
    tags = record.get("barcoded_cell_sample_tag_local_name")
    if tags is None:
        return False
    # NIMP has been observed returning both a bare dict and a list of dicts;
    # normalise to a list.
    if isinstance(tags, dict):
        tags = [tags]
    if not isinstance(tags, list):
        return False
    for entry in tags:
        if isinstance(entry, dict) and entry.get("name") == target_name:
            return True
    return False


def filter_bcs(nodes: Dict[str, Dict]) -> List[str]:
    return [n for n, node in nodes.items() if bcs_matches_tag(node, TARGET_TAG)]


# --- step 3: upstream Tissue ancestors -----------------------------------

def upstream_closure(seeds, parents):
    keep: Set[str] = set()
    stack = list(seeds)
    while stack:
        n = stack.pop()
        if n in keep:
            continue
        keep.add(n)
        stack.extend(parents.get(n, []))
    return keep


def tissue_ancestors(bcs_ids: List[str], nodes: Dict[str, Dict],
                     parents: Dict[str, List[str]]) -> Set[str]:
    ancestors = upstream_closure(bcs_ids, parents)
    return {a for a in ancestors
            if (nodes.get(a) or {}).get("category") == "Tissue"}


# --- main ----------------------------------------------------------------

def main() -> None:
    jwt = os.environ.get("jwt_token")
    if not jwt:
        raise SystemExit("Set the `jwt_token` env var to your NIMP PAT.")

    nodes, parents = fetch_graph(jwt)

    # Sanity report on what we pulled.
    cats = defaultdict(int)
    for n in nodes.values():
        cats[n.get("category", "?")] += 1
    print(f"\nTotal records: {len(nodes)}")
    print("Category counts:")
    for c, n in sorted(cats.items(), key=lambda kv: -kv[1]):
        print(f"  {c:32s} {n}")

    # Step 2
    matching = filter_bcs(nodes)
    total_bcs = cats.get("Barcoded Cell Sample", 0)
    print(f"\nBarcoded Cell Samples with tag name == {TARGET_TAG!r}: "
          f"{len(matching)} / {total_bcs}")

    # Step 3
    tissues = tissue_ancestors(matching, nodes, parents)
    print(f"Distinct Tissue ancestors of those BCS: {len(tissues)}")

    # A little more detail so you can spot-check.
    print("\nSample matching BCS (first 5):")
    for n in matching[:5]:
        rec = (nodes[n].get("record") or {})
        tags = rec.get("barcoded_cell_sample_tag_local_name")
        print(f"  {n}  tags={tags!r}")
    print("\nSample upstream Tissue structures (first 10):")
    for t in list(tissues)[:10]:
        rec = (nodes[t].get("record") or {})
        print(f"  {t}  structure={rec.get('structure')!r}  "
              f"acronym={rec.get('tissue_structure_acronym')!r}")


if __name__ == "__main__":
    main()
