import json

import anndata as ad
import numpy as np
import pandas as pd
import pytest
from click.testing import CliRunner

from bkbit.data_translators.ait_taxonomy_translator import AITTaxonomy, ait2jsonld

# cluster_id -> (Class, Subclass, accession_class, accession_subclass,
#                display_order_class, display_order_subclass, CL:ID_class, CL:ID_subclass)
CLUSTERS = {
    "c1": (
        "Glut",
        "L2/3 IT",
        "CS_CLASS_1",
        "CS_SUBCL_1",
        1,
        1,
        "CL:0000679",
        "CL:4023040",
    ),
    "c2": (
        "Glut",
        "L2/3 IT",
        "CS_CLASS_1",
        "CS_SUBCL_1",
        1,
        1,
        "CL:0000679",
        "CL:4023040",
    ),
    "c3": ("Glut", "L5 ET", "CS_CLASS_1", "CS_SUBCL_2", 1, 2, "CL:0000679", "PR 2579"),
    "c4": (
        "GABA",
        "Pvalb",
        "CS_CLASS_2",
        "CS_SUBCL_3",
        2,
        3,
        "CL:0000617",
        "CL:0000000",
    ),
}
# cells per cluster
CELLS = ["c1"] * 3 + ["c2"] * 2 + ["c3"] * 4 + ["c4"] * 1


def make_ait(path, filter_value=False, extra_uns=None):
    columns = [
        "Class",
        "Subclass",
        "accession_class",
        "accession_subclass",
        "display_order_class",
        "display_order_subclass",
        "CL:ID_class",
        "CL:ID_subclass",
    ]
    rows = [dict(zip(columns, CLUSTERS[c]), cluster_id=c) for c in CELLS]
    obs = pd.DataFrame(rows, index=[f"cell{i}" for i in range(len(CELLS))])
    for column in obs.columns:
        if obs[column].dtype == object:
            obs[column] = obs[column].astype("category")
    obs["load_id"] = "L1"
    obs["assay"] = "10x multiome"
    obs["suspension_type"] = "nucleus"
    obs["is_primary_data"] = "True"

    n_genes = 3
    adata = ad.AnnData(
        X=np.ones((len(CELLS), n_genes), dtype=np.float32),
        obs=obs,
        var=pd.DataFrame(index=[f"gene{i}" for i in range(n_genes)]),
        obsm={"X_umap": np.zeros((len(CELLS), 2)), "X_scVI": np.zeros((len(CELLS), 8))},
    )
    adata.raw = adata.copy()
    adata.uns = {
        "title": "Test_AIT",
        "schema_version": "v1.0",
        "batch_condition": np.array(["donor_id"]),
        "cluster_algorithm": "https://example.org/clustering",
        "hierarchy": {"Class": 0, "Subclass": 1, "cluster_id": 2},
        "mode": "standard",
        "filter": {"standard": filter_value},
        "default_embedding": "X_umap",
        "dataset_purl": "BICAN_s3_bucket",
        "cluster_info": obs.drop_duplicates("cluster_id").copy(),
        **(extra_uns or {}),
    }
    adata.write_h5ad(path)
    return path


def by_category(graph, category):
    return [o for o in graph if f"bican:{category}" in o["category"]]


@pytest.fixture
def ait_file(tmp_path):
    return make_ait(tmp_path / "test.h5ad")


def test_hierarchy(ait_file):
    graph = AITTaxonomy(ait_file).parse().to_jsonld()["@graph"]

    (taxonomy,) = by_category(graph, "CellTypeTaxonomy")
    assert taxonomy["title"] == "Test_AIT"
    assert taxonomy["schema_version"] == "v1.0"
    assert taxonomy["batch_condition"] == "donor_id"
    assert taxonomy["mode"] == "standard"
    assert taxonomy["filter"] is False
    assert json.loads(taxonomy["hierarchy"]) == {
        "Class": 0,
        "Subclass": 1,
        "cluster_id": 2,
    }
    # dataset_purl is not a URL, so it is not used as content_url
    assert "content_url" not in taxonomy

    sets = {s["name"]: s for s in by_category(graph, "CellTypeSet")}
    assert set(sets) == {"Class", "Subclass"}
    assert sets["Subclass"]["has_parent"] == sets["Class"]["id"]
    assert sets["Class"]["part_of_taxonomy"] == taxonomy["id"]
    assert "has_parent" not in sets["Class"]

    taxa = {
        (t["part_of_set"], t["name"]): t for t in by_category(graph, "CellTypeTaxon")
    }
    assert len(taxa) == 5
    glut = taxa[(sets["Class"]["id"], "Glut")]
    l23 = taxa[(sets["Subclass"]["id"], "L2/3 IT")]
    l5 = taxa[(sets["Subclass"]["id"], "L5 ET")]
    assert glut["number_of_cells"] == 9
    assert glut["accession_id"] == "CS_CLASS_1"
    assert glut["order"] == 1
    assert glut["cell_type_ontology_term_id"] == "CL:0000679"
    assert "has_parent" not in glut
    assert l23["has_parent"] == glut["id"]
    assert l23["number_of_cells"] == 5
    # "PR 2579" is not a CL term and is dropped
    assert "cell_type_ontology_term_id" not in l5

    clusters = {c["name"]: c for c in by_category(graph, "Cluster")}
    assert set(clusters) == {"c1", "c2", "c3", "c4"}
    assert clusters["c3"]["number_of_observations"] == 4
    assert clusters["c1"]["has_parent"] == [l23["id"]]
    (cluster_set,) = by_category(graph, "ClusterSet")
    assert clusters["c1"]["part_of_set"] == cluster_set["id"]
    assert taxonomy["was_derived_from"] == [cluster_set["id"]]

    matrices = {m["matrix_type"]: m for m in by_category(graph, "ExpressionMatrix")}
    assert set(matrices) == {"normalized", "raw_count"}
    assert "has_variable" not in matrices["normalized"]
    embeddings = {e["embedding_key"] for e in by_category(graph, "Embedding")}
    assert embeddings == {"X_umap", "X_scVI"}
    assert sorted(taxonomy["has_expression_matrix"]) == sorted(
        m["id"] for m in matrices.values()
    )

    assert not by_category(graph, "Cell")


def test_ids_are_deterministic(ait_file):
    first = AITTaxonomy(ait_file).parse().to_jsonld()
    second = AITTaxonomy(ait_file).parse().to_jsonld()
    assert first == second
    ids = [o["id"] for o in first["@graph"]]
    assert len(ids) == len(set(ids))


def test_cells_and_variables(ait_file):
    graph = (
        AITTaxonomy(ait_file, include_cells=True, include_variables=True)
        .parse()
        .to_jsonld()["@graph"]
    )
    cells = by_category(graph, "Cell")
    assert len(cells) == len(CELLS)
    clusters = {c["id"]: c["name"] for c in by_category(graph, "Cluster")}
    cell = cells[0]
    assert clusters[cell["part_of_cluster"]] == cell["cluster_id"] == "c1"
    assert cell["is_primary_data"] is True
    assert cell["suspension_type"] == "nucleus"
    assert cell["load_id"] == "L1"
    for matrix in by_category(graph, "ExpressionMatrix"):
        assert matrix["has_variable"] == ["gene0", "gene1", "gene2"]


def test_mode_filter(tmp_path):
    # remove every c3 cell in the "no_c3" mode
    ait_file = make_ait(
        tmp_path / "modes.h5ad",
        extra_uns={
            "filter": {"standard": False, "no_c3": np.array([c == "c3" for c in CELLS])}
        },
    )
    graph = AITTaxonomy(ait_file, mode="no_c3").parse().to_jsonld()["@graph"]
    assert {c["name"] for c in by_category(graph, "Cluster")} == {"c1", "c2", "c4"}
    taxa = {t["name"]: t for t in by_category(graph, "CellTypeTaxon")}
    assert "L5 ET" not in taxa
    assert taxa["Glut"]["number_of_cells"] == 5
    (taxonomy,) = by_category(graph, "CellTypeTaxonomy")
    assert taxonomy["mode"] == "no_c3"

    with pytest.raises(ValueError, match="not found"):
        AITTaxonomy(ait_file, mode="missing").parse()


def test_obs_fallback_without_cluster_info(tmp_path):
    ait_file = make_ait(tmp_path / "no_info.h5ad", extra_uns={"cluster_info": {}})
    graph = AITTaxonomy(ait_file).parse().to_jsonld()["@graph"]
    taxa = {t["name"]: t for t in by_category(graph, "CellTypeTaxon")}
    assert taxa["Pvalb"]["accession_id"] == "CS_SUBCL_3"
    assert taxa["Pvalb"]["number_of_cells"] == 1


def test_cli(ait_file, tmp_path):
    output_file = tmp_path / "out.jsonld"
    result = CliRunner().invoke(
        ait2jsonld, [str(ait_file), "-o", str(output_file), "-a", "CCN0001"]
    )
    assert result.exit_code == 0, result.output
    data = json.loads(output_file.read_text())
    assert data["@context"].endswith("cell_taxonomy.context.jsonld")
    (taxonomy,) = by_category(data["@graph"], "CellTypeTaxonomy")
    assert taxonomy["accession_id"] == "CCN0001"
