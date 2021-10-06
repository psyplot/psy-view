.. highlight:: bash

.. _command-line:

Command line usage
==================
The :mod:`psy_view.__main__` module defines the command line options for
psy-view. It can be run from the command line via::

    python -m psy-view [options] [arguments]

or simply::

    psy-view [options] [arguments]

.. argparse::
   :module: psy_view
   :func: get_parser
   :prog: psy-view
