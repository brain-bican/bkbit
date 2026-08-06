"""
Lazy, self-provisioning access to NCBI taxonomy names.

bkbit needs three lookups from the NCBI taxonomy: scientific name -> taxon id,
taxon id -> scientific name, and taxon id -> common name. This module serves
those lookups from two layers, in order:

1. A subset bundled inside the wheel (`ncbi_taxonomy_data/taxonomy_subset.json.gz`,
   ~600KB, every taxon that has a GenBank common name). No network, no setup,
   loads in milliseconds. This covers effectively every organism a genome
   annotation pipeline is run against.
2. The full NCBI taxonomy dump, downloaded and cached on first use for taxa that
   are not in the subset. The cache lives in a per-user cache directory - never
   inside `site-packages`, which may be read-only and is wiped on upgrade.

Nothing here runs at import time: the bundled subset is loaded on first lookup
and the full dump is only fetched if a lookup actually misses the subset.

Environment variables:
    BKBIT_DATA_DIR: Overrides the cache directory used for the full taxonomy.
    BKBIT_NO_DOWNLOAD: If set to a truthy value, a lookup that misses the
        bundled subset raises instead of downloading the full taxonomy.
"""

import gzip
import io
import json
import os
import zipfile
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
from typing import Dict, Optional, Tuple

import platformdirs
import requests

NCBI_TAXON_URL = "https://ftp.ncbi.nih.gov/pub/taxonomy/taxdmp.zip"

BUNDLED_SUBSET_PACKAGE = "bkbit.utils.ncbi_taxonomy_data"
BUNDLED_SUBSET_FILENAME = "taxonomy_subset.json.gz"
SUBSET_FORMAT_VERSION = 1

DATA_DIR_ENV_VAR = "BKBIT_DATA_DIR"
NO_DOWNLOAD_ENV_VAR = "BKBIT_NO_DOWNLOAD"

CACHE_SUBDIR = "ncbi_taxonomy"
CACHE_FILENAMES = {
    "scientific": "taxid_to_scientific_name.json",
    "common": "taxid_to_common_name.json",
    "scientific_to_taxid": "scientific_name_to_taxid.json",
}

# Older bkbit versions wrote the cache into the installed package directory.
# Reused read-only if it happens to still be there, but never written to.
LEGACY_CACHE_DIR = Path(__file__).parent / CACHE_SUBDIR


## CACHE LOCATION ##


def data_dir() -> Path:
    """
    Returns the directory bkbit uses for the downloaded NCBI taxonomy cache.

    Honours ``BKBIT_DATA_DIR`` if set, otherwise falls back to the platform's
    per-user cache directory (which respects ``XDG_CACHE_HOME`` on Linux).
    """
    override = os.environ.get(DATA_DIR_ENV_VAR)
    if override:
        return Path(override).expanduser()
    return Path(platformdirs.user_cache_dir("bkbit", appauthor=False)) / CACHE_SUBDIR


def full_cache_paths(cache_dir: Optional[Path] = None) -> Dict[str, Path]:
    """
    Returns the paths of the three JSON files that make up the full cache.

    Args:
        cache_dir: Directory to resolve against. Defaults to :func:`data_dir`.

    Returns:
        dict: Keys ``scientific``, ``common``, and ``scientific_to_taxid``.
    """
    base = Path(cache_dir) if cache_dir is not None else data_dir()
    return {key: base / name for key, name in CACHE_FILENAMES.items()}


def _existing_cache_dir() -> Optional[Path]:
    """
    Returns a directory containing a complete taxonomy cache, or None.

    Prefers the current cache location and falls back to the legacy in-package
    directory written by older bkbit versions.
    """
    candidates = [data_dir()]
    if not os.environ.get(DATA_DIR_ENV_VAR):
        candidates.append(LEGACY_CACHE_DIR)
    for candidate in candidates:
        if all(path.exists() for path in full_cache_paths(candidate).values()):
            return candidate
    return None


## DOWNLOAD / BUILD ##


def download_and_extract_zip_in_memory(url: str = NCBI_TAXON_URL) -> str:
    """
    Downloads the taxdump zip from the given URL and returns 'names.dmp'.

    Args:
        url: The URL of the zip file to download.

    Returns:
        str: The content of the 'names.dmp' file as a string.

    Raises:
        requests.exceptions.HTTPError: If the download fails.
    """
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    with zipfile.ZipFile(io.BytesIO(response.content)) as z:
        with z.open("names.dmp") as names_dmp_file:
            return names_dmp_file.read().decode("utf-8")


def parse_dmp_content(dmp_content: str) -> Tuple[dict, dict, dict]:
    """
    Parses the content of a names.dmp file into taxonomy name lookups.

    Args:
        dmp_content: The content of the DMP file.

    Returns:
        tuple: ``(taxid_to_scientific_name, taxid_to_common_name,
        scientific_name_to_taxid)``.
    """
    taxid_to_scientific_name = {}
    taxid_to_common_name = {}
    scientific_name_to_taxid = {}

    for line in dmp_content.strip().split("\n"):
        parts = [part.strip() for part in line.strip().split("|")]
        # names.dmp columns: tax_id | name_txt | unique name | name class
        taxid, name, unique_name, name_class = parts[0], parts[1], parts[2], parts[3]

        if name_class == "scientific name" and taxid not in taxid_to_scientific_name:
            resolved = unique_name or name
            taxid_to_scientific_name[taxid] = resolved
            scientific_name_to_taxid[resolved] = taxid
        elif name_class == "genbank common name" and taxid not in taxid_to_common_name:
            taxid_to_common_name[taxid] = name

    return taxid_to_scientific_name, taxid_to_common_name, scientific_name_to_taxid


def build_full_cache(
    url: str = NCBI_TAXON_URL, cache_dir: Optional[Path] = None
) -> Dict[str, Path]:
    """
    Downloads the NCBI taxdump and writes the full cache to disk.

    Args:
        url: The URL of the taxdump zip to download and process.
        cache_dir: Destination directory. Defaults to :func:`data_dir`.

    Returns:
        dict: The written cache paths, as returned by :func:`full_cache_paths`.
    """
    paths = full_cache_paths(cache_dir)
    target_dir = next(iter(paths.values())).parent
    target_dir.mkdir(parents=True, exist_ok=True)

    names_dmp_content = download_and_extract_zip_in_memory(url)
    scientific, common, scientific_to_taxid = parse_dmp_content(names_dmp_content)

    # Written compactly; these maps run to hundreds of MB when pretty-printed.
    for key, payload in (
        ("scientific", scientific),
        ("common", common),
        ("scientific_to_taxid", scientific_to_taxid),
    ):
        with paths[key].open("w", encoding="utf-8") as f:
            json.dump(payload, f, separators=(",", ":"), ensure_ascii=False)

    return paths


def ensure_full_cache(reload: bool = False, cache_dir: Optional[Path] = None) -> Path:
    """
    Makes sure the full taxonomy cache exists on disk, downloading if needed.

    Args:
        reload: Re-download even if a complete cache is already present.
        cache_dir: Destination directory. Defaults to :func:`data_dir`.

    Returns:
        Path: The directory containing the cache.
    """
    if not reload:
        if cache_dir is None:
            existing = _existing_cache_dir()
            if existing is not None:
                return existing
        elif all(path.exists() for path in full_cache_paths(cache_dir).values()):
            return Path(cache_dir)

    paths = build_full_cache(cache_dir=cache_dir)
    _full_taxonomy.cache_clear()
    return next(iter(paths.values())).parent


## LOOKUPS ##


@lru_cache(maxsize=1)
def _bundled_taxa() -> Dict[str, list]:
    """
    Loads the bundled taxonomy subset: ``{taxid: [scientific, common]}``.
    """
    raw = (files(BUNDLED_SUBSET_PACKAGE) / BUNDLED_SUBSET_FILENAME).read_bytes()
    payload = json.loads(gzip.decompress(raw).decode("utf-8"))
    if payload.get("format") != SUBSET_FORMAT_VERSION:
        raise RuntimeError(
            f"Unsupported bundled taxonomy subset format: {payload.get('format')!r}"
        )
    return payload["taxa"]


@lru_cache(maxsize=1)
def _bundled_scientific_name_to_taxid() -> Dict[str, str]:
    """
    Inverts the bundled subset into a scientific name -> taxon id lookup.
    """
    return {names[0]: taxid for taxid, names in _bundled_taxa().items()}


@lru_cache(maxsize=1)
def _full_taxonomy() -> Tuple[dict, dict, dict]:
    """
    Loads the full taxonomy from the cache, downloading it if necessary.

    Returns:
        tuple: ``(taxid_to_scientific_name, taxid_to_common_name,
        scientific_name_to_taxid)``.

    Raises:
        RuntimeError: If the cache is missing and downloads are disabled via
            ``BKBIT_NO_DOWNLOAD``.
    """
    cache_dir = _existing_cache_dir()
    if cache_dir is None:
        if os.environ.get(NO_DOWNLOAD_ENV_VAR):
            raise RuntimeError(
                "This taxon is not in the taxonomy subset bundled with bkbit and "
                f"{NO_DOWNLOAD_ENV_VAR} is set. Run 'bkbit download-ncbi-taxonomy' "
                f"or unset {NO_DOWNLOAD_ENV_VAR} to allow the download."
            )
        print(
            "Taxon not found in the bundled NCBI taxonomy subset; downloading the "
            f"full NCBI taxonomy to {data_dir()} (this happens once)."
        )
        cache_dir = ensure_full_cache()

    paths = full_cache_paths(cache_dir)
    with paths["scientific"].open(encoding="utf-8") as f:
        scientific = json.load(f)
    with paths["common"].open(encoding="utf-8") as f:
        common = json.load(f)
    with paths["scientific_to_taxid"].open(encoding="utf-8") as f:
        scientific_to_taxid = json.load(f)
    return scientific, common, scientific_to_taxid


def lookup_taxid(scientific_name: str) -> Optional[str]:
    """
    Returns the taxon id for a scientific name, or None if it is unknown.

    Args:
        scientific_name: Scientific name, e.g. ``"Homo sapiens"``.
    """
    taxid = _bundled_scientific_name_to_taxid().get(scientific_name)
    if taxid is not None:
        return taxid
    return _full_taxonomy()[2].get(scientific_name)


def lookup_scientific_name(taxid: str) -> Optional[str]:
    """
    Returns the scientific name for a taxon id, or None if it is unknown.

    Args:
        taxid: NCBI taxon id, as a string, e.g. ``"9606"``.
    """
    names = _bundled_taxa().get(str(taxid))
    if names is not None:
        return names[0]
    return _full_taxonomy()[0].get(str(taxid))


def lookup_common_name(taxid: str) -> Optional[str]:
    """
    Returns the GenBank common name for a taxon id, or None if it has none.

    Args:
        taxid: NCBI taxon id, as a string, e.g. ``"9606"``.
    """
    names = _bundled_taxa().get(str(taxid))
    if names is not None:
        return names[1]
    return _full_taxonomy()[1].get(str(taxid))
