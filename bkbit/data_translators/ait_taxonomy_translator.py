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

curated_markers has range GeneAnnotation, so its values must be links. The file
stores symbols; --gene_annotation (one gff2jsonld output, Turtle or JSON-LD, of
the taxonomy's species -- checked) supplies the GeneAnnotation IRIs. Symbols that do not
resolve are reported and left out, never written as strings -- a bare string
in an @id slot becomes a relative IRI against the output file's path.

Usage:
    python ait2jsonld.py URL_OR_PATH [--out out.jsonld] [--report rep.json]
                                     [--species NAME] [--no-counts]
                                     [--gene_annotation ANNOTATION.ttl|.jsonld]
"""

from __future__ import annotations

import contextlib
import csv
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
    """{(class, slot): {'loc':..., 'sep':...}} from the model's annotations.

    These come from the ``ait_location`` and ``ait_separator`` annotations on
    the cell_taxonomy LinkML schema. linkml's pydantic generator preserves them
    verbatim under each field's ``json_schema_extra["linkml_meta"]``, so the
    generated model is a complete source and the LinkML YAML does not have to
    ship alongside it. Verified equal to reading the schema with SchemaView:
    the same (class, slot) pairs with identical values.

    The sheet also has Notes and Source columns, but both are deliberately
    mapped to ``ignore`` and so never reach the model; this used to read them
    and no longer does.
    """
    out = {}
    for cname, cls in _model_classes():
        for fname, f in cls.model_fields.items():
            meta = (f.json_schema_extra or {}).get("linkml_meta") or {}
            ann = meta.get("annotations") or {}
            if not ann:
                continue
            get = lambda tag: (ann.get(tag) or {}).get("value", "")  # noqa: E731
            if get("ait_location"):
                out[(cname, fname)] = dict(
                    loc=get("ait_location"),
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
    if isinstance(o, h5py.Group) and "values" in o and "mask" in o:
        # nullable-string-array (anndata >= 0.11 writes pandas strings so);
        # a masked entry is missing.
        vals, mask = o["values"][:], o["mask"][:]
        return [None if m else dec(v) for v, m in zip(vals, mask)]
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


def blankish(v):
    """None for a cell that is empty or a stringified null, else its text."""
    if v is None:
        return None
    t = str(v).strip()
    return None if t in DROP_VALUES else t


def value_validators(cls_name: str) -> dict:
    """{slot: callable} for slots the model constrains, e.g. with a `pattern`.

    linkml's pydantic generator compiles a `pattern` into a @field_validator
    rather than leaving it on the field, so it cannot be read off FieldInfo or
    the JSON schema. Pulling the validators out of __pydantic_decorators__ and
    calling them keeps the model the single authority -- no regex is restated
    here.
    """
    cls = getattr(ct, cls_name, None)
    decs = getattr(cls, "__pydantic_decorators__", None)
    if decs is None:
        return {}
    return {
        field: dec.func
        for dec in decs.field_validators.values()
        for field in dec.info.fields
    }


def accepts(cls_name, slot, value, rep, loc, seen) -> bool:
    """True if the model accepts this value for this slot.

    A rejected value is dropped and reported once per distinct value, never
    raised: a tracking placeholder in one column should not fail a whole
    taxonomy. Deliberate -- see the ASK NELSON note on CL:ID_<level>.
    """
    fn = value_validators(cls_name).get(slot)
    if fn is None:
        return True
    try:
        fn(value)
        return True
    except Exception as exc:
        key = (cls_name, slot, str(value))
        if key not in seen:
            seen.add(key)
            rep.deviate(
                f"{cls_name}.{slot}",
                loc or "(blank)",
                f"value {value!r} skipped",
                f"rejected by the model's own validator ({exc}); "
                "dropped rather than raised",
            )
        return False


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BUNDLED_ABBREVIATIONS = {
    "hmba-basalganglia": DATA_DIR / "hmba_basalganglia_abbreviations.csv",
}
ABBREV_COLUMNS = {
    "abbreviation_term": "term",
    "abbreviation_meaning": "meaning",
    "abbreviation_type": "entity_type",
}

#: Prefixes whose terms are concepts in a published ontology, as opposed to
#: records in a database.
#:
#: The distinction decides which slot a value lands in. Biolink defines
#: ``xref`` as a cross reference to a database identifier, and it serialises
#: as a literal, so a CL or UBERON term sitting there joins with nothing. The
#: SKOS mapping slots have a class range, so the generated context gives them
#: ``"@type": "@id"`` and the CURIE becomes a real node that resolves against
#: the published ontology. Database identifiers stay in ``xref``, which is
#: what it is for.
#:
#: Keyed on the prefix rather than the table's ``abbreviation_type`` column,
#: because the two can disagree -- the prefix is what decides whether a value
#: is resolvable, and a row typed ``gene`` could still carry an ontology term.
#: An unrecognised prefix is left in ``xref`` and reported, so a new ontology
#: shows up as a deviation rather than silently becoming an unjoinable
#: literal.
ONTOLOGY_PREFIXES = frozenset({"CL", "UBERON", "DHBA"})

#: Which SKOS predicate the ontology terms are asserted with.
#:
#: ``broad_match``, not ``exact_match``: the mapping is many-to-one. Measured
#: across the HMBA files, up to three distinct CellTypeTaxon entries share one
#: CL term (CL:0000128, CL:4042025, CL:0000192), and abbreviations reuse terms
#: too. ``skos:exactMatch`` is symmetric *and* transitive, so asserting it
#: three times against one term would entail that those three taxa are
#: equivalent to each other, which is false -- they are distinct taxa sharing
#: a coarser class. ``skos:broadMatch`` says the true thing: the external
#: concept is broader than ours.
ONTOLOGY_PREDICATE = "broad_match"

#: Prefixes known to be database identifiers, so correctly left in ``xref``.
#: Anything in neither set is reported rather than silently assumed to be one.
KNOWN_DATABASE_PREFIXES = frozenset({"ENSEMBL", "NCBIGene"})


def load_abbreviations(spec: str) -> tuple[dict, list]:
    """{term: {meaning, entity_type, xref}} from an abbreviation table.

    `spec` is a path, or the name of a table bundled with bkbit (see
    BUNDLED_ABBREVIATIONS). The table is taxonomy-specific -- the HMBA
    basal-ganglia one does not describe the tokens in other taxonomies -- so
    there is no default: nothing is enriched unless a table is named.
    """
    path = BUNDLED_ABBREVIATIONS.get(spec, Path(spec))
    if not path.is_file():
        known = ", ".join(sorted(BUNDLED_ABBREVIATIONS))
        raise click.ClickException(
            f"abbreviation table not found: {spec}. Give a path, or one of: {known}"
        )
    out = {}
    unknown: set = set()
    with path.open(newline="", encoding="utf-8") as fh:
        reader = csv.DictReader(fh)
        missing = [c for c in ABBREV_COLUMNS if c not in (reader.fieldnames or [])]
        if missing:
            raise click.ClickException(
                f"{path}: missing column(s) {', '.join(missing)}. "
                f"Expected: {', '.join(ABBREV_COLUMNS)}"
            )
        for row in reader:
            term = (row.get("abbreviation_term") or "").strip()
            if not term:
                continue
            identifiers = [
                v
                for v in (
                    (row.get("primary_identifier") or "").strip(),
                    (row.get("secondary_identifier") or "").strip(),
                )
                if v
            ]
            rec = {}
            for src, slot in ABBREV_COLUMNS.items():
                if slot == "term":
                    continue
                val = (row.get(src) or "").strip()
                if val:
                    rec[slot] = val
            # Ontology terms go to a SKOS slot so they serialise as nodes;
            # database identifiers stay in xref. See ONTOLOGY_PREFIXES.
            mapped = [v for v in identifiers if v.split(":")[0] in ONTOLOGY_PREFIXES]
            xref = [v for v in identifiers if v not in mapped]
            if mapped:
                rec[ONTOLOGY_PREDICATE] = mapped
            if xref:
                rec["xref"] = xref
            unknown.update(
                v.split(":")[0]
                for v in xref
                if ":" in v and v.split(":")[0] not in KNOWN_DATABASE_PREFIXES
            )
            out[term] = rec
    return out, sorted(unknown)


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
# gene annotation: curated_markers links
# --------------------------------------------------------------------------
#: ``CellTypeTaxon.curated_markers`` has range ``GeneAnnotation``, so the
#: generated context types it ``"@type": "@id"``. The AIT file stores gene
#: *symbols* ("PDGFRA, DCN"). Written as they are, a JSON-LD processor reads
#: each symbol as a relative IRI and resolves it against the document's base --
#: the output file's own path -- so the graph ends up with
#: ``file:///.../ACTA2``: a node nothing else refers to. The value the model
#: asks for is the IRI of a GeneAnnotation, which ``gff2jsonld`` mints. So
#: symbols are looked up in the ONE gff2jsonld output the caller names for
#: this h5ad, and a symbol that cannot be resolved is reported, never written
#: as a string.
GENE_ANNOTATION_CLASS = "https://identifiers.org/brain-bican/vocab/GeneAnnotation"
GENOME_ANNOTATION_CLASS = "https://identifiers.org/brain-bican/vocab/GenomeAnnotation"
ORGANISM_TAXON_CLASS = "https://w3id.org/biolink/vocab/OrganismTaxon"
BIOLINK = "https://w3id.org/biolink/vocab/"
ORGANISM_COLUMN = "organism_ontology_term_id"
GENOME_ANNOTATION_CONTEXT = MODELS_DIR / "genome_annotation.context.jsonld"
_TAXON_NUMBER = re.compile(r"(?:NCBITaxon[:_]|txid)(\d+)$", re.IGNORECASE)
_JSONLD_SUFFIXES = (".jsonld", ".json")
_TURTLE_SUFFIXES = (".ttl",)


def ncbi_taxon_number(value) -> str | None:
    """'9606' from NCBITaxon:9606, NCBITaxon_9606 (IRI) or NCBI:txid9606."""
    m = _TAXON_NUMBER.search(str(value or "").strip())
    return m.group(1) if m else None


@dataclass
class GeneIndex:
    """Symbol lookup over the GeneAnnotations of one genome annotation file."""

    taxon: str  # NCBI taxon number of every gene in the file
    source: str = ""  # file name
    label: str = ""  # GenomeAnnotation label, e.g. ENSEMBL-9606-109
    by_symbol: dict = field(default_factory=lambda: defaultdict(set))
    by_folded: dict = field(default_factory=lambda: defaultdict(set))
    by_synonym: dict = field(default_factory=lambda: defaultdict(set))

    def resolve(self, symbol: str) -> tuple[str | None, str]:
        """(GeneAnnotation IRI, tier) or (None, why).

        Tiers, strongest first: ``symbol`` (exact), ``symbol_case`` (the same
        symbol in another case, e.g. mouse-style "Pou6f2" for POU6F2),
        ``synonym`` (exact). Each tier must name exactly one gene; an
        ambiguous tier is reported, never broken by picking one.
        """
        for tier, ids in (
            ("symbol", self.by_symbol.get(symbol)),
            ("symbol_case", self.by_folded.get(symbol.casefold())),
            ("synonym", self.by_synonym.get(symbol)),
        ):
            if not ids:
                continue
            if len(ids) == 1:
                return next(iter(ids)), tier
            return None, f"ambiguous: {len(ids)} genes match by {tier}"
        return None, "no gene with this symbol or synonym"


def gene_annotation_format(path) -> str:
    """'json-ld' or 'turtle', from the content, checked against the extension.

    The content decides (a JSON document starts with '{' or '['); a known
    extension that disagrees with it is an error rather than a guess, since a
    mislabelled file is usually the wrong file.
    """
    with open(path, encoding="utf-8") as fh:
        head = fh.read(4096).lstrip("\ufeff \t\r\n")
    by_content = "json-ld" if head[:1] in ("{", "[") else "turtle"
    name = str(path).lower()
    by_ext = (
        "json-ld"
        if name.endswith(_JSONLD_SUFFIXES)
        else "turtle" if name.endswith(_TURTLE_SUFFIXES) else None
    )
    if by_ext and by_ext != by_content:
        raise click.ClickException(
            f"{path}: the extension says {by_ext} but the content is {by_content}"
        )
    return by_content


def _jsonld_with_local_context(path) -> str:
    """The JSON-LD text, with gff2jsonld's context URL replaced by bkbit's copy.

    gff2jsonld writes its context by URL (pinned to a brain-bican/models
    commit), so parsing its output would fetch that URL. The context bundled
    with bkbit is the same document, so it is substituted and nothing is
    fetched. A context URL other than the one gff2jsonld pins is left alone.
    """
    from bkbit.data_translators.genome_annotation_translator import CONTEXT_URL

    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(doc, dict) and doc.get("@context") == CONTEXT_URL:
        doc["@context"] = json.loads(
            GENOME_ANNOTATION_CONTEXT.read_text(encoding="utf-8")
        )["@context"]
    return json.dumps(doc)


def load_gene_annotation(path) -> GeneIndex:
    """GeneIndex over one gff2jsonld output, in Turtle or JSON-LD.

    The file's species is the ``NCBITaxon:<n>`` xref of the OrganismTaxon its
    genes are ``in_taxon`` of -- the same number the AIT file stores in
    ``organism_ontology_term_id``, which build() checks it against. A file
    whose genes span several species is rejected: one h5ad, one annotation.
    """
    import rdflib
    from rdflib import RDF, RDFS, URIRef

    fmt = gene_annotation_format(path)
    g = rdflib.Graph()
    if fmt == "json-ld":
        g.parse(data=_jsonld_with_local_context(path), format="json-ld")
    else:
        g.parse(str(path), format="turtle")
    sym, syn = URIRef(BIOLINK + "symbol"), URIRef(BIOLINK + "synonym")
    in_taxon, xref = URIRef(BIOLINK + "in_taxon"), URIRef(BIOLINK + "xref")
    taxa = {}
    for t_ in g.subjects(RDF.type, URIRef(ORGANISM_TAXON_CLASS)):
        nums = {ncbi_taxon_number(x) for x in g.objects(t_, xref)} - {None}
        if len(nums) == 1:
            taxa[t_] = nums.pop()
    genes = [
        (gene, taxa.get(g.value(gene, in_taxon)))
        for gene in g.subjects(RDF.type, URIRef(GENE_ANNOTATION_CLASS))
    ]
    species = {num for _, num in genes if num}
    if not species:
        raise click.ClickException(
            f"{path}: no GeneAnnotation with an in_taxon OrganismTaxon carrying an "
            "NCBITaxon xref. Is this gff2jsonld output?"
        )
    if len(species) > 1:
        raise click.ClickException(
            f"{path}: genes of several species ({', '.join(sorted(species))}); "
            "give the annotation of the taxonomy's one species"
        )
    labels = sorted(
        str(g.value(a, RDFS.label))
        for a in g.subjects(RDF.type, URIRef(GENOME_ANNOTATION_CLASS))
        if g.value(a, RDFS.label) is not None
    )
    idx = GeneIndex(
        taxon=species.pop(), source=Path(str(path)).name, label=", ".join(labels)
    )
    for gene, num in genes:
        if num is None:
            continue
        gid = str(gene)
        for s_ in g.objects(gene, sym):
            idx.by_symbol[str(s_)].add(gid)
            idx.by_folded[str(s_).casefold()].add(gid)
        for s_ in g.objects(gene, syn):
            idx.by_synonym[str(s_)].add(gid)
    return idx


def resolve_markers(symbols, gene_index, tally) -> list[str]:
    """GeneAnnotation IRIs for the symbols that resolve; the rest go to `tally`.

    With no gene index nothing is emitted: a symbol is not a valid value of a
    GeneAnnotation-ranged slot. A cell that is not a symbol list at all (e.g.
    "Six3 and Foxp1") is not re-split -- the declared separator is the only
    one -- so it is reported unresolved for the data to be fixed upstream.
    """
    if gene_index is None:
        why = "no --gene_annotation given"
        tally["unresolved"].update({s_: why for s_ in symbols})
        return []
    out = []
    for s_ in symbols:
        gid, how = gene_index.resolve(s_)
        if gid:
            out.append(gid)
            tally["resolved"][how] += 1
            if how != "symbol":
                tally.setdefault("weaker", {})[s_] = how
        else:
            tally["unresolved"][s_] = how
    return list(dict.fromkeys(out))


def is_link(value, prefixes) -> bool:
    """True for an absolute IRI or a CURIE whose prefix the context defines.

    Anything else in an ``@id``-typed slot is a relative IRI reference, which a
    JSON-LD processor silently resolves against the document base.
    """
    v = str(value)
    if URI_SCHEME.match(v) or v.startswith(("urn:", "mailto:")):
        return True
    prefix, sep, rest = v.partition(":")
    return bool(sep) and prefix in prefixes and " " not in rest


def guard_links(ents, rep, context_path=None) -> int:
    """Drop values that would become relative IRIs, and report each one.

    The model is the authority on which slots hold links (the generated
    context marks them ``"@type": "@id"``); this applies it to every class
    and slot, so a new link slot fed a plain string fails loudly here rather
    than quietly becoming a ``file:///`` node. Returns the number dropped.
    """
    ctx_file = Path(context_path) if context_path else CONTEXT
    if not ctx_file.exists():
        return 0
    ctx = json.loads(ctx_file.read_text())["@context"]
    link_slots = {
        k for k, v in ctx.items() if isinstance(v, dict) and v.get("@type") == "@id"
    }
    # A prefix is a plain IRI string ("bican": "https://...") or an expanded
    # definition carrying "@prefix": true ("CL": {"@id": ..., "@prefix": true}).
    prefixes = {
        k
        for k, v in ctx.items()
        if not k.startswith("@")
        and (isinstance(v, str) or (isinstance(v, dict) and v.get("@prefix")))
    }
    dropped = 0
    seen: set = set()
    for cls_name, items in ents.items():
        for a in items:
            for k in [k for k in a if k in link_slots]:
                vals = a[k] if isinstance(a[k], list) else [a[k]]
                keep = [v for v in vals if is_link(v, prefixes)]
                for v in vals:
                    if v in keep or (cls_name, k, str(v)) in seen:
                        continue
                    seen.add((cls_name, k, str(v)))
                    rep.deviate(
                        f"{cls_name}.{k}",
                        "(link slot)",
                        f"value {v!r} dropped",
                        "the slot holds links (@type @id) and this is neither an "
                        "absolute IRI nor a CURIE with a known prefix; written "
                        "as is it would resolve against the output file's path",
                    )
                dropped += len(vals) - len(keep)
                if not keep:
                    del a[k]
                elif isinstance(a[k], list):
                    a[k] = keep
    return dropped


# --------------------------------------------------------------------------
# build
# --------------------------------------------------------------------------
LEVEL_COL = {"cluster_id": "Cluster"}  # hierarchy name -> cluster_info column


def build(
    path: str,
    species: str = "",
    want_counts: bool = False,
    cache_dir: str | None = None,
    abbreviations: str | None = None,
    gene_annotation: str | None = None,
):
    locs = load_locations()
    MULTI = multivalued_map()
    # Validate the abbreviation table before opening the .h5ad: a typo in the
    # table name should not cost a remote read of a 300 GB file first.
    abbrev_table, unknown_prefixes = (
        load_abbreviations(abbreviations) if abbreviations else ({}, [])
    )
    # Same for the gene annotation, which also takes a while to parse.
    gene_index = load_gene_annotation(gene_annotation) if gene_annotation else None
    marker_report: dict = {"resolved": Counter(), "unresolved": {}}
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
            # The species, to pick the gene annotation curated_markers resolve
            # against. The model declares no location for it, so it is read
            # from the AIT schema's own column and reported as such.
            # The gene annotation must be of the taxonomy's species: linking a
            # human taxon to macaque genes would be a plausible, silent error.
            # The model declares no location for the species, so it is read
            # from the AIT schema's own column.
            if gene_index is not None:
                organisms = (
                    {ncbi_taxon_number(v) for v in read_col(cig, ORGANISM_COLUMN)}
                    if ORGANISM_COLUMN in ci_cols
                    else set()
                )
                organisms.discard(None)
                if len(organisms) != 1:
                    raise click.ClickException(
                        f"cannot check --gene_annotation against this taxonomy: "
                        f"uns.cluster_info.{ORGANISM_COLUMN} gives "
                        f"{sorted(organisms) or 'no'} NCBI taxa, not one"
                    )
                taxon = organisms.pop()
                if taxon != gene_index.taxon:
                    raise click.ClickException(
                        f"--gene_annotation {gene_index.source} is NCBITaxon:"
                        f"{gene_index.taxon}, but this taxonomy is NCBITaxon:{taxon} "
                        f"({ORGANISM_COLUMN}); give the annotation of its species"
                    )
                rep.deviate(
                    "CellTypeTaxon.curated_markers",
                    f"uns.cluster_info.{ORGANISM_COLUMN}",
                    f"species NCBITaxon:{taxon} matches --gene_annotation "
                    f"{gene_index.source} ({gene_index.label})",
                    "the model declares no location for the taxonomy's species; "
                    "read from the AIT column to check the gene annotation",
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
            if p["kind"] == "path" and p["surface"] in MATRIX_GROUPS:
                # A matrix (e.g. varm.cluster_id_mean_expr, genes x clusters)
                # is declared so the model records where it lives, but its
                # values are not put in the graph. Say whether this file has it.
                grp = h5.get(p["surface"])
                present = grp is not None and bool(p["field"]) and p["field"] in grp
                rep.empty(
                    f"{c}.{s}",
                    meta["loc"],
                    "matrix values deliberately not materialised "
                    f"({'present' if present else 'absent'} in this file)",
                )
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
        # gene_annotation_version: the curated_markers point into the gene
        # annotation that was used, so the graph says which one. The file's
        # own value wins when it has one; the HMBA files leave it blank.
        if gene_index is not None and gene_index.label:
            gav_loc = locs.get(("CellTypeTaxonomy", "gene_annotation_version"), {})
            declared = blankish(tax_attrs.get("gene_annotation_version"))
            if declared is None:
                tax_attrs["gene_annotation_version"] = gene_index.label
                rep.deviate(
                    "CellTypeTaxonomy.gene_annotation_version",
                    gav_loc.get("loc") or "(blank)",
                    f"{gene_index.label} (from --gene_annotation {gene_index.source})",
                    "blank in the file; set to the annotation curated_markers "
                    "link into",
                )
            elif declared != gene_index.label:
                rep.deviate(
                    "CellTypeTaxonomy.gene_annotation_version",
                    gav_loc.get("loc") or "(blank)",
                    f"kept {declared!r}",
                    f"differs from --gene_annotation {gene_index.label}; the file's "
                    "value is kept, but curated_markers link into the latter",
                )

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
                            a.update(abbrev_table.get(t, {}))
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

            if abbreviations:
                matched = sorted(t for t in abbrev_id if t in abbrev_table)
                unmatched = sorted(t for t in abbrev_id if t not in abbrev_table)
                unused = sorted(set(abbrev_table) - set(abbrev_id))
                rep.ok(
                    "Abbreviation.meaning/entity_type/xref",
                    f"(external: {abbreviations})",
                    f"{len(matched)}/{len(abbrev_id)} terms enriched from the "
                    f"table; {len(unmatched)} token(s) absent from it; "
                    f"{len(unused)} table row(s) unused by this file",
                )
                # Unmatched tokens are the interesting direction: the table is
                # taxonomy-specific, so a long list means it does not describe
                # this taxonomy and should probably not have been passed.
                if unknown_prefixes:
                    rep.deviate(
                        f"Abbreviation.{ONTOLOGY_PREDICATE}/xref",
                        f"(external: {abbreviations})",
                        f"{', '.join(unknown_prefixes)} left in xref",
                        "prefix is in neither ONTOLOGY_PREFIXES nor "
                        "KNOWN_DATABASE_PREFIXES, so it was treated as a "
                        "database identifier. If it names an ontology, add it "
                        "to ONTOLOGY_PREFIXES or its terms will not resolve.",
                    )
                if unmatched:
                    rep.deviate(
                        "Abbreviation.meaning/entity_type/xref",
                        f"(external: {abbreviations})",
                        f"{len(unmatched)} token(s) left bare",
                        "not in the abbreviation table: "
                        + ", ".join(unmatched[:12])
                        + (" ..." if len(unmatched) > 12 else ""),
                    )
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
        rejected: set = set()
        per_level_tpl = {}
        plain_cols = {}
        for s, m in taxon_slots.items():
            p = parse_loc(m["loc"])
            if p["kind"] != "path" or not p.get("field", ""):
                continue
            field = p["field"] or ""
            if "<level>" in field:
                per_level_tpl[s] = p
            elif field.startswith(("uns.cluster_info.", "cluster_info.")):
                # A plain cluster_info column, not a per-level template:
                # curated_markers, literature_support, ... These are stored on
                # every cluster row but describe a coarser level, so they may
                # only be attached where the column is constant within the
                # level -- otherwise one of several values would be picked
                # arbitrarily.
                plain_cols[s] = field.split("cluster_info.", 1)[1]

        plain_levels = {}
        plain_values: dict = {}
        if ci is not None:
            for s_, colname in plain_cols.items():
                if colname not in ci.columns:
                    rep.empty(
                        f"CellTypeTaxon.{s_}",
                        taxon_slots[s_]["loc"],
                        f"no column '{colname}' in cluster_info",
                    )
                    continue
                vals = [blankish(v) for v in ci[colname]]
                filled = sum(v is not None for v in vals)
                constant_at = []
                by_level: dict = {}
                for lvl in levels:  # hierarchy order: coarsest first
                    namecol = LEVEL_COL.get(lvl, lvl)
                    if namecol not in ci.columns:
                        continue
                    byname: dict = {}
                    constant = True
                    for nm, v in zip(ci[namecol], vals):
                        if v is None:
                            continue
                        key = str(nm)
                        if byname.setdefault(key, v) != v:
                            constant = False
                            break
                    if constant and len(set(byname.values())) > 1:
                        constant_at.append(lvl)
                        by_level[lvl] = byname
                chosen = constant_at[0] if constant_at else None
                plain_levels[s_] = {chosen} if chosen else set()
                # name -> first non-empty value, verified constant within the
                # level. Reading the current row instead would lose a taxon
                # whose first cluster row happens to be blank.
                plain_values[s_] = by_level.get(chosen, {})
                if chosen:
                    note = (
                        f"constant within '{chosen}'; attached there "
                        f"(coarsest of {constant_at}). "
                        f"{filled}/{len(vals)} cluster rows populated"
                    )
                    # A sparse column is constant at coarse levels by accident:
                    # absent values constrain nothing. Say so rather than let
                    # the choice look better evidenced than it is.
                    if filled * 2 < len(vals):
                        note += (
                            " -- SPARSE (<50%), so the level may be an artifact "
                            "of missing values rather than real scope; review"
                        )
                    rep.ok(f"CellTypeTaxon.{s_}", taxon_slots[s_]["loc"], note)
                else:
                    rep.deviate(
                        f"CellTypeTaxon.{s_}",
                        taxon_slots[s_]["loc"],
                        "not attached",
                        "varies within every annotation level, or has a single "
                        "value throughout, so it describes no one taxon; skipped",
                    )
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
                                elif accepts(
                                    "CellTypeTaxon",
                                    s,
                                    str(val),
                                    rep,
                                    taxon_slots[s]["loc"],
                                    rejected,
                                ):
                                    a[s] = str(val)
                        # recorded once per slot, below
                    for s, colname in plain_cols.items():
                        if (
                            lvl not in plain_levels.get(s, ())
                            or colname not in ci.columns
                        ):
                            continue
                        val = plain_values.get(s, {}).get(nm)
                        if val is None:
                            continue
                        sep = taxon_slots[s].get("sep", "")
                        parts = split_values(val, sep)
                        parts = [
                            x
                            for x in parts
                            if accepts(
                                "CellTypeTaxon",
                                s,
                                x,
                                rep,
                                taxon_slots[s]["loc"],
                                rejected,
                            )
                        ]
                        if s == "curated_markers":
                            parts = resolve_markers(parts, gene_index, marker_report)
                        if not parts:
                            continue
                        a[s] = parts if MULTI.get(("CellTypeTaxon", s)) else parts[0]

                    if li > 0:
                        pn = str(row[LEVEL_COL.get(levels[li - 1], levels[li - 1])])
                        if (levels[li - 1], pn) in taxon_ids:
                            a["has_parent"] = taxon_ids[(levels[li - 1], pn)]
                    if want_counts and counts_by_level.get(lvl, {}).get(nm):
                        a["number_of_cells"] = counts_by_level[lvl][nm]
                    # cell_type_ontology_term is the declared AIT source field
                    # and stays a literal; asserting the same CL term through
                    # a SKOS slot as well is what makes it a node that resolves
                    # against the Cell Ontology. Kept rather than replaced, so
                    # the mapping back to the source column remains explicit.
                    cl = a.get("cell_type_ontology_term")
                    if cl:
                        terms = cl if isinstance(cl, list) else [cl]
                        terms = [
                            v for v in terms if v.split(":")[0] in ONTOLOGY_PREFIXES
                        ]
                        if terms:
                            a[ONTOLOGY_PREDICATE] = terms
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

    # ---- curated_markers: what the gene lookup did ------------------------
    resolved, unresolved = marker_report["resolved"], marker_report["unresolved"]
    if resolved:
        rep.ok(
            "CellTypeTaxon.curated_markers",
            "(external: gene annotation)",
            f"{sum(resolved.values())} symbol(s) linked to GeneAnnotation "
            f"({', '.join(f'{k}={v}' for k, v in sorted(resolved.items()))})",
        )
    for s_, how in sorted(marker_report.get("weaker", {}).items()):
        rep.deviate(
            "CellTypeTaxon.curated_markers",
            "(external: gene annotation)",
            f"{s_!r} linked by {how}",
            "no exact symbol match; matched on a weaker tier, review",
        )
    for s_, why in sorted(unresolved.items()):
        rep.deviate(
            "CellTypeTaxon.curated_markers",
            "uns.cluster_info.curated_markers",
            f"{s_!r} not linked",
            f"{why}; left out, since the slot holds GeneAnnotation links",
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


def _one_gene_annotation(ctx, param, value):
    """Accept the option at most once: one h5ad, one genome annotation.

    Click would otherwise keep the last of several silently."""
    if len(value) > 1:
        raise click.BadParameter(
            f"give one genome annotation, the taxonomy's species; got {len(value)}"
        )
    return value[0] if value else None


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
    "--abbreviations",
    default=None,
    help="abbreviation table (CSV) supplying Abbreviation meaning/entity_type/"
    "xref: a path, or a bundled name such as 'hmba-basalganglia'. Tables are "
    "taxonomy-specific, so none is used unless named.",
)
@click.option(
    "--context",
    default=str(CONTEXT),
    show_default=False,
    help="JSON-LD context [default: the copy packaged with bkbit]",
)
@click.option(
    "--gene_annotation",
    type=click.Path(exists=True, dir_okay=False),
    multiple=True,
    callback=_one_gene_annotation,
    help="The genome annotation for this taxonomy's species: one bkbit "
    "gff2jsonld output, Turtle or JSON-LD. curated_markers are linked to its "
    "GeneAnnotation IRIs and gene_annotation_version is set from it. Its "
    "species must match organism_ontology_term_id. Without it curated_markers "
    "is left out, since the slot holds links, not symbols.",
)
def ait2jsonld(
    path, out, report, species, counts, cache, abbreviations, context, gene_annotation
):
    """Translate an AIT .h5ad taxonomy into Cell Taxonomy JSON-LD.

    PATH is a local path or an http(s)/s3 URL. Remote files are read over range
    requests -- a 332 GB file needs no download.
    """
    ents, rep = build(
        path,
        species,
        want_counts=counts,
        cache_dir=cache,
        abbreviations=abbreviations,
        gene_annotation=gene_annotation,
    )
    guard_links(ents, rep, context)
    click.echo(f"--- {species or path} ---")
    for k, v in rep.counts.items():
        click.echo(f"  {k:<20} {v}")
    s = rep.to_dict()["summary"]
    click.echo(
        f"  resolved={s['resolved']} deviations={s['deviations']} "
        f"unpopulated={s['unpopulated']}"
    )

    if out:
        # ensure_ascii=False keeps non-ASCII readable in the output -- a
        # citation like "Munoz-Manchado" should render as written rather than
        # as \u00f1 escapes. Both are valid JSON; this one is legible.
        # The encoding is pinned rather than left to the locale.
        Path(out).write_text(
            json.dumps(
                to_jsonld(ents, context), indent=2, default=str, ensure_ascii=False
            ),
            encoding="utf-8",
        )
        click.echo(f"  wrote {out}")
    if report:
        Path(report).write_text(
            json.dumps(rep.to_dict(), indent=2, default=str, ensure_ascii=False),
            encoding="utf-8",
        )
        click.echo(f"  wrote {report}")


if __name__ == "__main__":
    ait2jsonld()
