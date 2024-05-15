import pytest
from bkbit.scripts.specimen_portal_translator import SpecimenPortal
from bkbit.models import library_generation as lg


def test_library_pool():
    nimp_data = {
        "id": "LP-CVFLMQ819998",
        "category": "Library Pool",
        "record": {
            "library_ids": [
                "LI-QLULNC273557",
                "LI-TWSPRO977953",
                "LI-XMNYRP891535",
                "LI-ZRTZNU703863",
                "LI-KRNJLQ134481",
                "LI-TMLOLP919130",
                "LI-DDFMNG372245",
                "LI-FGRWPY227572",
                "LI-SUSLVB268156",
            ],
            "technique": None,
            "lab_id": 7,
            "attachment": {
                "url": "/uploads/library_pool/attachment/11/BICAN_15568_ATX-16001_DemuxQC.csv"
            },
            "flowcell": "A2272TGLT3",
            "tags": [],
            "library_pool_database_id": 11,
            "library_pool_tube_barcode": "A1658809",
            "library_pool_local_name": "ATX-16001",
            "library_pool_local_tube_id": "NY-AT16001",
            "library_pool_preparation_date": "2023-06-21",
            "library_aliquot_local_names": [
                "NY-AT16001-2",
                "NY-AT16001-9",
                "NY-AT16001-3",
                "NY-AT16001-7",
                "NY-AT16001-5",
                "NY-AT16001-1",
                "NY-AT16001-6",
                "NY-AT16001-4",
                "NY-AT16001-8",
            ],
            "library_pool_nhash_id": "LP-CVFLMQ819998",
            "library_pool_sequencing_result_status": "Ready",
            "library_pool_sequencing_results_comments": None,
            "library_package_database_id": 9,
            "library_pool_alignment_status": "Ready",
        },
    }
    parents = ["LA-QLULNC273557CVFLMQ819998"]
    lp = SpecimenPortal.generate_bican_object(nimp_data, parents)
    # mapped attributes in green table:
    # 1. local_tube_id
    # 2. name
    assert lp.id == "NIMP:LP-CVFLMQ819998"
    assert lp.name == "ATX-16001"
    assert lp.local_tube_id == "NY-AT16001"
    assert lp.was_derived_from == ["NIMP:LA-QLULNC273557CVFLMQ819998"]


def test_library_aliquot():
    nimp_data = {
        "id": "LA-TWSPRO977953CVFLMQ819998",
        "category": "Library Aliquot",
        "record": {
            "id": 36,
            "project_id": None,
            "sequencing_result_date": "2023-07-03",
            "fastq_file_path": "Project_BICAN_15568_ATX-16001_B01_NAN_Lane.2023-06-30/NY-AT16001",
            "library_package_id": 9,
            "lab_id": 7,
            "fastq_file_alignment_status": "1",
            "library_aliquot_local_name": "NY-AT16001-9",
            "library_pool_database_id": 11,
            "library_aliquot_sequencing_result_status": "ready",
            "library_aliquot_nhash_id": "LA-TWSPRO977953CVFLMQ819998",
            "library_database_id": 32,
            "lab": "AIBS",
            "award": "U01MH130962",
            "run_qc_approval_status": "Accepted",
        },
    }
    parents = ["LI-SUSLVB268156"]
    # mapped attributes in green table:
    # 1. name
    la = SpecimenPortal.generate_bican_object(nimp_data, parents)
    assert la.id == "NIMP:LA-TWSPRO977953CVFLMQ819998"
    assert la.name == "NY-AT16001-9"
    assert la.was_derived_from == "NIMP:LI-SUSLVB268156"


def test_library():
    nimp_data = {
        "id": "LI-SUSLVB268156",
        "category": "Library",
        "record": {
            "library_submitted": None,
            "sequencing_center_recieved": None,
            "sequencing_result_posted": None,
            "patient_report_id": None,
            "human": True,
            "subject_ids": None,
            "project_name": None,
            "species": None,
            "region": None,
            "tube_id": None,
            "demultiplex": None,
            "contact_email": None,
            "expected_cell_number": None,
            "tissue_ids": None,
            "sequencing_center_id": None,
            "nemo_path": None,
            "study_name": None,
            "manifest_file": {"url": None},
            "lab_id": 7,
            "library_avg_size_bp": 889,
            "library_concentration_nm": "102.26961812",
            "library_input_ng": "0.0",
            "library_prep_pass_fail": "Pass",
            "library_prep_set": "L8XA_230516_01",
            "library_quantification_fmol": "2045.39236239",
            "library_quantification_ng": "1200.11351471",
            "library_database_id": 39,
            "library_preparation_date": "2023-05-16",
            "library_additional_commnents": None,
            "library_nhash_id": "LI-SUSLVB268156",
            "library_technique": "10xMultiome;ATAC",
            "library_local_name": "L8XA_230516_01_D05",
            "project_identifier": 10,
            "amplified_cdna_database_id": 38,
            "library_r1_r2_index": "SI-NA-D5",
            "barcoded_cell_sample_database_id": None,
            "library_source_type": "amplified_cdna",
        },
    }
    # mapped attributes in green table:
    # 1. average_size_bp
    # 2. concentration_nm
    # 3. pass_fail_result
    # 4. quantity_fmol
    # 5. quantity_ng
    # 6. r1_r2_index
    # 7. name
    parents = ["AC-ATDJAH472237"]
    l = SpecimenPortal.generate_bican_object(nimp_data, parents)
    assert l.id == "NIMP:LI-SUSLVB268156"
    assert l.name == "L8XA_230516_01_D05"
    assert l.average_size_bp == 889
    assert l.concentration_nm == 102.26961812
    assert l.pass_fail_result == "Pass"
    assert (
        l.quantity_fmol == 2045.39236239
    )
    assert (
        l.quantity_ng == 1200.11351471
    )
    assert l.r1_r2_index == "SI-NA-D5"
    assert l.was_derived_from == "NIMP:AC-ATDJAH472237"


def test_amplified_cdna():
    nimp_data = {
        "id": "AC-ATDJAH472237",
        "category": "Amplified cDNA",
        "record": {
            "lab_id": 7,
            "amplified_cdna_amplified_quantity_ng": 12.3,  # ? this value was set by me to test, but it is usually missing
            "amplified_cdna_pcr_cycles": None,
            "amplified_cdna_rna_amplification_pass_fail": "Pass",
            "amplified_cdna_percent_cdna_longer_than_400bp": 1.23,  # ? this value was set by me to test, but it is usually missing
            "cdna_amplification_set": "B8XM_230516_01",
            "amplified_cdna_database_id": 38,
            "project_identifier": 10,
            "amplified_cdna_local_name": "B8XM_230516_01_H01",
            "amplified_cdna_preparation_date": "2023-05-16",
            "barcoded_cell_sample_database_id": 33,
            "amplified_cdna_nhash_id": "AC-ATDJAH472237",
        },
    }
    # mapped attributes in green table:
    # 1. quantity_ng
    # 2. pass_fail_result
    # 3. percent_cdna_longer_than_400bp
    # 4. name
    parents = ["BC-ABUEKB857169"]
    ac = SpecimenPortal.generate_bican_object(nimp_data, parents)
    assert ac.id == "NIMP:AC-ATDJAH472237"
    assert ac.name == "B8XM_230516_01_H01"
    assert ac.pass_fail_result == "Pass"
    assert ac.quantity_ng == 12.3
    assert ac.percent_cdna_longer_than_400bp == 1.23
    assert ac.was_derived_from == "NIMP:BC-ABUEKB857169"


def test_barcoded_cell_sample():
    nimp_data = {
        "id": "BC-ABUEKB857169",
        "category": "Barcoded Cell Sample",
        "record": {
            "bar_code": None,
            "lab_id": 7,
            "barcoded_cell_sample_port_well": "B04",
            "barcoded_cell_input_quantity_count": 16038,
            "tags": ["P0_Pilot", "BICAN_Dev_Atlas"],
            "barcoded_cell_sample_database_id": 33,
            "project_identifier": 10,
            "barcoded_cell_sample_preparation_date": None,
            "barcoded_cell_sample_local_name": "1713_B04",
            "barcoded_cell_sample_nhash_id": "BC-ABUEKB857169",
            "dissociated_cell_sample_nhash_ids": [],
            "enriched_cell_sample_nhash_ids": ["EC-VVWZAT390537", "EC-RRSVWP134225"],
            "barcoded_cell_sample_number_of_expected_cells": 10000,
            "barcoded_cell_sample_technique": "Multiome",
        },
    }
    # mapped attributes in green table:
    # 1. number_of_expected_cells
    # 2. name
    parents = ["EC-VVWZAT390537", "EC-RRSVWP134225"]
    bc = SpecimenPortal.generate_bican_object(nimp_data, parents)
    assert bc.id == "NIMP:BC-ABUEKB857169"
    assert bc.name == "1713_B04"
    assert bc.number_of_expected_cells == 10000
    assert bc.was_derived_from == ["NIMP:EC-VVWZAT390537", "NIMP:EC-RRSVWP134225"]


def test_enriched_cell_sample():
    nimp_data = {
        "id": "EC-PRYTQZ751260",
        "category": "Enriched Cell Sample",
        "record": {
            "dissociated_cell_sample_ids": ["DC-CKVKZB830962"],
            "lab_id": 7,
            "enrichment_population": "No FACS",
            "histone_modification_marker": "test1",  # ? this value was set by me to test, but it is usually missing
            "enriched_cell_sample_database_id": 39,
            "project_identifier": 10,
            "enriched_cell_sample_local_name": "M2XM_230509_231-R_D01",
            "enriched_cell_sample_preparation_date": "2023-05-09",
            "enriched_cell_sample_nhash_id": "EC-PRYTQZ751260",
            "enriched_cell_sample_cell_label_barcode": "test2",  # ? this value was set by me to test, but it is usually missing
        },
    }
    # mapped attributes in green table:
    # 1.enrichment_population
    # 2. cell_source_oligo_name
    # 3. histone_modification_marker
    # 4. name
    parents = ["DC-CKVKZB830962"]
    ec = SpecimenPortal.generate_bican_object(nimp_data, parents)
    assert ec.id == "NIMP:EC-PRYTQZ751260"
    assert ec.name == "M2XM_230509_231-R_D01"
    assert ec.enrichment_population == "No FACS"
    assert ec.cell_source_oligo_name == "test2"
    assert ec.histone_modification_marker == "test1"
    assert ec.was_derived_from == ["NIMP:DC-CKVKZB830962"]


def test_dissociated_cell_sample():
    nimp_data = {
        "id": "DC-HUJRXV794951",
        "category": "Dissociated Cell Sample",
        "record": {
            "id": 26,
            "lab_id": 7,
            "project_identifier": 10,
            "tissue_nhash_ids": [
                "TI-YBDX191018",
                "TI-WEVD382834",
                "TI-QWUM539742",
                "TI-BSAS768968",
                "TI-PNFN361895",
                "TI-HQHP664203",
                "TI-HJPN208281",
                "TI-EXXI937842",
                "TI-KCKO297598",
                "TI-XZFD940925",
                "TI-UMNY703806",
                "TI-WOWI455660",
                "TI-BJVK810521",
            ],
            "dissociated_cell_sample_local_name": "20230508_670908.001",
            "dissociated_cell_sample_preparation_date": None,
            "dissociated_cell_sample_nhash_id": "DC-HUJRXV794951",
            "dissociated_cell_sample_cell_label_barcode": "CMO301",  # ? this value was set by me to test, but it is usually missing
            "dissociated_cell_sample_cell_prep_type": "Nuclei",
        },
    }
    # mapped attributes in green table:
    # 1. cell_prep_type
    # 2. cell_source_oligo_name
    # 3. name
    parents = ["TI-YBDX191018", "TI-WEVD382834"]
    dc = SpecimenPortal.generate_bican_object(nimp_data, parents)
    assert dc.id == "NIMP:DC-HUJRXV794951"
    assert dc.name == "20230508_670908.001"
    assert dc.cell_prep_type == "Nuclei"
    assert dc.cell_source_oligo_name == "CMO301"
    assert dc.was_derived_from == ["NIMP:TI-YBDX191018", "NIMP:TI-WEVD382834"]


def test_tissue_sample():
    nimp_data = {
        "id": "TI-YXLK752242",
        "category": "Tissue",
        "record": {
            "study_name": None,
            "lab_id": 7,
            "roi_desc": None,
            "tissue_nhash_id": "TI-YXLK752242",
            "tissue_sample_local_name": "C57BL6J-672032.08_Mouse-Multiome-CTXsp",
            "tissue_sample_preparation_date": None,
            "project_identifier": 10,
            "species": "NCBITaxon:10090",
            "roi_database_id": None,
            "structure": ["MBA:703"],
        },
    }
    # mapped attributes in green table:
    # 1. structure
    # 2. name
    parents = ["DO-GINI5305"]
    ts = SpecimenPortal.generate_bican_object(nimp_data, parents)
    assert ts.id == "NIMP:TI-YXLK752242"
    assert ts.name == "C57BL6J-672032.08_Mouse-Multiome-CTXsp"
    assert ts.structure == ["MBA:703"]
    assert ts.was_derived_from == "NIMP:DO-GINI5305"


def test_donor():
    nimp_data = {
        "id": "DO-GINI5305",
        "category": "Donor",
        "record": {
            "age_of_death": 0.0, # ? seems like this value is not set by NIMP because it is almost always 0.0
            "race": None,
            "sex": "2",
            "project_number": "U01MH130962",
            "age_at_death_unit": "days",
            "age_at_death_reference_point": "birth",
            "age_at_death_description": "P0",
            "donor_species": "NCBITaxon:10090",
            "donor_nhash_id": "DO-GINI5305",
            "donor_local_id": "C57BL6J-672032",
            "consent_status": None,
            "local_name": "C57BL6J-672032",
            "award": "U01MH130962",
        },
    }
    # mapped attributes in green table:
    # 1. biological_sex
    # 2. age_at_death_description
    # 3. age_at_death_reference_point
    # 4. age_at_death_unit
    # 5. age_at_death_value
    # 6. species
    # 7. name

    d = SpecimenPortal.generate_bican_object(nimp_data, [])
    assert d.id == "NIMP:DO-GINI5305"
    assert d.name == "C57BL6J-672032"
    assert d.biological_sex == "2"
    assert d.age_at_death_description == "P0"
    assert d.age_at_death_reference_point == "birth"
    assert d.age_at_death_unit == "days"
    assert d.age_at_death_value == 0.0
    assert d.species == "NCBITaxon:10090"
    assert d.was_derived_from is None
