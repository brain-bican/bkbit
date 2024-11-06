# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'bkbit'
copyright = '2024, BICAN'
author = 'BICAN'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

# autodoc pulls documentation from docstrings
# napoleon enables Sphinx to parse both NumPy and Google style docstrings
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.githubpages",
    'm2r'
]
# display documentation both from a class docstring and its __init__ methods’s.
autoclass_content = 'both'

templates_path = ['_templates']
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

# default: 'alabaster'
# other themes = 'sphinx_rtd_theme', 'classic', 'furo'
html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_show_sourcelink = False
html_context = {
    "display_github": True, # Integrate GitHub
    "github_user": "brain-bican", # Username
    "github_repo": "bkbit", # Repo name
    "github_version": "main", # Version
    "conf_py_path": "/docs/", # Path in the checkout to the docs root
}
# source_suffix = ['.rst', '.md']
