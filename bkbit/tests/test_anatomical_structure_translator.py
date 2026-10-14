"""Tests for the anatomical structure CSV translator."""

import json

import pytest

from bkbit.data_translators.anatomical_structure_translator import AnS

TERM_SET_HEADER = "label,name,description,version,parcellation_terminology_label,parcellation_term_set_order,parcellation_parent_term_set_label"
TERM_HEADER = "name,symbol,description,version,parcellation_term_set_label,parcellation_terminology_label,parcellation_term_identifier,parcellation_term_order,parcellation_parent_term_set_label,parcellation_parent_term_identifier"


def write_csv(path, header, row):
    path.write_text(header + "\n" + row + "\n", encoding="utf-8")


def test_term_set_and_term_carry_version(tmp_path):
    """ParcellationTermSet and ParcellationTerm require a version in the model."""
    write_csv(tmp_path / "term_set.csv", TERM_SET_HEADER, "ex:TS,Term set,d,1,ex:T,1,")
    write_csv(
        tmp_path / "term.csv", TERM_HEADER, "Cortex,CTX,d,1,ex:TS,ex:T,ex:PT1,1,,"
    )
    AnS().provide_data(str(tmp_path), "out.jsonld")
    graph = json.loads((tmp_path / "out.jsonld").read_text())["@graph"]
    by_id = {obj["id"]: obj for obj in graph}
    assert by_id["ex:TS"]["version"] == "1"
    assert by_id["ex:PT1"]["version"] == "1"
    assert by_id["ex:PT1"]["part_of_parcellation_term_set"] == "ex:TS"


@pytest.mark.parametrize("header", [TERM_SET_HEADER, TERM_HEADER])
def test_csv_without_version_is_an_error(tmp_path, header):
    """A CSV missing only 'version' must fail loudly, not be skipped."""
    columns = [c for c in header.split(",") if c != "version"]
    write_csv(tmp_path / "old.csv", ",".join(columns), ",".join("x" for _ in columns))
    with pytest.raises(ValueError, match="'version'"):
        AnS().read_data(str(tmp_path / "old.csv"))


def test_unrelated_csv_is_still_skipped(tmp_path):
    write_csv(tmp_path / "other.csv", "foo,bar", "1,2")
    ans = AnS()
    ans.read_data(str(tmp_path / "other.csv"))
    assert ans.parcellation_term == [] and ans.parcellation_term_set == []
