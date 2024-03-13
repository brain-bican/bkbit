import pytest
from bkbit.scripts import gfftranslator as gt
from bkbit.models import kbmodel
import hashlib


@pytest.fixture()
def df_ensembl_human_one_row(tmp_path):
    # create a temporary directory and file
    temp_dir = tmp_path / "gff3_temp_dir"
    temp_dir.mkdir()

    # create a file inside the temporary directory
    temp_file = temp_dir / "ensembl_data.gff"
    temp_file.write_text("##gff-version 3\n1	ensembl_havana	gene	450740	451678	.	-	.	ID=gene:ENSG00000284733;Name=OR4F29;biotype=protein_coding;description=olfactory receptor family 4 subfamily F member 29 [Source:HGNC Symbol%3BAcc:HGNC:31275];gene_id=ENSG00000284733;logic_name=ensembl_havana_gene_homo_sapiens;version=2")

    # check if the file exists
    assert temp_file.is_file()

    # read the file's contents
    return str(temp_file)

@pytest.fixture()
def df_ensembl_duplicates(tmp_path):
    # create a temporary directory and file
    temp_dir = tmp_path / "gff3_temp_dir"
    temp_dir.mkdir()

    # create a file inside the temporary directory
    temp_file = temp_dir / "ensembl_data.gff"
    temp_file.write_text("##gff-version 3\n1	ensembl_havana	gene	450740	451678	.	-	.	ID=gene:ENSG00000284733;Name=OR4F29;biotype=protein_coding;description=olfactory receptor family 4 subfamily F member 29 [Source:HGNC Symbol%3BAcc:HGNC:31275];gene_id=ENSG00000284733;logic_name=ensembl_havana_gene_homo_sapiens;version=2\n1	ensembl_havana	gene	450740	451678	.	-	.	ID=gene:ENSG00000284733;Name=OR4F29;biotype=protein_coding;description=olfactory receptor family 4 subfamily F member 29 [Source:HGNC Symbol%3BAcc:HGNC:31275];gene_id=ENSG00000284733;logic_name=ensembl_havana_gene_homo_sapiens;version=2")

    # check if the file exists
    assert temp_file.is_file()

    # read the file's contents
    return str(temp_file)

@pytest.fixture()
def gff_params_ensembl_human():
    taxon_id = '9606'
    assembly_id = 'GCF_000001405.40'
    assembly_version = '40'
    assembly_label = "GRCH38.p14"
    genome_label = 'ENSEMBL-9606-110'
    genome_version = '110'
    genome_authority = 'ensembl'
    hash_functions = ['SHA256']
    return {'taxon_id': taxon_id, 'assembly_id': assembly_id, 'assembly_version': assembly_version, 'assembly_label': assembly_label, 'genome_label': genome_label, 'genome_version': genome_version, 'genome_authority': genome_authority, 'hash_functions': hash_functions}
  
def test_parse_ensembl_one_row(df_ensembl_human_one_row, gff_params_ensembl_human):

    genome_label = 'ENSEMBL-9606-110'
    genome_version = '110'
    feature_filter = ['gene']

    gff = gt.Gff3(df_ensembl_human_one_row, **gff_params_ensembl_human)

    expected_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:9606', full_name = 'Homo sapiens', name = 'human', iri = 'http://purl.obolibrary.org/obo/NCBITaxon_9606')
    expected_genome_assembly = kbmodel.GenomeAssembly(id = "NCBIAssembly:GCF_000001405.40", in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, version = '40', name = 'GRCH38.p14')
    expected_checksums = [kbmodel.Checksum(id = gff.checksums[0].id, checksum_algorithm = kbmodel.DigestType.SHA256, value = hashlib.sha256(df_ensembl_human_one_row.encode('utf-8')).hexdigest())]
    expected_genome_annotation = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + genome_label.upper(), digest = [expected_checksums[0].id], content_url = [df_ensembl_human_one_row], reference_assembly = expected_genome_assembly.id, version = genome_version, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'ENSEMBL Homo sapiens Annotation Release 110', authority = kbmodel.AuthorityType.ENSEMBL)
    gene_annotation = kbmodel.GeneAnnotation(id = 'ENSEMBL:ENSG00000284733', source_id = 'ENSG00000284733', symbol = 'OR4F29', name = 'OR4F29', molecular_type = 'protein_coding', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'olfactory receptor family 4 subfamily F member 29')
    expected_gene_annotations = {gene_annotation:gene_annotation}
    gff.parse(feature_filter)
    assert gff.gene_annotations == expected_gene_annotations


def test_ensembl_duplicates(df_ensembl_duplicates, gff_params_ensembl_human):

    genome_label = 'ENSEMBL-9606-110'
    genome_version = '110'
    feature_filter = ['gene']

    gff = gt.Gff3(df_ensembl_duplicates, **gff_params_ensembl_human)

    expected_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:9606', full_name = 'Homo sapiens', name = 'human', iri = 'http://purl.obolibrary.org/obo/NCBITaxon_9606')
    expected_genome_assembly = kbmodel.GenomeAssembly(id = "NCBIAssembly:GCF_000001405.40", in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, version = '40', name = 'GRCH38.p14')
    expected_checksums = [kbmodel.Checksum(id = gff.checksums[0].id, checksum_algorithm = kbmodel.DigestType.SHA256, value = hashlib.sha256(df_ensembl_duplicates.encode('utf-8')).hexdigest())]
    expected_genome_annotation = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + genome_label.upper(), digest = [expected_checksums[0].id], content_url = [df_ensembl_duplicates], reference_assembly = expected_genome_assembly.id, version = genome_version, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'ENSEMBL Homo sapiens Annotation Release 110', authority = kbmodel.AuthorityType.ENSEMBL)
    gene_annotation = kbmodel.GeneAnnotation(id = 'ENSEMBL:ENSG00000284733', source_id = 'ENSG00000284733', symbol = 'OR4F29', name = 'OR4F29', molecular_type = 'protein_coding', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'olfactory receptor family 4 subfamily F member 29')
    expected_gene_annotations = {gene_annotation:gene_annotation}
    gff.parse(feature_filter)
    assert gff.gene_annotations == expected_gene_annotations