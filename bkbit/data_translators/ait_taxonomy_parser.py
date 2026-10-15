"""Parser for Allen Institute Taxonomy (AIT) files in ``.h5ad`` (AnnData) format.

AIT taxonomies (e.g. those produced by the ``scrattch`` toolkit and released for
the BICAN / HMBA project) are stored as `AnnData <https://anndata.readthedocs.io>`_
objects. The cell-by-gene expression matrix (``X``, ``layers``, ``raw``) makes up
essentially all of the file size (tens to >100 GB), while the *taxonomy* itself
lives in a handful of tiny groups:

* ``uns/hierarchy``   - the ordered taxonomy levels (top -> leaf).
* ``uns/cluster_info``- one row per leaf cluster, with the full ancestor path plus
                        per-level accession, color, CL ontology id, tokens and
                        display order.
* ``uns/*`` scalars   - taxonomy-level metadata (title, schema_version, ...).
* ``obs``             - per-cell assignments to each taxonomy level (categorical).

This module reads **only** those metadata groups and never materializes ``X``, so
it works against multi-GB files - including reading them directly from an
``https://`` or ``s3://`` URL via HDF5 range requests (no full download).

Example
-------
>>> from bkbit.data_translators.ait_taxonomy_parser import AITTaxonomy
>>> tax = AITTaxonomy.from_file(
...     "https://.../Marmoset_HMBA_basalganglia_AIT_pre-print.h5ad")
>>> tax.title
'Marmoset_HMBA_basalganglia_consensus_AIT'
>>> tax.levels
['Neighborhood', 'Class', 'Subclass', 'Group', 'cluster_id']
>>> tax.cluster_info.shape
(594, 80)
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass, field
from typing import Any, Iterator

import h5py
import pandas as pd
from anndata.io import read_elem

# Groups that hold the expression data - never read these when parsing taxonomy.
_MATRIX_GROUPS = ("X", "layers", "raw", "obsp", "varp", "varm")


def _open_h5(path: str) -> tuple[h5py.File, contextlib.ExitStack]:
    """Open a local path or a remote (http/https/s3/gcs) URL as an ``h5py.File``.

    Remote files are opened lazily with :mod:`fsspec` so that only the byte
    ranges actually accessed are fetched over the network.
    """
    stack = contextlib.ExitStack()
    if "://" in path and not path.startswith("file://"):
        import fsspec

        protocol = path.split("://", 1)[0]
        # A generous block size keeps the number of range requests low.
        fileobj = fsspec.open(path, block_size=8 * 1024 * 1024).open()
        stack.callback(fileobj.close)
        _ = protocol  # (kept for clarity / future protocol-specific handling)
        h5 = h5py.File(fileobj, "r")
    else:
        h5 = h5py.File(path.replace("file://", ""), "r")
    stack.callback(h5.close)
    return h5, stack


def _scalar(value: Any) -> Any:
    """Normalize an h5py-decoded scalar/array to a plain Python value."""
    if isinstance(value, bytes):
        return value.decode()
    if hasattr(value, "tolist"):
        out = value.tolist()
        if isinstance(out, list):
            return [v.decode() if isinstance(v, bytes) else v for v in out]
        return out
    return value


@dataclass
class AITTaxonomy:
    """Parsed contents of an AIT ``.h5ad`` taxonomy file (metadata only)."""

    title: str | None
    levels: list[str]
    """Taxonomy levels ordered from broadest (root) to finest (leaf)."""
    cluster_info: pd.DataFrame
    """One row per leaf cluster with the full ancestor path and per-level metadata."""
    obs: pd.DataFrame | None
    """Per-cell annotations (taxonomy assignments + sample metadata)."""
    var: pd.DataFrame | None
    """Gene metadata."""
    uns: dict[str, Any] = field(default_factory=dict)
    """Scalar / small unstructured metadata (title, schema_version, ...)."""

    # ---- constructors -------------------------------------------------------
    @classmethod
    def from_file(
        cls,
        path: str,
        *,
        load_obs: bool = True,
        load_var: bool = True,
    ) -> "AITTaxonomy":
        """Parse an AIT ``.h5ad`` file at a local path or remote URL.

        Parameters
        ----------
        path:
            Local filesystem path, or an ``https://`` / ``s3://`` / ``gs://`` URL.
        load_obs:
            Read the per-cell ``obs`` table. For files with millions of cells this
            is the largest metadata group; set ``False`` to skip it and read only
            the taxonomy definition (``uns`` + ``cluster_info``).
        load_var:
            Read the gene (``var``) table.
        """
        h5, stack = _open_h5(path)
        with stack:
            uns_group = h5["uns"]

            # Ordered taxonomy levels from uns/hierarchy: {level_name: position}.
            hierarchy = read_elem(uns_group["hierarchy"])
            levels = [name for name, _ in sorted(hierarchy.items(), key=lambda kv: int(kv[1]))]

            # cluster_info: the leaf-cluster taxonomy table.
            cluster_info = read_elem(uns_group["cluster_info"])

            # Remaining uns entries as scalars/small values (skip the two above).
            uns: dict[str, Any] = {}
            for key in uns_group.keys():
                if key in ("hierarchy", "cluster_info"):
                    continue
                with contextlib.suppress(Exception):
                    uns[key] = _scalar(read_elem(uns_group[key]))

            obs = read_elem(h5["obs"]) if load_obs else None
            var = read_elem(h5["var"]) if load_var else None

            title = _scalar(uns.get("title"))

        return cls(
            title=title,
            levels=levels,
            cluster_info=cluster_info,
            obs=obs,
            var=var,
            uns=uns,
        )

    # ---- taxonomy views -----------------------------------------------------
    def level_categories(self, level: str) -> list[str]:
        """Unique node names at a taxonomy ``level`` (in cluster_info order)."""
        col = "Cluster" if level == "cluster_id" and "Cluster" in self.cluster_info else level
        return list(pd.unique(self.cluster_info[col].astype(str)))

    def iter_leaves(self) -> Iterator[dict[str, Any]]:
        """Yield each leaf cluster row of ``cluster_info`` as a plain dict."""
        for _, row in self.cluster_info.iterrows():
            yield row.to_dict()

    def edges(self) -> list[tuple[str, str, str, str]]:
        """Parent/child edges of the taxonomy tree.

        Returns tuples ``(parent_level, parent_name, child_level, child_name)``
        derived from the per-cluster ancestor path in ``cluster_info``.
        """
        seen: set[tuple[str, str, str, str]] = set()
        edges: list[tuple[str, str, str, str]] = []
        cols = [("Cluster" if lvl == "cluster_id" else lvl) for lvl in self.levels]
        cols = [c for c in cols if c in self.cluster_info.columns]
        for _, row in self.cluster_info.iterrows():
            for (pl, pc), (cl, cc) in zip(zip(self.levels, cols), zip(self.levels[1:], cols[1:])):
                edge = (pl, str(row[pc]), cl, str(row[cc]))
                if edge not in seen:
                    seen.add(edge)
                    edges.append(edge)
        return edges

    def to_csv(self, path: str) -> str:
        """Write the leaf-cluster taxonomy table (``cluster_info``) to ``path``."""
        self.cluster_info.to_csv(path, index=True, index_label="cell_label")
        return path

    def summary(self) -> str:
        """Human-readable one-block summary of the taxonomy."""
        lines = [
            f"title:           {self.title}",
            f"schema_version:  {self.uns.get('schema_version')}",
            f"reference_genome:{self.uns.get('reference_genome')}",
            f"levels:          {' > '.join(self.levels)}",
            f"leaf clusters:   {len(self.cluster_info)}",
        ]
        for lvl in self.levels:
            with contextlib.suppress(Exception):
                lines.append(f"  {lvl:<14} {len(self.level_categories(lvl))} nodes")
        if self.obs is not None:
            lines.append(f"cells (obs):     {len(self.obs):,}")
        if self.var is not None:
            lines.append(f"genes (var):     {len(self.var):,}")
        return "\n".join(lines)


def parse_ait(path: str, **kwargs: Any) -> AITTaxonomy:
    """Convenience wrapper around :meth:`AITTaxonomy.from_file`."""
    return AITTaxonomy.from_file(path, **kwargs)


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Parse an AIT .h5ad taxonomy file.")
    ap.add_argument("path", help="Local path or http(s)/s3 URL to the .h5ad file")
    ap.add_argument("--no-obs", action="store_true", help="Skip the per-cell obs table")
    ap.add_argument("--out", metavar="CSV", help="Write the cluster_info taxonomy table to this CSV path")
    args = ap.parse_args()

    tax = AITTaxonomy.from_file(args.path, load_obs=not args.no_obs)
    print(tax.summary())
    if args.out:
        tax.to_csv(args.out)
        print(f"\nwrote {len(tax.cluster_info)} clusters x {tax.cluster_info.shape[1]} cols -> {args.out}")
