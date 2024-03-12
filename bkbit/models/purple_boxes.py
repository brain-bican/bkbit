from __future__ import annotations 
from datetime import (
    datetime,
    date
)
from decimal import Decimal 
from enum import Enum 
import re
from typing import (
    Any,
    List,
    Literal,
    Dict,
    Optional,
    Union
)
from pydantic.version import VERSION  as PYDANTIC_VERSION 
if int(PYDANTIC_VERSION[0])>=2:
    from pydantic import (
        BaseModel,
        ConfigDict,
        Field,
        field_validator
    )
else:
    from pydantic import (
        BaseModel,
        Field,
        validator
    )

metamodel_version = "None"
version = "None"


class ConfiguredBaseModel(BaseModel):
    model_config = ConfigDict(
        validate_assignment = True,
        validate_default = True,
        extra = "forbid",
        arbitrary_types_allowed = True,
        use_enum_values = True)
    pass


class ProvActivity(ConfiguredBaseModel):
    """
    An activity is something that occurs over a period of time and acts upon or with entities;  it may include consuming, processing, transforming, modifying, relocating, using, or generating entities.
    """
    used: Optional[str] = Field(None, description="""Usage is the beginning of utilizing an entity by an activity. Before usage, the activity had not begun to utilize this entity and could not have been affected by the entity.""")
    was_guided_by: Optional[str] = Field(None, description="""Guidance is the influence of an entity on an activity. This entity is known as an influencer, and the activity is influenced by the influencer.""")


class ProvEntity(ConfiguredBaseModel):
    """
    An entity is a physical, digital, conceptual, or other kind of thing with some fixed aspects;  entities may be real or imaginary.
    """
    was_derived_from: Optional[str] = Field(None, description="""A derivation is a transformation of an entity into another, an update of an entity resulting in a new one, or the construction of a new entity based on a pre-existing entity.""")
    was_generated_by: Optional[str] = Field(None, description="""Generation is the completion of production of a new entity by an activity. This entity did not exist before generation and becomes available for usage after this generation.""")
    annotates: Optional[str] = Field(None, description="""Annotation is the addition of metadata to an entity""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""Tranformation (dissection) of one entity into another entity.""")


class OntologyClass(ConfiguredBaseModel):
    """
    a concept or class in an ontology, vocabulary or thesaurus. Note that nodes in a biolink compatible KG can be considered both instances of biolink classes, and OWL classes in their own right. In general you should not need to use this class directly. Instead, use the appropriate biolink class. For example, for the GO concept of endocytosis (GO:0006897), use bl:BiologicalProcess as the type.
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")


class Annotation(ConfiguredBaseModel):
    """
    Biolink Model root class for entity annotations.
    """
    pass


class QuantityValue(Annotation):
    """
    A value of an attribute that is quantitative and measurable, expressed as a combination of a unit and a numeric value
    """
    has_unit: Optional[str] = Field(None, description="""connects a quantity value to a unit""")
    has_numeric_value: Optional[float] = Field(None, description="""connects a quantity value to a number""")


class Entity(ConfiguredBaseModel):
    """
    Root Biolink Model class for all things and informational relationships, real or imagined.
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    category: List[Literal["https://w3id.org/biolink/Entity","biolink:Entity"]] = Field(["biolink:Entity"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")


class DissectionRoiPolygon(Entity, ProvEntity):
    """
    A polygon annotated on a brain slab image delineating a region of interest (ROI) for a tissue sample dissectioning.
    """
    was_generated_by: Optional[str] = Field(None, description="""The delineation process from which the dissection ROI polygon was generated by.""")
    annotates: Optional[str] = Field(None, description="""The brain slab that was annotated by the delineation process.""")
    name: Optional[str] = Field(None, description="""Name of a polygon annotated on a brain slab image delineating a region of interest (ROI) for a tissue sample dissectioning.""")
    was_derived_from: Optional[str] = Field(None, description="""A derivation is a transformation of an entity into another, an update of an entity resulting in a new one, or the construction of a new entity based on a pre-existing entity.""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""Tranformation (dissection) of one entity into another entity.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/DissectionRoiPolygon","bican:DissectionRoiPolygon"]] = Field(["bican:DissectionRoiPolygon"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")


class NamedThing(Entity):
    """
    a databased entity or concept/class
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://w3id.org/biolink/NamedThing","biolink:NamedThing"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://w3id.org/biolink/NamedThing","biolink:NamedThing"]] = Field(["biolink:NamedThing"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class Attribute(NamedThing, OntologyClass):
    """
    A property or characteristic of an entity. For example, an apple may have properties such as color, shape, age, crispiness. An environmental sample may have attributes such as depth, lat, long, material.
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://w3id.org/biolink/Attribute","biolink:Attribute"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    attribute_name: Optional[str] = Field(None, description="""The human-readable 'attribute name' can be set to a string which reflects its context of interpretation, e.g. SEPIO evidence/provenance/confidence annotation or it can default to the name associated with the 'has attribute type' slot ontology term.""")
    has_attribute_type: str = Field(..., description="""connects an attribute to a class that describes it""")
    has_quantitative_value: Optional[List[QuantityValue]] = Field(None, description="""connects an attribute to a value""")
    has_qualitative_value: Optional[str] = Field(None, description="""connects an attribute to a value""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    name: Optional[str] = Field(None, description="""The human-readable 'attribute name' can be set to a string which reflects its context of interpretation, e.g. SEPIO evidence/provenance/confidence annotation or it can default to the name associated with the 'has attribute type' slot ontology term.""")
    category: List[Literal["https://w3id.org/biolink/Attribute","biolink:Attribute"]] = Field(["biolink:Attribute"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class TaxonomicRank(OntologyClass):
    """
    A descriptor for the rank within a taxonomic classification. Example instance: TAXRANK:0000017 (kingdom)
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")


class OrganismTaxon(NamedThing):
    """
    A classification of a set of organisms. Example instances: NCBITaxon:9606 (Homo sapiens), NCBITaxon:2 (Bacteria). Can also be used to represent strains or subspecies.
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://w3id.org/biolink/OrganismTaxon","biolink:OrganismTaxon"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    organism_taxon_has_taxonomic_rank: Optional[str] = Field(None)
    category: List[Literal["https://w3id.org/biolink/OrganismTaxon","biolink:OrganismTaxon"]] = Field(["biolink:OrganismTaxon"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class PhysicalEssenceOrOccurrent(ConfiguredBaseModel):
    """
    Either a physical or processual entity.
    """
    pass


class PhysicalEssence(PhysicalEssenceOrOccurrent):
    """
    Semantic mixin concept.  Pertains to entities that have physical properties such as mass, volume, or charge.
    """
    pass


class PhysicalEntity(PhysicalEssence, NamedThing):
    """
    An entity that has material reality (a.k.a. physical essence).
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://w3id.org/biolink/PhysicalEntity","biolink:PhysicalEntity"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://w3id.org/biolink/PhysicalEntity","biolink:PhysicalEntity"]] = Field(["biolink:PhysicalEntity"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class Occurrent(PhysicalEssenceOrOccurrent):
    """
    A processual entity.
    """
    pass


class ActivityAndBehavior(Occurrent):
    """
    Activity or behavior of any independent integral living, organization or mechanical actor in the world
    """
    pass


class Activity(ActivityAndBehavior, NamedThing):
    """
    An activity is something that occurs over a period of time and acts upon or with entities; it may include consuming, processing, transforming, modifying, relocating, using, or generating entities.
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://w3id.org/biolink/Activity","biolink:Activity"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://w3id.org/biolink/Activity","biolink:Activity"]] = Field(["biolink:Activity"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class Procedure(ActivityAndBehavior, NamedThing):
    """
    A series of actions conducted in a certain order or manner
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://w3id.org/biolink/Procedure","biolink:Procedure"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://w3id.org/biolink/Procedure","biolink:Procedure"]] = Field(["biolink:Procedure"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class DissectionRoiDelineation(Procedure, ProvActivity):
    """
    The process of outlining a region of interest on a brain slab image to guide the dissection and generation of a tissue sample.
    """
    used: Optional[str] = Field(None, description="""The brain slab that was annotated by the delineation process.""")
    was_guided_by: Optional[str] = Field(None, description="""Guidance is the influence of an entity on an activity. This entity is known as an influencer, and the activity is influenced by the influencer.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/DissectionRoiDelineation","bican:DissectionRoiDelineation"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/DissectionRoiDelineation","bican:DissectionRoiDelineation"]] = Field(["bican:DissectionRoiDelineation"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class TissueDissection(Procedure, ProvActivity):
    """
    The process of dissecting a tissue sample from a brain slab guided by a dissection region of interest (ROI) delineation.
    """
    was_guided_by: Optional[str] = Field(None, description="""The dissection ROI polygon which was used to guide the tissue dissection.""")
    used: Optional[str] = Field(None, description="""The brain slab from which the tissue sample was dissected from.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/TissueDissection","bican:TissueDissection"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/TissueDissection","bican:TissueDissection"]] = Field(["bican:TissueDissection"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class CellDissociation(Procedure, ProvActivity):
    """
    The process of generating dissociated cells from an input tissue sample. This process could also introduce a tissue-source barcode (eg cell hashing), allowing mixing of cell dissociation samples at the cell barcoding step.
    """
    used: Optional[List[str]] = Field(default_factory=list, description="""The input tissue sample(s) from which the dissociated cell sample was derived from.""")
    process_date: Optional[str] = Field(None, description="""Date of cell dissociation process.""")
    was_guided_by: Optional[str] = Field(None, description="""Guidance is the influence of an entity on an activity. This entity is known as an influencer, and the activity is influenced by the influencer.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/CellDissociation","bican:CellDissociation"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/CellDissociation","bican:CellDissociation"]] = Field(["bican:CellDissociation"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class CellEnrichment(Procedure, ProvActivity):
    """
    The process of enriching a dissociated cell sample by including or excluding cells of different types based on an enrichment plan using techniques such as fluorescence-activated cell sorting (FACS). This process could also introduce a tissue-source barcode (eg cell hashing), allowing mixing of cell enriched samples at the cell barcoding step.
    """
    used: Optional[List[str]] = Field(default_factory=list, description="""The input dissociated cell sample(s) from which the enriched cell sample was derived from.""")
    process_date: Optional[str] = Field(None, description="""Date of cell enrichment process.""")
    was_guided_by: Optional[str] = Field(None, description="""Guidance is the influence of an entity on an activity. This entity is known as an influencer, and the activity is influenced by the influencer.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/CellEnrichment","bican:CellEnrichment"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/CellEnrichment","bican:CellEnrichment"]] = Field(["bican:CellEnrichment"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class EnrichedCellSampleSplitting(Procedure, ProvActivity):
    """
    The process of splitting an enriched cell sample into several portions. Each portion may be used by the same or different groups for different scientific studies.
    """
    used: Optional[str] = Field(None, description="""The enrichment cell sample splitting process from which the enriched cell sample was generated by.""")
    was_guided_by: Optional[str] = Field(None, description="""Guidance is the influence of an entity on an activity. This entity is known as an influencer, and the activity is influenced by the influencer.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/EnrichedCellSampleSplitting","bican:EnrichedCellSampleSplitting"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/EnrichedCellSampleSplitting","bican:EnrichedCellSampleSplitting"]] = Field(["bican:EnrichedCellSampleSplitting"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class CellBarcoding(Procedure, ProvActivity):
    """
    The process of adding a molecular barcode to individual cells in a sample. The input will be either dissociated cell sample or enriched cell sample. Cell barcodes are only guaranteed to be unique within this one collection. One dissociated cell sample or enriched cell sample can lead to multiple barcoded cell samples.
    """
    used: Optional[List[str]] = Field(default_factory=list, description="""The input dissociated or enriched cell sample(s) from which the barcoded cell sample was derived from.""")
    port_well: Optional[str] = Field(None, description="""Specific position of the loaded port of the 10x chip.  An Enriched or Dissociated Cell Sample is loaded into a port on a chip (creating a Barcoded Cell Sample). Can be left null for non-10x methods.""")
    input_quantity: Optional[int] = Field(None, description="""Number of enriched or dissociated cells/nuclei going into the barcoding process.""")
    process_date: Optional[str] = Field(None, description="""Date of cell barcoding process.""")
    method: Optional[str] = Field(None, description="""Standardized nomenclature to describe the general barcoding method used.  For example: Multiome, ATAC Only, GEX Only or snm3C-seq.""")
    was_guided_by: Optional[str] = Field(None, description="""Guidance is the influence of an entity on an activity. This entity is known as an influencer, and the activity is influenced by the influencer.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/CellBarcoding","bican:CellBarcoding"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/CellBarcoding","bican:CellBarcoding"]] = Field(["bican:CellBarcoding"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class CdnaAmplification(Procedure, ProvActivity):
    """
    The process of creating a collection of cDNA molecules derived and amplified from an input barcoded cell sample.  A large amount of cDNA is needed to have accurate and reliable sequencing detection of gene expression.  This process generates multiple copies of each mRNA transcript (expressed gene) within each cell while retaining the cell's unique barcode from the barcoding step. This is a necessary step for GEX methods but is not used for ATAC methods.
    """
    used: Optional[str] = Field(None, description="""The input barcoded cell sample from which amplified cDNA was derived from.""")
    pcr_cycles: Optional[int] = Field(None, description="""Number of PCR cycles used during cDNA amplification for this cDNA.""")
    process_date: Optional[date] = Field(None, description="""Date of cDNA amplification.""")
    set: Optional[str] = Field(None, description="""cDNA amplification set, containing multiple amplified_cDNA_names that were processed at the same time.""")
    was_guided_by: Optional[str] = Field(None, description="""Guidance is the influence of an entity on an activity. This entity is known as an influencer, and the activity is influenced by the influencer.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/CdnaAmplification","bican:CdnaAmplification"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/CdnaAmplification","bican:CdnaAmplification"]] = Field(["bican:CdnaAmplification"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class LibraryConstruction(Procedure, ProvActivity):
    """
    The process of constructing a library from input material (such as amplified cDNA or barcoded cell sample) derived from one or more cell samples.  cDNA is fragmented into smaller pieces appropriate for sequencing and at the same time a library index barcode is incorporated to enable identification of library origin, allowing libraries to be pooled together for sequencing.
    """
    used: Optional[str] = Field(None, description="""The input barcoded cell sample or amplified cDNA from which the library was derived from.""")
    method: Optional[str] = Field(None, description="""Standardized nomenclature to describe the specific library method used.  This specifies the alignment method required for the library.  For example, 10xV3.1 (for RNASeq single assay), 10xMult-GEX (for RNASeq multiome assay), and 10xMult-ATAC (for ATACSeq multiome assay).""")
    process_date: Optional[date] = Field(None, description="""Date of library construction.""")
    input_quantity_ng: Optional[int] = Field(None, description="""Amount of cDNA going into library construction in nanograms.""")
    set: Optional[str] = Field(None, description="""Library set, containing multiple library_names that were processed at the same time.""")
    was_guided_by: Optional[str] = Field(None, description="""Guidance is the influence of an entity on an activity. This entity is known as an influencer, and the activity is influenced by the influencer.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/LibraryConstruction","bican:LibraryConstruction"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/LibraryConstruction","bican:LibraryConstruction"]] = Field(["bican:LibraryConstruction"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class LibraryPooling(Procedure, ProvActivity):
    """
    The process of constructing of a libray pool by combining library aliquots from a set of input libraries. Each library aliquot in a library pool will have a unique R1/R2 index to allow for sequencing together then separating the sequencing output by originating library aliquot through the process of demultiplexing.
    """
    used: Optional[List[str]] = Field(default_factory=list, description="""The input aliquot(s) from which the library pool was derived from.""")
    process_date: Optional[str] = Field(None, description="""Date of library pooling process.""")
    was_guided_by: Optional[str] = Field(None, description="""Guidance is the influence of an entity on an activity. This entity is known as an influencer, and the activity is influenced by the influencer.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/LibraryPooling","bican:LibraryPooling"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/LibraryPooling","bican:LibraryPooling"]] = Field(["bican:LibraryPooling"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class SubjectOfInvestigation(ConfiguredBaseModel):
    """
    An entity that has the role of being studied in an investigation, study, or experiment
    """
    pass


class MaterialSample(SubjectOfInvestigation, PhysicalEntity):
    """
    A sample is a limited quantity of something (e.g. an individual or set of individuals from a population, or a portion of a substance) to be used for testing, analysis, inspection, investigation, demonstration, or trial use. [SIO]
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://w3id.org/biolink/MaterialSample","biolink:MaterialSample"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://w3id.org/biolink/MaterialSample","biolink:MaterialSample"]] = Field(["biolink:MaterialSample"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class BrainSlab(MaterialSample, ProvEntity):
    """
    A thick flat piece of brain tissue obtained by slicing a whole brain, brain hemisphere or subdivision with a blade at regular interval.  When multiple brain slabs are obtained from the slicing process, an ordinal is assigned to provide information about the relative positioning of the slabs.
    """
    was_derived_from: Optional[str] = Field(None, description="""The donor from which the brain slab was derived from.""")
    name: Optional[str] = Field(None, description="""Name of a thick flat piece of brain tissue obtained by slicing a whole brain, brain hemisphere or subdivision with a blade at regular interval.  When multiple brain slabs are obtained from the slicing process, an ordinal is assigned to provide information about the relative positioning of the slabs.""")
    was_generated_by: Optional[str] = Field(None, description="""Generation is the completion of production of a new entity by an activity. This entity did not exist before generation and becomes available for usage after this generation.""")
    annotates: Optional[str] = Field(None, description="""Annotation is the addition of metadata to an entity""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""Tranformation (dissection) of one entity into another entity.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/BrainSlab","bican:BrainSlab"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/BrainSlab","bican:BrainSlab"]] = Field(["bican:BrainSlab"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class TissueSample(MaterialSample, ProvEntity):
    """
    The final intact piece of tissue before cell or nuclei prep. This piece of tissue will be used in dissociation and has an region of interest polygon (ROI) associated with it.
    """
    was_derived_from: Optional[str] = Field(None, description="""The donor or brain slab from which the tissue sample was derived from.""")
    was_generated_by: Optional[str] = Field(None, description="""The dissection process from which the tissue sample was generated by.""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""The dissection ROI polygon that was used to guide the dissection.""")
    name: Optional[str] = Field(None, description="""Identifier name for final intact piece of tissue before cell or nuclei prep.  This piece of tissue will be used in dissociation and has an ROI associated with it.""")
    annotates: Optional[str] = Field(None, description="""Annotation is the addition of metadata to an entity""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/TissueSample","bican:TissueSample"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/TissueSample","bican:TissueSample"]] = Field(["bican:TissueSample"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class DissociatedCellSample(MaterialSample, ProvEntity):
    """
    A collection of dissociated cells or nuclei derived from dissociation of a tissue sample.
    """
    was_generated_by: Optional[str] = Field(None, description="""The cell dissociation process from which the dissociated cell sample was generated by.""")
    was_derived_from: Optional[List[str]] = Field(default_factory=list, description="""The input tissue sample(s) from which dissociated cell sample was derived from.""")
    name: Optional[str] = Field(None, description="""Name of a collection of dissociated cells or nuclei derived from dissociation of a tissue sample.""")
    cell_prep_type: Optional[str] = Field(None, description="""The type of cell preparation. For example: Cells, Nuclei. This is a property of dissociated_cell_sample.""")
    cell_source_oligo_name: Optional[str] = Field(None, description="""Name of cell source oligo used in cell plexing.  The oligo molecularly tags all the cells in the dissociated cell sample and allows separate dissociated cell samples to be combined downstream in the barcoded cell sample.  The oligo name is associated with a sequence in a lookup table.  This sequence will be needed during alignment to associate reads with the parent source dissociated cell sample.""")
    annotates: Optional[str] = Field(None, description="""Annotation is the addition of metadata to an entity""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""Tranformation (dissection) of one entity into another entity.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/DissociatedCellSample","bican:DissociatedCellSample"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/DissociatedCellSample","bican:DissociatedCellSample"]] = Field(["bican:DissociatedCellSample"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class EnrichedCellSample(MaterialSample, ProvEntity):
    """
    A collection of enriched cells or nuclei after enrichment process, usually via fluorescence-activated cell sorting (FACS) using the enrichment plan, is applied to dissociated cell sample.
    """
    was_generated_by: Optional[str] = Field(None, description="""The cell enrichment or sample splitting process from which the enriched cell sample was generated by.""")
    was_derived_from: Optional[List[str]] = Field(default_factory=list, description="""The dissociated or enriched cell sample(s) from which the enriched cell sample was derived from.""")
    name: Optional[str] = Field(None, description="""Name of collection of enriched cells or nuclei after enrichment process (usually via FACS using the Enrichment Plan) applied to dissociated_cell_sample.""")
    enrichment_population: Optional[str] = Field(None, description="""Actual percentage of cells as a result of using set of fluorescent marker label(s) to enrich dissociated_cell_sample with desired mix of cell populations.  This plan can also be used to describe 'No FACS' where no enrichment was performed.  This is a property of enriched_cell_prep_container.""")
    cell_source_oligo_name: Optional[str] = Field(None, description="""Name of cell source oligo used in cell plexing.  The oligo molecularly tags all the cells in the enriched cell sample and allows separate enriched cell samples to be combined downstream in the barcoded cell sample.  The oligo name is associated with a sequence in a lookup table.  This sequence will be needed during alignment to associate reads with the parent source enriched cell sample.""")
    histone_modification_marker: Optional[str] = Field(None, description="""Histone modification marker antibodies (eg H3K27ac, H3K27me3, H3K9me3) used in conjunction with an Enriched Cell Source Barcode in order to combine multiple Enriched Cell Populations before Barcoded Cell Sample step for 10xMultiome method. Each of the Histone antibodies captures an essential part of the epigenome.""")
    annotates: Optional[str] = Field(None, description="""Annotation is the addition of metadata to an entity""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""Tranformation (dissection) of one entity into another entity.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/EnrichedCellSample","bican:EnrichedCellSample"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/EnrichedCellSample","bican:EnrichedCellSample"]] = Field(["bican:EnrichedCellSample"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class BarcodedCellSample(MaterialSample, ProvEntity):
    """
    A collection of molecularly barcoded cells. Input will be either dissociated cell sample or enriched cell sample. Cell barcodes are only guaranteed to be unique within this one collection. One dissociated cell sample or enriched cell sample can lead to multiple barcoded cell samples.  The sequences of the molecular barcodes are revealed during alignment of the resulting fastq files for the barcoded cell sample. The barcoded cell sample name and the cell level molecular barcode together uniquely identify a single cell.
    """
    was_generated_by: Optional[str] = Field(None, description="""The barcoding process from which the barcoded cell sample is generated from.""")
    was_derived_from: Optional[List[str]] = Field(default_factory=list, description="""The input dissociated or enriched cell sample(s) from which the barcoded cell sample was derived from.""")
    name: Optional[str] = Field(None, description="""Name of a collection of barcoded cells.  Input will be either dissociated_cell_sample or enriched_cell_sample.  Cell barcodes are only guaranteed to be unique within this one collection. One dissociated_cell_sample or enriched_cell_sample can lead to multiple barcoded_cell_samples.""")
    number_of_expected_cells: Optional[int] = Field(None, description="""Expected number of cells/nuclei of a barcoded_cell_sample that will be barcoded and available for sequencing.  This is a derived number from 'Barcoded cell input quantity count' that is dependent on the \"capture rate\" of the barcoding method.  It is usually a calculated fraction of the 'Barcoded cell input quantity count' going into the barcoding method.""")
    annotates: Optional[str] = Field(None, description="""Annotation is the addition of metadata to an entity""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""Tranformation (dissection) of one entity into another entity.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/BarcodedCellSample","bican:BarcodedCellSample"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/BarcodedCellSample","bican:BarcodedCellSample"]] = Field(["bican:BarcodedCellSample"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class AmplifiedCdna(MaterialSample, ProvEntity):
    """
    A collection of cDNA molecules derived and amplified from an input barcoded cell sample. These cDNA molecules represent the gene expression of each cell, with all cDNA molecules from a given cell retaining that cell's unique barcode from the cell barcoding step. This is a necessary step for GEX methods but is not used for ATAC methods.
    """
    was_generated_by: Optional[str] = Field(None, description="""The cDNA amplification process from which the amplified cDNA was generated by.""")
    was_derived_from: Optional[str] = Field(None, description="""The input barcoded cell sample from which amplified cDNA was derived from.""")
    name: Optional[str] = Field(None, description="""Name of a collection of cDNA molecules derived and amplified from an input barcoded_cell_sample.  These cDNA molecules represent the gene expression of each cell, with all cDNA molecules from a given cell retaining that cell's unique barcode from the cell barcoding step.  This is a necessary step for GEX methods but is not used for ATAC methods.""")
    quantity_ng: Optional[float] = Field(None, description="""Amount of cDNA produced after cDNA amplification measured in nanograms.""")
    pass_fail_result: Optional[str] = Field(None, description="""Pass or Fail result based on qualitative assessment of cDNA yield and size.""")
    percent_cdna__longer_than_400bp: Optional[float] = Field(None, description="""QC metric to measure mRNA degradation of cDNA.  Higher % is higher quality starting material.  Over 400bp is used as a universal cutoff for intact (full length) vs degraded cDNA and is a common output from Bioanalyzer and Fragment Analyzer elecropheragrams.""")
    annotates: Optional[str] = Field(None, description="""Annotation is the addition of metadata to an entity""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""Tranformation (dissection) of one entity into another entity.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/AmplifiedCdna","bican:AmplifiedCdna"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/AmplifiedCdna","bican:AmplifiedCdna"]] = Field(["bican:AmplifiedCdna"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class Library(MaterialSample, ProvEntity):
    """
    A collection of fragmented and barcode-indexed DNA molecules for sequencing. An index or barcode is typically introduced to enable identification of library origin to allow libraries to be pooled together for sequencing.
    """
    was_generated_by: Optional[str] = Field(None, description="""The library construction process from which the library was generated by.""")
    was_derived_from: Optional[str] = Field(None, description="""The input barcoded cell sample or amplified cDNA from which the library was derived from.""")
    name: Optional[str] = Field(None, description="""Name of a library, which is a collection of fragmented and barcode-indexed DNA molecules for sequencing.  An index or barcode is typically introduced to enable identification of library origin to allow libraries to be pooled together for sequencing.""")
    average_size_bp: Optional[int] = Field(None, description="""Average size of the library in terms of base pairs.  This is used to calculate the molarity before pooling and sequencing.""")
    concentration_nm: Optional[float] = Field(None, description="""Concentration of library in terms of nM (nMol/L).  Number of molecules is needed for accurate pooling of the libraries and for generating the number of target reads/cell in sequencing.""")
    pass_fail_result: Optional[str] = Field(None, description="""Pass or Fail result based on qualitative assessment of library yield and size.""")
    quantity_fmol: Optional[int] = Field(None, description="""Amount of library generated in terms of femtomoles""")
    quantity_ng: Optional[int] = Field(None, description="""Amount of library generated in terms of nanograms""")
    r1_r2_index: Optional[str] = Field(None, description="""Name of the pair of library indexes used for sequencing.  Indexes allow libraries to be pooled together for sequencing.  Sequencing output (fastq) are demultiplexed by using the indexes for each library.  The name will be associated with the sequences of i7, i5, and i5as, which are needed by SeqCores for demultiplexing.  The required direction of the sequence (sense or antisense) of the index can differ depending on sequencing instruments.""")
    annotates: Optional[str] = Field(None, description="""Annotation is the addition of metadata to an entity""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""Tranformation (dissection) of one entity into another entity.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/Library","bican:Library"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/Library","bican:Library"]] = Field(["bican:Library"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class LibraryAliquot(MaterialSample, ProvEntity):
    """
    One library in the library pool. Each library aliquot in a library pool will have a unique R1/R2 index to allow for sequencing together then separating the sequencing output by originating library aliquot through the process of demultiplexing. The resulting demultiplexed fastq files will include the library aliquot name.  A given library may produce multiple library aliquots, which is done in the case of resequencing.  Each library aliquot will produce a set of fastq files.
    """
    was_derived_from: Optional[str] = Field(None, description="""The input library from which the library aliquot was derived from.""")
    name: Optional[str] = Field(None, description="""One library in the library pool.  Each Library_aliquot_name in a library pool will have a unique R1/R2 index to allow for sequencing together then separating the sequencing output by originating library aliquot through the process of demultiplexing.  The resulting demultiplexed fastq files will include the library_aliquot_name.""")
    was_generated_by: Optional[str] = Field(None, description="""Generation is the completion of production of a new entity by an activity. This entity did not exist before generation and becomes available for usage after this generation.""")
    annotates: Optional[str] = Field(None, description="""Annotation is the addition of metadata to an entity""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""Tranformation (dissection) of one entity into another entity.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/LibraryAliquot","bican:LibraryAliquot"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/LibraryAliquot","bican:LibraryAliquot"]] = Field(["bican:LibraryAliquot"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class LibraryPool(MaterialSample, ProvEntity):
    """
    A library pool is made up of library aliquots from multiple libraries. Each library aliquot in a library pool will have a unique R1/R2 index to allow for sequencing together then separating the sequencing output by originating library aliquot through the process of demultiplexing.
    """
    was_generated_by: Optional[str] = Field(None, description="""The pooling process from which the library pool was generated by.""")
    was_derived_from: Optional[List[str]] = Field(default_factory=list, description="""The input aliquot(s) from which the library pool was derived from.""")
    name: Optional[str] = Field(None, description="""Library lab's library pool name.  For some labs this may be the same as \"Libray pool tube local name\".   Other labs distinguish between the local tube label of the library pool and the library pool name provided to SeqCore for tracking.  Local Pool Name is used to communicate sequencing status between SeqCore and Library Labs.""")
    local_tube_id: Optional[str] = Field(None, description="""Library Pool Tube local name.  Label of the tube containing the library pool, which is made up of multiple library_aliquots.  This is a Library Lab local tube name, before the pool is aliquoted to the Seq Core provided tube 'Library Pool Tube Name'.""")
    annotates: Optional[str] = Field(None, description="""Annotation is the addition of metadata to an entity""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""Tranformation (dissection) of one entity into another entity.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/LibraryPool","bican:LibraryPool"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/LibraryPool","bican:LibraryPool"]] = Field(["bican:LibraryPool"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class ThingWithTaxon(ConfiguredBaseModel):
    """
    A mixin that can be used on any entity that can be taxonomically classified. This includes individual organisms; genes, their products and other molecular entities; body parts; biological processes
    """
    in_taxon: Optional[List[str]] = Field(None, description="""connects an entity to its taxonomic classification. Only certain kinds of entities can be taxonomically classified; see 'thing with taxon'""")
    in_taxon_label: Optional[str] = Field(None, description="""The human readable scientific name for the taxon of the entity.""")


class Donor(ThingWithTaxon, MaterialSample, ProvEntity):
    """
    A person or organism that is the source of a biological sample for scientific study.  Many biological samples are generated from a single donor.
    """
    name: Optional[str] = Field(None, description="""Name of person or organism that is the source of a biological sample for scientific study.  Many biological samples are generated from a single donor.""")
    biological_sex: Optional[str] = Field(None, description="""Biological sex of donor at birth""")
    age_at_death_description: Optional[str] = Field(None, description="""Text description of the age of death following typical scientific convention for the species or developmental stage. For example: P56, E11.5""")
    age_at_death_reference_point: Optional[str] = Field(None, description="""The reference point for an age interval; for example, birth or conception.""")
    age_at_death_unit: Optional[str] = Field(None, description="""The unit used for representing the donor age from the reference point.""")
    age_at_death_value: Optional[str] = Field(None, description="""The value representing the donor age from the reference point.""")
    in_taxon: Optional[List[str]] = Field(None, description="""connects an entity to its taxonomic classification. Only certain kinds of entities can be taxonomically classified; see 'thing with taxon'""")
    in_taxon_label: Optional[str] = Field(None, description="""The human readable scientific name for the taxon of the entity.""")
    was_derived_from: Optional[str] = Field(None, description="""A derivation is a transformation of an entity into another, an update of an entity resulting in a new one, or the construction of a new entity based on a pre-existing entity.""")
    was_generated_by: Optional[str] = Field(None, description="""Generation is the completion of production of a new entity by an activity. This entity did not exist before generation and becomes available for usage after this generation.""")
    annotates: Optional[str] = Field(None, description="""Annotation is the addition of metadata to an entity""")
    dissection_was_guided_by: Optional[str] = Field(None, description="""Tranformation (dissection) of one entity into another entity.""")
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://identifiers.org/brain-bican/vocab/Donor","bican:Donor"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    category: List[Literal["https://identifiers.org/brain-bican/vocab/Donor","bican:Donor"]] = Field(["bican:Donor"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class BiologicalEntity(ThingWithTaxon, NamedThing):
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://w3id.org/biolink/BiologicalEntity","biolink:BiologicalEntity"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    in_taxon: Optional[List[str]] = Field(None, description="""connects an entity to its taxonomic classification. Only certain kinds of entities can be taxonomically classified; see 'thing with taxon'""")
    in_taxon_label: Optional[str] = Field(None, description="""The human readable scientific name for the taxon of the entity.""")
    category: List[Literal["https://w3id.org/biolink/BiologicalEntity","biolink:BiologicalEntity"]] = Field(["biolink:BiologicalEntity"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class GenomicEntity(ConfiguredBaseModel):
    has_biological_sequence: Optional[str] = Field(None, description="""connects a genomic feature to its sequence""")


class ChemicalEntityOrGeneOrGeneProduct(ConfiguredBaseModel):
    """
    A union of chemical entities and children, and gene or gene product. This mixin is helpful to use when searching across chemical entities that must include genes and their children as chemical entities.
    """
    pass


class MacromolecularMachineMixin(ConfiguredBaseModel):
    """
    A union of gene locus, gene product, and macromolecular complex. These are the basic units of function in a cell. They either carry out individual biological activities, or they encode molecules which do this.
    """
    macromolecular_machine_mixin_name: Optional[str] = Field(None, description="""genes are typically designated by a short symbol and a full name. We map the symbol to the default display name and use an additional slot for full name""")


class GeneOrGeneProduct(MacromolecularMachineMixin):
    """
    A union of gene loci or gene products. Frequently an identifier for one will be used as proxy for another
    """
    macromolecular_machine_mixin_name: Optional[str] = Field(None, description="""genes are typically designated by a short symbol and a full name. We map the symbol to the default display name and use an additional slot for full name""")


class Gene(GeneOrGeneProduct, ChemicalEntityOrGeneOrGeneProduct, GenomicEntity, BiologicalEntity, PhysicalEssence, OntologyClass):
    """
    A region (or regions) that includes all of the sequence elements necessary to encode a functional transcript. A gene locus may include regulatory regions, transcribed regions and/or other functional sequence regions.
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""genes are typically designated by a short symbol and a full name. We map the symbol to the default display name and use an additional slot for full name""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://w3id.org/biolink/Gene","biolink:Gene"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    in_taxon: Optional[List[str]] = Field(None, description="""connects an entity to its taxonomic classification. Only certain kinds of entities can be taxonomically classified; see 'thing with taxon'""")
    in_taxon_label: Optional[str] = Field(None, description="""The human readable scientific name for the taxon of the entity.""")
    symbol: Optional[str] = Field(None, description="""Symbol for a particular thing""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    has_biological_sequence: Optional[str] = Field(None, description="""connects a genomic feature to its sequence""")
    macromolecular_machine_mixin_name: Optional[str] = Field(None, description="""genes are typically designated by a short symbol and a full name. We map the symbol to the default display name and use an additional slot for full name""")
    category: List[Literal["https://w3id.org/biolink/Gene","biolink:Gene"]] = Field(["biolink:Gene"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


class Genome(GenomicEntity, BiologicalEntity, PhysicalEssence, OntologyClass):
    """
    A genome is the sum of genetic material within a cell or virion.
    """
    id: str = Field(..., description="""A unique identifier for an entity. Must be either a CURIE shorthand for a URI or a complete URI""")
    iri: Optional[str] = Field(None, description="""An IRI for an entity. This is determined by the id using expansion rules.""")
    type: Optional[List[str]] = Field(default_factory=list)
    name: Optional[str] = Field(None, description="""A human-readable name for an attribute or entity.""")
    description: Optional[str] = Field(None, description="""a human-readable description of an entity""")
    has_attribute: Optional[List[str]] = Field(None, description="""connects any entity to an attribute""")
    deprecated: Optional[bool] = Field(None, description="""A boolean flag indicating that an entity is no longer considered current or valid.""")
    provided_by: Optional[List[str]] = Field(None, description="""The value in this node property represents the knowledge provider that created or assembled the node and all of its attributes.  Used internally to represent how a particular node made its way into a knowledge provider or graph.""")
    xref: Optional[List[str]] = Field(default_factory=list, description="""A database cross reference or alternative identifier for a NamedThing or edge between two NamedThings.  This property should point to a database record or webpage that supports the existence of the edge, or gives more detail about the edge. This property can be used on a node or edge to provide multiple URIs or CURIE cross references.""")
    full_name: Optional[str] = Field(None, description="""a long-form human readable name for a thing""")
    synonym: Optional[List[str]] = Field(default_factory=list, description="""Alternate human-readable names for a thing""")
    named_thing_category: List[Literal["https://w3id.org/biolink/Genome","biolink:Genome"]] = Field(..., description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")
    in_taxon: Optional[List[str]] = Field(None, description="""connects an entity to its taxonomic classification. Only certain kinds of entities can be taxonomically classified; see 'thing with taxon'""")
    in_taxon_label: Optional[str] = Field(None, description="""The human readable scientific name for the taxon of the entity.""")
    has_biological_sequence: Optional[str] = Field(None, description="""connects a genomic feature to its sequence""")
    category: List[Literal["https://w3id.org/biolink/Genome","biolink:Genome"]] = Field(["biolink:Genome"], description="""Name of the high level ontology class in which this entity is categorized. Corresponds to the label for the biolink entity type class. In a neo4j database this MAY correspond to the neo4j label tag. In an RDF database it should be a biolink model class URI. This field is multi-valued. It should include values for ancestors of the biolink class; for example, a protein such as Shh would have category values `biolink:Protein`, `biolink:GeneProduct`, `biolink:MolecularEntity`. In an RDF database, nodes will typically have an rdf:type triples. This can be to the most specific biolink class, or potentially to a class more specific than something in biolink. For example, a sequence feature `f` may have a rdf:type assertion to a SO class such as TF_binding_site, which is more specific than anything in biolink. Here we would have categories {biolink:GenomicEntity, biolink:MolecularEntity, biolink:NamedThing}""")

    @field_validator('named_thing_category')
    def pattern_named_thing_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid named_thing_category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid named_thing_category format: {v}")
        return v

    @field_validator('category')
    def pattern_category(cls, v):
        pattern=re.compile(r"^biolink:[A-Z][A-Za-z]+$")
        if isinstance(v,list):
            for element in v:
                if not pattern.match(element):
                    raise ValueError(f"Invalid category format: {element}")
        elif isinstance(v,str):
            if not pattern.match(v):
                raise ValueError(f"Invalid category format: {v}")
        return v


# Model rebuild
# see https://pydantic-docs.helpmanual.io/usage/models/#rebuilding-a-model
ProvActivity.model_rebuild()
ProvEntity.model_rebuild()
OntologyClass.model_rebuild()
Annotation.model_rebuild()
QuantityValue.model_rebuild()
Entity.model_rebuild()
DissectionRoiPolygon.model_rebuild()
NamedThing.model_rebuild()
Attribute.model_rebuild()
TaxonomicRank.model_rebuild()
OrganismTaxon.model_rebuild()
PhysicalEssenceOrOccurrent.model_rebuild()
PhysicalEssence.model_rebuild()
PhysicalEntity.model_rebuild()
Occurrent.model_rebuild()
ActivityAndBehavior.model_rebuild()
Activity.model_rebuild()
Procedure.model_rebuild()
DissectionRoiDelineation.model_rebuild()
TissueDissection.model_rebuild()
CellDissociation.model_rebuild()
CellEnrichment.model_rebuild()
EnrichedCellSampleSplitting.model_rebuild()
CellBarcoding.model_rebuild()
CdnaAmplification.model_rebuild()
LibraryConstruction.model_rebuild()
LibraryPooling.model_rebuild()
SubjectOfInvestigation.model_rebuild()
MaterialSample.model_rebuild()
BrainSlab.model_rebuild()
TissueSample.model_rebuild()
DissociatedCellSample.model_rebuild()
EnrichedCellSample.model_rebuild()
BarcodedCellSample.model_rebuild()
AmplifiedCdna.model_rebuild()
Library.model_rebuild()
LibraryAliquot.model_rebuild()
LibraryPool.model_rebuild()
ThingWithTaxon.model_rebuild()
Donor.model_rebuild()
BiologicalEntity.model_rebuild()
GenomicEntity.model_rebuild()
ChemicalEntityOrGeneOrGeneProduct.model_rebuild()
MacromolecularMachineMixin.model_rebuild()
GeneOrGeneProduct.model_rebuild()
Gene.model_rebuild()
Genome.model_rebuild()

