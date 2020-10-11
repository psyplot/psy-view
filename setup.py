import os
import os.path as osp
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import sys

if os.getenv("READTHEDOCS") == "True":
    # to make versioneer working, we need to unshallow this repo
    # because RTD does a checkout with --depth 50
    import subprocess as spr
    rootdir = osp.dirname(__file__)
    spr.call(["git", "-C", rootdir, "fetch", "--unshallow", "origin"])

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
            'img/screenshot.png',
            'https://raw.githubusercontent.com/psyplot/psyplot/master/'
            'img/screenshot.png')

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
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Topic :: Scientific/Engineering :: Visualization',
        'Topic :: Scientific/Engineering :: GIS',
        'Topic :: Scientific/Engineering',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Operating System :: OS Independent',
      ],
      keywords=('visualization earth-sciences paleo climate paleoclimate '
                'pollen diagram digitization database'),
      url='https://github.com/psyplot/psy-view',
      author='Philipp S. Sommer',
      author_email='philipp.sommer@hzg.de',
      license="GPLv3",
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
      zip_safe=False)
