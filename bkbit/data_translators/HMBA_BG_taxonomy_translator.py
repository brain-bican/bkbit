"""
HMBA Basal Ganglia Taxonomy Translator

Translates Human-Mammalian Brain Atlas - Basal Ganglia (HMBA-BG) taxonomy data
from normalized CSV format to BKE Taxonomy model objects for Brain Knowledge Platform ingestion.

Data Source: s3://allen-brain-cell-atlas/metadata/HMBA-BG-taxonomy-CCN20250428/20250630/
Documentation: https://alleninstitute.github.io/abc_atlas_access/descriptions/HMBA-BG_dataset.html
"""

import hashlib
import json
from typing import Dict, List, Optional

import click
import pandas as pd
from linkml_runtime.dumpers import json_dumper

import bkbit.models.bke_taxonomy as bke
from bkbit.utils.generate_bkbit_id import generate_object_id


class HMBABGTaxonomy:
    """
    Translator for HMBA Basal Ganglia taxonomy data to BKE taxonomy model.

    Processes normalized CSV files containing 5-level taxonomy hierarchy:
    - Level 0: Neighborhood
    - Level 1: Class
    - Level 2: Subclass
    - Level 3: Group
    - Level 4: Cluster
    """

    def __init__(self):
        """Initialize storage dictionaries for all BKE taxonomy objects."""
        # CellTypeTaxon storage by level
        self.neighborhood_ctt = {}      # Level 0
        self.class_ctt = {}             # Level 1
        self.subclass_ctt = {}          # Level 2
        self.group_ctt = {}             # Level 3
        self.cluster_taxons = {}        # Level 4 (cluster annotations)

        # Other object storage
        self.clusters = {}              # Actual Cluster objects (with cell counts)
        self.abbreviations = {}         # Abbreviation objects
        self.display_colors = {}        # DisplayColor objects
        self.cell_type_sets = {}        # CellTypeSet objects (5 total)
        self.spatial_proportions = {}   # SpatialProportions objects (optional)

        # Lookup mapping: label → generated object ID
        self.label_to_id = {}

    def _generate_object(self, cls, attributes: Dict) -> object:
        """
        Generate a BKE model object with deterministic ID.

        Args:
            cls: BKE model class (e.g., bke.CellTypeTaxon)
            attributes: Dictionary of object attributes

        Returns:
            Instantiated BKE model object with generated ID
        """
        # Generate deterministic ID from normalized attributes
        obj_id = generate_object_id(attributes)
        attributes["id"] = obj_id

        # Instantiate object
        return cls(**attributes)

    def parse_abbreviations(self, abbreviation_csv_path: str):
        """
        Parse abbreviation_term.csv and create Abbreviation objects.

        Args:
            abbreviation_csv_path: Path to abbreviation_term.csv file
        """
        df = pd.read_csv(abbreviation_csv_path)

        for _, row in df.iterrows():
            term = row["abbreviation_term"]
            meaning = row["abbreviation_meaning"]
            abbrev_type = row["abbreviation_type"]
            primary_id = row["primary_identifier"]
            secondary_id = row.get("secondary_identifier", "")

            # Map abbreviation_type to AbbreviationEntityType enum
            try:
                if abbrev_type == "gene":
                    entity_type = bke.AbbreviationEntityType.gene
                elif abbrev_type == "cell_type":
                    entity_type = bke.AbbreviationEntityType.cell_type
                elif abbrev_type == "anatomical":
                    entity_type = bke.AbbreviationEntityType.anatomical
                else:
                    print(f"Warning: Unknown abbreviation type '{abbrev_type}' for term '{term}'")
                    continue
            except Exception as e:
                print(f"Warning: Error converting abbreviation type '{abbrev_type}': {e}")
                continue

            # Build attributes
            attributes = {
                "term": term,
                "meaning": meaning,
                "entity_type": entity_type,
            }

            # Populate denotes_* fields based on entity type
            identifiers = [primary_id] if pd.notna(primary_id) else []
            if pd.notna(secondary_id) and secondary_id:
                identifiers.append(secondary_id)

            if entity_type == bke.AbbreviationEntityType.gene:
                attributes["denotes_gene_annotation"] = identifiers
            elif entity_type == bke.AbbreviationEntityType.cell_type:
                attributes["denotes_cell_type"] = identifiers
            elif entity_type == bke.AbbreviationEntityType.anatomical:
                attributes["denotes_parcellation_term"] = identifiers

            # Create Abbreviation object
            abbrev_obj = self._generate_object(bke.Abbreviation, attributes)

            # Store in dict keyed by term
            self.abbreviations[term] = abbrev_obj
            self.label_to_id[term] = abbrev_obj.id

    def parse_clusters(self, cluster_csv_path: str):
        """
        Parse cluster.csv and create Cluster objects.

        Args:
            cluster_csv_path: Path to cluster.csv file
        """
        df = pd.read_csv(cluster_csv_path)

        for _, row in df.iterrows():
            label = row["label"]
            cluster_alias = row["cluster_alias"]
            num_cells = int(row["number_of_cells"]) if pd.notna(row["number_of_cells"]) else 0

            # Build attributes
            attributes = {
                "name": cluster_alias,
                "accession_id": label,
                "number_of_observations": num_cells,
            }

            # Create Cluster object
            cluster_obj = self._generate_object(bke.Cluster, attributes)

            # Store in dict keyed by label
            self.clusters[label] = cluster_obj
            self.label_to_id[label] = cluster_obj.id

    def parse_taxonomy_terms(
        self,
        annotation_term_csv_path: str,
        abbrev_map_csv_path: str
    ):
        """
        Parse cluster_annotation_term.csv and create CellTypeTaxon and DisplayColor objects.

        Links abbreviations to taxons via cluster_annotation_to_abbreviation_map.csv.

        Args:
            annotation_term_csv_path: Path to cluster_annotation_term.csv
            abbrev_map_csv_path: Path to cluster_annotation_to_abbreviation_map.csv
        """
        # Read taxonomy terms
        df = pd.read_csv(annotation_term_csv_path)

        # Read abbreviation mapping
        abbrev_map_df = pd.read_csv(abbrev_map_csv_path)

        # Create dict: term_label → list of abbreviation terms
        term_to_abbrevs = {}
        for _, row in abbrev_map_df.iterrows():
            term_label = row["cluster_annotation_term_label"]
            abbrev_term = row["abbreviation_term"]

            if term_label not in term_to_abbrevs:
                term_to_abbrevs[term_label] = []

            # Only add if abbreviation exists
            if abbrev_term in self.abbreviations:
                abbrev_id = self.abbreviations[abbrev_term].id
                term_to_abbrevs[term_label].append(abbrev_id)

        # Process each taxonomy level (0-4)
        # Level mapping
        level_names = {
            "Neighborhood": (0, self.neighborhood_ctt),
            "Class": (1, self.class_ctt),
            "Subclass": (2, self.subclass_ctt),
            "Group": (3, self.group_ctt),
            "Cluster": (4, self.cluster_taxons),
        }

        for _, row in df.iterrows():
            label = row["label"]
            name = row["name"]
            term_set_name = row["cluster_annotation_term_set_name"]
            color_hex = row.get("color_hex_triplet", None)
            term_order = int(row["term_order"]) if pd.notna(row["term_order"]) else None
            parent_label = row.get("parent_term_label", None)

            # Determine which level this belongs to
            if term_set_name not in level_names:
                continue

            level_num, storage_dict = level_names[term_set_name]

            # Build CellTypeTaxon attributes
            attributes = {
                "name": name,
                "accession_id": label,
            }

            if term_order is not None:
                attributes["order"] = term_order

            # Resolve parent reference
            if pd.notna(parent_label) and parent_label:
                if parent_label in self.label_to_id:
                    attributes["has_parent"] = self.label_to_id[parent_label]
                else:
                    print(f"Warning: Parent '{parent_label}' not found for taxon '{label}'")

            # Link abbreviations
            if label in term_to_abbrevs:
                attributes["has_abbreviation"] = term_to_abbrevs[label]

            # Create CellTypeTaxon object
            taxon_obj = self._generate_object(bke.CellTypeTaxon, attributes)

            # Store in appropriate level dict
            storage_dict[label] = taxon_obj
            self.label_to_id[label] = taxon_obj.id

            # Create DisplayColor if color exists
            if pd.notna(color_hex) and color_hex:
                color_attributes = {
                    "color_hex_triplet": color_hex,
                    "is_color_for_taxon": taxon_obj.id,
                }
                color_obj = self._generate_object(bke.DisplayColor, color_attributes)

                # Store with unique key
                color_key = f"{label}_color"
                self.display_colors[color_key] = color_obj

    def enrich_cluster_membership(self, membership_csv_path: str):
        """
        Parse cluster_to_cluster_annotation_membership.csv and link clusters to taxons.

        Populates the contains_cluster field for Group-level CellTypeTaxons.

        Args:
            membership_csv_path: Path to cluster_to_cluster_annotation_membership.csv
        """
        df = pd.read_csv(membership_csv_path)

        # Group by cluster_annotation_term_label to collect clusters per taxon
        grouped = df.groupby("cluster_annotation_term_label")

        for term_label, group in grouped:
            # Find the taxon (should be at Cluster level, Level 4)
            if term_label in self.cluster_taxons:
                # Get cluster labels for this annotation term
                cluster_labels = group["cluster_annotation_term_label"].tolist()

                # Resolve cluster labels to Cluster object IDs
                cluster_ids = []
                for clust_label in cluster_labels:
                    if clust_label in self.label_to_id:
                        cluster_ids.append(self.label_to_id[clust_label])

                # NOTE: For this dataset, cluster_annotation_term_label IS the cluster label
                # So we need to link the Cluster object itself
                if term_label in self.clusters:
                    cluster_id = self.clusters[term_label].id

                    # Find parent Group taxon and add this cluster to contains_cluster
                    taxon = self.cluster_taxons[term_label]
                    if taxon.has_parent and taxon.has_parent in [t.id for t in self.group_ctt.values()]:
                        # Find the Group taxon
                        for group_label, group_taxon in self.group_ctt.items():
                            if group_taxon.id == taxon.has_parent:
                                # Add cluster to Group's contains_cluster
                                if hasattr(group_taxon, "contains_cluster"):
                                    if group_taxon.contains_cluster is None:
                                        group_taxon.contains_cluster = []
                                    if cluster_id not in group_taxon.contains_cluster:
                                        group_taxon.contains_cluster.append(cluster_id)
                                else:
                                    # Modify attributes and recreate
                                    # This is tricky with Pydantic - need to track separately
                                    pass

        # Alternative approach: track cluster containment separately and rebuild
        # For now, we'll create a mapping and update during serialization
        self.cluster_containment = {}  # Group taxon ID → list of Cluster IDs

        # Map each Cluster-level taxon to its parent Group, then link actual Cluster
        for cluster_label, cluster_taxon in self.cluster_taxons.items():
            if cluster_taxon.has_parent:
                # Parent should be a Group taxon
                parent_id = cluster_taxon.has_parent

                # Get the actual Cluster object ID
                if cluster_label in self.clusters:
                    cluster_obj_id = self.clusters[cluster_label].id

                    if parent_id not in self.cluster_containment:
                        self.cluster_containment[parent_id] = []

                    if cluster_obj_id not in self.cluster_containment[parent_id]:
                        self.cluster_containment[parent_id].append(cluster_obj_id)

    def parse_cell_type_sets(self, term_set_csv_path: str):
        """
        Parse cluster_annotation_term_set.csv and create CellTypeSet objects.

        Creates one CellTypeSet per taxonomy level (5 total).

        Args:
            term_set_csv_path: Path to cluster_annotation_term_set.csv
        """
        df = pd.read_csv(term_set_csv_path)

        # Level name → storage dict mapping
        level_storage = {
            "Neighborhood": self.neighborhood_ctt,
            "Class": self.class_ctt,
            "Subclass": self.subclass_ctt,
            "Group": self.group_ctt,
            "Cluster": self.cluster_taxons,
        }

        for _, row in df.iterrows():
            label = row["label"]
            name = row["name"]
            description = row.get("description", "")
            order = int(row["order"]) if pd.notna(row["order"]) else None

            # Get all taxon IDs from this level
            if name in level_storage:
                storage_dict = level_storage[name]
                taxon_ids = [taxon.id for taxon in storage_dict.values()]

                # Build attributes
                attributes = {
                    "name": name,
                    "accession_id": label,
                    "description": description if pd.notna(description) else None,
                    "order": order,
                    "contains_taxon": taxon_ids,
                }

                # Create CellTypeSet object
                set_obj = self._generate_object(bke.CellTypeSet, attributes)

                # Store
                self.cell_type_sets[name] = set_obj

    def serialize_to_jsonld(self) -> str:
        """
        Serialize all BKE taxonomy objects to JSON-LD format.

        Returns:
            JSON-LD string with @context and @graph
        """
        # Serialize objects to JSON
        graph = []

        # Collect all CellTypeTaxons (all 5 levels)
        for taxon in self.neighborhood_ctt.values():
            graph.append(json.loads(json_dumper.dumps(taxon)))

        for taxon in self.class_ctt.values():
            graph.append(json.loads(json_dumper.dumps(taxon)))

        for taxon in self.subclass_ctt.values():
            graph.append(json.loads(json_dumper.dumps(taxon)))

        # For Group taxons, add contains_cluster if available
        for taxon in self.group_ctt.values():
            taxon_json = json.loads(json_dumper.dumps(taxon))

            # Check if this Group has clusters
            if taxon.id in self.cluster_containment:
                taxon_json["contains_cluster"] = self.cluster_containment[taxon.id]

            graph.append(taxon_json)

        for taxon in self.cluster_taxons.values():
            graph.append(json.loads(json_dumper.dumps(taxon)))

        # Add Cluster objects
        for cluster in self.clusters.values():
            graph.append(json.loads(json_dumper.dumps(cluster)))

        # Add Abbreviations
        for abbrev in self.abbreviations.values():
            graph.append(json.loads(json_dumper.dumps(abbrev)))

        # Add DisplayColors
        for color in self.display_colors.values():
            graph.append(json.loads(json_dumper.dumps(color)))

        # Add CellTypeSets
        for cell_set in self.cell_type_sets.values():
            graph.append(json.loads(json_dumper.dumps(cell_set)))

        # Add SpatialProportions (if any)
        for spatial in self.spatial_proportions.values():
            graph.append(json.loads(json_dumper.dumps(spatial)))

        # Build JSON-LD output
        output_data = {
            "@context": "https://raw.githubusercontent.com/brain-bican/models/main/jsonld-context-autogen/bke_taxonomy.context.jsonld",
            "@graph": graph
        }

        return json.dumps(output_data, indent=2)


@click.command()
@click.argument("annotation_term_csv", type=click.Path(exists=True))
@click.argument("term_set_csv", type=click.Path(exists=True))
@click.argument("abbreviation_csv", type=click.Path(exists=True))
@click.argument("cluster_csv", type=click.Path(exists=True))
@click.argument("membership_csv", type=click.Path(exists=True))
@click.argument("abbrev_map_csv", type=click.Path(exists=True))
@click.option(
    "--output-format",
    "-o",
    type=click.Choice(["json-ld", "turtle"]),
    default="json-ld",
    help="Output format (json-ld or turtle)"
)
@click.option(
    "--output-file",
    "-f",
    type=click.Path(),
    default=None,
    help="Optional output file path (prints to stdout if not specified)"
)
def bg_taxonomy2jsonld(
    annotation_term_csv,
    term_set_csv,
    abbreviation_csv,
    cluster_csv,
    membership_csv,
    abbrev_map_csv,
    output_format,
    output_file
):
    """
    Convert HMBA Basal Ganglia taxonomy CSV files to BKE taxonomy JSON-LD.

    Processes normalized CSV files from HMBA-BG-taxonomy-CCN20250428 dataset
    and generates BKE taxonomy objects for Brain Knowledge Platform ingestion.

    Required arguments (in order):

        ANNOTATION_TERM_CSV: Path to cluster_annotation_term.csv

        TERM_SET_CSV: Path to cluster_annotation_term_set.csv

        ABBREVIATION_CSV: Path to abbreviation_term.csv

        CLUSTER_CSV: Path to cluster.csv

        MEMBERSHIP_CSV: Path to cluster_to_cluster_annotation_membership.csv

        ABBREV_MAP_CSV: Path to cluster_annotation_to_abbreviation_map.csv

    Example:

        bkbit bg_taxonomy2jsonld \\
            cluster_annotation_term.csv \\
            cluster_annotation_term_set.csv \\
            abbreviation_term.csv \\
            cluster.csv \\
            cluster_to_cluster_annotation_membership.csv \\
            cluster_annotation_to_abbreviation_map.csv \\
            -o json-ld -f output.jsonld
    """
    # Instantiate translator
    translator = HMBABGTaxonomy()

    # Parse data in sequence
    print("Parsing abbreviations...")
    translator.parse_abbreviations(abbreviation_csv)

    print("Parsing clusters...")
    translator.parse_clusters(cluster_csv)

    print("Parsing taxonomy terms...")
    translator.parse_taxonomy_terms(annotation_term_csv, abbrev_map_csv)

    print("Enriching cluster membership...")
    translator.enrich_cluster_membership(membership_csv)

    print("Parsing cell type sets...")
    translator.parse_cell_type_sets(term_set_csv)

    # Serialize to JSON-LD
    print("Serializing to JSON-LD...")
    json_ld_output = translator.serialize_to_jsonld()

    # Handle turtle format if requested
    if output_format == "turtle":
        # TODO: Convert to Turtle using RDFlib (similar to other translators)
        print("Warning: Turtle format not yet implemented, outputting JSON-LD")

    # Output
    if output_file:
        with open(output_file, "w") as f:
            f.write(json_ld_output)
        print(f"Output written to {output_file}")
    else:
        print(json_ld_output)
