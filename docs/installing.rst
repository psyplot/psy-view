.. _install:

Installation
============

.. highlight:: bash

How to install
--------------

.. _install-conda:

Installation using conda
^^^^^^^^^^^^^^^^^^^^^^^^

We strongly recommend to install psy-view via the anaconda package
manager. Either by downloading anaconda_, or miniconda_ for you operating
system. If you installed `conda` for your operating system, open the
terminal (or `Anaconda Prompt` on Windows) and type::

    $ conda create -n psyplot -c conda-forge psy-view

to install it. On Linux and OS X, you may instead want to type::

    $ conda create -n psyplot -c conda-forge --override-channels psy-view

in order to not mix the anaconda defaults and and conda-forge channel, because
mixing them can sometimes cause incompatibilities.

The commands above installed psy-view and all it's necessary
dependencies into a separate environment that you can activate via::

    $ conda activate psyplot

Now launch the GUI via typing::

    $ psy-view

in the terminal (Anaconda Prompt). On Windows, you will also have a
corresponding entry in the start menu.

Note that you will always have to activate the conda environment
(`conda activate psyplot`) in order to start `psy-view`. The advantage, however,
is that other packages installed via conda are not affected by the dependencies
of psy-view.

.. note::

    Alternatively, you can also install psy-view directly in an existing conda
    environment by using::

        $ conda install -c conda-forge psy-view


.. _install-pip:

Installation using pip
^^^^^^^^^^^^^^^^^^^^^^
If you do not want to use conda for managing your python packages, you can also
use the python package manager ``pip`` and install via::

    $ pip install psy-view

But we strongly recommend that you make sure you have the :ref:`dependencies`
installed before.

.. _install-source:

Installation from source
^^^^^^^^^^^^^^^^^^^^^^^^
To install it from source, make sure you have the :ref:`dependencies`
installed, clone the github_ repository via::

    git clone https://github.com/psyplot/psy-view.git

and install it via::

    python -m pip install ./psy-view


.. _dependencies:

Dependencies
------------

Required dependencies
^^^^^^^^^^^^^^^^^^^^^
Psy-view supports all python versions greater than 3.7. Other dependencies are

- psyplot_ and `the corresponding dependencies`_
- the psyplot plugin psy-maps_
- the general GUI for psyplot, psyplot-gui_
- netCDF4_


.. _conda: https://conda.io/docs/
.. _anaconda: https://www.anaconda.com/download/
.. _miniconda: https://conda.io/miniconda.html
.. _psyplot: https://psyplot.readthedocs.io/en/latest/installing.html
.. _the corresponding dependencies: https://psyplot.readthedocs.io/en/latest/installing.html#dependencies
.. _psy-maps: https://psyplot.readthedocs.io/projects/psy-maps/en/latest/installing.html
.. _psyplot-gui: https://psyplot.readthedocs.io/projects/psyplot-gui/en/latest/installing.html
.. _netCDF4: https://github.com/Unidata/netcdf4-python


Running the tests
-----------------
We us pytest_ to run our tests. So install pytest and pytest-qt via::

    $ conda install -c conda-forge pytest pytest-qt

clone the github repository via::

    $ git clone https://github.com/psyplot/psy-view.git

And from within the cloned repository, run

    $ pytest -xv

Alternatively, you can build the conda recipe at ``ci/conda-recipe`` which
will also run the test suite. Just install `conda-build` via::

    $ conda install -n base conda-build

and build the recipe via::

    $ conda build ci/conda-recipe


.. _install-docs:

Building the docs
-----------------
To build the docs, check out the github_ repository and install the
requirements in ``'docs/environment.yml'``. The easiest way to do this is,
again, via conda::

    $ conda env create -f docs/environment.yml
    $ conda activate psy-view-docs

You also need to install the sphinx_rtd_theme via::

    $ pip install sphinx_rtd_theme

Then build the docs via::

    $ cd docs
    $ make html


.. _github: https://github.com/psyplot/psy-view
.. _pytest: https://pytest.org/latest/contents.html


.. _uninstall:

Uninstallation
--------------
The uninstallation depends on the system you used to install psyplot. Either
you did it via :ref:`conda <install-conda>` (see
:ref:`uninstall-conda`), via :ref:`pip <install-pip>` or from the
:ref:`source files <install-source>` (see :ref:`uninstall-pip`).

Anyway, if you may want to remove the psyplot configuration files. If you did
not specify anything else (see :func:`psyplot.config.rcsetup.psyplot_fname`),
the configuration files for psyplot are located in the user home directory.
Under linux and OSX, this is ``$HOME/.config/psyplot``. On other platforms it
is in the ``.psyplot`` directory in the user home.

.. _uninstall-conda:

Uninstallation via conda
^^^^^^^^^^^^^^^^^^^^^^^^
If you installed psy-view via :ref:`conda <install-conda>` into a separate
environment, simply run::

    conda env remove -n psyplot  # assuming you named the environment psyplot

If you want to uninstall psy-view, only, type::

    conda uninstall psy-view

.. _uninstall-pip:

Uninstallation via pip
^^^^^^^^^^^^^^^^^^^^^^
Uninstalling via pip simply goes via::

    pip uninstall psy-view

Note, however, that you should use :ref:`conda <uninstall-conda>` if you
installed it via conda.
