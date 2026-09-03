#!/usr/bin/env python
"""Cross-check section->tissue mappings between the manager's spreadsheet
and what NIMP returns.

For each row in the spreadsheet:

1. Read the ``Section NHash ID`` and ``Tissue NHash ID`` columns.
2. Query NIMP for that section's ancestors and extract every ancestor whose
   category is ``Tissue``.
3. Compare the spreadsheet's Tissue NHash to the NIMP-derived set:

   - ``match``            spreadsheet's tissue is exactly the (only) tissue
                          NIMP returned upstream of the section.
   - ``mismatch``         both sides name a tissue but they differ.
   - ``multiple``         NIMP returned more than one Tissue ancestor and the
                          spreadsheet's tissue is one of them.
   - ``missing_in_nimp``  NIMP returned no Tissue ancestors.
   - ``missing_in_sheet`` spreadsheet's Tissue NHash cell was blank.

Writes ``out/section_vs_tissue.csv`` with the per-section detail plus prints
a summary breakdown to stdout.

Run:
    export jwt_token=<PAT>
    python scripts/compare_section_tissue.py path/to/sheet.csv

Optional flags::

    --out PATH          override the output CSV path
    --cache-dir DIR     directory for NIMP response cache (default: ./_nimp_cache)
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Set

from tqdm import tqdm

from bkbit.utils.nimp_api_endpoints import get_ancestors, get_data


# ---- on-disk NIMP cache (same layout the other scripts use) --------------

def _cache_path(cache_dir: Path, kind: str, key: str) -> Path:
    cache_dir.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r"[^A-Za-z0-9_.-]+", "_", key)
    return cache_dir / f"{kind}_{safe}.json"


def _cached(cache_dir: Path, kind: str, key: str, fetch):
    p = _cache_path(cache_dir, kind, key)
    if p.exists():
        return json.loads(p.read_text())
    payload = fetch()
    p.write_text(json.dumps(payload))
    return payload


# ---- CSV helpers ---------------------------------------------------------

def _match_header(fieldnames, want: str) -> Optional[str]:
    for h in (fieldnames or []):
        if h.strip().lower() == want.strip().lower():
            return h
    return None


def read_sheet(path: Path):
    """Yield (section_nhash, tissue_nhash) per row, skipping blank sections."""
    with open(path, newline="") as f:
        reader = csv.DictReader(f)
        sec_col = _match_header(reader.fieldnames, "Section NHash ID")
        tis_col = _match_header(reader.fieldnames, "Tissue NHash ID")
        if sec_col is None:
            raise SystemExit(f"No 'Section NHash ID' column in {path}")
        if tis_col is None:
            print(f"[warn] no 'Tissue NHash ID' column in {path}; every row "
                  f"will report as missing_in_sheet.")
        for row in reader:
            sec = (row.get(sec_col) or "").strip()
            if not sec:
                continue
            tis = (row.get(tis_col) or "").strip() if tis_col else ""
            yield sec, tis


# ---- NIMP: tissue ancestors of a section ---------------------------------

def nimp_tissue_ancestors(section_id: str, jwt: str, cache_dir: Path,
                          category_cache: Dict[str, Optional[str]]) -> List[str]:
    """Return the list of NHash IDs among ``section_id``'s ancestors whose
    category is Tissue. category_cache memoises get_data() calls."""
    try:
        anc = _cached(cache_dir, "ancestors", section_id,
                      lambda: get_ancestors(section_id, jwt, nhash_only=True))
    except Exception as exc:  # noqa: BLE001
        print(f"[warn] get_ancestors failed for {section_id}: {exc}")
        return []

    ancestors = list((anc.get("data") or {}).keys())
    tissues: List[str] = []
    for a in ancestors:
        cat = category_cache.get(a)
        if cat is None and a not in category_cache:
            try:
                dp = _cached(cache_dir, "data", a,
                             lambda a=a: get_data(a, jwt))
                cat = ((dp.get("data") or {}).get("category"))
            except Exception as exc:  # noqa: BLE001
                print(f"[warn] get_data failed for {a}: {exc}")
                cat = None
            category_cache[a] = cat
        if cat == "Tissue":
            tissues.append(a)
    return tissues


# ---- comparison ----------------------------------------------------------

def classify(sheet_tissue: str, nimp_tissues: List[str]) -> str:
    if not sheet_tissue and not nimp_tissues:
        return "both_blank"
    if not sheet_tissue:
        return "missing_in_sheet"
    if not nimp_tissues:
        return "missing_in_nimp"
    if len(nimp_tissues) == 1:
        return "match" if nimp_tissues[0] == sheet_tissue else "mismatch"
    return "multiple" if sheet_tissue in nimp_tissues else "mismatch"


# ---- main ---------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n", 1)[0])
    ap.add_argument("sheet", type=Path, help="Path to the manager's CSV")
    ap.add_argument("--out", type=Path, default=Path("out/section_vs_tissue.csv"))
    ap.add_argument("--cache-dir", type=Path, default=Path("./_nimp_cache"))
    args = ap.parse_args()

    jwt = os.environ.get("jwt_token")
    if not jwt:
        raise SystemExit("Set the `jwt_token` env var to your NIMP PAT.")

    rows = list(read_sheet(args.sheet))
    print(f"Read {len(rows)} section rows from {args.sheet}")

    category_cache: Dict[str, Optional[str]] = {}
    verdicts = Counter()
    results = []

    for sec, sheet_tissue in tqdm(rows, desc="checking sections", unit="sec"):
        nimp_tissues = nimp_tissue_ancestors(sec, jwt, args.cache_dir,
                                             category_cache)
        verdict = classify(sheet_tissue, nimp_tissues)
        verdicts[verdict] += 1
        results.append({
            "Section NHash ID": sec,
            "Tissue NHash ID (sheet)": sheet_tissue,
            "Tissue NHash IDs (NIMP)": ", ".join(nimp_tissues),
            "NIMP tissue count": len(nimp_tissues),
            "Verdict": verdict,
        })

    args.out.parent.mkdir(parents=True, exist_ok=True)
    with open(args.out, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(results[0].keys()) if results
                                else ["Section NHash ID"])
        writer.writeheader()
        writer.writerows(results)
    print(f"\nWrote {args.out} ({len(results)} rows)")

    # Summary
    print("\nSummary:")
    for v, n in verdicts.most_common():
        print(f"  {v:20s} {n}")

    # A little detail on the mismatch/multiple cases for triage.
    for cat in ("mismatch", "missing_in_nimp", "missing_in_sheet", "multiple"):
        picks = [r for r in results if r["Verdict"] == cat][:5]
        if not picks:
            continue
        print(f"\nFirst up to 5 rows with verdict={cat!r}:")
        for r in picks:
            print(f"  {r['Section NHash ID']:20s}  "
                  f"sheet={r['Tissue NHash ID (sheet)']!r:20s}  "
                  f"nimp={r['Tissue NHash IDs (NIMP)']!r}")


if __name__ == "__main__":
    main()
