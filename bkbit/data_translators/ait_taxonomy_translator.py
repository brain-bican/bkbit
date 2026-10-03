"""
Translate a cell type taxonomy stored in Allen Institute Taxonomy (AIT) format into
BICAN ``cell_taxonomy`` model objects serialized as JSON-LD.

An AIT file is an AnnData ``.h5ad`` file following the schema at
https://github.com/AllenInstitute/AllenInstituteTaxonomy/blob/main/docs/schema.md.
This translator only reads the metadata parts of the file (``uns``, selected ``obs``
columns, ``var`` index, and the keys/shapes of ``obsm``, ``X`` and ``raw``). The
expression matrices are never loaded, so it also works on very large files and on
remote files (http(s):// or s3:// URLs, read through ``fsspec`` range requests).

Mapping from AIT to the cell_taxonomy model:

====================================  ===========================================
AIT component                         cell_taxonomy class
====================================  ===========================================
``uns`` (title, schema_version, ...)  CellTypeTaxonomy
``uns['hierarchy']`` levels           CellTypeSet (one per annotation level)
distinct values of each level         CellTypeTaxon (has_parent -> broader taxon)
``obs['cluster_id']`` categories      Cluster, grouped in one ClusterSet
``X`` / ``raw.X``                     ExpressionMatrix (normalized / raw_count)
``obsm['X_*']``                       Embedding
``obs`` rows (optional)               Cell
====================================  ===========================================

Taxon data that the cell_taxonomy model has no slot for is expressed with the
``bke_taxonomy`` model (the JSON-LD output then uses both models' contexts):

====================================  ===========================================
AIT column                            bke_taxonomy class / slot
====================================  ===========================================
``color_hex_<level>``                 DisplayColor in one ColorPalette
``tokens_<level>`` ("STR|D1|MSN")     Abbreviation + CellTypeTaxon.has_abbreviation
====================================  ===========================================

Columns without a level suffix describe the finest annotation level (e.g. Group):
``curated_markers`` -> CellTypeTaxon.curated_markers_to_primates (or ``_to_mouse``),
``literature_name_short`` -> synonym, ``literature_name_long`` -> full_name.

Per-level taxon attributes are read from columns that follow the HMBA naming
convention, ``<prefix>_<level in lower case>`` (e.g. ``accession_subclass``,
``display_order_subclass``, ``CL:ID_subclass``). See ``LEVEL_ATTRIBUTE_COLUMNS``.

Example:
    >>> taxonomy = AITTaxonomy("Human_HMBA_basalganglia_AIT_pre-print.h5ad")
    >>> taxonomy.parse()
    >>> taxonomy.serialize_to_jsonld("human_bg_taxonomy.jsonld")
"""

import json
import logging
import re
from collections import Counter, defaultdict

import click
import numpy as np
import pandas as pd

from bkbit.models import bke_taxonomy as bt
from bkbit.models import cell_taxonomy as ct
from bkbit.utils.generate_bkbit_id import generate_object_id
from bkbit.utils.serialize_to_ttl import convert_jsonld_to_ttl

logger = logging.getLogger(__name__)

CELL_TAXONOMY_CONTEXT = "https://raw.githubusercontent.com/brain-bican/models/main/jsonld-context-autogen/cell_taxonomy.context.jsonld"
BKE_TAXONOMY_CONTEXT = "https://raw.githubusercontent.com/brain-bican/models/main/jsonld-context-autogen/bke_taxonomy.context.jsonld"

# AIT requires `cluster_id` in obs and as the finest level of uns['hierarchy'].
CLUSTER_LEVEL = "cluster_id"

# CellTypeTaxon slot -> candidate obs/cluster_info column templates; `{level}` is the
# annotation level name in lower case. The first column present in the file is used.
LEVEL_ATTRIBUTE_COLUMNS = {
    "accession_id": ["accession_{level}", "{level}_accession", "{level}_label"],
    "order": ["display_order_{level}", "{level}_order", "order_{level}"],
    "cell_type_ontology_term_id": [
        "CL:ID_{level}",
        "CL_ID_{level}",
        "cell_type_ontology_term_id_{level}",
        "{level}_cell_type_ontology_term_id",
    ],
}

# Per-level columns expressed with the bke_taxonomy model (same template rules).
LEVEL_BKE_COLUMNS = {
    "color_hex_triplet": ["color_hex_{level}", "{level}_color_hex"],
    "tokens": ["tokens_{level}", "{level}_tokens"],
}

# CellTypeTaxon slot -> column without a level suffix; it describes the finest
# annotation level. curated_markers is resolved to the _to_primates/_to_mouse slot.
FINEST_LEVEL_COLUMNS = {
    "curated_markers": "curated_markers",
    "synonym": "literature_name_short",
    "full_name": "literature_name_long",
}

MOUSE_TAXON = "NCBITaxon:10090"
TOKEN_SEPARATOR = "|"

# Cell slot -> obs column. part_of_cluster and cluster_id are set separately.
CELL_OBS_COLUMNS = {
    "load_id": "load_id",
    "assay": "assay",
    "assay_ontology_term_id": "assay_ontology_term_id",
    "anatomical_region": "anatomical_region",
    "anatomical_region_ontology_term_id": "anatomical_region_ontology_term_id",
    "brain_region_ontology_term_id": "brain_region_ontology_term_id",
    "suspension_type": "suspension_type",
    "is_primary_data": "is_primary_data",
}

# uns keys that are read; everything else in uns (mapping statistics, QC data, ...)
# is never loaded.
UNS_KEYS = (
    "title",
    "schema_version",
    "batch_condition",
    "cluster_algorithm",
    "hierarchy",
    "mode",
    "filter",
    "default_embedding",
    "dataset_purl",
    "dendrogram",
    "dend",
    "cellannotation_schema",
    "cluster_info",
)

CL_TERM_PATTERN = re.compile(r"^CL:\d{7}$")
HEX_COLOR_PATTERN = re.compile(r"^#[0-9a-fA-F]{6}$")
URL_PATTERN = re.compile(r"^(https?|s3|ftp)://", re.IGNORECASE)


def _read_elem(elem):
    """Read an h5py group/dataset written by anndata into its python representation."""
    try:
        from anndata.io import read_elem
    except ImportError:  # anndata < 0.11
        from anndata.experimental import read_elem
    return read_elem(elem)


def _open_h5(path):
    """Open a local or remote (http(s)://, s3://, ...) h5ad file with h5py."""
    import h5py

    if "://" not in str(path):
        return h5py.File(path, "r")
    try:
        import fsspec
    except ImportError as e:
        raise ImportError(
            "Reading remote AIT files requires fsspec (and aiohttp for http(s) URLs): "
            "pip install 'fsspec[http]'"
        ) from e
    kwargs = (
        {"client_kwargs": {"trust_env": True}} if str(path).startswith("http") else {}
    )
    fs, fs_path = fsspec.core.url_to_fs(str(path), **kwargs)
    # blockcache keeps the many small HDF5 metadata reads from turning into one
    # request each.
    handle = fs.open(fs_path, "rb", block_size=2 * 1024 * 1024, cache_type="blockcache")
    return h5py.File(handle, "r")


def _is_missing(value):
    if value is None:
        return True
    if isinstance(value, str):
        return value.strip() == ""
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def _to_python(value):
    """Convert numpy scalars/arrays (as returned by anndata) to plain python objects."""
    if isinstance(value, bytes):
        return value.decode()
    if isinstance(value, np.generic):
        return value.item()
    if isinstance(value, np.ndarray):
        return [_to_python(v) for v in value.tolist()]
    if isinstance(value, pd.DataFrame):
        return json.loads(value.to_json(orient="split"))
    if isinstance(value, dict):
        return {str(k): _to_python(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_python(v) for v in value]
    return value


def _to_json_string(value):
    """Serialize a (possibly already JSON-encoded) uns value to a JSON string."""
    value = _to_python(value)
    if isinstance(value, str):
        return value
    return json.dumps(value)


def _to_bool(value):
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in ("true", "t", "1", "yes"):
            return True
        if lowered in ("false", "f", "0", "no"):
            return False
    return None


class AITTaxonomy:
    """
    Reads a cell type taxonomy in AIT (h5ad) format and generates cell_taxonomy objects.

    Args:
        h5ad_path (str): Path or URL of the AIT .h5ad file.
        mode (str, optional): Taxonomy mode to translate. Defaults to ``uns['mode']``,
            or "standard" if unset. Cells flagged by ``uns['filter'][mode]`` are
            excluded from cell counts, clusters, and (optional) Cell objects.
        include_cells (bool): Also generate one Cell object per (unfiltered) obs row.
            Off by default since taxonomies routinely hold millions of cells.
        include_variables (bool): List every gene (var index) in
            ExpressionMatrix.has_variable. Off by default to keep the output small.
        taxonomy_accession (str, optional): Accession ID for the taxonomy
            (e.g. "CCN20250428"); AIT files do not store one.
        abbreviation_file (str, optional): CSV giving the meaning of abbreviation
            tokens, in the format used by ``taxonomy2jsonld`` (columns ``token``,
            ``meaning``, ``type`` and optionally ``primary_identifier`` and
            ``secondary_identifier``). AIT files store only the tokens themselves.
    """

    def __init__(
        self,
        h5ad_path,
        mode=None,
        include_cells=False,
        include_variables=False,
        taxonomy_accession=None,
        abbreviation_file=None,
    ):
        self.h5ad_path = str(h5ad_path)
        self.requested_mode = mode
        self.include_cells = include_cells
        self.include_variables = include_variables
        self.taxonomy_accession = taxonomy_accession
        self.abbreviation_meanings = (
            self._read_abbreviation_file(abbreviation_file) if abbreviation_file else {}
        )

        self.uns = {}
        self.mode = None
        self.levels = []  # annotation levels ordered broad -> fine, without cluster_id
        self.taxonomy = None
        self.cluster_set = None
        self.cell_type_sets = {}  # level -> CellTypeSet
        self.cell_type_taxa = {}  # (level, name) -> CellTypeTaxon
        self.clusters = {}  # cluster label -> Cluster
        self.expression_matrices = []
        self.embeddings = []
        self.cells = []
        # bke_taxonomy objects and slots
        self.color_palette = None
        self.display_colors = []
        self.abbreviations = {}  # token -> Abbreviation
        self.taxon_bke_slots = {}  # CellTypeTaxon id -> {bke_taxonomy slot: value}

    # ------------------------------------------------------------------ reading

    def parse(self):
        """Read the AIT file and generate all cell_taxonomy objects."""
        with _open_h5(self.h5ad_path) as h5:
            self.uns = self._read_uns(h5)
            self.levels = self._annotation_levels()
            self.mode = self._resolve_mode()
            keep = self._cell_filter(h5)

            obs_cluster_ids = self._read_obs_column(h5, CLUSTER_LEVEL)
            if keep is not None:
                obs_cluster_ids = obs_cluster_ids[keep]
            cluster_sizes = Counter(obs_cluster_ids.astype(str))

            cluster_table = self._cluster_table(h5)
            # Drop clusters that the mode filters out entirely.
            cluster_table = cluster_table[
                cluster_table[CLUSTER_LEVEL].isin(cluster_sizes.keys())
            ]

            self._generate_taxonomy()
            self._generate_cell_type_sets()
            self._generate_taxa(cluster_table, cluster_sizes)
            self._generate_clusters(cluster_table, cluster_sizes)
            self._generate_expression_matrices(h5)
            self._generate_embeddings(h5)
            if self.include_cells:
                self._generate_cells(h5, keep)

        self.taxonomy.has_expression_matrix = [
            m.id for m in self.expression_matrices
        ] or None
        self.taxonomy.has_embedding = [e.id for e in self.embeddings] or None
        return self

    def _read_uns(self, h5):
        if "uns" not in h5:
            raise ValueError(f"{self.h5ad_path} has no 'uns' group; not an AIT file.")
        return {key: _read_elem(h5["uns"][key]) for key in UNS_KEYS if key in h5["uns"]}

    def _annotation_levels(self):
        hierarchy = self.uns.get("hierarchy")
        if not hierarchy:
            raise ValueError(
                "uns['hierarchy'] is missing or empty; it is REQUIRED by the AIT schema."
            )
        ordered = sorted(
            ((str(level), int(_to_python(rank))) for level, rank in hierarchy.items()),
            key=lambda item: item[1],
        )
        levels = [level for level, _ in ordered if level != CLUSTER_LEVEL]
        if not levels:
            logger.warning(
                "uns['hierarchy'] has no annotation levels above cluster_id."
            )
        return levels

    def _resolve_mode(self):
        file_mode = _to_python(self.uns.get("mode")) or "standard"
        return self.requested_mode or file_mode

    def _cell_filter(self, h5):
        """Return a boolean mask of cells to keep for the active mode, or None for all."""
        filters = self.uns.get("filter")
        if not filters:
            return None
        if self.mode not in filters:
            if self.requested_mode:
                raise ValueError(
                    f"Mode '{self.mode}' not found in uns['filter'] "
                    f"(available: {sorted(filters)})."
                )
            return None
        mode_filter = np.asarray(filters[self.mode]).astype(bool)
        if mode_filter.ndim == 0:
            # A scalar flag applies to every cell; AIT stores `False` for the
            # unfiltered "standard" mode.
            if mode_filter:
                raise ValueError(f"Mode '{self.mode}' filters out every cell.")
            return None
        n_obs = self._n_obs(h5)
        if mode_filter.shape[0] != n_obs:
            raise ValueError(
                f"uns['filter']['{self.mode}'] has {mode_filter.shape[0]} entries "
                f"but obs has {n_obs} cells."
            )
        return ~mode_filter

    @staticmethod
    def _n_obs(h5):
        obs = h5["obs"]
        return obs[obs.attrs["_index"]].shape[0]

    @staticmethod
    def _read_obs_column(h5, column):
        obs = h5["obs"]
        if column not in obs:
            raise ValueError(f"obs has no '{column}' column.")
        values = _read_elem(obs[column])
        return pd.Series(np.asarray(values, dtype=object))

    def _cluster_table(self, h5):
        """
        One row per cluster with the annotation levels and per-level attribute columns.

        Uses uns['cluster_info'] when it carries cluster_id and every annotation level;
        otherwise derives it from the corresponding obs columns.
        """
        cluster_info = self.uns.get("cluster_info")
        required = [CLUSTER_LEVEL] + self.levels
        if isinstance(cluster_info, pd.DataFrame) and all(
            c in cluster_info.columns for c in required
        ):
            table = cluster_info.reset_index(drop=True)
        else:
            available = set(h5["obs"].keys())
            columns = [c for c in required if c in available]
            columns += [
                c
                for level in self.levels
                for templates in (LEVEL_ATTRIBUTE_COLUMNS, LEVEL_BKE_COLUMNS)
                for c in self._attribute_columns(level, available, templates).values()
            ]
            columns += [
                c
                for c in [*FINEST_LEVEL_COLUMNS.values(), "organism_ontology_term_id"]
                if c in available
            ]
            table = pd.DataFrame(
                {c: self._read_obs_column(h5, c) for c in dict.fromkeys(columns)}
            )
        table = table.astype(object)
        table[CLUSTER_LEVEL] = table[CLUSTER_LEVEL].astype(str)
        return table.drop_duplicates(subset=CLUSTER_LEVEL).reset_index(drop=True)

    @staticmethod
    def _attribute_columns(level, columns, column_templates=LEVEL_ATTRIBUTE_COLUMNS):
        """Map slot -> column name present in `columns` for `level`."""
        found = {}
        for slot, templates in column_templates.items():
            for template in templates:
                column = template.format(level=level.lower())
                if column in columns:
                    found[slot] = column
                    break
        return found

    # --------------------------------------------------------------- generating

    def _object_id(self, kind, **key):
        return generate_object_id(
            {
                "class": kind,
                "taxonomy": self.taxonomy.id if self.taxonomy else None,
                **key,
            }
        )

    def _generate_taxonomy(self):
        uns = self.uns
        title = _to_python(uns.get("title"))
        attributes = {
            "name": title,
            "title": title,
            "accession_id": self.taxonomy_accession,
            "schema_version": _to_python(uns.get("schema_version")),
            "mode": self.mode,
            "default_embedding": _to_python(uns.get("default_embedding")) or None,
        }
        batch_condition = _to_python(uns.get("batch_condition"))
        if batch_condition:
            attributes["batch_condition"] = (
                ",".join(batch_condition)
                if isinstance(batch_condition, list)
                else batch_condition
            )
        if "cluster_algorithm" in uns:
            attributes["cluster_algorithm"] = _to_json_string(uns["cluster_algorithm"])
        if "hierarchy" in uns:
            attributes["hierarchy"] = json.dumps(
                {str(k): int(_to_python(v)) for k, v in uns["hierarchy"].items()}
            )
        filters = uns.get("filter")
        if filters and self.mode in filters and np.ndim(filters[self.mode]) == 0:
            attributes["filter"] = bool(filters[self.mode])
        dendrogram = uns.get("dendrogram")
        if dendrogram is None and isinstance(uns.get("dend"), dict):
            dendrogram = uns["dend"].get(self.mode)
        if dendrogram is not None:
            attributes["dendrogram"] = _to_json_string(dendrogram)
        if "cellannotation_schema" in uns:
            attributes["cellannotation_schema"] = _to_json_string(
                uns["cellannotation_schema"]
            )
        dataset_purl = _to_python(uns.get("dataset_purl"))
        if dataset_purl and URL_PATTERN.match(dataset_purl):
            attributes["content_url"] = [dataset_purl]

        attributes = {k: v for k, v in attributes.items() if not _is_missing(v)}
        attributes["id"] = generate_object_id(
            {
                "class": "CellTypeTaxonomy",
                "title": title,
                "accession_id": self.taxonomy_accession,
                "schema_version": attributes.get("schema_version"),
                "mode": self.mode,
            }
        )
        self.taxonomy = ct.CellTypeTaxonomy(**attributes)

        self.cluster_set = ct.ClusterSet(
            id=self._object_id("ClusterSet", name=CLUSTER_LEVEL),
            name=f"{title} clusters" if title else CLUSTER_LEVEL,
        )
        self.taxonomy.was_derived_from = [self.cluster_set.id]
        self.color_palette = bt.ColorPalette(
            id=self._object_id("ColorPalette"),
            name=f"{title} color palette" if title else "color palette",
            is_palette_for=self.taxonomy.id,
        )

    def _generate_cell_type_sets(self):
        hierarchy = {
            str(k): int(_to_python(v)) for k, v in self.uns["hierarchy"].items()
        }
        parent = None
        for level in self.levels:
            cell_type_set = ct.CellTypeSet(
                id=self._object_id("CellTypeSet", name=level),
                name=level,
                order=hierarchy[level],
                part_of_taxonomy=self.taxonomy.id,
                has_parent=parent.id if parent else None,
                cell_type_set_type=ct.CellTypeSetType.taxonomic_level,
            )
            self.cell_type_sets[level] = cell_type_set
            parent = cell_type_set

    def _generate_taxa(self, cluster_table, cluster_sizes):
        columns = set(cluster_table.columns)
        missing = [level for level in self.levels if level not in columns]
        if missing:
            raise ValueError(
                f"Annotation level column(s) {missing} not found in the file."
            )

        sizes = cluster_table[CLUSTER_LEVEL].map(cluster_sizes).fillna(0).astype(int)
        marker_slot = self._curated_marker_slot(cluster_table)
        invalid_cl_terms = set()
        parent_level = None
        for level in self.levels:
            attribute_columns = self._attribute_columns(level, columns)
            if level == self.levels[-1]:
                attribute_columns.update(
                    {
                        slot: column
                        for slot, column in FINEST_LEVEL_COLUMNS.items()
                        if column in columns
                    }
                )
            bke_columns = self._attribute_columns(level, columns, LEVEL_BKE_COLUMNS)
            parents = self._parent_names(cluster_table, level, parent_level)
            for name, rows in cluster_table.groupby(level, sort=False, observed=True):
                if _is_missing(name):
                    continue
                name = str(name)
                attributes = {
                    "name": name,
                    "part_of_set": self.cell_type_sets[level].id,
                    "number_of_cells": int(sizes[rows.index].sum()),
                }
                for slot, column in attribute_columns.items():
                    value = self._single_value(rows[column], level, name, column)
                    if _is_missing(value):
                        continue
                    if slot == "order":
                        value = int(value)
                    elif slot == "cell_type_ontology_term_id":
                        value = str(value).strip()
                        if not CL_TERM_PATTERN.match(value):
                            invalid_cl_terms.add(value)
                            continue
                    elif slot == "curated_markers":
                        slot = marker_slot
                        value = [m.strip() for m in str(value).split(",") if m.strip()]
                    elif slot == "synonym":
                        value = [str(value)]
                    else:
                        value = str(value)
                    attributes[slot] = value
                parent_name = parents.get(name)
                if parent_name is not None:
                    attributes["has_parent"] = self.cell_type_taxa[
                        (parent_level, parent_name)
                    ].id
                attributes["id"] = self._object_id(
                    "CellTypeTaxon", level=level, name=name
                )
                taxon = ct.CellTypeTaxon(**attributes)
                self.cell_type_taxa[(level, name)] = taxon
                self._generate_bke_taxon_data(taxon, level, rows, bke_columns)
            parent_level = level
        if invalid_cl_terms:
            logger.warning(
                "Skipped cell type ontology term(s) that are not CL IDs: %s",
                sorted(invalid_cl_terms),
            )

    @staticmethod
    def _curated_marker_slot(cluster_table):
        """curated_markers_to_mouse for mouse taxonomies, else _to_primates."""
        organisms = set()
        if "organism_ontology_term_id" in cluster_table.columns:
            organisms = {
                str(o).strip()
                for o in cluster_table["organism_ontology_term_id"].dropna().unique()
            }
        if organisms == {MOUSE_TAXON}:
            return "curated_markers_to_mouse"
        return "curated_markers_to_primates"

    def _generate_bke_taxon_data(self, taxon, level, rows, bke_columns):
        """Generate the bke_taxonomy DisplayColor/Abbreviation objects of a taxon."""
        if "color_hex_triplet" in bke_columns:
            column = bke_columns["color_hex_triplet"]
            color = self._single_value(rows[column], level, taxon.name, column)
            if not _is_missing(color):
                color = str(color).strip()
                if HEX_COLOR_PATTERN.match(color):
                    self.display_colors.append(
                        bt.DisplayColor(
                            id=self._object_id("DisplayColor", taxon=taxon.id),
                            color_hex_triplet=color,
                            is_color_for_taxon=taxon.id,
                            part_of_palette=self.color_palette.id,
                        )
                    )
                else:
                    logger.warning(
                        "%s '%s' has an invalid hex color '%s'; skipped.",
                        level,
                        taxon.name,
                        color,
                    )
        if "tokens" in bke_columns:
            column = bke_columns["tokens"]
            tokens = self._single_value(rows[column], level, taxon.name, column)
            if not _is_missing(tokens):
                abbreviation_ids = [
                    self._abbreviation(token.strip()).id
                    for token in str(tokens).split(TOKEN_SEPARATOR)
                    if token.strip()
                ]
                if abbreviation_ids:
                    self.taxon_bke_slots[taxon.id] = {
                        "has_abbreviation": list(dict.fromkeys(abbreviation_ids))
                    }

    def _abbreviation(self, token):
        """Return the Abbreviation for `token`, creating it on first use."""
        if token in self.abbreviations:
            return self.abbreviations[token]
        attributes = {"term": token}
        known = self.abbreviation_meanings.get(token)
        if known:
            attributes.update(known)
        attributes["id"] = generate_object_id({"class": "Abbreviation", **attributes})
        self.abbreviations[token] = bt.Abbreviation(**attributes)
        return self.abbreviations[token]

    @staticmethod
    def _read_abbreviation_file(path):
        """Read token -> Abbreviation attributes from a taxonomy2jsonld-style CSV."""
        denotes_slot = {
            bt.AbbreviationEntityType.cell_type.value: "denotes_cell_type",
            bt.AbbreviationEntityType.gene.value: "denotes_gene_annotation",
            bt.AbbreviationEntityType.anatomical.value: "denotes_parcellation_term",
        }
        meanings = {}
        for row in pd.read_csv(path, dtype=str).fillna("").to_dict("records"):
            token = row.get("token", "").strip()
            if not token:
                continue
            attributes = {}
            if row.get("meaning", "").strip():
                attributes["meaning"] = row["meaning"].strip()
            entity_type = row.get("type", "").strip()
            if entity_type in denotes_slot:
                attributes["entity_type"] = entity_type
                identifiers = [
                    row[c].strip()
                    for c in ("primary_identifier", "secondary_identifier")
                    if row.get(c, "").strip()
                ]
                if identifiers:
                    attributes[denotes_slot[entity_type]] = identifiers
            elif entity_type:
                logger.warning(
                    "Unknown abbreviation type '%s' for token '%s'.", entity_type, token
                )
            meanings[token] = attributes
        return meanings

    @staticmethod
    def _parent_names(cluster_table, level, parent_level):
        """Map each taxon name at `level` to the name of its parent at `parent_level`."""
        if parent_level is None:
            return {}
        parents = {}
        pairs = cluster_table[[level, parent_level]].dropna()
        for name, candidates in pairs.groupby(level, sort=False, observed=True)[
            parent_level
        ]:
            counts = candidates.astype(str).value_counts()
            if len(counts) > 1:
                logger.warning(
                    "%s '%s' falls under several %s taxa %s; using '%s'.",
                    level,
                    name,
                    parent_level,
                    list(counts.index),
                    counts.index[0],
                )
            parents[str(name)] = counts.index[0]
        return parents

    @staticmethod
    def _single_value(values, level, name, column):
        # Most frequent value wins; ties go to the value seen first.
        counts = Counter(v for v in values if not _is_missing(v)).most_common()
        if len(counts) > 1:
            logger.warning(
                "%s '%s' has several values in '%s' %s; using '%s'.",
                level,
                name,
                column,
                [v for v, _ in counts],
                counts[0][0],
            )
        return counts[0][0] if counts else None

    def _generate_clusters(self, cluster_table, cluster_sizes):
        finest_level = self.levels[-1] if self.levels else None
        for _, row in cluster_table.iterrows():
            label = row[CLUSTER_LEVEL]
            parent = None
            if finest_level and not _is_missing(row[finest_level]):
                parent = self.cell_type_taxa[(finest_level, str(row[finest_level]))].id
            self.clusters[label] = ct.Cluster(
                id=self._object_id("Cluster", name=label),
                name=label,
                part_of_set=self.cluster_set.id,
                has_parent=[parent] if parent else None,
                number_of_observations=cluster_sizes.get(label, 0),
            )

    def _generate_expression_matrices(self, h5):
        variables = None
        if self.include_variables and "var" in h5:
            var = h5["var"]
            variables = [str(v) for v in _read_elem(var[var.attrs["_index"]])]
        content_url = _to_python(self.uns.get("dataset_purl"))
        content_url = (
            [content_url] if content_url and URL_PATTERN.match(content_url) else None
        )

        locations = [
            ("X", ct.ExpressionMatrixType.normalized),
            ("raw/X", ct.ExpressionMatrixType.raw_count),
        ]
        for location, matrix_type in locations:
            if location not in h5:
                continue
            shape = self._matrix_shape(h5[location])
            embedded = shape is not None and 0 not in shape
            if not embedded and not content_url:
                continue
            description = f"AIT {location}" + (
                f" ({shape[0]} cells x {shape[1]} genes)" if embedded else ""
            )
            matrix = ct.ExpressionMatrix(
                id=self._object_id("ExpressionMatrix", location=location),
                name=f"{self.taxonomy.name} {location}",
                description=description,
                matrix_type=matrix_type,
                has_variable=variables,
                content_url=None if embedded else content_url,
            )
            self.expression_matrices.append(matrix)

    @staticmethod
    def _matrix_shape(elem):
        if "shape" in elem.attrs:
            return tuple(int(s) for s in elem.attrs["shape"])
        if hasattr(elem, "shape"):
            return tuple(elem.shape)
        return None

    def _generate_embeddings(self, h5):
        if "obsm" not in h5:
            return
        for key in h5["obsm"].keys():
            if not key.startswith("X_"):
                continue
            shape = self._matrix_shape(h5["obsm"][key])
            self.embeddings.append(
                ct.Embedding(
                    id=self._object_id("Embedding", embedding_key=key),
                    name=key[2:],
                    embedding_key=key,
                    description=(
                        f"{shape[1]}-dimensional embedding"
                        if shape and len(shape) == 2
                        else None
                    ),
                )
            )

    def _generate_cells(self, h5, keep):
        obs = h5["obs"]
        available = set(obs.keys())
        index = self._read_obs_column(h5, obs.attrs["_index"])
        cluster_ids = self._read_obs_column(h5, CLUSTER_LEVEL)
        columns = {
            slot: self._read_obs_column(h5, column)
            for slot, column in CELL_OBS_COLUMNS.items()
            if column in available
        }
        if keep is not None:
            index, cluster_ids = index[keep], cluster_ids[keep]
            columns = {slot: values[keep] for slot, values in columns.items()}
        suspension_types = {t.value for t in ct.SuspensionType}

        for i, cell_label in enumerate(index):
            cluster_label = str(cluster_ids.iloc[i])
            attributes = {
                "id": self._object_id("Cell", name=str(cell_label)),
                "name": str(cell_label),
                "cluster_id": cluster_label,
                "part_of_cluster": (
                    self.clusters[cluster_label].id
                    if cluster_label in self.clusters
                    else None
                ),
            }
            for slot, values in columns.items():
                value = values.iloc[i]
                if _is_missing(value):
                    continue
                if slot == "is_primary_data":
                    value = _to_bool(value)
                elif slot == "suspension_type":
                    value = str(value) if str(value) in suspension_types else None
                else:
                    value = str(value)
                attributes[slot] = value
            self.cells.append(
                ct.Cell(**{k: v for k, v in attributes.items() if v is not None})
            )

    # ------------------------------------------------------------ serializing

    def all_objects(self):
        """All generated objects (cell_taxonomy and bke_taxonomy), taxonomy first."""
        objects = [self.taxonomy, self.cluster_set]
        objects += list(self.cell_type_sets.values())
        objects += list(self.cell_type_taxa.values())
        objects += list(self.clusters.values())
        objects += self.expression_matrices
        objects += self.embeddings
        if self.display_colors:
            objects += [self.color_palette, *self.display_colors]
        objects += list(self.abbreviations.values())
        objects += self.cells
        return [o for o in objects if o is not None]

    def _to_node(self, obj):
        node = obj.model_dump(mode="json", exclude_none=True)
        bke_slots = self.taxon_bke_slots.get(node["id"])
        if bke_slots:
            # Slots the cell_taxonomy CellTypeTaxon lacks are validated against the
            # bke_taxonomy CellTypeTaxon and merged into the same node.
            node.update(
                bt.CellTypeTaxon(id=node["id"], **bke_slots).model_dump(
                    mode="json", exclude_none=True, exclude={"id", "category"}
                )
            )
        return node

    def to_jsonld(self):
        """Return the generated objects as a JSON-LD document (dict)."""
        graph = [self._to_node(o) for o in self.all_objects()]
        uses_bke = bool(self.display_colors or self.abbreviations)
        return {
            # cell_taxonomy comes last so its term definitions take precedence.
            "@context": (
                [BKE_TAXONOMY_CONTEXT, CELL_TAXONOMY_CONTEXT]
                if uses_bke
                else CELL_TAXONOMY_CONTEXT
            ),
            "@graph": graph,
        }

    def serialize_to_jsonld(self, output_file=None, output_format="jsonld"):
        """
        Serialize the generated objects as JSON-LD (or Turtle).

        Args:
            output_file (str, optional): File to write to. Returns the string if None.
            output_format (str): "jsonld" or "turtle".
        """
        output = json.dumps(self.to_jsonld(), indent=2)
        if output_format == "turtle":
            output = convert_jsonld_to_ttl(output)
        if output_file is None:
            return output
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(output)
        return None


@click.command()
## ARGUMENTS ##
# Argument: path or URL of the AIT h5ad file
@click.argument("h5ad_file", type=str)
## OPTIONS ##
@click.option(
    "--output_file",
    "-o",
    type=click.Path(),
    default=None,
    help="The output file path. Prints to stdout if not given.",
)
@click.option(
    "--output_format",
    "-f",
    type=click.Choice(["jsonld", "turtle"]),
    default="jsonld",
    show_default=True,
    help="The output format.",
)
@click.option(
    "--mode",
    "-m",
    type=str,
    default=None,
    help="Taxonomy mode to translate. Defaults to the mode stored in uns['mode'].",
)
@click.option(
    "--taxonomy_accession",
    "-a",
    type=str,
    default=None,
    help="Accession ID to assign to the taxonomy (e.g. CCN20250428).",
)
@click.option(
    "--abbreviation_file",
    "-b",
    type=click.Path(exists=True),
    default=None,
    help="CSV with the meaning of abbreviation tokens "
    "(columns: token, meaning, type, primary_identifier, secondary_identifier).",
)
@click.option(
    "--include_cells",
    is_flag=True,
    help="Also generate a Cell object for every cell in obs (can be very large).",
)
@click.option(
    "--include_variables",
    is_flag=True,
    help="List every gene of the var index in ExpressionMatrix.has_variable.",
)
def ait2jsonld(
    h5ad_file,
    output_file,
    output_format,
    mode,
    taxonomy_accession,
    abbreviation_file,
    include_cells,
    include_variables,
):
    """
    Generate cell_taxonomy objects from a taxonomy in AIT (h5ad) format.

    H5AD_FILE is a local path or a URL (http(s)://, s3://). Only metadata is read,
    so remote files are not downloaded in full.
    """
    taxonomy = AITTaxonomy(
        h5ad_file,
        mode=mode,
        include_cells=include_cells,
        include_variables=include_variables,
        taxonomy_accession=taxonomy_accession,
        abbreviation_file=abbreviation_file,
    ).parse()
    output = taxonomy.serialize_to_jsonld(output_file, output_format)
    if output is not None:
        click.echo(output)


if __name__ == "__main__":
    ait2jsonld()
