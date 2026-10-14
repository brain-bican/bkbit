"""Tests for filemanifest2jsonld (Brain Knowledge Platform file manifest -> DigitalAsset)."""

import json

from click.testing import CliRunner

from bkbit.data_translators.file_manifest_translator import (
    filemanifest2jsonld,
    process_row,
)
from bkbit.models import library_generation as lg

ROW = {
    "Project ID": "P1",
    "Specimen ID": "LA-ABC123",
    "File Name": "S1_S1_L001_R1_001.fastq.gz",
    "Checksum": "d41d8cd98f00b204e9800998ecf8427e",
    "File Type": "fastq",
    "Archive": "NEMO",
    "Archive URI": "s3://bucket/S1_S1_L001_R1_001.fastq.gz",
}


def test_content_url_is_multivalued():
    """The schema makes content_url multivalued, so the model must accept a list."""
    asset = lg.DigitalAsset(id="NEMO:x", content_url=["s3://a", "s3://b"])
    assert asset.content_url == ["s3://a", "s3://b"]


def test_process_row():
    digital_obj, checksum_obj, specimen_id = process_row(ROW)
    assert digital_obj.id == "NEMO:S1_S1_L001_R1_001.fastq.gz"
    assert digital_obj.content_url == [ROW["Archive URI"]]
    assert digital_obj.was_derived_from == "NIMP:LA-ABC123"
    assert digital_obj.data_type == "R1"
    assert digital_obj.digest == [checksum_obj.id]
    assert checksum_obj.value == ROW["Checksum"]
    assert specimen_id == "LA-ABC123"


def test_cli_writes_jsonld_and_aliquot_list():
    runner = CliRunner()
    with runner.isolated_filesystem():
        with open("manifest.csv", "w", encoding="utf-8") as f:
            f.write(",".join(ROW) + "\n" + ",".join(ROW.values()) + "\n")
        result = runner.invoke(filemanifest2jsonld, ["-l", "manifest.csv"])
        assert result.exit_code == 0, result.output
        graph = json.loads(result.output)["@graph"]
        assert [obj["category"] for obj in graph] == [
            ["bican:DigitalAsset"],
            ["bican:Checksum"],
        ]
        with open("file_manifest_library_aliquots.txt", encoding="utf-8") as f:
            assert f.read().split() == ["LA-ABC123"]
