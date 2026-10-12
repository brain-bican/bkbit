"""Module for generating unique BKBit object IDs using SHA-256 hashing."""

import json
import hashlib

BKBIT_OBJECT_ID_PREFIX = "urn:bkbit:"

#: Attributes deliberately kept out of the identity hash.
#:
#: The id is a content hash, so whatever is hashed becomes part of what makes
#: an entity *that* entity. Two consequences follow, and both argue for a
#: narrow hash:
#:
#: 1. Changing a hashed attribute renumbers the entity, then everything that
#:    refers to it, recursively. In the AIT taxonomy one abbreviation feeds
#:    ``CellTypeTaxon.has_abbreviation``, which feeds the taxon's own id, which
#:    feeds ``has_parent`` on its children -- so editing a single cross
#:    reference renumbers 100% of the taxa in the file.
#: 2. Two sources recording *different* mappings for the same entity produce
#:    two different nodes, so the mappings never meet. Keeping them out lets
#:    the descriptions merge onto one node, which is the point of a graph.
#:
#: Cross references and ontology mappings are assertions *about* an entity
#: rather than part of what it is. Biolink defines ``xref`` as "Alternate
#: CURIEs for a thing" -- alternate, so by definition not the identifier -- and
#: the SKOS mapping properties are defined as links between concepts in
#: different schemes. Both are open-ended: more get discovered over time.
#:
#: Verified collision-free: across all 17 released AIT taxonomy files (22,534
#: entities) and the NCBI Sus scrofa genome annotation (30,379 entities),
#: hashing without these keys produces no duplicate ids. The information is
#: already carried by an intrinsic attribute in every case --
#: ``GeneAnnotation.source_id`` holds the same accession as its ``NCBIGene:``
#: xref, ``OrganismTaxon.iri`` the same taxon id as its ``NCBITaxon:`` xref,
#: and an ``Abbreviation`` is keyed by its ``term`` -- so these keys were
#: adding instability without adding specificity.
NON_IDENTIFYING_ATTRIBUTES = frozenset(
    {
        "xref",
        "mapping_relation",
        "exact_match",
        "close_match",
        "broad_match",
        "narrow_match",
        "related_match",
    }
)


def generate_object_id(attributes: dict):
    """
    Generate a unique object ID based on the provided attributes.

    Attributes named in :data:`NON_IDENTIFYING_ATTRIBUTES` are ignored, so
    recording a new cross reference or ontology mapping for an entity does not
    change its id.

    Args:
        attributes (dict): A dictionary containing the attributes of the object.
    Returns:
        str: The generated object ID.
    """
    identifying = {
        k: v for k, v in attributes.items() if k not in NON_IDENTIFYING_ATTRIBUTES
    }
    # Sort the attributes by keys and convert to a consistent JSON string
    normalized_attributes = json.dumps(identifying, sort_keys=True)
    object_id = hashlib.sha256(normalized_attributes.encode()).hexdigest()
    return BKBIT_OBJECT_ID_PREFIX + object_id
