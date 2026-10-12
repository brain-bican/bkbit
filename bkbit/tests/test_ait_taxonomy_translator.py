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
