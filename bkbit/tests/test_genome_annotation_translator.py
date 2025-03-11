from bkbit.data_translators.genome_annotation_translator import Gff3
from bkbit.models import genome_annotation as ga
import pytest
import hashlib


# def test_generate_organism_taxon():
#     test_org_taxon_1 = Gff3.generate_organism_taxon('9606')
#     temp = ga.OrganismTaxon(id='urn:bkbit:94ce74f4f8189281ec98dcb3803708f78ef3ffc207afc3d6030cb920e63029b5', iri='http://purl.obolibrary.org/obo/NCBITaxon_9606', category=['biolink:OrganismTaxon'], type=['bican:OrganismTaxon'], name='human', description=None, has_attribute=None, deprecated=None, provided_by=None, xref=['NCBITaxon:9606'], full_name='Homo sapiens', synonym=None, has_taxonomic_rank=None)


#     assert test_org_taxon_1 == temp
#     # # Check if the return type is an instance of OrganismTaxon
#     # assert isinstance(test_org_taxon_1, ga.OrganismTaxon)
#     # # Check if the return object has the correct "full_name" value
#     # assert test_org_taxon_1.full_name == 'Homo sapiens'
#     # # Check if the return object has the correct "name" value
#     # assert test_org_taxon_1.name  == 'human'
#     # # Check if the return object has the correct "xref" value
#     # assert Gff3.generate_organism_taxon('9606').xref[0] == 'NCBITaxon:9606'

#     # # Check if the function is deterministic given the same input 
#     # test_org_taxon_2 = Gff3.generate_organism_taxon('9606')
#     # assert test_org_taxon_1.id == test_org_taxon_2.id 


@pytest.mark.parametrize(
    "url, expected_output",
    [
        # Valid NCBI URL (where url is: */release_version/*)
        # Metadata listed here: https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/106/GCF_000003025.6_Sscrofa11.1/README_Sus_scrofa_annotation_release_106
        (
            "https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/106/GCF_000003025.6_Sscrofa11.1/GCF_000003025.6_Sscrofa11.1_genomic.gff.gz",
            {
                "authority": ga.AuthorityType.NCBI,
                "taxonid": "9823",
                "release_version": "106",
                "assembly_accession": "GCF_000003025.6",
                "assembly_name": "Sscrofa11.1",
            }
        ),
        # Valid NCBI URL (where url is: */assembly_accession-release_version/*)
        # Metadata listed here: 
        (
            "https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9361/GCF_030445035.1-RS_2023_07/GCF_030445035.1_mDasNov1.hap2_genomic.gff.gz",
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
            {
                "authority": ga.AuthorityType.ENSEMBL,
                "release_version": "110",
                "scientific_name": "Homo_sapiens",
                "assembly_name": "GRCh38",
            }
        ),
        # Unsupported Authority URL
        (
            "http://www.treeshrewdb.org/data/TS_3.0.genomeannotation.gtf.gz",
            None
        ),
        # Invalid Ensembl URL (missing genome version)
        (
            "https://ftp.ensembl.org/pub/gff3/homo_sapiens/Homo_sapiens.GRCh38.gff3.gz",
            None
        ),
        # Invalid NCBI URL (missing release version)
        (
            "https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9823/GCF_000003025.6_Sscrofa11.1/GCF_000003025.6_Sscrofa11.1_genomic.gff.gz",
            None
        ),
        # Valid NCBI URL but in data gtf format 
        (
            "https://ftp.ncbi.nlm.nih.gov/genomes/all/annotation_releases/9407/101/GCF_014176215.1_mRouAeg1.p/GCF_014176215.1_mRouAeg1.p_genomic.gtf.gz",
            None
        )
    ],
)
def test_parse_url(url, expected_output):
    assert Gff3.parse_url(url) == expected_output

@pytest.mark.parametrize(
    "input1, input2",
    [
        # Identical inputs should produce the same output
        (
            {"a": 1, "b": 2, "c": 6},
            {"a": 1, "b": 2, "c": 6}
        ),
        # Different order of keys should not effect the output 
        (
            {"a": 1, "b": 2, "c": 6},
            {"b": 2, "c": 6, "a": 1}
        ),
        # Empty dictionary
        (
            {},
            {}
        )
    ],
)
def test_generate_object_id_inputs_produces_same_output(input1, input2):
    assert Gff3.generate_object_id(input1) == Gff3.generate_object_id(input2) 

@pytest.mark.parametrize(
    "input1, input2",
    [
        # Different inputs should produce different output
        (
            {"a": 1, "b": 2, "c": 6},
            {"a": 1, "b": 2, "c": 7}
        ),
        (
            {"a": 1, "b": 2, "c": 6},
            {"b": 2, "c": 6}
        )
    ],
)
def test_generate_object_id_inputs_produces_different_output(input1, input2):
    assert Gff3.generate_object_id(input1) != Gff3.generate_object_id(input2) 