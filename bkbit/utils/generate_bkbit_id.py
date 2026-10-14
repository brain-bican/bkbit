"""Module for generating unique BKBit object IDs using SHA-256 hashing."""

import json
import hashlib

BKBIT_OBJECT_ID_PREFIX = "urn:bkbit:"

#: Attributes deliberately kept out of the identity hash: the SKOS ontology
#: mappings.
#:
#: The id is a content hash, so whatever is hashed becomes part of what makes
#: an entity *that* entity. Two consequences follow:
#:
#: 1. Changing a hashed attribute renumbers the entity, then everything that
#:    refers to it, recursively. In a cell taxonomy one abbreviation feeds
#:    ``CellTypeTaxon.has_abbreviation``, which feeds the taxon's own id, which
#:    feeds ``has_parent`` on its children -- so recording a new ontology
#:    mapping on an abbreviation would renumber most of the tree.
#: 2. Two sources recording *different* mappings for the same entity produce
#:    two different nodes, so the mappings never meet. Keeping them out lets
#:    the descriptions merge onto one node.
#:
#: The SKOS mapping properties are links between concepts in different
#: schemes -- assertions *about* an entity rather than part of what it is --
#: and they are open-ended: more get discovered over time.
#:
#: ``xref`` is deliberately *not* listed. For some classes it is the only
#: attribute that tells two entities apart: a ``GenomeAssembly``'s accession
#: lives only in its ``NCBIAssembly:`` xref, so the GenBank (GCA_) and RefSeq
#: (GCF_) assemblies of one genome, which share a name and version, would
#: otherwise get the same id.
NON_IDENTIFYING_ATTRIBUTES = frozenset(
    {
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
    recording a new ontology mapping for an entity does not change its id.
    Cross references (``xref``) are still hashed.

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
