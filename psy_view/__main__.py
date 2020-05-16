# -*- coding: utf-8 -*-
"""main module of straditize

**Disclaimer**

Copyright (C) 2020  Philipp S. Sommer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program. If not, see <https://www.gnu.org/licenses/>."""
import sys
import argparse
from textwrap import dedent
import psy_view


def start_app(ds):
    from PyQt5 import QtWidgets
    from PyQt5.QtGui import QIcon
    from psyplot_gui import rcParams

    rcParams['help_explorer.use_webengineview'] = False

    from psy_view.ds_widget import DatasetWidget
    from psyplot_gui.common import get_icon

    app = QtWidgets.QApplication(sys.argv)
    ds_widget = DatasetWidget(ds)
    ds_widget.setWindowIcon(QIcon(get_icon('logo.svg')))
    ds_widget.show()
    sys.excepthook = ds_widget.excepthook
    sys.exit(app.exec_())


def get_parser():
    parser = argparse.ArgumentParser('psy-view')

    parser.add_argument(
        'input_file', help="The file to visualize", nargs='?', default=None)

    parser.add_argument(
        '-V', '--version', action='version', version=psy_view.__version__)

    parser.epilog = dedent("""
    psy-view  Copyright (C) 2020  Philipp S. Sommer

    This program comes with ABSOLUTELY NO WARRANTY.
    This is free software, and you are welcome to redistribute it
    under the conditions of the GNU GENERAL PUBLIC LICENSE, Version 3.""")

    return parser


def main():
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

    start_app(ds)


if __name__ == '__main__':
    main()