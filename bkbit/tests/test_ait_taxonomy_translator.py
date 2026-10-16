"""Offline tests for the AIT taxonomy translator.

Nothing here touches the network: the expensive part of ait2jsonld is reading a
remote .h5ad, and that is exercised by running the CLI against a real file. What
is worth pinning down in CI is the part that silently produces a wrong-but-valid
graph if it regresses -- the id scheme and the annotation lookup.
"""

import click
import pytest

from bkbit.data_translators import ait_taxonomy_translator as t
from bkbit.utils.generate_bkbit_id import generate_object_id


class TestObjectIds:
    """ids must stay byte-identical to every other bkbit translator."""

    def test_matches_bkbit_scheme(self):
        attrs = {"name": "Glut", "part_of_set": "urn:bkbit:abc"}
        assert t.oid("CellTypeTaxon", attrs) == generate_object_id(attrs)

    def test_class_name_is_not_hashed(self):
        # The class is taken for readability at the call site only. If it ever
        # starts contributing to the digest, this translator's ids fork away
        # from taxonomy2jsonld and the two can never be merged.
        attrs = {"name": "Glut"}
        assert t.oid("CellTypeTaxon", attrs) == t.oid("Cluster", attrs)

    def test_id_key_is_excluded(self):
        # build() assigns attrs["id"] after minting; re-minting from a dict that
        # already carries one must not change the answer.
        attrs = {"name": "Glut"}
        with_id = {**attrs, "id": "urn:bkbit:stale"}
        assert t.oid("CellTypeTaxon", with_id) == t.oid("CellTypeTaxon", attrs)

    def test_key_order_does_not_matter(self):
        a = {"name": "Glut", "part_of_set": "x"}
        b = {"part_of_set": "x", "name": "Glut"}
        assert t.oid("CellTypeTaxon", a) == t.oid("CellTypeTaxon", b)

    def test_prefix(self):
        assert t.oid("Cluster", {"name": "1"}).startswith("urn:bkbit:")


# The ait_location annotations were added to the model on 2026-10-01. An older
# bkbit/models/cell_taxonomy.py has none, and these tests cannot say anything
# useful -- skip with a pointer rather than fail the suite for an unrelated
# reason.
_HAS_ANNOTATIONS = any(
    "ait_location"
    in ((f.json_schema_extra or {}).get("linkml_meta", {}).get("annotations") or {})
    for _n, cls in t._model_classes()
    for f in cls.model_fields.values()
)
needs_current_model = pytest.mark.skipif(
    not _HAS_ANNOTATIONS,
    reason="bkbit.models.cell_taxonomy predates the ait_location annotations; "
    "refresh it via the models repo's push_model_to_bkbit.yaml workflow",
)


@needs_current_model
class TestLocationsFromPydantic:
    """Locations come from the generated model, so no LinkML YAML has to ship."""

    def test_locations_resolve(self):
        locs = t.load_locations()
        assert locs, "no ait_location annotations found in the generated model"

    def test_known_locations_present(self):
        locs = t.load_locations()
        by_slot = {slot: v["loc"] for (_cls, slot), v in locs.items()}
        assert by_slot.get("title") == "uns.title"

    def test_matrix_location_is_declared(self):
        """cluster_id_mean_expr is declared in varm; the translator reports it
        as not materialised instead of skipping it silently."""
        locs = t.load_locations()
        loc = locs[("CellTypeTaxonomy", "cluster_id_mean_expr")]["loc"]
        p = t.parse_loc(loc)
        assert p["kind"] == "path" and p["surface"] in t.MATRIX_GROUPS

    def test_separator_captured(self):
        """ait_separator rides along with ait_location, and is the only other
        annotation the pipeline consumes. The sheet's Notes and Source columns
        are deliberately mapped to ignore, so they never reach the model."""
        locs = t.load_locations()
        assert any(v["sep"] for v in locs.values())
        assert not any(set(v) - {"loc", "sep"} for v in locs.values())


def test_stale_model_fails_loudly(monkeypatch):
    """A model without the annotations must raise, not quietly emit a graph
    with every field unpopulated."""
    monkeypatch.setattr(t, "_model_classes", lambda: iter(()))
    with pytest.raises(click.ClickException) as err:
        t.load_locations()
    assert "push_model_to_bkbit" in str(err.value)


class TestCardinality:
    def test_is_per_class_not_per_slot_name(self):
        mv = t.multivalued_map()
        assert mv, "no fields found in the generated model"
        # Read off the generated field types; a bare value and a list must not
        # collapse to one answer keyed by slot name alone.
        assert all(isinstance(v, bool) for v in mv.values())


def test_strip_class_is_stable_across_entity_types():
    """Dropping the class from the digest was checked against all 13 released
    AIT files for cross-class collisions; none exist. This guards the much
    weaker property that two genuinely distinct entities still differ."""
    a = t.oid("CellTypeTaxon", {"name": "Glut", "part_of_set": "s1"})
    b = t.oid("CellTypeTaxon", {"name": "GABA", "part_of_set": "s1"})
    assert a != b


def test_module_imports_without_h5py(monkeypatch):
    """cli.py imports this module to register the command, so a missing h5py
    must not take down `bkbit --help` along with it -- the same failure mode
    CLAUDE.md records for the NCBI taxonomy cache."""
    import importlib

    import bkbit.data_translators.ait_taxonomy_translator as mod

    real_import = (
        __builtins__["__import__"]
        if isinstance(__builtins__, dict)
        else __builtins__.__import__
    )

    def fake_import(name, *args, **kwargs):
        if name in ("h5py", "anndata", "anndata.io"):
            raise ImportError(f"No module named '{name}'")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr("builtins.__import__", fake_import)
    reloaded = importlib.reload(mod)
    try:
        assert reloaded.h5py is None
        with pytest.raises(click.ClickException) as err:
            reloaded._require_h5_deps()
        assert "h5py" in str(err.value)
    finally:
        monkeypatch.undo()
        importlib.reload(mod)


class TestSplitValues:
    """How a packed cell becomes a multivalued slot is declared in the model,
    via the ait_separator annotation -- never guessed from the data."""

    def test_splits_on_the_declared_separator(self):
        assert t.split_values("a|b|c", "|") == ["a", "b", "c"]
        assert t.split_values("PDGFRA, DCN", ",") == ["PDGFRA", "DCN"]

    def test_no_separator_means_one_value(self):
        # Guessing a delimiter would invent entities: "PDGFRA, DCN" must stay
        # a single value unless the model says otherwise.
        assert t.split_values("PDGFRA, DCN", "") == ["PDGFRA, DCN"]
        assert t.split_values("a|b", None) == ["a|b"]

    def test_strips_and_drops_empties(self):
        assert t.split_values(" a | | b ", "|") == ["a", "b"]

    def test_drops_stringified_nulls(self):
        # cluster_info columns arrive as strings, so a missing value shows up
        # as the text "nan"/"None" rather than as None.
        assert t.split_values("nan", "|") == []
        assert t.split_values("a|None|b", "|") == ["a", "b"]

    def test_handles_none_and_non_str(self):
        assert t.split_values(None, "|") == []
        assert t.split_values(123, "|") == ["123"]


@needs_current_model
def test_separator_is_read_from_annotations():
    """load_locations() must surface ait_separator next to the location, so a
    sheet edit changes splitting with no code change."""
    locs = t.load_locations()
    assert all("sep" in v for v in locs.values())


class TestSourceAsUri:
    """content_url falls back to where the file was actually read from."""

    def test_s3_https_is_rewritten_to_s3_scheme(self):
        # Verified against AIT33, whose own uns.dataset_purl equals exactly the
        # value derived from its https URL.
        got = t.source_as_uri(
            "https://allen-paper-supplements.s3.us-west-2.amazonaws.com"
            "/changkyul_preprint_2025/AIT33.h5ad"
        )
        assert got == "s3://allen-paper-supplements/changkyul_preprint_2025/AIT33.h5ad"

    def test_bucket_name_containing_digits_and_dashes(self):
        got = t.source_as_uri(
            "https://released-taxonomies-802451596237-us-west-2.s3.us-west-2"
            ".amazonaws.com/HMBA/BasalGanglia/x.h5ad"
        )
        assert (
            got
            == "s3://released-taxonomies-802451596237-us-west-2/HMBA/BasalGanglia/x.h5ad"
        )

    def test_existing_s3_uri_passes_through(self):
        assert t.source_as_uri("s3://b/k.h5ad") == "s3://b/k.h5ad"

    def test_non_s3_url_passes_through(self):
        assert (
            t.source_as_uri("https://example.org/x.h5ad")
            == "https://example.org/x.h5ad"
        )

    def test_local_paths_give_nothing(self):
        # A filesystem location is not a permanent URL and must never be
        # published as content_url.
        assert t.source_as_uri("/data/x.h5ad") is None
        assert t.source_as_uri("file:///data/x.h5ad") is None
        assert t.source_as_uri("") is None


class TestValueValidators:
    """Constraints come from the model's own validators, not restated regexes."""

    @needs_current_model
    def test_pattern_validator_is_discovered(self):
        v = t.value_validators("CellTypeTaxon")
        assert "cell_type_ontology_term" in v

    @needs_current_model
    def test_bad_value_is_dropped_not_raised(self):
        rep, seen = t.Report(), set()
        assert (
            t.accepts(
                "CellTypeTaxon", "cell_type_ontology_term", "PR 2579", rep, "loc", seen
            )
            is False
        )
        assert len(rep.deviations) == 1
        assert "dropped rather than raised" in rep.deviations[0]["reason"]

    @needs_current_model
    def test_good_value_passes_silently(self):
        rep, seen = t.Report(), set()
        assert (
            t.accepts(
                "CellTypeTaxon",
                "cell_type_ontology_term",
                "CL:0000003",
                rep,
                "loc",
                seen,
            )
            is True
        )
        assert rep.deviations == []

    @needs_current_model
    def test_repeated_rejection_reported_once(self):
        # 216 placeholder values in one file must not mean 216 report entries.
        rep, seen = t.Report(), set()
        for _ in range(5):
            t.accepts(
                "CellTypeTaxon", "cell_type_ontology_term", "PR 2579", rep, "loc", seen
            )
        assert len(rep.deviations) == 1

    def test_unconstrained_slot_accepts_anything(self):
        rep, seen = t.Report(), set()
        assert t.accepts("CellTypeTaxon", "name", "anything", rep, "loc", seen) is True


def test_blankish_normalises_null_sentinels():
    assert t.blankish(None) is None
    assert t.blankish("nan") is None
    assert t.blankish("None") is None
    assert t.blankish("") is None
    assert t.blankish("  x  ") == "x"


class TestAbbreviationTable:
    """Abbreviation meaning/type/xref come from an opt-in, taxonomy-specific
    table -- the AIT files carry only the bare token."""

    def test_bundled_table_loads(self):
        tbl, _ = t.load_abbreviations("hmba-basalganglia")
        assert len(tbl) == 105
        assert tbl["Glut"] == {
            "meaning": "glutamatergic neuron",
            "entity_type": "cell_type",
            "broad_match": ["CL:0000679"],
        }

    def test_both_identifiers_are_kept_and_routed_by_prefix(self):
        """Ontology terms become a node-valued SKOS mapping; database
        identifiers stay in xref, which is what biolink defines it as."""
        tbl, _ = t.load_abbreviations("hmba-basalganglia")
        assert tbl["F"]["broad_match"] == ["DHBA:10156", "UBERON:0004024"]
        assert "xref" not in tbl["F"]
        # ADARB2 is a gene: ENSEMBL is a database, so it stays put
        assert tbl["ADARB2"]["xref"] == ["ENSEMBL:ENSG00000185736"]
        assert "broad_match" not in tbl["ADARB2"]

    def test_routing_loses_nothing_and_duplicates_nothing(self):
        """Every identifier in the CSV must land in exactly one slot.

        Checked against the file rather than a count, so the test still means
        something if the table is edited.
        """
        import csv

        path = t.BUNDLED_ABBREVIATIONS["hmba-basalganglia"]
        expected = {}
        with path.open(newline="", encoding="utf-8") as fh:
            for row in csv.DictReader(fh):
                term = (row.get("abbreviation_term") or "").strip()
                if not term:
                    continue
                expected[term] = [
                    v
                    for v in (
                        (row.get("primary_identifier") or "").strip(),
                        (row.get("secondary_identifier") or "").strip(),
                    )
                    if v
                ]

        tbl, _ = t.load_abbreviations("hmba-basalganglia")
        for term, ids in expected.items():
            rec = tbl[term]
            routed = list(rec.get("xref", [])) + list(rec.get("broad_match", []))
            assert sorted(routed) == sorted(ids), term

    def test_an_unrecognised_prefix_is_reported_not_swallowed(self, tmp_path):
        """A new ontology must surface, rather than silently becoming an
        unjoinable literal in xref."""
        f = tmp_path / "t.csv"
        f.write_text(
            "abbreviation_term,abbreviation_meaning,abbreviation_type,"
            "primary_identifier,secondary_identifier\n"
            "X,something,anatomical,MBA:12345,\n"
        )
        tbl, unknown = t.load_abbreviations(str(f))
        assert unknown == ["MBA"]
        assert tbl["X"]["xref"] == ["MBA:12345"]

    @needs_current_model
    def test_entity_type_values_match_the_model_enum(self):
        import bkbit.models.cell_taxonomy as ct

        allowed = {e.value for e in ct.AbbreviationEntityType}
        tbl, _ = t.load_abbreviations("hmba-basalganglia")
        used = {v["entity_type"] for v in tbl.values()}
        assert used <= allowed, f"table has types the model rejects: {used - allowed}"

    def test_unknown_name_is_rejected_with_the_known_ones(self):
        with pytest.raises(click.ClickException) as err:
            t.load_abbreviations("no-such-table")
        assert "hmba-basalganglia" in str(err.value)

    def test_missing_columns_are_rejected(self, tmp_path):
        bad = tmp_path / "bad.csv"
        bad.write_text("a,b\n1,2\n")
        with pytest.raises(click.ClickException) as err:
            t.load_abbreviations(str(bad))
        assert "abbreviation_term" in str(err.value)

    def test_blank_terms_are_skipped(self, tmp_path):
        f = tmp_path / "t.csv"
        f.write_text(
            "abbreviation_term,abbreviation_meaning,abbreviation_type,"
            "primary_identifier,secondary_identifier\n"
            ",nothing,gene,,\n"
            "X,something,gene,ENSEMBL:1,\n"
        )
        tbl, _ = t.load_abbreviations(str(f))
        assert list(tbl) == ["X"]


# A minimal gff2jsonld-shaped Turtle file: one taxon, three genes, one symbol
# deliberately duplicated so the ambiguity rule is exercised.
GENE_TTL = """
@prefix bican: <https://identifiers.org/brain-bican/vocab/> .
@prefix biolink: <https://w3id.org/biolink/vocab/> .
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<urn:bkbit:taxon> a biolink:OrganismTaxon ;
    biolink:full_name "Macaca mulatta" ;
    biolink:xref "NCBITaxon:9544"^^xsd:anyURI .
<urn:bkbit:annotation> a bican:GenomeAnnotation ;
    rdfs:label "NCBI-9544-103" .

<urn:bkbit:acta2> a bican:GeneAnnotation ;
    biolink:in_taxon <urn:bkbit:taxon> ; biolink:symbol "ACTA2" .
<urn:bkbit:pou6f2> a bican:GeneAnnotation ;
    biolink:in_taxon <urn:bkbit:taxon> ; biolink:symbol "POU6F2" ;
    biolink:synonym "RPF-1" .
<urn:bkbit:dup1> a bican:GeneAnnotation ;
    biolink:in_taxon <urn:bkbit:taxon> ; biolink:symbol "DUP" .
<urn:bkbit:dup2> a bican:GeneAnnotation ;
    biolink:in_taxon <urn:bkbit:taxon> ; biolink:symbol "DUP" .
"""


@pytest.fixture
def gene_index(tmp_path):
    f = tmp_path / "annotation-NCBI-9544-103.ttl"
    f.write_text(GENE_TTL)
    idx = t.load_gene_annotation(str(f))
    assert (idx.taxon, idx.source, idx.label) == ("9544", f.name, "NCBI-9544-103")
    return idx


@pytest.fixture
def no_network(monkeypatch):
    """Fail any attempt to open a connection (e.g. to fetch a JSON-LD context)."""
    import socket

    def refuse(*args, **kwargs):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket.socket, "connect", refuse)
    monkeypatch.setattr(socket, "create_connection", refuse)


@pytest.fixture
def gff2jsonld_output(tmp_path, monkeypatch):
    """The same gff2jsonld output written as JSON-LD and as Turtle.

    The JSON-LD is what gff2jsonld itself serialises (context by URL); the
    Turtle is that document converted with the bundled context. The GFF3 is
    the offline fixture of the genome annotation tests (pig, NCBITaxon:9823).
    """
    import json

    import rdflib

    from bkbit.data_translators import genome_annotation_translator as gat
    from bkbit.tests import test_genome_annotation_temp_files as gfx

    gfx.offline.__wrapped__(tmp_path, monkeypatch)
    gff3 = gat.Gff3(gfx.NCBI_URL)
    gff3.setup()
    gff3.parse_gff3_file()
    gff3.parse()
    gff3.cleanup()
    jsonld = gff3.serialize_to_jsonld()
    assert json.loads(jsonld)["@context"] == gat.CONTEXT_URL
    out = tmp_path / "out"
    out.mkdir()
    jl = out / "annotation-NCBI-9823-106.jsonld"
    jl.write_text(jsonld)
    ttl = out / "annotation-NCBI-9823-106.ttl"
    g = rdflib.Graph().parse(data=t._jsonld_with_local_context(jl), format="json-ld")
    ttl.write_text(g.serialize(format="turtle"))
    return jl, ttl


class TestGeneAnnotationFile:
    """One annotation file, in either format, gives the same links."""

    def test_jsonld_and_turtle_agree(self, gff2jsonld_output, no_network):
        jl, ttl = gff2jsonld_output
        a, b = t.load_gene_annotation(str(jl)), t.load_gene_annotation(str(ttl))
        assert a.taxon == b.taxon == "9823"
        assert a.label == b.label == "NCBI-9823-106"
        assert dict(a.by_symbol) == dict(b.by_symbol)
        assert sorted(a.by_symbol) == ["ABC1", "XYZ2"]
        gid, tier = a.resolve("ABC1")
        assert tier == "symbol" and gid.startswith("urn:bkbit:")

    def test_jsonld_context_is_not_fetched(self, gff2jsonld_output, no_network):
        # gff2jsonld writes the context by URL; the bundled copy is used.
        jl, _ = gff2jsonld_output
        assert t.load_gene_annotation(str(jl)).taxon == "9823"

    def test_format_comes_from_content(self, tmp_path):
        f = tmp_path / "annotation"  # no extension
        f.write_text(GENE_TTL)
        assert t.gene_annotation_format(f) == "turtle"
        f.write_text('{"@graph": []}')
        assert t.gene_annotation_format(f) == "json-ld"

    def test_mislabelled_file_is_rejected(self, tmp_path):
        f = tmp_path / "annotation.jsonld"
        f.write_text(GENE_TTL)
        with pytest.raises(click.ClickException, match="extension says json-ld"):
            t.load_gene_annotation(str(f))

    def test_several_species_are_rejected(self, tmp_path):
        f = tmp_path / "two.ttl"
        f.write_text(GENE_TTL + """
<urn:bkbit:taxon2> a biolink:OrganismTaxon ; biolink:xref "NCBITaxon:9606" .
<urn:bkbit:x> a bican:GeneAnnotation ;
    biolink:in_taxon <urn:bkbit:taxon2> ; biolink:symbol "X" .
""")
        with pytest.raises(click.ClickException, match="several species"):
            t.load_gene_annotation(str(f))


class TestCuratedMarkerLinks:
    """curated_markers hold GeneAnnotation links, never bare symbols."""

    @pytest.mark.parametrize(
        "value,number",
        [
            ("NCBITaxon:9606", "9606"),
            ("http://purl.obolibrary.org/obo/NCBITaxon_9544", "9544"),
            # the HMBA marmoset file writes it this way
            ("NCBI:txid9483", "9483"),
            ("Homo sapiens", None),
            (None, None),
        ],
    )
    def test_taxon_number(self, value, number):
        assert t.ncbi_taxon_number(value) == number

    def test_tiers(self, gene_index):
        assert gene_index.resolve("ACTA2") == ("urn:bkbit:acta2", "symbol")
        assert gene_index.resolve("Pou6f2") == ("urn:bkbit:pou6f2", "symbol_case")
        assert gene_index.resolve("RPF-1") == ("urn:bkbit:pou6f2", "synonym")

    def test_ambiguous_and_missing_are_not_guessed(self, gene_index):
        gid, why = gene_index.resolve("DUP")
        assert gid is None and why.startswith("ambiguous")
        assert gene_index.resolve("Six3 and Foxp1")[0] is None

    def test_resolve_markers_reports_what_it_cannot_link(self, gene_index):
        tally = {"resolved": t.Counter(), "unresolved": {}}
        out = t.resolve_markers(
            ["ACTA2", "Pou6f2", "Ctip2", "ACTA2"], gene_index, tally
        )
        assert out == ["urn:bkbit:acta2", "urn:bkbit:pou6f2"]
        assert tally["unresolved"] == {"Ctip2": "no gene with this symbol or synonym"}
        assert tally["weaker"] == {"Pou6f2": "symbol_case"}

    def test_no_gene_annotation_emits_nothing(self):
        tally = {"resolved": t.Counter(), "unresolved": {}}
        assert t.resolve_markers(["ACTA2"], None, tally) == []
        assert "ACTA2" in tally["unresolved"]

    def test_non_gene_annotation_file_is_rejected(self, tmp_path):
        f = tmp_path / "empty.ttl"
        f.write_text("<urn:a> <urn:b> <urn:c> .\n")
        with pytest.raises(click.ClickException):
            t.load_gene_annotation(str(f))

    def test_is_link(self):
        prefixes = {"CL", "bican"}
        assert t.is_link("urn:bkbit:abc", prefixes)
        assert t.is_link("http://purl.obolibrary.org/obo/CL_0000128", prefixes)
        assert t.is_link("CL:0000128", prefixes)
        # a bare symbol is a relative IRI reference: it would resolve
        # against the output file's path (file:///.../ACTA2)
        assert not t.is_link("ACTA2", prefixes)
        assert not t.is_link("Six3 and Foxp1", prefixes)
        assert not t.is_link("NOPREFIX:1", prefixes)

    def test_guard_drops_and_reports_relative_links(self):
        ents = {
            "CellTypeTaxon": [
                {
                    "id": "urn:bkbit:t1",
                    "curated_markers": ["urn:bkbit:acta2", "DCN"],
                    "broad_match": ["CL:0000192"],
                },
                {"id": "urn:bkbit:t2", "curated_markers": ["DCN"]},
            ]
        }
        rep = t.Report()
        assert t.guard_links(ents, rep) == 2
        t1, t2 = ents["CellTypeTaxon"]
        assert t1["curated_markers"] == ["urn:bkbit:acta2"]
        assert t1["broad_match"] == ["CL:0000192"]  # an expanded @prefix term
        assert "curated_markers" not in t2
        # reported once per distinct value
        assert [d["actually_read"] for d in rep.deviations] == ["value 'DCN' dropped"]


def _tiny_ait(path, organism="NCBITaxon:9544"):
    """A minimal AIT .h5ad: two Groups, one cluster each, curated markers."""
    import anndata as ad
    import numpy as np
    import pandas as pd

    obs = pd.DataFrame(
        {"cluster_id": pd.Categorical(["c1", "c2"])}, index=["cell1", "cell2"]
    )
    adata = ad.AnnData(X=np.zeros((2, 1), dtype="float32"), obs=obs)
    adata.uns["title"] = "tiny_AIT"
    adata.uns["gene_annotation_version"] = ""
    adata.uns["hierarchy"] = {"Group": 0, "cluster_id": 1}
    adata.uns["cluster_info"] = pd.DataFrame(
        {
            "Group": ["SMC", "Pericyte"],
            "Cluster": ["c1", "c2"],
            "cluster_id": ["c1", "c2"],
            ORGANISM: [organism, organism],
            "curated_markers": ["ACTA2, Pou6f2", "Ctip2"],
        }
    )
    adata.write_h5ad(path)
    return str(path)


ORGANISM = "organism_ontology_term_id"


@needs_current_model
class TestBuildWithGeneAnnotation:
    def test_markers_link_and_version_is_recorded(self, tmp_path, gene_index):
        ann = tmp_path / "annotation-NCBI-9544-103.ttl"  # written by gene_index
        ents, rep = t.build(_tiny_ait(tmp_path / "tiny.h5ad"), gene_annotation=str(ann))
        taxa = {a["name"]: a for a in ents["CellTypeTaxon"]}
        assert taxa["SMC"]["curated_markers"] == ["urn:bkbit:acta2", "urn:bkbit:pou6f2"]
        assert "curated_markers" not in taxa["Pericyte"]  # Ctip2 does not resolve
        (tax,) = ents["CellTypeTaxonomy"]
        assert tax["gene_annotation_version"] == "NCBI-9544-103"
        read = " ".join(d["actually_read"] for d in rep.deviations)
        assert "'Ctip2' not linked" in read and "'Pou6f2' linked by symbol_case" in read

    def test_species_mismatch_is_an_error(self, tmp_path, gene_index):
        ann = tmp_path / "annotation-NCBI-9544-103.ttl"
        h5ad = _tiny_ait(tmp_path / "tiny.h5ad", organism="NCBITaxon:9606")
        with pytest.raises(click.ClickException, match="NCBITaxon:9544, but this"):
            t.build(h5ad, gene_annotation=str(ann))

    def test_without_annotation_markers_are_left_out(self, tmp_path):
        ents, rep = t.build(_tiny_ait(tmp_path / "tiny.h5ad"))
        assert not any("curated_markers" in a for a in ents["CellTypeTaxon"])
        assert "no --gene_annotation given" in " ".join(
            d["reason"] for d in rep.deviations
        )

    def test_the_cli_takes_one_file(self, tmp_path, gene_index):
        from click.testing import CliRunner

        ann = tmp_path / "annotation-NCBI-9544-103.ttl"
        out = tmp_path / "out.jsonld"
        h5ad = _tiny_ait(tmp_path / "tiny.h5ad")
        r = CliRunner().invoke(
            t.ait2jsonld, [h5ad, "--gene_annotation", str(ann), "--out", str(out)]
        )
        assert r.exit_code == 0, r.output
        r = CliRunner().invoke(
            t.ait2jsonld,
            [h5ad, "--gene_annotation", str(ann), "--gene_annotation", str(ann)],
        )
        assert r.exit_code != 0  # a second file is not accepted
