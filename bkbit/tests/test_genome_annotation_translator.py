import pytest
import hashlib
from bkbit.data_translators.genome_annotation_translator import Gff3
from bkbit.models import genome_annotation as ga

@pytest.mark.parametrize(
    "url, assembly_accession, expected_output",
    [
        # Valid NCBI URL (where url format is: */release_version/*)
        # Metadata listed here: https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/106/GCF_000003025.6_Sscrofa11.1/README_Sus_scrofa_annotation_release_106
        (
            "https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/106/GCF_000003025.6_Sscrofa11.1/GCF_000003025.6_Sscrofa11.1_genomic.gff.gz",
            None,
            {
                "authority": ga.AuthorityType.NCBI,
                "taxonid": "9823",
                "release_version": "106",
                "assembly_accession": "GCF_000003025.6",
                "assembly_name": "Sscrofa11.1",
            }
        ),
        # Valid NCBI URL (where url format is: */assembly_accession-release_version/*)
        # Metadata listed here: 
        (
            "https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9361/GCF_030445035.1-RS_2023_07/GCF_030445035.1_mDasNov1.hap2_genomic.gff.gz",
            None,
            {
                "authority": ga.AuthorityType.NCBI,
                "taxonid": "9361",
                "release_version": "RS_2023_07",
                "assembly_accession": "GCF_030445035.1",
                "assembly_name": "mDasNov1.hap2",
            }
        ),
        # Valid Ensembl URL
        (
            "https://ftp.ensembl.org/pub/release-110/gff3/homo_sapiens/Homo_sapiens.GRCh38.110.gff3.gz",
            "GCF_000001405.39",
            {
                "authority": ga.AuthorityType.ENSEMBL,
                "taxonid": "9606",
                "release_version": "110",
                "assembly_accession": "GCF_000001405.39",
                "assembly_name": "GRCh38",
            }
            
        ),
        # Unsupported Authority URL
        (
            "http://www.treeshrewdb.org/data/TS_3.0.genomeannotation.gtf.gz",
            None,
            None
        ),
        # Unsupported Data Format 
        (
            "https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9407/101/GCF_014176215.1_mRouAeg1.p/GCF_014176215.1_mRouAeg1.p_genomic.gtf.gz",
            None,
            None
        ),
        # Invalid Ensembl URL (missing genome version)
        (
            "https://ftp.ensembl.org/pub/gff3/homo_sapiens/Homo_sapiens.GRCh38.gff3.gz",
            None,
            None
        ),
        # Invalid NCBI URL (missing release version)
        (
            "https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/GCF_000003025.6_Sscrofa11.1/GCF_000003025.6_Sscrofa11.1_genomic.gff.gz",
            None,
            None
        )
    ],
)
def test_parse_url(url, assembly_accession, expected_output):
    assert Gff3.parse_url(url, assembly_accession) == expected_output

# @pytest.mark.parametrize(
#     "input1, input2",
#     [
#         # Identical inputs should produce the same output
#         (
#             {"a": 1, "b": 2, "c": 6},
#             {"a": 1, "b": 2, "c": 6}
#         ),
#         # Different order of keys should not effect the output 
#         (
#             {"a": 1, "b": 2, "c": 6},
#             {"b": 2, "c": 6, "a": 1}
#         ),
#         # Empty dictionary
#         (
#             {},
#             {}
#         )
#     ],
# )
# def test_generate_object_id_inputs_produces_same_output(input1, input2):
#     assert Gff3.generate_object_id(input1) == Gff3.generate_object_id(input2) 

# @pytest.mark.parametrize(
#     "input1, input2",
#     [
#         # Different inputs should produce different output
#         (
#             {"a": 1, "b": 2, "c": 6},
#             {"a": 1, "b": 2, "c": 7}
#         ),
#         (
#             {"a": 1, "b": 2, "c": 6},
#             {"b": 2, "c": 6}
#         )
#     ],
# )
# def test_generate_object_id_inputs_produces_different_output(input1, input2):
#     assert Gff3.generate_object_id(input1) != Gff3.generate_object_id(input2) 

# @pytest.mark.parametrize(
#     "content_url, expected_md5_hash",
#     [
#         # NCBI URL
#         # Checksum obtained from: https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/106/GCF_000003025.6_Sscrofa11.1/md5checksums.txt
#         (
#             "https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/106/GCF_000003025.6_Sscrofa11.1/GCF_000003025.6_Sscrofa11.1_genomic.gff.gz",
#             "b010f8d53476725e8a01424a0dd2cecf"
#         ),
#     ]
# )
# @pytest.mark.slow
# def test_download_gff_file_md5_hash(content_url, expected_md5_hash):
#     gzip_file, hash_values = Gff3.download_gff_file(content_url)
#     assert hash_values.get("MD5") == expected_md5_hash