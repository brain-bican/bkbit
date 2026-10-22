"""Tests for the Donor / library_generation model split in specimen2jsonld."""

import pytest

from bkbit.data_translators.library_generation_translator import (
    CATEGORY_TO_CLASS,
    CONTEXT,
    SpecimenPortal,
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

# donor.Donor's name and xref have NIMP_resource_type and NIMP_variable_name
# swapped (variable name "Donor"), so the translator cannot find their values.
DONOR_MAPPING_SWAPPED = pytest.mark.xfail(
    strict=True, reason="donor model swaps NIMP_resource_type/NIMP_variable_name"
)


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


@DONOR_MAPPING_SWAPPED
def test_donor_name_and_xref():
    d = SpecimenPortal("token").generate_bican_object(DONOR_RECORD)
    assert d.name == "C57BL6J-672032"
    # xref is multivalued; a single NIMP value must not be split into characters
    assert d.xref == ["DO-GINI5305"]


def test_nimp_variable_name_mapping():
    la = SpecimenPortal("token").generate_bican_object(
        {
            "id": "LA-1",
            "category": "Library Aliquot",
            "record": {"library_aliquot_local_name": "MyAliquot-01"},
        }
    )
    assert la.name == "MyAliquot-01"


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
