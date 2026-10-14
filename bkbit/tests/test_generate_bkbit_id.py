"""Tests for the bkbit identity hash.

The id is a content hash, so these tests are really about one question: what
counts as part of an entity, and what is merely said about it.
"""

import pathlib

import pytest

from bkbit.utils.generate_bkbit_id import (
    BKBIT_OBJECT_ID_PREFIX,
    NON_IDENTIFYING_ATTRIBUTES,
    generate_object_id,
)


def test_shape():
    oid = generate_object_id({"name": "x"})
    assert oid.startswith(BKBIT_OBJECT_ID_PREFIX)
    assert len(oid) == len(BKBIT_OBJECT_ID_PREFIX) + 64


def test_key_order_does_not_matter():
    assert generate_object_id({"a": 1, "b": 2}) == generate_object_id({"b": 2, "a": 1})


def test_intrinsic_attributes_still_identify():
    """The narrowing must not go so far that distinct entities collide."""
    base = {"term": "Astro", "meaning": "astrocyte", "entity_type": "cell_type"}
    for field, other in [
        ("term", "Astrocyte"),
        ("meaning", "astroglia"),
        ("entity_type", "anatomical"),
    ]:
        assert generate_object_id(base) != generate_object_id({**base, field: other})


@pytest.mark.parametrize("slot", sorted(NON_IDENTIFYING_ATTRIBUTES))
def test_mappings_do_not_change_the_id(slot):
    """Recording an ontology mapping must not renumber the entity.

    This is the property the whole module exists for: a mapping discovered
    later would otherwise renumber the entity and, transitively, everything
    pointing at it.
    """
    base = {"term": "Astro", "meaning": "astrocyte"}
    assert generate_object_id(base) == generate_object_id(
        {**base, slot: ["CL:0000127"]}
    )


def test_moving_a_value_between_mapping_slots_is_a_no_op():
    """Refining a mapping's predicate (exact -> broad) must not renumber."""
    before = {"term": "M", "meaning": "midbrain", "exact_match": ["DHBA:10648"]}
    after = {"term": "M", "meaning": "midbrain", "broad_match": ["DHBA:10648"]}
    assert generate_object_id(before) == generate_object_id(after)


def test_xref_still_identifies():
    """xref stays in the hash: for some classes it is the only distinguishing
    attribute. GenBank and RefSeq assemblies of one genome share name and
    version and differ only in the accession carried by their xref."""
    base = {"name": "mRatBN7.2", "version": "1", "in_taxon": ["NCBITaxon:10116"]}
    genbank = {**base, "xref": ["NCBIAssembly:GCA_015227675.1"]}
    refseq = {**base, "xref": ["NCBIAssembly:GCF_015227675.1"]}
    assert generate_object_id(genbank) != generate_object_id(refseq)
    assert "xref" not in NON_IDENTIFYING_ATTRIBUTES


def test_two_sources_disagreeing_about_a_mapping_describe_one_node():
    """Different mappings for the same entity must merge, not fork."""
    a = {"term": "Astro", "meaning": "astrocyte", "broad_match": ["CL:0000127"]}
    b = {"term": "Astro", "meaning": "astrocyte", "broad_match": ["CL:0000128"]}
    assert generate_object_id(a) == generate_object_id(b)


def test_absent_and_empty_mapping_agree():
    base = {"term": "Astro"}
    assert generate_object_id(base) == generate_object_id({**base, "broad_match": []})


def test_known_ids_are_stable():
    """Regression guard: these values are what downstream data carries.

    Changing them renumbers every published graph, so a diff here should only
    ever be deliberate.
    """
    assert generate_object_id({"term": "Astro"}) == (
        "urn:bkbit:944bbb61253ef08254feb749a856aa29053d6b39c5ff27eee6ad320e5ba78426"
    )


def test_no_translator_redefines_the_hasher():
    """No translator may keep its own copy of the hash.

    HMBA_annotation_translator did, so the filter above silently did not apply
    to it. A local
    reimplementation is invisible at the call site, which is why this is
    checked rather than assumed. Parsed rather than imported, so a module that
    cannot be imported does not mask the result.
    """
    import ast
    import bkbit.data_translators as pkg

    offenders = []
    for path in sorted(pathlib.Path(pkg.__path__[0]).glob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == "generate_object_id":
                offenders.append(f"{path.name}:{node.lineno}")
    assert not offenders, (
        "these redefine generate_object_id instead of importing it from "
        f"bkbit.utils.generate_bkbit_id: {', '.join(offenders)}"
    )


def test_hmba_translator_uses_the_shared_hasher():
    """The taxonomy2jsonld path itself, not just the helper.

    Exercises generate_object rather than generate_object_id so that
    reintroducing a local hasher in the translator fails here too.
    """
    from bkbit.data_translators.HMBA_annotation_translator import generate_object
    from bkbit.models import bke_taxonomy

    attrs = {"name": "Astro_1", "accession_id": "CS001", "xref": ["CL:0000127"]}
    obj = generate_object(bke_taxonomy.CellTypeTaxon, dict(attrs))
    assert obj.id == generate_object_id(attrs)
    assert obj.xref == ["CL:0000127"]
