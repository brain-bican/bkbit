"""Tests for the Donor / library_generation model split in specimen2jsonld."""

from bkbit.data_translators.library_generation_translator import (
    CATEGORY_TO_CLASS,
    CONTEXT,
    SpecimenPortal,
    derived_classes,
)
from bkbit.models import donor
from bkbit.models import library_generation as lg

DONOR_RECORD = {
    "id": "DO-GINI5305",
    "category": "Donor",
    "record": {
        "sex": "Female",
        "age_at_death_unit": "days",
        "age_at_death_reference_point": "birth",
        "age_at_death_value": "0",
        "donor_species": "NCBITaxon:10090",
        "donor_nhash_id": "DO-GINI5305",
        "donor_local_name": "C57BL6J-672032",
        "post_mortem_interval": "12.5",
    },
}

FASTQ_URL = "https://data.nemoarchive.org/biccn/grant/u01_lein/lein/transcriptome/sncell/10x_v3/mouse/raw/LA-1/"

ALIQUOT_RECORD = {
    "id": "LA-1",
    "category": "Library Aliquot",
    "record": {
        "library_aliquot_local_name": "MyAliquot-01",
        "nemo_aliquot_fastq_public_url": FASTQ_URL,
    },
}


def test_donor_uses_donor_model():
    assert CATEGORY_TO_CLASS["Donor"] is donor.Donor
    assert CATEGORY_TO_CLASS["Tissue"] is lg.TissueSample
    assert CATEGORY_TO_CLASS["ROI"] is lg.DissectionRoiPolygon


def test_donor_fields():
    d = SpecimenPortal("token").generate_bican_object(DONOR_RECORD)
    assert isinstance(d, donor.Donor)
    assert d.sex == donor.Sex.female
    assert d.donor_species == "NCBITaxon:10090"
    assert d.age_at_death_value == 0.0
    assert d.post_mortem_interval == 12.5


def test_donor_name_and_xref():
    d = SpecimenPortal("token").generate_bican_object(DONOR_RECORD)
    assert d.name == "C57BL6J-672032"
    # xref is multivalued; a single NIMP value must not be split into characters
    assert d.xref == ["NIMP:DO-GINI5305"]


def test_nimp_variable_name_mapping():
    la = SpecimenPortal("token").generate_bican_object(ALIQUOT_RECORD)
    assert la.name == "MyAliquot-01"


def test_xref_already_prefixed_is_kept():
    record = {
        **DONOR_RECORD,
        "record": {**DONOR_RECORD["record"], "donor_nhash_id": "NIMP:DO-GINI5305"},
    }
    assert SpecimenPortal("token").generate_bican_object(record).xref == ["NIMP:DO-GINI5305"]


def test_digital_asset_declared_from_library_aliquot():
    assert [cls for cls, _ in derived_classes("Library Aliquot")] == [lg.DigitalAsset]
    assert derived_classes("Donor") == ()


def test_digital_asset_from_library_aliquot():
    derived = SpecimenPortal("token").generate_derived_objects(ALIQUOT_RECORD, "LA-1")
    assert list(derived) == ["LA-1/DigitalAsset"]
    asset = derived["LA-1/DigitalAsset"]
    assert isinstance(asset, lg.DigitalAsset)
    assert asset.content_url == [FASTQ_URL]
    assert asset.was_derived_from == "LA-1"
    # nothing else is read off the aliquot record
    assert asset.name is None


def test_no_digital_asset_without_url():
    record = {**ALIQUOT_RECORD, "record": {"library_aliquot_local_name": "MyAliquot-01"}}
    assert SpecimenPortal("token").generate_derived_objects(record, "LA-1") == {}


def test_digital_asset_links_to_aliquot_id(monkeypatch):
    """Bottom-up parsing rewrites was_derived_from from the NHash ID to the aliquot's id."""
    from bkbit.data_translators import library_generation_translator as t

    monkeypatch.setattr(
        t, "get_ancestors", lambda nhash_id, token: {"data": {"LA-1": {"edges": {}}}}
    )
    monkeypatch.setattr(t, "get_data", lambda nhash_id, token: {"data": ALIQUOT_RECORD})
    sp = SpecimenPortal("token")
    sp.parse_nhash_id_bottom_up("LA-1")
    assert sp.generated_objects["LA-1/DigitalAsset"].was_derived_from == (
        sp.generated_objects["LA-1"].id
    )


def test_enum_match_is_case_insensitive():
    for nimp_value, expected in [("Male", donor.Sex.male), ("Female", donor.Sex.female)]:
        record = {**DONOR_RECORD, "record": {**DONOR_RECORD["record"], "sex": nimp_value}}
        assert SpecimenPortal("token").generate_bican_object(record).sex == expected


def test_multivalued_builtin_list():
    assert SpecimenPortal.get_field_type(list[str] | None) == (True, str)
    assert SpecimenPortal.get_field_type(str | None) == (False, str)


def test_context_includes_donor():
    assert any(c.endswith("/donor.context.jsonld") for c in CONTEXT)
    assert any(c.endswith("/library_generation.context.jsonld") for c in CONTEXT)


def test_top_down_links_use_bkbit_ids(monkeypatch):
    """Descendant parsing must not leave NHash IDs in was_derived_from."""
    from bkbit.data_translators import library_generation_translator as t

    records = {
        "LI-1": {"id": "LI-1", "category": "Library", "record": {}},
        "LA-1": ALIQUOT_RECORD,
    }
    parents = {"LI-1": ["AC-OUTSIDE"], "LA-1": ["LI-1"]}
    monkeypatch.setattr(
        t, "get_descendants", lambda nhash_id, token: {"data": {"LI-1": {}, "LA-1": {}}}
    )
    monkeypatch.setattr(t, "get_data", lambda nhash_id, token: {"data": records[nhash_id]})
    monkeypatch.setattr(
        t,
        "get_ancestors",
        lambda nhash_id, token: {
            "data": {nhash_id: {"edges": {"has_parent": parents[nhash_id]}}}
        },
    )
    sp = SpecimenPortal("token")
    sp.parse_nhash_id_top_down("LI-1")
    objs = sp.generated_objects
    assert objs["LA-1"].was_derived_from == objs["LI-1"].id
    assert objs["LA-1/DigitalAsset"].was_derived_from == objs["LA-1"].id
    # the starting node's parent was not generated, so there is nothing to link to
    assert objs["LI-1"].was_derived_from is None
    assert all(
        o.was_derived_from is None or o.was_derived_from.startswith("urn:bkbit:")
        for o in objs.values()
    )
