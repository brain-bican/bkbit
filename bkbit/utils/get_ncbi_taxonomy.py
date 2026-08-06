"""
CLI for pre-fetching the full NCBI taxonomy cache.

bkbit does not require this step: a taxonomy subset covering every organism with
a GenBank common name ships inside the wheel, and the full taxonomy is downloaded
automatically the first time a lookup falls outside that subset. This command
exists for the cases where you want the download to happen up front rather than
mid-pipeline - air-gapped runs, container images, CI, or reproducible builds.

All of the download and cache logic lives in
:mod:`bkbit.utils.ncbi_taxonomy_cache`; this module is a thin wrapper around it
and re-exports the previous function names for backwards compatibility.

Usage:
    bkbit download-ncbi-taxonomy [--reload] [--data-dir PATH]
"""

import click

from bkbit.utils.ncbi_taxonomy_cache import (
    NCBI_TAXON_URL,
    build_full_cache,
    download_and_extract_zip_in_memory,
    ensure_full_cache,
    parse_dmp_content,
)

__all__ = [
    "NCBI_TAXON_URL",
    "build_full_cache",
    "download_and_extract_zip_in_memory",
    "download_ncbi_taxonomy",
    "parse_dmp_content",
    "process_and_save_taxdmp_in_memory",
]


def process_and_save_taxdmp_in_memory(url=NCBI_TAXON_URL, output_dir=None):
    """
    Downloads and processes the taxdump file, saving the parsed data as JSON.

    Deprecated alias for :func:`bkbit.utils.ncbi_taxonomy_cache.build_full_cache`.

    Args:
        url: The URL of the taxdump file to download and process.
        output_dir: Destination directory. Defaults to the bkbit cache directory.
    """
    build_full_cache(url=url, cache_dir=output_dir)


@click.command()
@click.option(
    "--reload", "-r", is_flag=True, help="Re-download even if already cached."
)
@click.option(
    "--data-dir",
    "-d",
    type=click.Path(file_okay=False),
    default=None,
    help="Directory to store the taxonomy cache in. Defaults to the bkbit cache directory (override with BKBIT_DATA_DIR).",
)
def download_ncbi_taxonomy(reload=False, data_dir=None):
    """Pre-download the full NCBI taxonomy used by gff2jsonld (optional)."""
    target = ensure_full_cache(reload=reload, cache_dir=data_dir)
    if reload:
        click.echo(f"Re-downloaded NCBI taxonomy to {target}")
    else:
        click.echo(f"NCBI taxonomy cache ready at {target}")


if __name__ == "__main__":
    download_ncbi_taxonomy()
