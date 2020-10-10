.. psy-view documentation master file, created by
   sphinx-quickstart on Wed Jul  8 21:08:22 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

.. _psy-view:

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
        * - get in touch
          - |gitter| |mailing-list| |issues|

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

    .. |gitter| image:: https://img.shields.io/gitter/room/psyplot/community.svg?style=flat
        :target: https://gitter.im/psyplot/community
        :alt: Gitter

    .. |mailing-list| image:: https://img.shields.io/badge/join-mailing%20list-brightgreen.svg?style=flat
        :target: https://www.listserv.dfn.de/sympa/subscribe/psyplot
        :alt: DFN mailing list

    .. |issues| image:: https://img.shields.io/github/issues-raw/psyplot/psy-view.svg?style=flat
        :target: https://github.com/psyplot/psy-view/issues
        :alt: GitHub issues

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

   installing
   getting-started
   user-guide
   ncview
   command_line
   api/psy_view
   todo


Get in touch
------------
Any quesions? Do not hessitate to get in touch with the psyplot developers.

- Create an issue at the `bug tracker`_
- Chat with the developers in out `channel on gitter`_
- Subscribe to the `mailing list`_ and ask for support
- Sent a mail to psyplot@hzg.de

See also the `code of conduct`_, and our `contribution guide`_ for more
information and a guide about good bug reports.

.. _bug tracker: https://github.com/psyplot/psy-view
.. _channel on gitter: https://gitter.im/psyplot/community
.. _mailing list: https://www.listserv.dfn.de/sympa/subscribe/psyplot
.. _code of conduct: https://github.com/psyplot/psyplot/blob/master/CODE_OF_CONDUCT.md
.. _contribution guide: https://github.com/psyplot/psyplot/blob/master/CONTRIBUTING.md




Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
