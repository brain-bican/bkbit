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


class TestPackagedSchema:
    """The packaged schema must be self-contained and carry the annotations."""

    def test_schema_ships_with_the_package(self):
        assert t.MODEL.is_file(), f"missing packaged schema: {t.MODEL}"

    def test_locations_resolve(self):
        # Reads bkbit/models/cell_taxonomy.yaml. If the import closure were not
        # merged in, SchemaView would raise FileNotFoundError on a sibling
        # schema that bkbit does not ship.
        sv, locs = t.load_locations()
        assert locs, "no ait_location annotations found in the packaged schema"

    def test_known_locations_present(self):
        _, locs = t.load_locations()
        by_slot = {slot: v["loc"] for (_cls, slot), v in locs.items()}
        assert by_slot.get("title") == "uns.title"
        assert "cluster_info" in str(by_slot.get("cluster_info", ""))


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
