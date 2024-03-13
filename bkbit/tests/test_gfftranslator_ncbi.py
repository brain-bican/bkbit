import pytest
from bkbit.scripts import gfftranslator as gt
from bkbit.models import kbmodel
import hashlib


@pytest.fixture()
def df_ncbi_human_one_row(tmp_path):
    # create a temporary directory and file
    temp_dir = tmp_path / "gff3_temp_dir"
    temp_dir.mkdir()

    # create a file inside the temporary directory
    temp_file = temp_dir / "ncbi_data.gff"
    temp_file.write_text("##gff-version 3\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA")

    return str(temp_file)


@pytest.fixture()
def df_ncbi_duplicates(tmp_path):
    # create a temporary directory and file
    temp_dir = tmp_path / "gff3_temp_dir"
    temp_dir.mkdir()

    # create a file inside the temporary directory
    temp_file = temp_dir / "ncbi_duplicates_data.gff"
    temp_file.write_text("##gff-version 3\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA")

    return str(temp_file)

@pytest.fixture()
def df_ncbi_dbxref(tmp_path):
    # create a temporary directory and file
    temp_dir = tmp_path / "gff3_temp_dir"
    temp_dir.mkdir()

    # create a file inside the temporary directory
    temp_file = temp_dir / "ncbi_dbxref_data.gff"
    # Data: first row has extra occurrences of dbxref (but all prefixes are unique), second row has missing dbxref, third row has multiple occurrences of GeneID prefix in dbxref, fourth row is missing GeneID prefix in dbxref
    temp_file.write_text("##gff-version 3\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730,HGNC:HGNC:52482;Dbxref=Extra:123;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2H;gene_biotype=lncRNA\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730,HGNC:HGNC:52482;Dbxref=GeneID:123;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2H;gene_biotype=lncRNA")

    return str(temp_file)


@pytest.fixture()
def df_ncbi_name(tmp_path):
    # create a temporary directory and file
    temp_dir = tmp_path / "gff3_temp_dir"
    temp_dir.mkdir()

    # create a file inside the temporary directory
    temp_file = temp_dir / "ncbi_name_data.gff"
    # Data: first row has extra occurrences of Name attribute, second row has multiple names provided in Name attribute, third row has no Name attribute, fourth row has exactly one name provided, fifth row has multiple names provided in Name attribute
    temp_file.write_text("##gff-version 3\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730A,HGNC:HGNC:52482;Name=MIR1302-2HG;Name=EXTRANAME;gbkey=Gene;gene=MIR1302-2H;gene_biotype=lncRNA\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730B,HGNC:HGNC:52482;Name=MIR1302-2HG,EXTRANAME;gbkey=Gene;gene=MIR1302-2H;gene_biotype=lncRNA\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730C,HGNC:HGNC:52482;gbkey=Gene;gene=MIR1302-2H;gene_biotype=lncRNA\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730D,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2H;gene_biotype=lncRNA\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730E,HGNC:HGNC:52482;Name=MIR1302-2HG,EXTRANAME;gbkey=Gene;gene=MIR1302-2H;gene_biotype=lncRNA")

    return str(temp_file)

@pytest.fixture()
def df_ncbi_description(tmp_path):
    # create a temporary directory and file
    temp_dir = tmp_path / "gff3_temp_dir"
    temp_dir.mkdir()

    # create a file inside the temporary directory
    temp_file = temp_dir / "ncbi_description_data.gff"
    # Data: first row has description attribute, second row has multiple description attributes, third row is missing description attributes
    temp_file.write_text("##gff-version 3\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730A,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA;description=example description\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730B,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA;description=example description1;description=example description 2\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730C,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA")

    return str(temp_file)

@pytest.fixture()
def df_ncbi_biotype(tmp_path):
    # create a temporary directory and file
    temp_dir = tmp_path / "gff3_temp_dir"
    temp_dir.mkdir()

    # create a file inside the temporary directory
    temp_file = temp_dir / "ncbi_biotype_data.gff"
    # Data: first row has biotype attribute, second row has multiple gene_biotype attributes, third row has multiple biotypes listed within gene_biotype attribute, fourth row is missing gene_biotype attribute
    temp_file.write_text("##gff-version 3\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730A,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730B,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA;gene_biotype=protein_coding\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730C,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA,protein_coding\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730D,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG")

    return str(temp_file)

@pytest.fixture()
def df_ncbi_synonyms(tmp_path):
    # create a temporary directory and file
    temp_dir = tmp_path / "gff3_temp_dir"
    temp_dir.mkdir()

    # create a file inside the temporary directory
    temp_file = temp_dir / "ncbi_synonym_data.gff" 
    # Data: first row has multiple synonyms within one gene_synonym attribute, second row has multiple synonyms across multiple gene_synonym attributes, third row has multiple synonyms across multiple gene_synonym attributes and also includes duplicates
    temp_file.write_text("##gff-version 3\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730A,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA;gene_synonym=S1,S2,S3\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730B,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA;gene_synonym=S1,S2;gene_synonym=S3\nNC_000001.11	Gnomon	gene	29774	35418	.	+	.	ID=gene-MIR1302-2HG;Dbxref=GeneID:107985730C,HGNC:HGNC:52482;Name=MIR1302-2HG;gbkey=Gene;gene=MIR1302-2HG;gene_biotype=lncRNA;gene_synonym=S1,S2;gene_synonym=S2,S3;gene_synonym=S1,S3")
    return str(temp_file)


@pytest.fixture()
def gff_params_ncbi_human():
    taxon_id = '9606'
    assembly_id = 'GCF_000001405.40'
    assembly_version = '40'
    assembly_label = "GRCH38.p14"
    genome_label = 'NCBI-9606-110'
    genome_version = '110'
    genome_authority = 'ncbi'
    hash_functions = ['SHA256']
    return {'taxon_id': taxon_id, 'assembly_id': assembly_id, 'assembly_version': assembly_version, 'assembly_label': assembly_label, 'genome_label': genome_label, 'genome_version': genome_version, 'genome_authority': genome_authority, 'hash_functions': hash_functions}



def test_intialization(df_ncbi_human_one_row, gff_params_ncbi_human):
    genome_label = 'NCBI-9606-110'
    genome_version = '110'


    gff = gt.Gff3(df_ncbi_human_one_row, **gff_params_ncbi_human)
    expected_authority = kbmodel.AuthorityType.NCBI
    expected_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:9606', full_name = 'Homo sapiens', name = 'human', iri = 'http://purl.obolibrary.org/obo/NCBITaxon_9606')
    expected_genome_assembly = kbmodel.GenomeAssembly(id = "NCBIAssembly:GCF_000001405.40", in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, version = '40', name = 'GRCH38.p14')
    expected_checksums = [kbmodel.Checksum(id = gff.checksums[0].id, checksum_algorithm = kbmodel.DigestType.SHA256, value = hashlib.sha256(df_ncbi_human_one_row.encode('utf-8')).hexdigest())]
    expected_genome_annotation = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + genome_label.upper(), digest = [expected_checksums[0].id], content_url = [df_ncbi_human_one_row], reference_assembly = expected_genome_assembly.id, version = genome_version, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'NCBI Homo sapiens Annotation Release 110', authority = kbmodel.AuthorityType.NCBI)
    
    assert gff.authority == expected_authority
    assert gff.organism_taxon == expected_org_taxon
    assert gff.genome_assembly == expected_genome_assembly
    assert gff.checksums == expected_checksums
    assert gff.genome_annotation == expected_genome_annotation


def test_parse_one_row(df_ncbi_human_one_row, gff_params_ncbi_human):
    genome_label = 'NCBI-9606-110'
    genome_version = '110'
    feature_filter = ['gene']

    gff = gt.Gff3(df_ncbi_human_one_row, **gff_params_ncbi_human)

    expected_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:9606', full_name = 'Homo sapiens', name = 'human', iri = 'http://purl.obolibrary.org/obo/NCBITaxon_9606')
    expected_genome_assembly = kbmodel.GenomeAssembly(id = "NCBIAssembly:GCF_000001405.40", in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, version = '40', name = 'GRCH38.p14')
    expected_checksums = [kbmodel.Checksum(id = gff.checksums[0].id, checksum_algorithm = kbmodel.DigestType.SHA256, value = hashlib.sha256(df_ncbi_human_one_row.encode('utf-8')).hexdigest())]
    expected_genome_annotation = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + genome_label.upper(), digest = [expected_checksums[0].id], content_url = [df_ncbi_human_one_row], reference_assembly = expected_genome_assembly.id, version = genome_version, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'NCBI Homo sapiens Annotation Release 110', authority = kbmodel.AuthorityType.NCBI)
    gene_annotation = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730', source_id = '107985730', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    expected_gene_annotations = {gene_annotation.id:gene_annotation}
    gff.parse(feature_filter)
    assert gff.gene_annotations == expected_gene_annotations


def test_duplicates_missing_biotype(df_ncbi_duplicates, gff_params_ncbi_human):
    genome_label = 'NCBI-9606-110'
    genome_version = '110'
    feature_filter = ['gene']

    gff = gt.Gff3(df_ncbi_duplicates, **gff_params_ncbi_human)

    expected_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:9606', full_name = 'Homo sapiens', name = 'human', iri = 'http://purl.obolibrary.org/obo/NCBITaxon_9606')
    expected_genome_assembly = kbmodel.GenomeAssembly(id = "NCBIAssembly:GCF_000001405.40", in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, version = '40', name = 'GRCH38.p14')
    expected_checksums = [kbmodel.Checksum(id = gff.checksums[0].id, checksum_algorithm = kbmodel.DigestType.SHA256, value = hashlib.sha256(df_ncbi_duplicates.encode('utf-8')).hexdigest())]
    expected_genome_annotation = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + genome_label.upper(), digest = [expected_checksums[0].id], content_url = [df_ncbi_duplicates], reference_assembly = expected_genome_assembly.id, version = genome_version, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'NCBI Homo sapiens Annotation Release 110', authority = kbmodel.AuthorityType.NCBI)
    gene_annotation = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730', source_id = '107985730', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    expected_gene_annotations = {gene_annotation.id:gene_annotation}
    gff.parse(feature_filter)
    assert gff.gene_annotations == expected_gene_annotations


def test_dbxref(df_ncbi_dbxref, gff_params_ncbi_human):
    # Data: first row has extra occurrences of dbxref (but all prefixes are unique), second row has missing dbxref, third row has multiple occurrences of GeneID prefix in dbxref, fourth row is missing GeneID prefix in dbxref
    # Expected Output: only the first row should produce a geneannotation object

    genome_label = 'NCBI-9606-110'
    genome_version = '110'
    feature_filter = ['gene']

    gff = gt.Gff3(df_ncbi_dbxref, **gff_params_ncbi_human)

    expected_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:9606', full_name = 'Homo sapiens', name = 'human', iri = 'http://purl.obolibrary.org/obo/NCBITaxon_9606')
    expected_genome_assembly = kbmodel.GenomeAssembly(id = "NCBIAssembly:GCF_000001405.40", in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, version = '40', name = 'GRCH38.p14')
    expected_checksums = [kbmodel.Checksum(id = gff.checksums[0].id, checksum_algorithm = kbmodel.DigestType.SHA256, value = hashlib.sha256(df_ncbi_dbxref.encode('utf-8')).hexdigest())]
    expected_genome_annotation = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + genome_label.upper(), digest = [expected_checksums[0].id], content_url = [df_ncbi_dbxref], reference_assembly = expected_genome_assembly.id, version = genome_version, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'NCBI Homo sapiens Annotation Release 110', authority = kbmodel.AuthorityType.NCBI)
    gene_annotation = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730', source_id = '107985730', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    expected_gene_annotations = {gene_annotation.id:gene_annotation}
    gff.parse(feature_filter)
    assert gff.gene_annotations == expected_gene_annotations

def test_name(df_ncbi_name, gff_params_ncbi_human):
    genome_label = 'NCBI-9606-110'
    genome_version = '110'
    feature_filter = ['gene']

    gff = gt.Gff3(df_ncbi_name, **gff_params_ncbi_human)

    expected_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:9606', full_name = 'Homo sapiens', name = 'human', iri = 'http://purl.obolibrary.org/obo/NCBITaxon_9606')
    expected_genome_assembly = kbmodel.GenomeAssembly(id = "NCBIAssembly:GCF_000001405.40", in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, version = '40', name = 'GRCH38.p14')
    expected_checksums = [kbmodel.Checksum(id = gff.checksums[0].id, checksum_algorithm = kbmodel.DigestType.SHA256, value = hashlib.sha256(df_ncbi_name.encode('utf-8')).hexdigest())]
    expected_genome_annotation = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + genome_label.upper(), digest = [expected_checksums[0].id], content_url = [df_ncbi_name], reference_assembly = expected_genome_assembly.id, version = genome_version, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'NCBI Homo sapiens Annotation Release 110', authority = kbmodel.AuthorityType.NCBI)
    
    ga_A = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730A', source_id = '107985730A', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    ga_B = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730B', source_id = '107985730B', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    ga_C = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730C', source_id = '107985730C', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    ga_D = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730D', source_id = '107985730D', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    ga_E = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730E', source_id = '107985730E', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)

    expected_gene_annotations = {ga_A.id:ga_A, ga_B.id:ga_B, ga_C.id:ga_C, ga_D.id:ga_D, ga_E.id:ga_E}
    gff.parse(feature_filter)
    assert gff.gene_annotations == expected_gene_annotations



def test_definiton(df_ncbi_description, gff_params_ncbi_human):
    genome_label = 'NCBI-9606-110'
    genome_version = '110'
    feature_filter = ['gene']

    gff = gt.Gff3(df_ncbi_description, **gff_params_ncbi_human)

    expected_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:9606', full_name = 'Homo sapiens', name = 'human', iri = 'http://purl.obolibrary.org/obo/NCBITaxon_9606')
    expected_genome_assembly = kbmodel.GenomeAssembly(id = "NCBIAssembly:GCF_000001405.40", in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, version = '40', name = 'GRCH38.p14')
    expected_checksums = [kbmodel.Checksum(id = gff.checksums[0].id, checksum_algorithm = kbmodel.DigestType.SHA256, value = hashlib.sha256(df_ncbi_description.encode('utf-8')).hexdigest())]
    expected_genome_annotation = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + genome_label.upper(), digest = [expected_checksums[0].id], content_url = [df_ncbi_description], reference_assembly = expected_genome_assembly.id, version = genome_version, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'NCBI Homo sapiens Annotation Release 110', authority = kbmodel.AuthorityType.NCBI)
    

    ga_A = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730A', source_id = '107985730A', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'example description')
    ga_B = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730B', source_id = '107985730B', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    ga_C = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730C', source_id = '107985730C', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)

    expected_gene_annotations = {ga_A.id:ga_A, ga_B.id:ga_B, ga_C.id:ga_C}
    gff.parse(feature_filter)
    assert gff.gene_annotations == expected_gene_annotations



def test_biotype(df_ncbi_biotype, gff_params_ncbi_human):
    genome_label = 'NCBI-9606-110'
    genome_version = '110'
    feature_filter = ['gene']

    gff = gt.Gff3(df_ncbi_biotype, **gff_params_ncbi_human)

    expected_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:9606', full_name = 'Homo sapiens', name = 'human', iri = 'http://purl.obolibrary.org/obo/NCBITaxon_9606')
    expected_genome_assembly = kbmodel.GenomeAssembly(id = "NCBIAssembly:GCF_000001405.40", in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, version = '40', name = 'GRCH38.p14')
    expected_checksums = [kbmodel.Checksum(id = gff.checksums[0].id, checksum_algorithm = kbmodel.DigestType.SHA256, value = hashlib.sha256(df_ncbi_biotype.encode('utf-8')).hexdigest())]
    expected_genome_annotation = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + genome_label.upper(), digest = [expected_checksums[0].id], content_url = [df_ncbi_biotype], reference_assembly = expected_genome_assembly.id, version = genome_version, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'NCBI Homo sapiens Annotation Release 110', authority = kbmodel.AuthorityType.NCBI)
    

    ga_A = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730A', source_id = '107985730A', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    ga_B = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730B', source_id = '107985730B', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    ga_C = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730C', source_id = '107985730C', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    ga_D = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730D', source_id = '107985730D', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name)
    
    expected_gene_annotations = {ga_A.id:ga_A, ga_B.id:ga_B, ga_C.id:ga_C, ga_D.id:ga_D}
    gff.parse(feature_filter)
    assert gff.gene_annotations == expected_gene_annotations


def test_synonyms(df_ncbi_synonyms, gff_params_ncbi_human):
    genome_label = 'NCBI-9606-110'
    genome_version = '110'
    feature_filter = ['gene']

    gff = gt.Gff3(df_ncbi_synonyms, **gff_params_ncbi_human)

    expected_org_taxon = kbmodel.OrganismTaxon(id = 'NCBITaxon:9606', full_name = 'Homo sapiens', name = 'human', iri = 'http://purl.obolibrary.org/obo/NCBITaxon_9606')
    expected_genome_assembly = kbmodel.GenomeAssembly(id = "NCBIAssembly:GCF_000001405.40", in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, version = '40', name = 'GRCH38.p14')
    expected_checksums = [kbmodel.Checksum(id = gff.checksums[0].id, checksum_algorithm = kbmodel.DigestType.SHA256, value = hashlib.sha256(df_ncbi_synonyms.encode('utf-8')).hexdigest())]
    expected_genome_annotation = kbmodel.GenomeAnnotation(id = 'bican:annotation-' + genome_label.upper(), digest = [expected_checksums[0].id], content_url = [df_ncbi_synonyms], reference_assembly = expected_genome_assembly.id, version = genome_version, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, description = 'NCBI Homo sapiens Annotation Release 110', authority = kbmodel.AuthorityType.NCBI)
    
    ga_A = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730A', source_id = '107985730A', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, synonym = ['S1', 'S2', 'S3'])
    ga_B = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730B', source_id = '107985730B', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, synonym = ['S1', 'S2', 'S3'])
    ga_C = kbmodel.GeneAnnotation(id = 'NCBIGene:107985730C', source_id = '107985730C', symbol = 'MIR1302-2HG', name = 'MIR1302-2HG', molecular_type = 'lncRNA', referenced_in = expected_genome_annotation.id, in_taxon = [expected_org_taxon.id], in_taxon_label = expected_org_taxon.full_name, synonym = ['S1', 'S2', 'S3'])

    expected_gene_annotations = {ga_A.id:ga_A, ga_B.id:ga_B, ga_C.id:ga_C}
    gff.parse(feature_filter)
    assert gff.gene_annotations == expected_gene_annotations