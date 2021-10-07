"""Setup script for the psy-view package."""

# Disclaimer
# ----------
#
# Copyright (C) 2021 Helmholtz-Zentrum Hereon
# Copyright (C) 2020-2021 Helmholtz-Zentrum Geesthacht
#
# This file is part of psy-view and is released under the GNU LGPL-3.O license.
# See COPYING and COPYING.LESSER in the root of the repository for full
# licensing details.
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License version 3.0 as
# published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU LGPL-3.0 license for more details.
#
# You should have received a copy of the GNU LGPL-3.0 license
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

import os
import os.path as osp
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import sys

import versioneer


class PyTest(TestCommand):
    user_options = [('pytest-args=', 'a', "Arguments to pass to pytest")]

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.pytest_args = ''

    def run_tests(self):
        import shlex
        # import here, cause outside the eggs aren't loaded
        import pytest
        errno = pytest.main(shlex.split(self.pytest_args))
        sys.exit(errno)


def readme():
    with open('README.rst') as f:
        return f.read().replace(
            'docs/_static/screenshot.png',
            'https://raw.githubusercontent.com/psyplot/psy-view/master/'
            'docs/_static/screenshot.png')


version = versioneer.get_version()

dependencies = [
    'psyplot-gui>=1.3.0',
    'psy-maps>=1.3.0',
    'netCDF4',
]

# Test for PyQt5 dependency. During a conda build, this is handled by the
# meta.yaml so we can skip this dependency
if not os.getenv('CONDA_BUILD'):
    # The package might nevertheless be installed, just registered with a
    # different name
    try:
        import PyQt5
    except ImportError:
        dependencies.append('pyqt5!=5.12')
        dependencies.append('PyQtWebEngine')
        dependencies.append('pyqt5-sip')


cmdclass = versioneer.get_cmdclass({'test': PyTest})


setup(name='psy-view',
      version=version,
      description='ncview-like interface to psyplot',
      long_description=readme(),
      long_description_content_type="text/x-rst",
      classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: GNU Lesser General Public License v3 (LGPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
        'Operating System :: OS Independent',
      ],
      keywords=(
          'visualization netcdf raster cartopy earth-sciences pyqt qt '
          'ipython jupyter qtconsole ncview'
      ),
      url='https://github.com/psyplot/psy-view',
      author='Philipp S. Sommer',
      author_email='psyplot@hereon.de',
      license="LGPL-3.0-only",
      packages=find_packages(exclude=['docs', 'tests*', 'examples']),
      install_requires=dependencies,
      package_data={'psy_view': [
          osp.join('psy_view', 'icons', '*.png'),
          ]},
      include_package_data=True,
      tests_require=['pytest', 'pytest-qt'],
      cmdclass=cmdclass,
      entry_points={
          'console_scripts': ['psy-view=psy_view:main'],
          'psyplot_gui': ['psy-view=psy_view.ds_widget:DatasetWidgetPlugin'],
          },
      project_urls={
          'Documentation': 'https://psyplot.github.io/psy-view',
          'Source': 'https://github.com/psyplot/psy-viewi',
          'Tracker': 'https://github.com/psyplot/psy-view/issues',
      },
      zip_safe=False)
