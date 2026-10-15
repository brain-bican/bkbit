"""Gff3.parse_url must keep NCBI assembly names whole, underscores included."""

import pytest

from bkbit.data_translators import genome_annotation_translator as gat

NCBI_BASE = "https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/"


@pytest.mark.parametrize(
    "path, taxon, release, accession, name",
    [
        # Pattern 1: <taxon>/<release>/<accession>_<name>/<accession>_<name>_genomic.gff.gz
        (
            "9544/103/GCF_003339765.1_Mmul_10/GCF_003339765.1_Mmul_10_genomic.gff.gz",
            "9544", "103", "GCF_003339765.1", "Mmul_10",
        ),
        (
            "27679/102/GCF_016699345.1_BCM_Sbol_2.0/GCF_016699345.1_BCM_Sbol_2.0_genomic.gff.gz",
            "27679", "102", "GCF_016699345.1", "BCM_Sbol_2.0",
        ),
        (
            "9823/106/GCF_000003025.6_Sscrofa11.1/GCF_000003025.6_Sscrofa11.1_genomic.gff.gz",
            "9823", "106", "GCF_000003025.6", "Sscrofa11.1",
        ),
        # Pattern 2: <taxon>/<accession>-<release>/<accession>_<name>_genomic.gff.gz
        (
            "9986/GCF_009806435.1-RS_2023_02/GCF_009806435.1_UM_NZW_1.0_genomic.gff.gz",
            "9986", "RS_2023_02", "GCF_009806435.1", "UM_NZW_1.0",
        ),
        (
            "9361/GCF_030445035.1-RS_2023_07/GCF_030445035.1_mDasNov1.hap2_genomic.gff.gz",
            "9361", "RS_2023_07", "GCF_030445035.1", "mDasNov1.hap2",
        ),
    ],
)
def test_parse_ncbi_url(path, taxon, release, accession, name):
    gff3 = gat.Gff3(NCBI_BASE + path)
    metadata = gff3.parse_url()
    assert metadata["taxonid"] == taxon
    assert metadata["release_version"] == release
    assert metadata["assembly_accession"] == accession
    assert metadata["assembly_name"] == name
