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
import shutil
import re
import warnings

import subprocess as spr

# note: we need to import pyplot here, because otherwise it might fail to load
# the ipython extension
import matplotlib.pyplot as plt

from docutils import nodes
from docutils.statemachine import StringList
from docutils.parsers.rst import directives

from sphinx.util.docutils import SphinxDirective

warnings.filterwarnings("ignore", message=r"\s*Downloading:")

# -- Project information -----------------------------------------------------

import psy_view

confdir = osp.dirname(__file__)

project = 'psy-view'
copyright = '2020, Philipp S. Sommer'
author = 'Philipp S. Sommer'


version = re.match(r'\d+\.\d+\.\d+', psy_view.__version__).group()  # type: ignore
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
    'sphinx.ext.todo',
]

rebuild_screenshots = False

todo_include_todos = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# on_rtd is whether we are on readthedocs.org, this line of code grabbed from
# docs.readthedocs.org
on_rtd = os.environ.get('READTHEDOCS', None) == 'True'

# create the api documentation
if not osp.exists(osp.join(osp.dirname(__file__), 'api')):
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

html_context = {
    'css_files': [
        # overrides for wide tables in RTD theme, particularly for
        # psy-view vs. ncview comparison
        '_static/theme_overrides.css',
        ],
    }

autodoc_default_options = {
    'show_inheritance': True,
    'autosummary': True,
    }

not_document_data = ['psy_view.rcsetup.defaultParams',
                     'psy_view.rcsetup.rcParams']

# -- Options for LaTeX output ---------------------------------------------

latex_elements = {
    # Additional stuff for the LaTeX preamble.
    'preamble': r'\setcounter{tocdepth}{10}'
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


def create_screenshot(
        code: str, output: str, make_plot: bool = False, enable: bool = None,
        plotmethod: str = "mapplot", minwidth=None,
        generate=rebuild_screenshots,
    ) -> str:
    """Generate a screenshot of the GUI."""
    from PyQt5.QtWidgets import QApplication, QSizePolicy  # pylint: disable=no-name-in-module
    from psy_view.ds_widget import DatasetWidget
    from psyplot.data import open_dataset

    output = osp.join("_static", output)
    if on_rtd:
        return output

    app = QApplication.instance()
    if app is None:
        app = QApplication([])

    if not generate and osp.exists(output):
        return output

    ds_widget = DatasetWidget(open_dataset(osp.join(confdir, "demo.nc")))
    ds_widget.plotmethod = plotmethod

    if make_plot:
        ds_widget.variable_buttons["t2m"].click()

    if minwidth:
        ds_widget.setMinimumWidth(minwidth)

    options = {"ds_widget": ds_widget}
    exec("w = " + code, options)
    w = options['w']

    if enable is not None:
        w.setEnabled(enable)

    w.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)

    ds_widget.show()  # to make sure we can see everything

    w.grab().save(osp.join(confdir, output))
    ds_widget.close_sp()
    ds_widget.close()
    return output


def plotmethod(argument):
    return directives.choice(argument, ("mapplot", "lineplot", "plot2d"))


class ScreenshotDirective(SphinxDirective):
    """A directive to generate screenshots of the GUI.

    Usage::

        .. screenshot:: <widget> <img-file>
            :width: 20px
            ... other image options ...
    """

    has_content = False

    option_spec = directives.images.Image.option_spec.copy()

    option_spec["plot"] = directives.flag
    option_spec["enable"] = directives.flag
    option_spec["plotmethod"] = plotmethod
    option_spec["minwidth"] = directives.positive_int
    option_spec["generate"] = directives.flag

    target_directive = "image"

    required_arguments = 2
    optional_arguments = 0

    def add_line(self, line: str) -> None:
        """Append one line of generated reST to the output."""
        source = self.get_source_info()
        if line.strip():  # not a blank line
            self.result.append(line, *source)
        else:
            self.result.append('', *source)

    def generate(self) -> None:
        """Generate the content."""
        self.add_line(f".. {self.target_directive}:: {self.img_name}")

        for option, val in self.options.items():
            self.add_line(f"    :{option}: {val}")

    def run(self):
        """Run the directive."""
        self.result = StringList()

        make_plot = self.options.pop("plot", False) is None
        enable = True if self.options.pop("enable", False) is None else None

        rebuild_screenshot = (
            self.options.pop("generate", False) or
            self.env.app.config.rebuild_screenshots
        )

        self.img_name = create_screenshot(
            *self.arguments, make_plot=make_plot, enable=enable,
            plotmethod=self.options.pop("plotmethod", None) or "mapplot",
            minwidth=self.options.pop("minwidth", None),
            generate=rebuild_screenshot,
        )

        self.generate()

        node = nodes.paragraph()
        node.document = self.state.document
        self.state.nested_parse(self.result, 0, node)

        return node.children


class ScreenshotFigureDirective(ScreenshotDirective):
    """A directive to generate screenshots of the GUI.

    Usage::

        .. screenshot-figure:: <widget> <img-file>
            :width: 20px
            ... other image options ...

            some caption
    """

    target_directive = "figure"

    has_content = True

    def generate(self):
        super().generate()

        if self.content:
            self.add_line('')
            indent = "    "
            for line in self.content:
                self.add_line(indent + line)



def setup(app):
    app.add_directive('screenshot', ScreenshotDirective)
    app.add_directive("screenshot-figure", ScreenshotFigureDirective)
    app.add_config_value('rebuild_screenshots', rebuild_screenshots, 'env')
