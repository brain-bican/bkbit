"""Tests for the bkbit identity hash.

The id is a content hash, so these tests are really about one question: what
counts as part of an entity, and what is merely said about it.
"""

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
    """Recording a cross reference or mapping must not renumber the entity.

    This is the property the whole module exists for: a mapping discovered
    later would otherwise renumber the entity and, transitively, everything
    pointing at it.
    """
    base = {"term": "Astro", "meaning": "astrocyte"}
    assert generate_object_id(base) == generate_object_id(
        {**base, slot: ["CL:0000127"]}
    )


def test_moving_a_value_between_mapping_slots_is_a_no_op():
    """The migration this enables: ontology terms leave xref for broad_match."""
    before = {"term": "M", "meaning": "midbrain", "xref": ["DHBA:10648"]}
    after = {"term": "M", "meaning": "midbrain", "broad_match": ["DHBA:10648"]}
    assert generate_object_id(before) == generate_object_id(after)


def test_two_sources_disagreeing_about_a_mapping_describe_one_node():
    """Different mappings for the same entity must merge, not fork."""
    a = {"term": "Astro", "meaning": "astrocyte", "broad_match": ["CL:0000127"]}
    b = {"term": "Astro", "meaning": "astrocyte", "broad_match": ["CL:0000128"]}
    assert generate_object_id(a) == generate_object_id(b)


def test_absent_and_empty_mapping_agree():
    base = {"term": "Astro"}
    assert generate_object_id(base) == generate_object_id({**base, "xref": []})


def test_known_ids_are_stable():
    """Regression guard: these values are what downstream data carries.

    Changing them renumbers every published graph, so a diff here should only
    ever be deliberate.
    """
    assert generate_object_id({"term": "Astro"}) == (
        "urn:bkbit:944bbb61253ef08254feb749a856aa29053d6b39c5ff27eee6ad320e5ba78426"
    )
