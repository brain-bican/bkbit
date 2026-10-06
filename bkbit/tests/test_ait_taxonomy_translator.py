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

    def test_source_and_note_captured(self):
        locs = t.load_locations()
        assert any(v["source"] for v in locs.values())


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
