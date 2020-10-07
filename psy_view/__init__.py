# -*- coding: utf-8 -*-
"""ncview-like GUI to the psyplot framework

**Disclaimer**

Copyright (C) 2020 Philipp S. Sommer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see https://www.gnu.org/licenses/."""
from __future__ import annotations
from typing import (
    TYPE_CHECKING,
    Dict,
    Any,
    Optional,
    Tuple,
    Union,
    Type,
)

import sys
import argparse

if TYPE_CHECKING:
    from xarray import Dataset

from ._version import get_versions

__version__ = get_versions()['version']

del get_versions

__author__ = "Philipp S. Sommer"

__copyright__ = "Copyright 2020, Philipp S. Sommer"

__email__ = "philipp.sommer@hzg.de"

__status__ = "Development"

__license__ = "GPLv3"


def start_app(
        ds: Optional[Dataset], name: Optional[str] = None,
        plotmethod: str = 'mapplot', preset: Optional[str] = None
    ) -> None:
    """Start the standalone GUI application.

    This function creates a `QApplication` instance, an instance of the
    :class:`psy_view.ds_widget.DatasetWidget` and enters the main event loop.

    Parameters
    ----------
    ds: xarray.Dataset
        The dataset to display. If None, the user can select it afterwards
    name: str
        The variable name in `ds` to display. If None, the user can select it
        afterwards
    plotmethod: {'mapplot' | 'lineplot' | 'plot2d' }
        The plotmethod to use
    preset: str
        The preset to apply
    """
    from PyQt5 import QtWidgets
    from PyQt5.QtGui import QIcon  # pylint: disable=no-name-in-module
    from psyplot_gui import rcParams

    rcParams['help_explorer.use_webengineview'] = False

    from psy_view.ds_widget import DatasetWidget
    from psyplot_gui.common import get_icon

    app = QtWidgets.QApplication(sys.argv)
    ds_widget = DatasetWidget(ds)
    ds_widget.setWindowIcon(QIcon(get_icon('logo.svg')))
    if preset is not None:
        ds_widget.load_preset(preset)
    if name is not None:
        if ds is None:
            raise ValueError("Variable specified but without dataset")
        elif name not in ds_widget.variable_buttons:
            valid = list(ds_widget.variable_buttons)
            raise ValueError(f"{name} is not part of the dataset. "
                             f"Possible variables are {valid}.")
        ds_widget.plotmethod = plotmethod
        ds_widget.variable = name
        ds_widget.make_plot()
        ds_widget.refresh()
    ds_widget.show()
    ds_widget.show_current_figure()
    sys.excepthook = ds_widget.excepthook
    sys.exit(app.exec_())


def get_parser() -> argparse.ArgumentParser:
    """Get the command line parser for psy-view."""
    from textwrap import dedent
    parser = argparse.ArgumentParser('psy-view')

    parser.add_argument(
        'input_file', help="The file to visualize", nargs='?', default=None)

    parser.add_argument(
        '-n', '--name',
        help=("Variable name to display. Don't provide a variable to display "
              "the first variable found in the dataset."),
        const=object, nargs="?")

    parser.add_argument(
        '-pm', '--plotmethod', help="The plotmethod to use", default="mapplot",
        choices=["mapplot", "plot2d", "lineplot"])

    parser.add_argument(
        '--preset', help="Apply a preset to the plot")

    parser.add_argument(
        '-V', '--version', action='version', version=__version__)

    parser.epilog = dedent("""
    psy-view  Copyright (C) 2020  Philipp S. Sommer

    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it
    under the conditions of the GNU GENERAL PUBLIC LICENSE, Version 3.""")

    return parser


def main() -> None:
    """Start the app with the provided command-line options."""
    import psyplot.project as psy
    parser = get_parser()
    args = parser.parse_known_args()[0]

    if args.input_file is not None:
        try:
            ds = psy.open_dataset(args.input_file)
        except:
            ds = psy.open_dataset(args.input_file, decode_times=False)
    else:
        ds = None

    if args.name is object and ds is not None:
        args.name = list(ds)[0]

    start_app(ds, args.name, args.plotmethod, args.preset)


if __name__ == "__main__":
    main()
