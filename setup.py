import os
import os.path as osp
from setuptools import setup, find_packages
from setuptools.command.test import test as TestCommand
import sys


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
        return f.read()


# read the version from version.py
with open(osp.join('psy_view', 'version.py')) as f:
    exec(f.read())


dependencies = [
    'psyplot-gui>1.2.4',
    'psyplot>1.2.1',
    'psy-maps>1.2.0',
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


setup(name='psy-view',
      version=__version__,
      description='ncview-like interface to psyplot',
      long_description=readme(),
      classifiers=[
        'Development Status :: 2 - Pre-Alpha',
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
      cmdclass={'test': PyTest},
      entry_points={
          'console_scripts': ['psy-view=psy_view.__main__:main'],
          'psyplot_gui': ['psy-view=psy_view.ds_widget:DatasetWidgetPlugin'],
          },
      zip_safe=False)
