import sys
import argparse
from PyQt5 import QtWidgets
from PyQt5.QtGui import QIcon
from psy_view import DatasetWidget
from psyplot_gui.common import get_icon


def start_app(ds):
    app = QtWidgets.QApplication(sys.argv)
    main = QtWidgets.QMainWindow()
    main.setWindowIcon(QIcon(get_icon('logo.png')))
    ds_widget = DatasetWidget(ds)
    main.setCentralWidget(ds_widget)
    main.show()
    sys.exit(app.exec_())


def setup_parser():
    parser = argparse.ArgumentParser('psy-view')

    parser.add_argument(
        'input_file', help="The file to visualize")

    parser.add_argument(
        "--display-style", default="html",
        help="Display style for netCDF dataset. Default: %(default)s",
        choices=["html", "text"])

    return parser


def main():
    import xarray as xr
    import psyplot.project as psy
    parser = setup_parser()
    args = parser.parse_known_args()[0]

    xr.set_options(display_style=args.display_style)

    try:
        ds = psy.open_dataset(args.input_file)
    except:
        ds = psy.open_dataset(args.input_file, decode_times=False)

    start_app(ds)


if __name__ == '__main__':
    main()