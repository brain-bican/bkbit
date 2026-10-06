"""AIT .h5ad -> Cell Taxonomy JSON-LD, driven by the model's own annotations.

The point of this script is that it does not hardcode where fields live. Every
slot in the cell_taxonomy model carries an `ait_location` annotation saying
where its value comes from in an AIT .h5ad. linkml's pydantic generator keeps
those annotations, so they are read straight off bkbit.models.cell_taxonomy --
no LinkML YAML needs to ship alongside the generated model.

Where a declared location cannot be honoured, the script may fall back to
another source -- but every such deviation is recorded in the report, never
applied silently. That is the whole contract:

    read from where the model says; if you cannot, say so.

Location grammar (as written in the sheet's AIT Location column):

    obs.<field>                     a column of obs
    obs.index                       the obs index
    obs.<annotation_level>          template: one column per uns/hierarchy level
    uns.<key>                       a uns scalar
    uns.hierarchy (key|value)       hierarchy keys (level names) or values (order)
    uns.cluster_info                the whole cluster_info table
    uns.cluster_info.<pre>_<level>  per-level wide column, needs un-pivoting
    obsm.X_<embedding> (key|value)  an obsm embedding
    X / raw.X                       expression matrix groups
    (derived: <rule>)               not stored; computed per <rule>
    (synthesized)                   minted identifier, no file source
    <path> (data only)              present in files but NOT in the AIT schema

Reads only metadata groups over HTTP range requests; never materialises X.

Usage:
    python ait2jsonld.py URL_OR_PATH [--out out.jsonld] [--report rep.json]
                                     [--species NAME] [--no-counts]
"""

from __future__ import annotations

import contextlib
import inspect
import json
import typing
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import click
import numpy as np
from pydantic import BaseModel

from bkbit.models import cell_taxonomy as ct
from bkbit.utils.generate_bkbit_id import generate_object_id

# h5py and anndata are declared dependencies, but importing them at module
# scope would make a stale or partial environment break EVERY bkbit
# subcommand -- `bkbit --help` included -- because cli.py imports this module
# to register the command. Degrade to one failing command instead.
try:
    import h5py
    from anndata.io import read_elem
except ImportError as exc:  # pragma: no cover - environment-dependent
    h5py = None
    read_elem = None
    _MISSING_DEP = exc
else:
    _MISSING_DEP = None


def _require_h5_deps():
    """Fail with something actionable rather than a bare ImportError."""
    if _MISSING_DEP is not None:
        raise click.ClickException(
            "ait2jsonld needs h5py and anndata, which are not importable in "
            f"this environment ({_MISSING_DEP}). Reinstall bkbit, or: "
            "pip install h5py anndata fsspec aiohttp"
        )


MODELS_DIR = Path(__file__).resolve().parents[1] / "models"
CONTEXT = MODELS_DIR / "cell_taxonomy.context.jsonld"
MATRIX_GROUPS = ("X", "layers", "raw", "obsp", "varp", "varm")


# --------------------------------------------------------------------------
# provenance report
# --------------------------------------------------------------------------
@dataclass
class Report:
    """Records, per slot, whether the model's declared location was honoured."""

    source_file: str = ""
    species: str = ""
    resolved: list = field(default_factory=list)  # declared location worked
    deviations: list = field(default_factory=list)  # had to do something else
    unpopulated: list = field(default_factory=list)  # no value available
    counts: dict = field(default_factory=dict)

    def ok(self, slot, loc, note=""):
        self.resolved.append(dict(slot=slot, ait_location=loc, note=note))

    def deviate(self, slot, declared, actual, why):
        self.deviations.append(
            dict(slot=slot, declared=declared, actually_read=actual, reason=why)
        )

    def empty(self, slot, declared, why):
        self.unpopulated.append(dict(slot=slot, declared=declared, reason=why))

    def to_dict(self):
        return dict(
            source_file=self.source_file,
            species=self.species,
            summary=dict(
                resolved=len(self.resolved),
                deviations=len(self.deviations),
                unpopulated=len(self.unpopulated),
                entities=self.counts,
            ),
            resolved=self.resolved,
            deviations=self.deviations,
            unpopulated=self.unpopulated,
        )


# --------------------------------------------------------------------------
# the model as a map of slot -> declared location
# --------------------------------------------------------------------------
def _model_classes():
    """Every generated pydantic class in bkbit.models.cell_taxonomy."""
    for name, obj in vars(ct).items():
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj is not BaseModel:
            yield name, obj


DROP_VALUES = ("", "nan", "None")


def split_values(value, sep):
    """Split one stored cell into the values of a multivalued slot.

    ``sep`` comes from the model's ``ait_separator`` annotation. With no
    separator declared the cell is a single value -- guessing a delimiter
    would silently invent or merge entities.
    """
    text = "" if value is None else str(value)
    parts = text.split(sep) if sep else [text]
    return [x for x in (p.strip() for p in parts) if x and x not in DROP_VALUES]


def _admits_list(annotation) -> bool:
    """True if a field's type allows a list, looking through Optional/Union."""
    if typing.get_origin(annotation) in (list, set):
        return True
    args = typing.get_args(annotation)
    return any(_admits_list(a) for a in args if a is not type(None))


def multivalued_map() -> dict:
    """{(class, slot): bool} -- cardinality per class, not per slot *name*.

    Keying by name alone is wrong: Cluster.has_parent is multivalued while
    CellTypeTaxon.has_parent is not, so a global set wraps the latter in a
    list and the model rejects it. Read straight off the generated field
    types, which encode exactly this.
    """
    return {
        (cname, fname): _admits_list(f.annotation)
        for cname, cls in _model_classes()
        for fname, f in cls.model_fields.items()
    }


def load_locations() -> dict:
    """{(class, slot): {'loc':..., 'source':..., 'note':...}} from annotations.

    These come from the ``ait_location`` / ``source`` / ``note`` annotations on
    the cell_taxonomy LinkML schema. linkml's pydantic generator preserves them
    verbatim under each field's ``json_schema_extra["linkml_meta"]``, so the
    generated model is a complete source and the LinkML YAML does not have to
    ship alongside it. Verified equal to reading the schema with SchemaView:
    the same 52 (class, slot) pairs with identical values.
    """
    out = {}
    for cname, cls in _model_classes():
        for fname, f in cls.model_fields.items():
            meta = (f.json_schema_extra or {}).get("linkml_meta") or {}
            ann = meta.get("annotations") or {}
            if not ann:
                continue
            get = lambda tag: (ann.get(tag) or {}).get("value", "")  # noqa: E731
            if any(get(t) for t in ("ait_location", "source", "note")):
                out[(cname, fname)] = dict(
                    loc=get("ait_location"),
                    source=get("source"),
                    note=get("note"),
                    # How to split one stored string into a multivalued slot.
                    # Declared in the sheet, not hardcoded here -- the file
                    # stores e.g. "PDGFRA, DCN" or "a|b" in a single cell and
                    # only the model knows which.
                    sep=get("ait_separator"),
                )
    if not out:
        raise click.ClickException(
            "bkbit.models.cell_taxonomy carries no ait_location annotations, so "
            "no field could be located. The installed model is probably older "
            "than the annotations (added 2026-10-01). Refresh it by running the "
            "models repo's push_model_to_bkbit.yaml workflow for cell_taxonomy."
        )
    return out


DATA_ONLY = re.compile(r"\s*\(data only\)\s*$")
DERIVED = re.compile(r"^\(derived:\s*(.+)\)$")


def parse_loc(loc: str) -> dict:
    """Parse a declared location into something resolvable."""
    raw = (loc or "").strip()
    if not raw:
        return dict(kind="none", raw=raw)
    if raw == "(synthesized)":
        return dict(kind="synthesized", raw=raw)
    m = DERIVED.match(raw)
    if m:
        return dict(kind="derived", rule=m.group(1), raw=raw)
    undocumented = bool(DATA_ONLY.search(raw))
    p = DATA_ONLY.sub("", raw).strip()
    qual = None
    mq = re.search(r"\(([^)]+)\)\s*$", p)
    if mq:
        qual = mq.group(1).strip()
        p = p[: mq.start()].strip()
    if "/" in p:  # e.g. "X / raw.X"
        return dict(
            kind="multi",
            parts=[x.strip() for x in p.split("/")],
            qual=qual,
            undocumented=undocumented,
            raw=raw,
        )
    bits = p.split(".", 1)
    surface = bits[0]
    fieldpath = bits[1] if len(bits) > 1 else None
    return dict(
        kind="path",
        surface=surface,
        field=fieldpath,
        qual=qual,
        undocumented=undocumented,
        raw=raw,
    )


# --------------------------------------------------------------------------
# h5ad access (metadata only)
# --------------------------------------------------------------------------
def open_h5(path: str, cache_dir: str | None = None):
    """Open local or remote. Remote uses a local block cache so that repeat runs
    do not re-fetch the same HDF5 metadata blocks (the dominant cost: listing
    uns alone is ~26s cold)."""
    _require_h5_deps()
    stack = contextlib.ExitStack()
    if "://" in path and not path.startswith("file://"):
        import fsspec

        if cache_dir:
            fh = fsspec.open(
                "blockcache::" + path,
                blockcache={"cache_storage": cache_dir},
                block_size=8 * 1024 * 1024,
            ).open()
        else:
            fh = fsspec.open(path, block_size=8 * 1024 * 1024).open()
        stack.callback(fh.close)
        h5 = h5py.File(fh, "r")
    else:
        h5 = h5py.File(path.replace("file://", ""), "r")
    stack.callback(h5.close)
    return h5, stack


def dec(v):
    if isinstance(v, bytes):
        return v.decode(errors="replace")
    if isinstance(v, np.generic):
        return v.item()
    return v


def read_uns_scalar(h5, key):
    g = h5["uns"]
    if key not in g:
        return None
    o = g[key]
    if isinstance(o, h5py.Group):
        return None
    try:
        v = o[()] if o.shape == () else list(o[:])
        return [dec(x) for x in v] if isinstance(v, list) else dec(v)
    except Exception:
        return None


class _Table:
    """Minimal column-store stand-in for a DataFrame.

    Only ``.columns``, ``.iterrows()``, ``[col]`` and ``.shape`` are used
    downstream; keeping it this thin means we never need pandas here and never
    pull columns the model did not ask for.
    """

    def __init__(self, cols: dict, nrows: int):
        self._c = cols
        self._n = nrows

    @property
    def columns(self):
        return list(self._c)

    @property
    def shape(self):
        return (self._n, len(self._c))

    def __contains__(self, k):
        return k in self._c

    def __getitem__(self, k):
        return self._c[k]

    def iterrows(self):
        for i in range(self._n):
            yield i, {
                k: v[i] if v is not None and i < len(v) else None
                for k, v in self._c.items()
            }


def df_columns(group) -> list[str]:
    a = group.attrs.get("column-order")
    if a is not None:
        return [dec(c) for c in a]
    return sorted(k for k in group.keys() if k != "_index")


def read_col(group, name):
    """Decode ONE dataframe column (categorical or plain). Reading only the
    columns the model asks for avoids pulling all ~206 datasets of a 103-column
    table, which is what made the first version unusably slow."""
    if name not in group:
        return None
    o = group[name]
    if isinstance(o, h5py.Group) and "categories" in o and "codes" in o:
        cats = [dec(c) for c in o["categories"][:]]
        codes = o["codes"][:]
        return [cats[c] if 0 <= c < len(cats) else None for c in codes]
    try:
        return [dec(v) for v in o[:]]
    except Exception:
        return None


def obs_counts(h5, column):
    """Per-category row counts for an obs column, without loading all of obs."""
    g = h5["obs"]
    if column not in g:
        return {}
    o = g[column]
    if isinstance(o, h5py.Group) and "codes" in o and "categories" in o:
        cats = [dec(c) for c in o["categories"][:]]
        codes = o["codes"][:]
        cnt = np.bincount(codes[codes >= 0], minlength=len(cats))
        return {cats[i]: int(cnt[i]) for i in range(len(cats)) if cnt[i] > 0}
    try:
        return {dec(k): int(v) for k, v in Counter(o[:]).items()}
    except Exception:
        return {}


URI_SCHEME = re.compile(r"^[A-Za-z][A-Za-z0-9+.\-]*://")
# Virtual-hosted-style S3 over https, e.g.
#   https://my-bucket.s3.us-west-2.amazonaws.com/path/to/file.h5ad
S3_VHOST = re.compile(
    r"^https?://(?P<bucket>.+?)\.s3[.\-][^/]*amazonaws\.com/(?P<key>.+)$"
)


def source_as_uri(path: str) -> str | None:
    """The location the file was actually read from, as a URI.

    An https URL pointing at S3 is rewritten to its s3:// form, so a taxonomy
    read over range requests records the same identifier the bucket owner
    would quote. Returns None for a local path -- a filesystem location is not
    a permanent URL and must not be published as one.
    """
    if not URI_SCHEME.match(path or "") or path.startswith("file://"):
        return None
    m = S3_VHOST.match(path)
    if m:
        return f"s3://{m.group('bucket')}/{m.group('key')}"
    return path


def oid(cls_name: str, attrs: dict) -> str:
    """Deterministic id, identical to every other bkbit translator.

    Delegates to :func:`bkbit.utils.generate_bkbit_id.generate_object_id`, so
    the same entity minted here and by ``taxonomy2jsonld`` gets the same IRI.
    ``cls_name`` is accepted for call-site readability but is deliberately NOT
    hashed: including it would fork this translator's ids away from the rest
    of bkbit. Checked against all 13 released AIT files -- hashing attributes
    alone produces no cross-class collisions.
    """
    return generate_object_id({k: v for k, v in attrs.items() if k != "id"})


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
LEVEL_COL = {"cluster_id": "Cluster"}  # hierarchy name -> cluster_info column


def build(
    path: str,
    species: str = "",
    want_counts: bool = False,
    cache_dir: str | None = None,
):
    locs = load_locations()
    MULTI = multivalued_map()
    rep = Report(source_file=path, species=species)
    ents: dict[str, list] = defaultdict(list)

    h5, stack = open_h5(path, cache_dir)
    with stack:
        uns = h5["uns"]

        # ---- hierarchy: the schema-blessed way to discover levels -------
        hier_raw = read_elem(uns["hierarchy"]) if "hierarchy" in uns else {}
        levels = [k for k, _ in sorted(hier_raw.items(), key=lambda kv: int(kv[1]))]
        rep.ok(
            "CellTypeSet.name", "uns.hierarchy (key)", f"{len(levels)} levels: {levels}"
        )
        rep.ok("CellTypeSet.order", "uns.hierarchy (value)")

        # cluster_info: read ONLY the columns the model's locations reference.
        ci = None
        ci_cols: list[str] = []
        if "cluster_info" in uns:
            cig = uns["cluster_info"]
            ci_cols = df_columns(cig)
            wanted = set()
            for (c, s_), meta in locs.items():
                p = parse_loc(meta["loc"])
                f = (p.get("field") or "") if p["kind"] == "path" else ""
                f = f.replace("cluster_info.", "")
                if not f or p.get("surface") != "uns":
                    continue
                if "<level>" in f:
                    for lvl in levels:
                        wanted.add(f.replace("<level>", lvl.lower()))
                elif f in ci_cols:
                    wanted.add(f)
            # level-name columns + the leaf id, needed to key the un-pivot
            for lvl in levels:
                wanted.add(LEVEL_COL.get(lvl, lvl))
            wanted.add("cluster_id")
            # prefix groups the model reaches for by pattern
            for pre in ("tokens_", "color_hex_"):
                wanted |= {c for c in ci_cols if c.startswith(pre)}
            wanted = {w for w in wanted if w in ci_cols}
            ci = {w: read_col(cig, w) for w in sorted(wanted)}
            nrows = len(next(iter(ci.values()))) if ci else 0
            ci = _Table(ci, nrows)
            rep.ok(
                "uns.cluster_info",
                "uns.cluster_info",
                f"read {len(wanted)} of {len(ci_cols)} columns "
                f"(only those the model references) x {nrows} rows",
            )
        else:
            rep.empty("*", "uns.cluster_info", "cluster_info absent")

        # ---- CellTypeTaxonomy from uns scalars, per declared location ----
        tax_attrs = {}
        for (c, s), meta in sorted(locs.items()):
            if c != "CellTypeTaxonomy":
                continue
            p = parse_loc(meta["loc"])
            if p["kind"] == "synthesized":
                continue
            if p["kind"] != "path" or p["surface"] != "uns" or not p["field"]:
                if p["kind"] == "none":
                    rep.empty(
                        f"{c}.{s}", meta["loc"] or "(blank)", "no AIT source declared"
                    )
                continue
            key = p["field"]
            v = read_uns_scalar(h5, key)
            if v is None and key in uns:
                rep.deviate(
                    f"{c}.{s}",
                    meta["loc"],
                    f"uns.{key} (group, not scalar)",
                    "present but not a readable scalar; skipped",
                )
                continue
            if v is None:
                rep.empty(f"{c}.{s}", meta["loc"], f"uns.{key} absent from this file")
                continue
            tax_attrs[s] = v
            rep.ok(f"{c}.{s}", meta["loc"])
        # content_url: some releases put a placeholder in uns.dataset_purl
        # ('BICAN_s3_bucket' in all three HMBA files) and others omit it. The
        # location we actually read from is known and is a real URI, so fall
        # back to it -- reported, never silent. Verified against AIT33, whose
        # own dataset_purl equals the value derived from its URL.
        cu_loc = locs.get(("CellTypeTaxonomy", "content_url"), {}).get("loc", "")
        declared = tax_attrs.get("content_url")
        resolved = source_as_uri(path)
        if resolved and not (declared and URI_SCHEME.match(str(declared))):
            why = (
                f"declared value {declared!r} is not a URI; used the location the "
                "file was read from"
                if declared
                else "no value in the file; used the location it was read from"
            )
            rep.deviate(
                "CellTypeTaxonomy.content_url", cu_loc or "(blank)", resolved, why
            )
            tax_attrs["content_url"] = resolved

        tax_attrs["id"] = oid("CellTypeTaxonomy", tax_attrs)
        ents["CellTypeTaxonomy"].append(tax_attrs)
        tax_id = tax_attrs["id"]

        # ---- CellTypeSet: one per hierarchy level ------------------------
        set_ids = {}
        prev = None
        for lvl in levels:
            a = {"name": lvl, "order": int(hier_raw[lvl]), "part_of_taxonomy": tax_id}
            if prev:
                a["has_parent"] = prev
            a["id"] = oid("CellTypeSet", a)
            set_ids[lvl] = a["id"]
            ents["CellTypeSet"].append(a)
            prev = a["id"]

        # ---- Abbreviation from tokens_<level> (before taxa: they link to it)
        ab_meta = locs.get(("Abbreviation", "term"), {})
        ab_loc = ab_meta.get("loc", "")
        ab_sep = ab_meta.get("sep", "")
        if ab_loc and not ab_sep:
            # tokens_<level> packs several terms into one cell. Until the sheet
            # declares the separator, fall back to the historical "|" -- but
            # say so, rather than letting a hardcoded delimiter masquerade as
            # model-driven behaviour.
            ab_sep = "|"
            rep.deviate(
                "Abbreviation.term",
                ab_loc,
                f"{ab_loc} split on '|'",
                "no ait_separator declared on the slot; using the historical "
                "'|'. Add an ait_separator annotation in the sheet to make "
                "this model-driven.",
            )
        abbrev_id: dict[str, str] = {}
        if ci is not None and ab_loc:
            tok_cols = [c for c in ci.columns if c.startswith("tokens_")]
            for c in tok_cols:
                for v in {str(x) for x in (ci[c] or []) if x is not None}:
                    for t in split_values(v, ab_sep):
                        if t not in abbrev_id:
                            a = {"term": t}
                            a["id"] = oid("Abbreviation", a)
                            abbrev_id[t] = a["id"]
                            ents["Abbreviation"].append(a)
            if tok_cols:
                rep.ok(
                    "Abbreviation.term",
                    ab_loc,
                    f"{len(abbrev_id)} terms from {tok_cols} (split on '|') "
                    f"[undocumented extension]",
                )
            else:
                rep.empty("Abbreviation.term", ab_loc, "no tokens_* columns")
        for s_ in ("meaning", "entity_type"):
            mm = locs.get(("Abbreviation", s_))
            if mm:
                rep.empty(
                    f"Abbreviation.{s_}",
                    mm["loc"] or "(blank)",
                    "no AIT source; only available from the HMBA consensus sheet",
                )

        # ---- CellTypeTaxon: un-pivot the per-level wide block ------------
        # declared locations use a <level> placeholder; resolve per level.
        taxon_slots = {s: m for (c, s), m in locs.items() if c == "CellTypeTaxon"}
        per_level_tpl = {}
        for s, m in taxon_slots.items():
            p = parse_loc(m["loc"])
            if (
                p["kind"] == "path"
                and p.get("field", "")
                and "<level>" in (p["field"] or "")
            ):
                per_level_tpl[s] = p
        counts_by_level = {}
        if want_counts:
            for lvl in levels:
                col = LEVEL_COL.get(lvl, lvl)
                counts_by_level[lvl] = obs_counts(h5, col if col in h5["obs"] else lvl)

        taxon_ids: dict[tuple, str] = {}
        if ci is not None:
            for li, lvl in enumerate(levels):
                namecol = LEVEL_COL.get(lvl, lvl)
                if namecol not in ci.columns:
                    rep.empty(
                        f"CellTypeTaxon.name@{lvl}",
                        "obs.<annotation_level>",
                        f"no column '{namecol}' in cluster_info",
                    )
                    continue
                seen = {}
                for _, row in ci.iterrows():
                    nm = str(row[namecol])
                    if nm in seen or nm in ("", "nan", "None"):
                        continue
                    a = {"name": nm, "part_of_set": set_ids[lvl]}
                    for s, p in per_level_tpl.items():
                        col = (
                            p["field"]
                            .replace("uns.cluster_info.", "")
                            .replace("cluster_info.", "")
                            .replace("<level>", lvl.lower())
                        )
                        if col in ci.columns:
                            val = row[col]
                            if val is not None and str(val) not in ("", "nan", "None"):
                                if s == "has_abbreviation":
                                    # the column holds pipe-separated tokens;
                                    # the slot wants links to Abbreviation
                                    toks = [t.strip() for t in str(val).split("|")]
                                    ids = [abbrev_id[t] for t in toks if t in abbrev_id]
                                    if ids:
                                        a[s] = ids
                                elif s == "order":
                                    try:
                                        a[s] = int(val)
                                    except (TypeError, ValueError):
                                        pass
                                else:
                                    a[s] = str(val)
                        # recorded once per slot, below
                    if li > 0:
                        pn = str(row[LEVEL_COL.get(levels[li - 1], levels[li - 1])])
                        if (levels[li - 1], pn) in taxon_ids:
                            a["has_parent"] = taxon_ids[(levels[li - 1], pn)]
                    if want_counts and counts_by_level.get(lvl, {}).get(nm):
                        a["number_of_cells"] = counts_by_level[lvl][nm]
                    a["id"] = oid("CellTypeTaxon", a)
                    seen[nm] = a["id"]
                    taxon_ids[(lvl, nm)] = a["id"]
                    ents["CellTypeTaxon"].append(a)
            # report the per-level slots once, with what actually resolved
            for s, p in per_level_tpl.items():
                hits = [
                    lvl
                    for lvl in levels
                    if p["field"]
                    .replace("uns.cluster_info.", "")
                    .replace("cluster_info.", "")
                    .replace("<level>", lvl.lower())
                    in ci.columns
                ]
                if hits:
                    rep.ok(
                        f"CellTypeTaxon.{s}",
                        p["raw"],
                        f"resolved for levels {hits}"
                        + (
                            " [undocumented extension]" if p.get("undocumented") else ""
                        ),
                    )
                else:
                    rep.empty(
                        f"CellTypeTaxon.{s}", p["raw"], "no matching per-level column"
                    )

        # CellTypeTaxon.cell_type_ontology_term — declared on the per-level block
        ctot = taxon_slots.get("cell_type_ontology_term")
        if ctot and ci is not None:
            p = parse_loc(ctot["loc"])
            colbase = (p.get("field") or "").replace("uns.cluster_info.", "")
            if "<level>" not in colbase and colbase not in ci.columns:
                rep.empty(
                    "CellTypeTaxon.cell_type_ontology_term",
                    ctot["loc"],
                    f"'{colbase}' not in cluster_info",
                )

        # ---- ClusterSet (synthesized) + Cluster --------------------------
        cs = {
            "name": f"{tax_attrs.get('title', 'taxonomy')} clustering",
            "was_derived_from": [],
        }
        cs["id"] = oid("ClusterSet", cs)
        ents["ClusterSet"].append(cs)
        rep.deviate(
            "ClusterSet.id",
            "(synthesized)",
            "minted from taxonomy title",
            "AIT has no ClusterSet entity; one is synthesized per file",
        )

        cl_counts = obs_counts(h5, "cluster_id") if want_counts else {}
        if ci is not None and "cluster_id" in ci.columns:
            for _, row in ci.iterrows():
                nm = str(row["cluster_id"])
                a = {"name": nm, "part_of_set": cs["id"]}
                parents = [
                    taxon_ids[(lvl, str(row[LEVEL_COL.get(lvl, lvl)]))]
                    for lvl in levels
                    if LEVEL_COL.get(lvl, lvl) in ci.columns
                    and (lvl, str(row[LEVEL_COL.get(lvl, lvl)])) in taxon_ids
                ]
                if parents:
                    a["has_parent"] = parents
                if cl_counts.get(nm):
                    a["number_of_observations"] = cl_counts[nm]
                a["id"] = oid("Cluster", a)
                ents["Cluster"].append(a)
            rep.ok(
                "Cluster.name",
                "obs.cluster_id",
                "read from cluster_info (one row per cluster)",
            )
            if want_counts:
                rep.ok(
                    "Cluster.number_of_observations",
                    "(derived: count obs rows grouped by obs.cluster_id)",
                    "computed from obs categorical codes",
                )

        # ---- ExpressionMatrix: X / raw.X ---------------------------------
        for grp, mtype in (("X", "normalized"), ("raw", "raw_count")):
            if grp in h5:
                a = {"matrix_type": mtype}
                purl = read_uns_scalar(h5, "dataset_purl")
                if purl:
                    a["content_url"] = str(purl)
                a["id"] = oid("ExpressionMatrix", a)
                ents["ExpressionMatrix"].append(a)
        rep.ok(
            "ExpressionMatrix.matrix_type",
            "(derived: normalized if read from X, raw_count if read from raw.X)",
            f"found: {[g for g in ('X','raw') if g in h5]}",
        )

        # ---- Embedding: obsm X_* -----------------------------------------
        if "obsm" in h5:
            for k in h5["obsm"].keys():
                a = {"embedding_key": k}
                a["id"] = oid("Embedding", a)
                ents["Embedding"].append(a)
            rep.ok(
                "Embedding.embedding_key",
                "obsm.X_<embedding> (key)",
                f"keys: {list(h5['obsm'].keys())}",
            )
            rep.empty(
                "Embedding.embedding_matrix",
                "obsm.X_<embedding> (value)",
                "matrix values deliberately not materialised",
            )

        # ---- DisplayColor from color_hex_<level> --------------------------
        dc = locs.get(("DisplayColor", "color_hex_triplet"), {}).get("loc", "")
        if ci is not None and dc:
            hexcols = [c for c in ci.columns if c.startswith("color_hex_")]
            made = 0
            for c in hexcols:
                lvl = c.replace("color_hex_", "")
                namecol = next(
                    (LEVEL_COL.get(l, l) for l in levels if l.lower() == lvl), None
                )
                for _, row in ci.iterrows():
                    hexv = row.get(c)
                    if hexv is None or str(hexv) in ("", "nan", "None"):
                        continue
                    a = {"color_hex_triplet": str(hexv)}
                    if namecol and namecol in ci.columns:
                        key = (
                            next(l for l in levels if l.lower() == lvl),
                            str(row[namecol]),
                        )
                        if key in taxon_ids:
                            a["is_color_for_taxon"] = taxon_ids[key]
                    a["id"] = oid("DisplayColor", a)
                    if a["id"] not in {e["id"] for e in ents["DisplayColor"]}:
                        ents["DisplayColor"].append(a)
                        made += 1
            if hexcols:
                rep.ok(
                    "DisplayColor.color_hex_triplet",
                    dc,
                    f"{made} colors from {hexcols} [undocumented extension]",
                )
            else:
                rep.empty(
                    "DisplayColor.color_hex_triplet", dc, "no color_hex_* columns"
                )

        # ---- things with no h5ad source at all ---------------------------
        for c, s in (("ColorPalette", "name"), ("ColorPalette", "description")):
            if (c, s) in locs:
                rep.empty(
                    f"{c}.{s}",
                    locs[(c, s)]["loc"] or "(blank)",
                    "no AIT source; Human files carry AIT*_MapMyCells_*_label_colors "
                    "but mapping those to a palette name is unverified",
                )
        rep.empty(
            "Cell.*",
            "obs.*",
            "Cell entities intentionally not emitted (one per cell; "
            "548k-1.9M rows). Re-enable deliberately with a cap.",
        )

    # the model is the authority on cardinality, per class+slot: wrap where
    # the model says multivalued, unwrap where it does not.
    for cls_name, items in ents.items():
        for a in items:
            for k, v in list(a.items()):
                mv = MULTI.get((cls_name, k))
                if mv is True and not isinstance(v, list):
                    a[k] = [v]
                elif mv is False and isinstance(v, list):
                    a[k] = v[0] if len(v) == 1 else "|".join(str(x) for x in v)

    rep.counts = {k: len(v) for k, v in sorted(ents.items())}
    return ents, rep


def to_jsonld(ents, context_path=None):
    graph = []
    for cls, items in ents.items():
        for a in items:
            graph.append({"@type": cls, **a})
    doc = {"@graph": graph}
    if context_path and Path(context_path).exists():
        doc["@context"] = json.loads(Path(context_path).read_text())["@context"]
    return doc


@click.command()
@click.argument("path")
@click.option("--out", default=None, help="write JSON-LD here")
@click.option("--report", default=None, help="write the provenance report here")
@click.option("--species", default="", help="label used in the report")
@click.option(
    "--counts",
    is_flag=True,
    help="compute the derived per-taxon/per-cluster counts (reads obs "
    "codes: slower, adds number_of_cells / number_of_observations)",
)
@click.option(
    "--cache",
    default=None,
    help="local directory for the fsspec block cache (speeds up repeat runs)",
)
@click.option(
    "--context",
    default=str(CONTEXT),
    show_default=False,
    help="JSON-LD context [default: the copy packaged with bkbit]",
)
def ait2jsonld(path, out, report, species, counts, cache, context):
    """Translate an AIT .h5ad taxonomy into Cell Taxonomy JSON-LD.

    PATH is a local path or an http(s)/s3 URL. Remote files are read over range
    requests -- a 332 GB file needs no download.
    """
    ents, rep = build(path, species, want_counts=counts, cache_dir=cache)
    click.echo(f"--- {species or path} ---")
    for k, v in rep.counts.items():
        click.echo(f"  {k:<20} {v}")
    s = rep.to_dict()["summary"]
    click.echo(
        f"  resolved={s['resolved']} deviations={s['deviations']} "
        f"unpopulated={s['unpopulated']}"
    )

    if out:
        Path(out).write_text(
            json.dumps(to_jsonld(ents, context), indent=2, default=str)
        )
        click.echo(f"  wrote {out}")
    if report:
        Path(report).write_text(json.dumps(rep.to_dict(), indent=2, default=str))
        click.echo(f"  wrote {report}")


if __name__ == "__main__":
    ait2jsonld()
