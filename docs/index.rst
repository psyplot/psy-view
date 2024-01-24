.. SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
..
.. SPDX-License-Identifier: CC-BY-4.0

.. psy-view documentation master file
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to psy-view's documentation!
====================================

|CI|
|Code coverage|
|Latest Release|
|PyPI version|
|Code style: black|
|Imports: isort|
|PEP8|
|Checked with mypy|
|REUSE status|

.. rubric:: ncview-like interface to psyplot

.. warning::

    This page has been automatically generated as has not yet been reviewed by
    the authors of psy-view!
    Stay tuned for updates and discuss with us at
    https://codebase.helmholtz.cloud/psyplot/psy-view

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

.. _ICON: https://code.mpimet.mpg.de/projects/iconpublic
.. _UGRID: http://ugrid-conventions.github.io/ugrid-conventions/
.. _psyplot-gui: https://psyplot.github.io/psyplot-gui




.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installing
   getting-started
   user-guide
   ncview
   command_line
   api
   contributing
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


How to cite this software
-------------------------

.. card:: Please do cite this software!

   .. tab-set::

      .. tab-item:: APA

         .. citation-info::
            :format: apalike

      .. tab-item:: BibTex

         .. citation-info::
            :format: bibtex

      .. tab-item:: RIS

         .. citation-info::
            :format: ris

      .. tab-item:: Endnote

         .. citation-info::
            :format: endnote

      .. tab-item:: CFF

         .. citation-info::
            :format: cff


License information
-------------------
Copyright © 2021-2024 Helmholtz-Zentrum hereon GmbH

The source code of psy-view is licensed under
LGPL-3.0-only.

If not stated otherwise, the contents of this documentation is licensed under
CC-BY-4.0.


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


.. |CI| image:: https://codebase.helmholtz.cloud/psyplot/psy-view/badges/main/pipeline.svg
   :target: https://codebase.helmholtz.cloud/psyplot/psy-view/-/pipelines?page=1&scope=all&ref=main
.. |Code coverage| image:: https://codebase.helmholtz.cloud/psyplot/psy-view/badges/main/coverage.svg
   :target: https://codebase.helmholtz.cloud/psyplot/psy-view/-/graphs/main/charts
.. |Latest Release| image:: https://codebase.helmholtz.cloud/psyplot/psy-view/-/badges/release.svg
   :target: https://codebase.helmholtz.cloud/psyplot/psy-view
.. .. TODO: uncomment the following line when the package is published at https://pypi.org
.. .. |PyPI version| image:: https://img.shields.io/pypi/v/psy-view.svg
..    :target: https://pypi.python.org/pypi/psy-view/
.. |Code style: black| image:: https://img.shields.io/badge/code%20style-black-000000.svg
   :target: https://github.com/psf/black
.. |Imports: isort| image:: https://img.shields.io/badge/%20imports-isort-%231674b1?style=flat&labelColor=ef8336
   :target: https://pycqa.github.io/isort/
.. |PEP8| image:: https://img.shields.io/badge/code%20style-pep8-orange.svg
   :target: https://www.python.org/dev/peps/pep-0008/
.. |Checked with mypy| image:: http://www.mypy-lang.org/static/mypy_badge.svg
   :target: http://mypy-lang.org/
.. TODO: uncomment the following line when the package is registered at https://api.reuse.software
.. .. |REUSE status| image:: https://api.reuse.software/badge/codebase.helmholtz.cloud/psyplot/psy-view
..    :target: https://api.reuse.software/info/codebase.helmholtz.cloud/psyplot/psy-view
