.. psy-view documentation master file, created by
   sphinx-quickstart on Wed Jul  8 21:08:22 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to psy-view!
====================

.. image:: _static/screenshot.png
    :width: 50%
    :alt: GUI screenshot
    :align: center

*psy-view* defines a viewer application for netCDF files, that is highly
motivated by the ncview_ software but entirely built upon the psyplot framework.
It supports strucutured and unstructured grids and provides an intuitive
graphical user interface to quickly dive into the data inside a netCDF file.

.. _ncview: http://meteora.ucsd.edu/~pierce/ncview_home_page.html

.. warning::

    This package is currently under development and we highly appreciate your
    feedback! Please try it out yourself and, if you would like to see more features,
    find bugs or want to say anything else, please leave your comments and
    experiences at https://github.com/psyplot/psy-view/issues or send a mail to
    psyplot@hzg.de.

.. start-badges

.. only:: html and not epub

   .. list-table::
       :stub-columns: 1
       :widths: 10 90

       * - examples
         - |mybinder|
       * - tests
         - |travis| |appveyor| |codecov|
       * - package
         - |version| |conda| |supported-versions| |supported-implementations| |github|

   .. |mybinder| image:: https://mybinder.org/badge_logo.svg
       :target: https://mybinder.org/v2/gh/psyplot/psy-view/master?urlpath=%2Fdesktop
       :alt: mybinder.org

   .. |travis| image:: https://travis-ci.org/psyplot/psy-view.svg?branch=master
       :alt: Travis
       :target: https://travis-ci.org/psyplot/psy-view

   .. |appveyor| image:: https://ci.appveyor.com/api/projects/status/a7qxvvwt0e41j32h/branch/master?svg=true
       :alt: AppVeyor
       :target: https://ci.appveyor.com/project/psyplot/psy-view/branch/master

   .. |codecov| image:: https://codecov.io/gh/psyplot/psy-view/branch/master/graph/badge.svg
       :alt: Coverage
       :target: https://codecov.io/gh/psyplot/psy-view

   .. |conda| image:: https://anaconda.org/conda-forge/psy-view/badges/version.svg
       :alt: conda
       :target: https://anaconda.org/conda-forge/psy-view

   .. |github| image:: https://img.shields.io/github/release/psyplot/psy-view.svg
       :target: https://github.com/psyplot/psy-view/releases/latest
       :alt: Latest github release

   .. |version| image:: https://img.shields.io/pypi/v/psy-view.svg?style=flat
       :alt: PyPI Package latest release
       :target: https://pypi.python.org/pypi/psy-view

   .. |supported-versions| image:: https://img.shields.io/pypi/pyversions/psy-view.svg?style=flat
       :alt: Supported versions
       :target: https://pypi.python.org/pypi/psy-view

   .. |supported-implementations| image:: https://img.shields.io/pypi/implementation/psy-view.svg?style=flat
       :alt: Supported implementations
       :target: https://pypi.python.org/pypi/psy-view

.. end-badges

Features
--------
Some of the most important features offered by psy-view are:

- intuitive GUI to select variables, dimensions, slices, etc. and change the
  plot
- automatically decodes CF-conventions and supports unstructured grid, such as
  ICON_ or UGRID_
- animation interface
- different projections
- implemented in psyplot-gui_ for full flexibility (if desired)

Interested? Read more in the section :ref:`psy-view-vs-ncview`.

.. _ICON: https://mpimet.mpg.de/en/communication/news/focus-on-overview/icon-development
.. _UGRID: http://ugrid-conventions.github.io/ugrid-conventions/
.. _psyplot-gui: https://psyplot.readthedocs.io/projects/psyplot-gui

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   ncview   
   api/psy_view
   todo



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
