"""Dialogs for manipulating formatoptions.

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
along with this program.  If not, see https://www.gnu.org/licenses/.
"""
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

import yaml
from PyQt5 import QtWidgets, QtGui
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas)
from matplotlib.figure import Figure

from psyplot.plotter import Plotter, Formatoption

if TYPE_CHECKING:
    from psyplot.project import Project
    from PyQt5.QtCore import QEvent  # pylint: disable=no-name-in-module


#: TODO: Find a more appropriate description here
Color = Any

#: TODO: Find a more appropriate description here
LSM_T = Dict[str, Any]


class BasemapDialog(QtWidgets.QDialog):
    """A dialog to modify the basemap settings."""

    xgrid_value: Optional[Union[str, Tuple[Any, Any]]]
    ygrid_value: Optional[Union[str, Tuple[Any, Any]]]

    def __init__(self, plotter: Plotter, *args, **kwargs) -> None:
        """
        Parameters
        ----------
        plotter: psy_maps.plotters.MapPlotter
            The psyplot plotter to configure
        """
        import psy_simple.widgets.colors as pswc
        import pandas as pd
        super().__init__(*args, **kwargs)
        vbox = QtWidgets.QVBoxLayout(self)

        #: colors that affect the map background
        self.colors = ['background', 'land', 'ocean', 'coast']

        #: QGridLayout to display the various colors
        grid = QtWidgets.QGridLayout()

        defaults = self.default_colors

        #: :class:`pandas.DataFrame` of widgets to modifiy the :attr:`colors`
        self.widgets = widgets = pd.DataFrame(
            index=['enable', 'color'], columns=self.colors, dtype=object)

        for i, col in enumerate(self.colors):
            widgets.iloc[0, i] = cb = QtWidgets.QCheckBox()
            cb.setChecked(False)
            widgets.iloc[1, i] = lbl = pswc.ColorLabel(defaults[col])
            lbl.setEnabled(False)

            cb.stateChanged.connect(lbl.setEnabled)

            grid.addWidget(QtWidgets.QLabel(col), 0, i)
            grid.addWidget(cb, 1, i)
            grid.addWidget(lbl, 2, i)

        vbox.addLayout(grid)

        #: Button box to cancel the operator or update the plotter
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        proj_box = QtWidgets.QGroupBox("Projection settings")
        layout = QtWidgets.QFormLayout(proj_box)

        #: text box for the central longitude (clon formatoption)
        self.txt_clon = QtWidgets.QLineEdit()
        self.txt_clon.setPlaceholderText('auto')
        self.txt_clon.setToolTip('Central longitude in degrees East')
        self.txt_clon.setValidator(QtGui.QDoubleValidator(-360, 360, 7))
        layout.addRow('Central longitude: ', self.txt_clon)

        #: text box for the central latitude (clat formatoption)
        self.txt_clat = QtWidgets.QLineEdit()
        self.txt_clat.setPlaceholderText('auto')
        self.txt_clat.setToolTip('Central latitude in degrees North')
        self.txt_clat.setValidator(QtGui.QDoubleValidator(-90, 90, 7))
        layout.addRow('Central latitude: ', self.txt_clat)

        vbox.addWidget(proj_box)

        #: group box for modifying the resolution of the land-sea-mask, see
        #: :attr:`opt_110m`, :attr:`opt_50m`, :attr:`opt_10m`
        self.lsm_box = QtWidgets.QGroupBox('Coastlines')
        self.lsm_box.setCheckable(True)
        hbox = QtWidgets.QHBoxLayout(self.lsm_box)
        hbox.addWidget(QtWidgets.QLabel("Resolution:"))

        #: Radiobutton for 110m resolution of lsm
        self.opt_110m = QtWidgets.QRadioButton("110m")

        #: Radiobutton for 50m resolution of lsm
        self.opt_50m = QtWidgets.QRadioButton("50m")

        #: Radiobutton for 10m resolution of lsm
        self.opt_10m = QtWidgets.QRadioButton("10m")
        hbox.addWidget(self.opt_110m)
        hbox.addWidget(self.opt_50m)
        hbox.addWidget(self.opt_10m)

        vbox.addWidget(self.lsm_box)

        #: group box drawing grid lines and labels
        self.grid_labels_box = QtWidgets.QGroupBox('Labels')
        self.grid_labels_box.setToolTip("Draw labels of meridionals and "
                                        "parallels")
        self.grid_labels_box.setCheckable(True)

        #: text box for the fontsize of grid labels
        self.txt_grid_fontsize = QtWidgets.QLineEdit()

        form = QtWidgets.QFormLayout(self.grid_labels_box)
        form.addRow("Font size:", self.txt_grid_fontsize)

        vbox.addWidget(self.grid_labels_box)

        #: Group box for options specific to meridionals (see
        #: :attr:`opt_meri_auto`, :attr:`opt_meri_at` and
        #: :attr:`opt_meri_every`, :attr:`opt_meri_num`)
        self.meridionals_box = QtWidgets.QGroupBox('Meridionals')
        self.meridionals_box.setCheckable(True)

        #: Radiobutton for automatic drawing of meridionals
        self.opt_meri_auto = QtWidgets.QRadioButton("auto")

        #: Radiobutton for giving the exact position of meridionals (see
        #: :attr:`txt_meri_at`)
        self.opt_meri_at = QtWidgets.QRadioButton("At:")

        #: Text field to enter the location of the meridionals on the map (see
        #: :attr:`opt_meri_at`)
        self.txt_meri_at = QtWidgets.QLineEdit()
        self.txt_meri_at.setPlaceholderText("30, 60, 90, 120, ... °E")
        # TODO: Add validator

        #: Radiobutton for equal-width spaced meridionals (see
        #: :attr:`txt_meri_every`)
        self.opt_meri_every = QtWidgets.QRadioButton("Every:")

        #: Text box to specify the distance between two meridionals (see
        #: :attr:`opt_meri_every`)
        self.txt_meri_every = QtWidgets.QLineEdit()
        self.txt_meri_every.setPlaceholderText("30 °E")
        self.txt_meri_every.setValidator(QtGui.QDoubleValidator(0, 360, 7))

        #: Radiobutton to draw a specific number of meridionals with
        #: equal-distance (see also :attr:`txt_meri_num`)
        self.opt_meri_num = QtWidgets.QRadioButton("Number:")

        #: Text box to set the number of meridionals to be shown (see
        #: :attr:`opt_meri_num`)
        self.txt_meri_num = QtWidgets.QLineEdit()
        self.txt_meri_num.setPlaceholderText("5")
        self.txt_meri_num.setValidator(QtGui.QIntValidator(1, 720))

        form = QtWidgets.QFormLayout(self.meridionals_box)
        form.addRow(self.opt_meri_auto)
        form.addRow(self.opt_meri_at, self.txt_meri_at)
        form.addRow(self.opt_meri_every, self.txt_meri_every)
        form.addRow(self.opt_meri_num, self.txt_meri_num)

        vbox.addWidget(self.meridionals_box)

        #: Group box for options specific to parallels (see
        #: :attr:`opt_para_auto`, :attr:`opt_para_at` and
        #: :attr:`opt_para_every`, :attr:`opt_para_num`)
        self.parallels_box = QtWidgets.QGroupBox('Parallels')
        self.parallels_box.setCheckable(True)

        #: Radiobutton for automatic drawing of parallels
        self.opt_para_auto = QtWidgets.QRadioButton("auto")

        #: Radiobutton for giving the exact position of parallels (see
        #: :attr:`txt_para_at`)
        self.opt_para_at = QtWidgets.QRadioButton("At:")

        #: Text field to enter the location of the parallels on the map (see
        #: :attr:`opt_para_at`)
        self.txt_para_at = QtWidgets.QLineEdit()
        self.txt_para_at.setPlaceholderText("-60, -30, 0, 30, ... °N")
        # TODO: Add validator

        #: Radiobutton for equal-width spaced parallels (see
        #: :attr:`txt_para_every`)
        self.opt_para_every = QtWidgets.QRadioButton("Every:")

        #: Text box to specify the distance between two parallels (see
        #: :attr:`opt_para_every`)
        self.txt_para_every = QtWidgets.QLineEdit()
        self.txt_para_every.setPlaceholderText("30 °N")
        self.txt_para_every.setValidator(QtGui.QDoubleValidator(0, 90, 7))

        #: Radiobutton to draw a specific number of parallels with
        #: equal-distance (see also :attr:`txt_para_num`)
        self.opt_para_num = QtWidgets.QRadioButton("Number:")

        #: Text box to set the number of parallels to be shown (see
        #: :attr:`opt_para_num`)
        self.txt_para_num = QtWidgets.QLineEdit()
        self.txt_para_num.setPlaceholderText("5")
        self.txt_para_num.setValidator(QtGui.QIntValidator(1, 360))

        form = QtWidgets.QFormLayout(self.parallels_box)
        form.addRow(self.opt_para_auto)
        form.addRow(self.opt_para_at, self.txt_para_at)
        form.addRow(self.opt_para_every, self.txt_para_every)
        form.addRow(self.opt_para_num, self.txt_para_num)

        vbox.addWidget(self.parallels_box)

        vbox.addWidget(self.button_box)

        self.fill_from_plotter(plotter)

        for button in [self.opt_meri_at, self.opt_meri_auto, self.opt_meri_num,
                       self.opt_meri_every, self.opt_para_at,
                       self.opt_para_auto, self.opt_para_num,
                       self.opt_para_every]:
            button.clicked.connect(self.update_forms)

    @property
    def default_colors(self) -> Dict[str, Color]:
        """Get default colors for the color labels in :attr:`widgets`."""
        import cartopy.feature as cf
        import matplotlib as mpl
        return {
            'background': mpl.rcParams['axes.facecolor'],
            'land': cf.LAND._kwargs['facecolor'],
            'ocean': cf.OCEAN._kwargs['facecolor'],
            'coast': 'k',
            }

    def get_colors(self, plotter: Plotter) -> Dict[str, Color]:
        """Get the colors for :attr:`widgets` from the plotter formatoptions.

        Parameters
        ----------
        plotter: psy_maps.plotters.MapPlotter
            The plotter with the formatoptions

        Returns
        -------
        dict
            A mapping from formatoptions in :attr:`colors` to the corresponding
            color in the `plotter`.
        """
        ret = {}
        if plotter.background.value != 'rc':
            ret['background'] = plotter.background.value
        lsm = plotter.lsm.value
        for part in ['land', 'ocean', 'coast']:
            if part in lsm:
                ret[part] = lsm[part]
        return ret

    def fill_from_plotter(self, plotter: Plotter) -> None:
        """Fill the dialog from a given plotter.

        Parameters
        ----------
        plotter: psy_maps.plotters.MapPlotter
            The plotter to get the formatoptions from.
        """
        chosen_colors = self.get_colors(plotter)

        for i, col in enumerate(self.colors):
            enable = col in chosen_colors
            cb = self.widgets.iloc[0, i]
            lbl = self.widgets.iloc[1, i]
            cb.setChecked(enable)
            if enable:
                lbl._set_color(chosen_colors[col])

        if plotter.clon.value is not None:
            self.txt_clon.setText(str(plotter.clon.value))
        if plotter.clat.value is not None:
            self.txt_clat.setText(str(plotter.clat.value))

        lsm = plotter.lsm.value

        if not lsm:
            self.lsm_box.setChecked(False)
        else:
            res = lsm['res']
            getattr(self, 'opt_' + res).setChecked(True)

        grid_labels = plotter.grid_labels.value
        if grid_labels is None:
            grid_labels = True
        self.grid_labels_box.setChecked(grid_labels)
        self.txt_grid_fontsize.setText(str(plotter.grid_labelsize.value))

        self.xgrid_value = None
        value = plotter.xgrid.value
        if not value:
            self.meridionals_box.setChecked(False)
        elif value is True:
            self.opt_meri_auto.setChecked(True)
        elif isinstance(value[0], str):
            self.xgrid_value = value[0]
            self.opt_meri_num.setChecked(True)
            self.txt_meri_num.setText(str(value[1]))
        elif isinstance(value, tuple):
            self.xgrid_value: Tuple[Any, Any] = value[:2]  # type: ignore
            self.opt_meri_num.setChecked(True)
            steps = 11 if len(value) == 2 else value[3]
            self.txt_meri_num.setText(str(steps))
        else:
            self.opt_meri_at.setChecked(True)
            self.txt_meri_at.setText(', '.join(map(str, value)))

        self.ygrid_value = None
        value = plotter.ygrid.value
        if not value:
            self.parallels_box.setChecked(False)
        elif value is True:
            self.opt_para_auto.setChecked(True)
        elif isinstance(value[0], str):
            self.opt_para_num.setChecked(True)
            self.txt_para_num.setText(str(value[1]))
            self.ygrid_value = value[0]
        elif isinstance(value, tuple):
            self.ygrid_value: Tuple[Any, Any] = value[:2]  # type: ignore
            self.opt_para_num.setChecked(True)
            steps = 11 if len(value) == 2 else value[3]
            self.txt_para_num.setText(str(steps))
        else:
            self.opt_para_at.setChecked(True)
            self.txt_para_at.setText(', '.join(map(str, value)))

    def update_forms(self) -> None:
        """Update text widgets for the options to draw merdionals and parallels.
        """
        if self.meridionals_box.isChecked():
            self.txt_meri_at.setEnabled(self.opt_meri_at.isChecked())
            self.txt_meri_every.setEnabled(self.opt_meri_every.isChecked())
            self.txt_meri_num.setEnabled(self.opt_meri_num.isChecked())
        if self.parallels_box.isChecked():
            self.txt_para_at.setEnabled(self.opt_para_at.isChecked())
            self.txt_para_every.setEnabled(self.opt_para_every.isChecked())
            self.txt_para_num.setEnabled(self.opt_para_num.isChecked())

    @property
    def value(self) -> Dict[str, Any]:
        """Get the formatoptions of this dialog to update a plotter."""
        import numpy as np
        ret: Dict[str, Any] = {}
        ret['clon'] = None if not self.txt_clon.text().strip() else float(
            self.txt_clon.text().strip())
        ret['clat'] = None if not self.txt_clat.text().strip() else float(
            self.txt_clat.text().strip())

        lsm: LSM_T = {}

        for col in ['land', 'ocean', 'coast']:
            lbl = self.widgets.loc['color', col]
            if lbl.isEnabled():
                lsm[col] = list(lbl.color.getRgbF())

        if lsm or self.lsm_box.isChecked():
            if self.opt_110m.isChecked():
                lsm['res'] = '110m'
            elif self.opt_50m.isChecked():
                lsm['res'] = '50m'
            elif self.opt_10m.isChecked():
                lsm['res'] = '10m'
            else:
                lsm['res'] = '110m'
        else:
            lsm['res'] = False
        if lsm:
            ret['lsm'] = lsm

        bc_lbl = self.widgets.loc['color', 'background']
        if bc_lbl.isEnabled():
            ret['background'] = list(bc_lbl.color.getRgbF())

        ret["grid_labels"] = self.grid_labels_box.isChecked()
        if ret["grid_labels"]:
            ret["grid_labels"] = None
            labelsize = self.txt_grid_fontsize.text().strip()
            if labelsize:
                try:
                    labelsize = float(labelsize)
                except TypeError:
                    pass
                ret["grid_labelsize"] = labelsize

        if not self.meridionals_box.isChecked():
            ret['xgrid'] = False
        elif self.opt_meri_auto.isChecked():
            ret['xgrid'] = True
        elif self.opt_meri_every.isChecked():
            ret['xgrid'] = np.arange(
                -180, 180, float(self.txt_meri_every.text().strip() or 30))
        elif self.opt_meri_at.isChecked():
            ret['xgrid'] = list(map(
                float, self.txt_meri_at.text().split(','))) or False
        elif self.opt_meri_num.isChecked():
            if self.xgrid_value is None:
                ret['xgrid'] = ['rounded', int(self.txt_meri_num.text() or 5)]
            elif isinstance(self.xgrid_value, str):
                ret['xgrid'] = [self.xgrid_value,
                                int(self.txt_meri_num.text() or 5)]
            else:
                ret['xgrid'] = tuple(self.xgrid_value) + (
                    int(self.txt_meri_num.text() or 5), )

        if not self.parallels_box.isChecked():
            ret['ygrid'] = False
        elif self.opt_para_auto.isChecked():
            ret['ygrid'] = True
        elif self.opt_para_every.isChecked():
            ret['ygrid'] = np.arange(
                -180, 180, float(self.txt_para_every.text().strip() or 30))
        elif self.opt_para_at.isChecked():
            ret['ygrid'] = list(map(
                float, self.txt_para_at.text().split(','))) or False
        elif self.opt_para_num.isChecked():
            if self.ygrid_value is None:
                ret['ygrid'] = ['rounded', int(self.txt_para_num.text() or 5)]
            elif isinstance(self.ygrid_value, str):
                ret['ygrid'] = [self.ygrid_value,
                                int(self.txt_para_num.text() or 5)]
            else:
                ret['ygrid'] = tuple(self.ygrid_value) + (
                    int(self.txt_para_num.text() or 5), )
        return ret

    @classmethod
    def update_plotter(cls, plotter: Plotter) -> None:
        """Open a :class:`BasemapDialog` to update a plotter.

        Parameters
        ----------
        plotter: psy_maps.plotters.MapPlotter
            The plotter to update.
        """
        dialog = cls(plotter)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec_()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            plotter.update(
                **dialog.value)


class CmapDialog(QtWidgets.QDialog):
    """A dialog to modify color bounds and colormaps."""

    def __init__(self, project: Project, *args, **kwargs) -> None:
        """
        Parameters
        ----------
        project: psyplot.project.Project
            The psyplot project to update. Note that we will only use the
            very first plotter in this project
        """
        import psy_simple.widgets.colors as pswc
        super().__init__(*args, **kwargs)

        #: Button box to accept or cancel this dialog
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        #: Mapping from formatoption key to :class:`LabelWidgetLine` widgets to
        #: controlling the formatoption
        self.fmt_widgets = {}
        plotter = project(fmts=['cmap', 'bounds']).plotters[0]

        #: Widget for manipulating the color map
        self.cmap_widget = self.fmt_widgets['cmap'] = LabelWidgetLine(
            plotter.cmap, project, pswc.CMapFmtWidget,
            widget_kws=dict(properties=False))
        self.cmap_widget.editor.setVisible(False)
        self.cmap_widget.editor.line_edit.textChanged.connect(
            self.update_preview)

        #: tabs for switching between bounds (:attr:`bounds_widget`) and
        #: colorbar ticks (:attr:`cticks_widget`)
        self.tabs = QtWidgets.QTabWidget()

        #: :class:`LabelWidgetLine` to controll the colorbar bounds
        self.bounds_widget = self.fmt_widgets['bounds'] = LabelWidgetLine(
            plotter.bounds, project, pswc.BoundsFmtWidget,
            widget_kws=dict(properties=False))
        self.bounds_widget.editor.line_edit.textChanged.connect(
            self.update_preview)
        self.tabs.addTab(self.bounds_widget, "Colormap boundaries")

        #: :class:`LabelWidgetLine` to controll the ctick positions
        self.cticks_widget = self.fmt_widgets['cticks'] = LabelWidgetLine(
            plotter.cticks, project, pswc.CTicksFmtWidget,
            widget_kws=dict(properties=False))
        self.cticks_widget.editor.line_edit.textChanged.connect(
            self.update_preview)
        self.tabs.addTab(self.cticks_widget, "Colorbar ticks")

        #: :class:`ColorbarPreview` to show a preview of the colorbar with
        #: the selected formatoption in :attr:`fmt_widgets`
        self.cbar_preview = ColorbarPreview(plotter)
        self.cbar_preview.setMaximumHeight(self.tabs.sizeHint().height() // 3)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.cmap_widget)
        vbox.addWidget(self.tabs)
        vbox.addWidget(self.cbar_preview)
        vbox.addWidget(self.button_box)

    @property
    def plotter(self) -> Plotter:
        """Get the plotter with the formatoptions we use to fill this dialog."""
        return self.bounds_widget.editor.fmto.plotter

    def update_preview(self) -> None:
        """Update the :attr:`cbar_preview` from the various :attr:`fmt_widgets`.
        """
        try:
            bounds = self.bounds_widget.editor.value
        except Exception:
            bounds = self.plotter.bounds.value
        try:
            cticks = self.cticks_widget.editor.value
        except Exception:
            cticks = self.plotter.cticks.value
        try:
            cmap = self.cmap_widget.editor.value
        except Exception:
            cmap = self.plotter.cmap.value
        self.cbar_preview.update_colorbar(
            bounds=bounds, cticks=cticks, cmap=cmap)

    @property
    def fmts(self) -> Dict[str, Any]:
        """Map from formatoption in :attr:`fmt_widgets` to values."""
        ret = {}
        for fmt, widget in self.fmt_widgets.items():
            if widget.editor.changed:
                try:
                    value = widget.editor.value
                except:
                    raise IOError(f"{fmt}-value {widget.editor.text} could "
                                  "not be parsed to python!")
                else:
                    ret[fmt] = value
        return ret

    @classmethod
    def update_project(cls, project: Project) -> None:
        """Create a :class:`CmapDialog` to update a `project`

        This classmethod creates a new :class:`CmapDialog` instance, fills it
        with the formatoptions of the first plotter in `project`, enters the
        main event loop, and updates the `project` upon acceptance.

        Parameters
        ----------
        project: psyplot.project.Project
            The psyplot project to update
        """
        dialog = cls(project)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec_()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            project.update(**dialog.fmts)


class _DummyFormatOption(Formatoption):
    """Dummy formatoption for static type checking.
    
    This is just a workaround for the static type checker to be able to tell
    what the :class:`FakePlotter` formatoptions are, used in 
    :attr:`ColorbarPreview.fake_plotter`
    """
    def update(self,):
        pass


class FakePlotter(Plotter):
    """A dummy plotter for the colorbar preview."""

    bounds: Formatoption = _DummyFormatOption('bounds')
    cmap: Formatoption = _DummyFormatOption('cmap')
    cticks: Formatoption = _DummyFormatOption('cticks')
    cbar: Formatoption = _DummyFormatOption('cbar')


class ColorbarPreview(FigureCanvas):
    """A preview widget of a colorbar.

    This matplotlib figure contains one single axes to display the colorbar
    filled by the formatoptions of a given `plotter`."""

    def __init__(
            self,
            plotter: Plotter,
            parent: Optional[QtWidgets.QWidget] = None,
            *args, **kwargs
        ) -> None:
        """
        Parameters
        ----------
        plotter: psy_simple.plotters.Base2D
            The plotter to use to draw the colorbar from
        parent: QtWidget.QWidget
            The parent widget
        """
        fig = Figure(*args, **kwargs)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.axes_counter = 0

        #: The plotter to use for displaying the colorbar
        self.plotter = plotter
        self.init_colorbar(plotter)

    def resizeEvent(self, event: QEvent) -> Any:
        """Reimplemented to make sure we cannot get smaller than 0."""
        h = event.size().height()
        if h <= 0:
            return
        return super().resizeEvent(event)

    def init_colorbar(self, plotter: Plotter) -> None:
        """Initialize the colorbar.

        This method extracts the formatoptions of the given `plotter` and draws
        the colorbar.
        """
        from matplotlib.cm import ScalarMappable
        norm = plotter.bounds.norm
        cmap = plotter.cmap.get_cmap(self.plotter.plot.array)

        self.mappable = sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])

        self.cax = self.figure.add_axes([0.1, 0.5, 0.8, 0.5],
                                        label=self.axes_counter)

        self.cbar = self.figure.colorbar(
            sm, norm=norm, cmap=cmap, cax=self.cax, orientation='horizontal')

    @property
    def fake_plotter(self) -> FakePlotter:
        """Create a plotter with the formatoptions of the real :attr:`plotter`.

        We can update this plotter without impacting the origin :attr:`plotter`
        """
        from psyplot.plotter import Plotter

        class _FakePlotter(FakePlotter):
            bounds = self.plotter.bounds.__class__('bounds')
            cmap = self.plotter.cmap.__class__('cmap')
            cticks = self.plotter.cticks.__class__('cticks')
            cbar = self.plotter.cbar.__class__('cbar')

            _rcparams_string = self.plotter._get_rc_strings()

        ref = self.plotter
        fig = Figure()
        ax = fig.add_subplot()

        plotter = _FakePlotter(
            ref.data.copy(), make_plot=False, bounds=ref['bounds'],
            cmap=ref['cmap'], cticks=ref['cticks'], cbar='', ax=ax)

        plotter.cticks._colorbar = self.cbar

        plotter.plot_data = ref.plot_data
        return plotter

    def update_colorbar(self, **kwargs) -> None:
        """Update the colorbar with new formatoptions.

        This method takes the :attr:`fake_plotter`, updates it from the given
        `kwargs`, updates the colorbar preview.

        Parameters
        ----------
        ``**kwargs``
            `bounds`, `cmap`, `cticks` or `cbar` formatoption keyword-value
            pairs
        """

        # create a dummy plotter
        plotter = self.fake_plotter

        # update from the given kwargs
        try:
            for key, val in kwargs.items():
                plotter[key] = val
        except (ValueError, TypeError):
            return

        plotter.initialize_plot(ax=plotter.ax)

        current_norm = self.mappable.norm
        current_cmap = self.mappable.get_cmap()
        current_locator = self.cbar.locator

        # update the preview with the norm of the plotter
        try:
            try:
                plotter.bounds.norm._check_vmin_vmax()
            except (AttributeError, TypeError):
                pass
            try:
                plotter.bounds.norm.autoscale_None(plotter.bounds.array)
            except AttributeError:
                pass
            self.mappable.set_norm(plotter.bounds.norm)
            self.mappable.set_cmap(plotter.cmap.get_cmap(
                self.plotter.plot.array))
            plotter.cticks.colorbar = self.cbar
            plotter.cticks.default_locator = \
                self.plotter.cticks.default_locator
            plotter.cticks.update_axis(plotter.cticks.value)
            self.draw()

        except Exception:
            self.mappable.set_norm(current_norm)
            self.mappable.set_cmap(current_cmap)
            self.cbar.locator = current_locator
            self.cbar.update_ticks()


class FormatoptionsEditor(QtWidgets.QWidget):
    """A widget to update a formatoption.

    This widget is a light-weight version of the
    :class:`psyplot_gui.fmt_widget.FormatoptionsWidget` class. It contains
    a line editor and a text editor to set the value of a specific formatoption.
    """

    def __init__(self, fmto: Formatoption, *args, **kwargs) -> None:
        """
        Parameters
        ----------
        fmto: psyplot.plotter.Formatoption
            The formatoption instance to display the value from
        """
        super().__init__(*args, **kwargs)
        layout = QtWidgets.QHBoxLayout()

        #: The :class:`~psyplot.plotter.Formatoption` that fills this widget
        self.fmto = fmto

        #: A single line editor holding the formatoption value (see also
        #: :attr:`text_edit` and :attr:`btn_multiline`)
        self.line_edit = QtWidgets.QLineEdit()
        layout.addWidget(self.line_edit)

        #: A multi-line editor holiding the value of :attr:`fmto` (see also
        #: :attr:`line_edit` and :attr:`btn_multiline`)
        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setVisible(False)
        layout.addWidget(self.text_edit)

        #: A tool button to switch from the single line editor :attr:`line_edit`
        #: to the multi-line editor :attr:`text_edit`
        self.btn_multiline = QtWidgets.QToolButton()
        self.btn_multiline.setText('⌵')
        self.btn_multiline.setCheckable(True)
        self.btn_multiline.setToolTip("Toggle multiline editor")
        self.btn_multiline.clicked.connect(self.toggle_multiline)
        layout.addWidget(self.btn_multiline)

        self.insert_obj(fmto.value)

        #: Value of the :attr:`fmto` at the initialization of this widget
        self.initial_value = self.line_edit.text()

        self.setLayout(layout)

    @property
    def changed(self) -> bool:
        """Check if the value in this editor differs from the original `fmto`.
        """
        return self.fmto.diff(self.fmto.validate(self.get_obj()))

    def toggle_multiline(self) -> None:
        """Switch from :attr:`line_edit` and :attr:`text_edit` or back."""
        multiline = self.multiline
        self.text_edit.setVisible(multiline)
        self.line_edit.setVisible(not multiline)
        if multiline:
            self.text_edit.setPlainText(self.line_edit.text())
        else:
            self.line_edit.setText(self.text_edit.toPlainText())

    @property
    def multiline(self) -> bool:
        """True if the :attr:`text_edit` should be visible."""
        return self.btn_multiline.isChecked()

    @property
    def text(self) -> str:
        """Text of the :attr:`text_edit` (or :attr:`line_edit`)."""
        return (self.text_edit.toPlainText() if self.multiline else
                self.line_edit.text())

    @text.setter
    def text(self, s: str) -> None:
        self.clear_text()
        if self.multiline:
            self.text_edit.insertPlainText(s)
        else:
            self.line_edit.insert(s)

    @property
    def value(self) -> Any:
        """Load the value of :attr:`text` with yaml."""
        text = self.text
        return yaml.load(text, Loader=yaml.Loader)

    def clear_text(self) -> None:
        """Clear the editor."""
        if self.multiline:
            self.text_edit.clear()
        else:
            self.line_edit.clear()

    def set_obj(self, obj: Any) -> None:
        """Clear the editor and set another object."""
        self.clear_text()
        self.insert_obj(obj)

    def get_obj(self) -> Any:
        """Alias for :attr:`value`."""
        return self.value

    def insert_obj(self, obj: Any) -> None:
        """Add a string to the formatoption widget.

        Parameters
        ----------
        obj: object
            The object to insert into the line editor. it will be dumped
            using yaml and displayed in the :attr:`text_edit` (or
            :attr:`line_edit`)
        """
        current = self.text
        use_line_edit = not self.multiline
        # strings are treated separately such that we consider quotation marks
        # at the borders
        if isinstance(obj, str) and current:
            if use_line_edit:
                pos = self.line_edit.cursorPosition()
            else:
                pos = self.text_edit.textCursor().position()
            if pos not in [0, len(current)]:
                s = obj
            else:
                if current[0] in ['"', "'"]:
                    current = current[1:-1]
                self.clear_text()
                if pos == 0:
                    s = '"' + obj + current + '"'
                else:
                    s = '"' + current + obj + '"'
                current = ''
        elif isinstance(obj, str):  # add quotation marks
            s = '"' + obj + '"'
        else:
            s = yaml.dump(obj, default_flow_style=True).strip()
            if s.endswith('\n...'):
                s = s[:-4]
        if use_line_edit:
            self.line_edit.insert(s)
        else:
            self.text_edit.insertPlainText(s)


class LabelWidgetLine(QtWidgets.QGroupBox):
    """A widget to change a formatoption.

    This class holds a :class:`FormatoptionsEditor` to control the
    appearance of a specific formatoption. Additionally it displays the
    formatoption specific line widget (see
    :meth:`psyplot.plotter.Formatoption.get_fmt_widget`) to contol it.
    """

    def __init__(self, fmto: Formatoption, project: Project,
                 fmto_widget: Type[QtWidgets.QWidget],
                 widget_kws: Dict[str, Any] = {}, *args, **kwargs) -> None:
        """
        Parameters
        ----------
        fmto: psyplot.plotter.Formatoption
            The formatoption to manipulate
        project: psyplot.project.Project
            The project to use to fill this formatoption
        fmto_widget: type
            A subclass of the :class:`QWidget` that can be used to control
            the formatoption. This class is commonly used in the
            :meth:`psyplot.plotter.Formatoption.get_fmt_widget` of the given
            `fmto`
        widget_kws: dict
            Further keywords that are passed to the creation of the
            `fmto_widget` instance.
        """
        super().__init__(f'{fmto.name} ({fmto.key})', *args, **kwargs)
        self.editor = FormatoptionsEditor(fmto)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(
            fmto_widget(self.editor, fmto, project, **widget_kws))
        vbox.addWidget(self.editor)
        self.setLayout(vbox)


class LabelDialog(QtWidgets.QDialog):
    """A dialog to change labels.

    This class contains one :class:`LabelWidgetLine` per text formatoption."""

    def __init__(self, project: Project, *fmts: str) -> None:
        """
        Parameters
        ----------
        project: psyplot.project.Project
            The psyplot project to update. Note that we will only use the
            very first plotter in this project
        ``*fmts``
            The formatoption keys to display. Each formatoption should be a
            subclass of :class:`psy_simple.base.TextBase`
        """
        from psy_simple.widgets.texts import LabelWidget
        super().__init__()
        self.project = project
        layout = QtWidgets.QVBoxLayout()
        plotter = project.plotters[0]
        self.fmt_widgets = {}
        for fmt in fmts:
            fmto = getattr(plotter, fmt)
            fmt_widget = LabelWidgetLine(
                fmto, project, LabelWidget, widget_kws=dict(properties=False))
            self.fmt_widgets[fmt] = fmt_widget
            layout.addWidget(fmt_widget)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    @property
    def fmts(self) -> Dict[str, Any]:
        """Mapping from formatoption key to value in this dialog."""
        ret = {}
        for fmt, widget in self.fmt_widgets.items():
            if widget.editor.changed:
                try:
                    value = widget.editor.value
                except Exception:
                    raise IOError(f"{fmt}-value {widget.editor.text} could "
                                  "not be parsed to python!")
                else:
                    ret[fmt] = value
        return ret

    @classmethod
    def update_project(cls, project: Project, *fmts: str) -> None:
        """Create a :class:`LabelDialog` to update the labels in a `project`.

        This classmethod creates a new :class:`LabelDialog` instance, fills it
        with the formatoptions of the first plotter in `project`, enters the
        main event loop, and updates the `project` upon acceptance.

        Parameters
        ----------
        project: psyplot.project.Project
            The psyplot project to update. Note that we will only use the
            very first plotter in this project
        ``*fmts``
            The formatoption keys to display. Each formatoption should be a
            subclass of :class:`psy_simple.base.TextBase`
        """
        dialog = cls(project, *fmts)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec_()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            project.update(
                **dialog.fmts)
