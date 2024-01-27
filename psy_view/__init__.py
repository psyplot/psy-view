# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

"""psy-view

ncview-like interface to psyplot
"""

from __future__ import annotations

import argparse
import sys
from typing import Optional

# importing xarray here for some reason speeds up starting the GUI...
import xarray as xr

from . import _version

__version__ = _version.get_versions()["version"]

__author__ = "Philipp S. Sommer"

__copyright__ = """
Copyright (C) 2021 Helmholtz-Zentrum Hereon
Copyright (C) 2020-2021 Helmholtz-Zentrum Geesthacht
"""

__credits__ = ["Philipp S. Sommer"]
__license__ = "LGPL-3.0-only"

__maintainer__ = "Philipp S. Sommer"
__email__ = "philipp.sommer@hereon.de"

__status__ = "Production"


def start_app(
    ds: Optional[xr.Dataset],
    name: Optional[str] = None,
    plotmethod: str = "mapplot",
    preset: Optional[str] = None,
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
    from psyplot_gui import rcParams
    from PyQt5 import QtWidgets
    from PyQt5.QtGui import QIcon  # pylint: disable=no-name-in-module

    rcParams["help_explorer.use_webengineview"] = False

    from psyplot_gui.common import get_icon

    from psy_view.ds_widget import DatasetWidgetStandAlone

    app = QtWidgets.QApplication(sys.argv)
    ds_widget = DatasetWidgetStandAlone(ds)
    ds_widget.setWindowIcon(QIcon(get_icon("logo.svg")))
    if preset is not None:
        ds_widget.load_preset(preset)
    if name is not None:
        if ds is None:
            raise ValueError("Variable specified but without dataset")
        elif name not in ds_widget.variable_buttons:
            valid = list(ds_widget.variable_buttons)
            raise ValueError(
                f"{name} is not part of the dataset. "
                f"Possible variables are {valid}."
            )
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

    parser = argparse.ArgumentParser("psy-view")

    parser.add_argument(
        "input_file", help="The file to visualize", nargs="?", default=None
    )

    parser.add_argument(
        "-n",
        "--name",
        help=(
            "Variable name to display. Don't provide a variable to display "
            "the first variable found in the dataset."
        ),
        const=object,
        nargs="?",
    )

    parser.add_argument(
        "-pm",
        "--plotmethod",
        help="The plotmethod to use",
        default="mapplot",
        choices=["mapplot", "plot2d", "lineplot"],
    )

    parser.add_argument("--preset", help="Apply a preset to the plot")

    parser.add_argument(
        "-V", "--version", action="version", version=__version__
    )

    parser.epilog = dedent(
        """
    psy-view  Copyright (C) 2020  Philipp S. Sommer

    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it
    under the conditions of the GNU GENERAL PUBLIC LICENSE, Version 3."""
    )

    return parser


def main() -> None:
    """Start the app with the provided command-line options."""
    import psyplot.project as psy

    parser = get_parser()
    args = parser.parse_known_args()[0]

    if args.input_file is not None:
        try:
            ds = psy.open_dataset(args.input_file)
        except Exception:
            ds = psy.open_dataset(args.input_file, decode_times=False)
    else:
        ds = None

    if args.name is object and ds is not None:
        args.name = list(ds)[0]

    start_app(ds, args.name, args.plotmethod, args.preset)


if __name__ == "__main__":
    main()
