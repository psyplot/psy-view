# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import os.path as osp
import subprocess as spr
import shutil
import re
# import sys
# sys.path.insert(0, os.path.abspath('.'))


# -- Project information -----------------------------------------------------

import psy_view

project = 'psy-view'
copyright = '2020, Philipp S. Sommer'
author = 'Philipp S. Sommer'


version = re.match('\d+\.\d+\.\d+', psy_view.__version__).group()
# The full version, including alpha/beta/rc tags.
release = psy_view.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.autosummary',
    'sphinx.ext.viewcode',
    'IPython.sphinxext.ipython_console_highlighting',
    'IPython.sphinxext.ipython_directive',
    'sphinxarg.ext',
    'psyplot.sphinxext.extended_napoleon',
    'autodocsumm',
]

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# on_rtd is whether we are on readthedocs.org, this line of code grabbed from
# docs.readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

# create the api documentation
if osp.exists(osp.join(osp.dirname(__file__), 'api')):
    shutil.rmtree(osp.join(osp.dirname(__file__), 'api'))
spr.check_call(['bash', 'apigen.bash'])

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
if not on_rtd:  # only import and set the theme if we're building docs locally
    import sphinx_rtd_theme
    html_theme = 'sphinx_rtd_theme'
    html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']

autodoc_default_options = {
    'show_inheritance': True,
    'autosummary': True,
    }

not_document_data = ['psy_view.rcsetup.defaultParams',
                     'psy_view.rcsetup.rcParams']

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # Additional stuff for the LaTeX preamble.
    'preamble': '\setcounter{tocdepth}{10}'
}

master_doc = 'index'

# Grouping the document tree into LaTeX files. List of tuples
# (source start file, target name, title,
#  author, documentclass [howto, manual, or own class]).
latex_documents = [
  (master_doc, 'psy-view.tex', u'psy-view Documentation',
   u'Philipp S. Sommer', 'manual'),
]

# -- Options for Epub output ----------------------------------------------

# Bibliographic Dublin Core info.
epub_title = project
epub_author = author
epub_publisher = author
epub_copyright = copyright

# A list of files that should not be packed into the epub file.
epub_exclude_files = ['search.html']

# Example configuration for intersphinx: refer to the Python standard library.
intersphinx_mapping = {
    'pandas': ('https://pandas.pydata.org/pandas-docs/stable/', None),
    'numpy': ('https://numpy.org/doc/stable/', None),
    'matplotlib': ('https://matplotlib.org/', None),
    'sphinx': ('https://www.sphinx-doc.org/en/master/', None),
    'xarray': ('https://xarray.pydata.org/en/stable/', None),
    'cartopy': ('https://scitools.org.uk/cartopy/docs/latest/', None),
    'psyplot': ('https://psyplot.readthedocs.io/en/latest/', None),
    'psy_simple': ('https://psyplot.readthedocs.io/projects/'
                   'psy-simple/en/latest/', None),
    'psy_maps': ('https://psyplot.readthedocs.io/projects/'
                 'psy-maps/en/latest/', None),
    'psyplot_gui': ('https://psyplot.readthedocs.io/projects/'
                    'psyplot-gui/en/latest/', None),
}