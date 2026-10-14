"""gff2jsonld must not leave downloaded or decompressed GFF3 files behind.

The download is replaced with a local gzip file, so these tests run offline.
"""

import gzip
import io
import json
import tempfile

import pytest
from click.testing import CliRunner

from bkbit.data_translators import genome_annotation_translator as gat

NCBI_URL = (
    "https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/106/"
    "GCF_000003025.6_Sscrofa11.1/GCF_000003025.6_Sscrofa11.1_genomic.gff.gz"
)
GFF3 = (
    "##gff-version 3\n"
    "NC_010443.5\tGnomon\tgene\t1\t100\t.\t+\t.\t"
    "ID=gene-ABC1;Dbxref=GeneID:100001;Name=ABC1;description=gene one;gene_biotype=protein_coding\n"
    "\n"
    "NC_010443.5\tGnomon\tmRNA\t1\t100\t.\t+\t.\tID=rna-1;Parent=gene-ABC1\n"
    "NC_010443.5\tGnomon\tgene\t200\t300\t.\t-\t.\t"
    "ID=gene-XYZ2;Dbxref=GeneID:100002;Name=XYZ2;description=gene two;gene_biotype=lncRNA\n"
)


@pytest.fixture
def offline(tmp_path, monkeypatch):
    """Serve GFF3 for any URL and send every temp file to an empty directory."""
    payload = gzip.compress(GFF3.encode(), mtime=0)

    class Response(io.BytesIO):
        headers = {"content-length": str(len(payload))}

    monkeypatch.setattr(gat.urllib.request, "urlopen", lambda url: Response(payload))
    temp_dir = tmp_path / "tmp"
    temp_dir.mkdir()
    monkeypatch.setattr(tempfile, "tempdir", str(temp_dir))
    monkeypatch.setenv("BKBIT_NO_DOWNLOAD", "1")
    return temp_dir


def test_cli_leaves_no_temp_files(offline):
    result = CliRunner().invoke(gat.gff2jsonld, [NCBI_URL])
    assert result.exit_code == 0, result.output
    assert list(offline.iterdir()) == []


def test_cli_output(offline):
    result = CliRunner().invoke(gat.gff2jsonld, [NCBI_URL])
    graph = json.loads(result.output[result.output.index("{") :])["@graph"]
    genes = sorted(o["symbol"] for o in graph if "GeneAnnotation" in str(o["category"]))
    assert genes == ["ABC1", "XYZ2"]


def test_cleanup_runs_when_parsing_fails(offline, monkeypatch):
    def broken_parse(self, *args, **kwargs):
        raise RuntimeError("parse failed")

    monkeypatch.setattr(gat.Gff3, "parse", broken_parse)
    result = CliRunner().invoke(gat.gff2jsonld, [NCBI_URL])
    assert isinstance(result.exception, RuntimeError)
    assert list(offline.iterdir()) == []


def test_python_api_cleanup(offline):
    gff3 = gat.Gff3(NCBI_URL)
    gff3.setup()
    gff3.parse_gff3_file()
    gff3.parse()
    assert {g.symbol for g in gff3.gene_annotations.values()} == {"ABC1", "XYZ2"}
    gff3.cleanup()
    assert list(offline.iterdir()) == []
    gff3.cleanup()  # safe to call twice


def test_parse_reads_uncompressed_file(tmp_path, offline):
    path = tmp_path / "plain.gff3"
    path.write_text(GFF3)
    gff3 = gat.Gff3(NCBI_URL)
    gff3.setup()
    gff3.parse_gff3_file()
    gff3.cleanup()
    gff3.gff_file = str(path)
    gff3.parse()
    assert len(gff3.gene_annotations) == 2
    assert path.exists()  # files the caller supplied are never deleted


def test_failed_download_leaves_no_temp_files(offline, monkeypatch):
    class Broken(io.BytesIO):
        headers = {"content-length": "100"}

        def read(self, size=-1):
            raise ConnectionResetError("connection dropped")

    monkeypatch.setattr(gat.urllib.request, "urlopen", lambda url: Broken())
    result = CliRunner().invoke(gat.gff2jsonld, [NCBI_URL])
    assert isinstance(result.exception, ConnectionResetError)
    assert list(offline.iterdir()) == []
