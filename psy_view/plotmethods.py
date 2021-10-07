"""Plotmethod widgets.

This module defines the widgets to interface with the mapplot, plot2d and
lineplot plotmethods.
"""

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

from __future__ import annotations
import os.path as osp

from typing import (
    TYPE_CHECKING,
    ClassVar,
    Callable,
    Optional,
    Union,
    List,
    Hashable,
    Dict,
    Any,
    Tuple,
    Iterator,
    TypeVar,
    Type,
)
from enum import Enum

from functools import partial
from itertools import chain, cycle
import contextlib
import textwrap

import dataclasses

import xarray as xr
from psyplot.utils import unique_everseen

from PyQt5 import QtWidgets, QtCore, QtGui
import psy_view.dialogs as dialogs
import psy_view.utils as utils
from psy_view.rcsetup import rcParams

from psyplot_gui.common import get_icon as get_psy_icon
import psy_simple.widgets.colors as pswc
import matplotlib.colors as mcol

if TYPE_CHECKING:
    from xarray import DataArray, Dataset, Variable
    from psyplot.project import PlotterInterface, Project
    from psyplot.data import InteractiveList
    from psyplot.plotter import Plotter


T = TypeVar("T", bound="GridCell")


class PlotType(str, Enum):
    """A value for the 2D ``plot`` formatoption.

    See Also
    --------
    psy_simple.plotters.Simple2DPlotter.plot
    psy_maps.plotters.FieldPlotter.plot
    """

    mesh = "mesh"
    contourf = "contourf"
    contour = "contour"
    poly = "poly"


#: A mapping from projection identifier to the text we want to use in the GUI
projection_map = {
    "cf": "Default",
    "cyl": "Cylindric",
    "robin": "Robinson",
    "ortho": "Orthographic",
    "moll": "Mollweide",
    "northpole": "Arctic (Northpole)",
    "southpole": "Antarctic (Southpole)",
}


@dataclasses.dataclass
class GridCell:
    """A grid cell within a QGridLayout managing one QWidget."""

    #: the :class:`PyQt5.QtWidgets.QWidget` instance (i.e. the widget) or a
    #: layout (:class:`PyQt5.QtWidgets.QLayout`)
    qobject: Union[QtWidgets.QWidget, QtWidgets.QLayout]

    #: The starting column for the widget. If None, it will be estimated based
    #: on the other widgets in the row
    column: Optional[int] = None

    #: The number of columns to cover
    colspan: int = 1

    #: A boolean whether to add stretch or not
    stretch: bool = False

    @classmethod
    def from_alias(
        cls: Type[T],
        o: Union[QtWidgets.QWidget, QtWidgets.QLayout],
        c: Optional[int] = None,
        cs: int = 1,
        s: bool = False
    ) -> T:
        """Create a :class:`GridCell` from shorter kws.

        Parameters
        ----------
        o: QWidget or QLayout
            The alias for :attr:`qobject`
        c: int or None, optional
            The alias for :attr:`column`
        cs: int, optional
            The alias for :attr:`colspan`
        s: bool, optional
            The alias for :attr:`stretch`

        Returns
        -------
        GridCell
            The generated instance of :class:`GridCell`
        """
        return cls(qobject=o, column=c, colspan=cs, stretch=s)


class PlotMethodWidget(QtWidgets.QWidget):
    """Base class for interfacing a psyplot plotmethod.

    This method serves as a base class for interfacing any of the psyplot
    plot methods registered via :func:`psyplot.project.register_plotter`.

    The name of the plotmethod should be implemented as the :attr:`plotmethod`
    attribute.
    """

    plotmethod: ClassVar[str] = ''

    #: trigger a replot of this widget. This can be emitted with the
    #: :meth:`trigger_replot` method
    replot = QtCore.pyqtSignal(str)

    #: trigger a replot of this widget. This can be emitted with the
    #: :meth:`trigger_reset` method
    reset = QtCore.pyqtSignal(str)

    #: signalize that the widget has been changed but not plot changes are
    #: needed
    changed = QtCore.pyqtSignal(str)

    array_info = None

    layout: QtWidgets.QGridLayout = None

    def __init__(
            self, get_sp: Callable[[], Optional[Project]],
            ds: Optional[Dataset]):
        super().__init__()
        self._get_sp = get_sp

        self.setup()

        if hasattr(self, "layout"):
            self.setLayout(self.layout)

        self.refresh(ds)

    def setup(self) -> None:
        """Set up the widget during initialization."""
        self.layout = QtWidgets.QGridLayout()
        self.setup_widgets()
        self.setup_widget_grid()

    @property
    def formatoption_rows(self) -> List[List[GridCell]]:
        """Get a mapping from row name to a row of :class:`GridCells`."""
        rows: List[List[GridCell]] = []
        for func in self.fmt_setup_functions:
            rows.extend(self.get_rows(func))
        return rows


    def get_rows(self, func: Callable) -> List[List[GridCell]]:
        """Get the rows of the formatoption widgets.

        This method should take callable from the :attr:`fmt_setup_functions`
        list and return the rows corresponding to :attr:`formatoption_rows`.
        """
        return [[]]

    @property
    def fmt_setup_functions(self) -> List[Callable]:
        """Get a list of rows for formatoptions.

        This property returns a list of callable. Each callable should setup
        a horizonal (or widget) that is added to the :attr:`layout` vbox.
        """
        return []

    def setup_widgets(self) -> None:
        """Set up the widgets for this plotmethod."""
        for func in self.fmt_setup_functions:
            func()

    def setup_separation_line(self) -> None:
        """Just a convenience function to create a separation line.

        This method does nothing but tells :meth:`get_rows` to add an instance
        of :class:`QHline`.
        """
        pass

    def setup_widget_grid(self) -> None:
        """Setup the widget grid based on :attr:`formatoption_rows`."""
        rows = self.formatoption_rows
        layout = self.layout
        for i, row in enumerate(rows):
            col: int = 0
            for gc in row:
                col = gc.column if gc.column is not None else col
                if isinstance(gc.qobject, QtWidgets.QLayout):
                    layout.addLayout(gc.qobject, i, col, 1, gc.colspan)
                else:
                    layout.addWidget(gc.qobject, i, col, 1, gc.colspan)
                col += gc.colspan
        layout.setRowStretch(len(rows), 1)
    @property
    def sp(self) -> Optional[Project]:
        """Get the subproject of this plotmethod interface."""
        return getattr(self._get_sp(), self.plotmethod, None)

    @property
    def data(self) -> Union[DataArray, InteractiveList]:
        """Get the data of this plotmethod interface."""
        if self.sp is None:
            raise ValueError("No plot has yet been initialized")
        else:
            return self.sp[0]

    @property
    def plotter(self) -> Optional[Plotter]:
        """Get the first plotter of the :attr:`sp` project."""
        if self.sp and self.sp.plotters:
            return self.sp.plotters[0]
        else:
            return None

    @property
    def formatoptions(self) -> List[str]:
        """Get the formatoption keys of this plotmethod."""
        if self.plotter is not None:
            return list(self.plotter)
        else:
            import psyplot.project as psy
            return list(getattr(psy.plot, self.plotmethod).plotter_cls())

    def get_fmts(
            self, var: DataArray, init: bool = False
        ) -> Dict[Union[Hashable, str, Any], Any]:
        """Get the formatoptions for a new plot.

        Parameters
        ----------
        var: xarray.Variable
            The variable in the base dataset
        init: bool
            If True, call the :meth:`init_dims` method to inject necessary
            formatoptions and dimensions for the initialization.

        Returns
        -------
        dict
            A mapping from formatoption or dimension to the corresponding value
            for the plotmethod.
        """
        ret = {}
        if init:
            ret.update(self.init_dims(var))
        return ret

    def init_dims(
            self, var: DataArray
        ) -> Dict[Union[Hashable, str, Any], Any]:
        """Get the formatoptions for a new plot.

        Parameters
        ----------
        var: xarray.Variable
            The variable in the base dataset

        Returns
        -------
        dict
            A mapping from formatoption or dimension to the corresponding value
            for the plotmethod.

        """
        return {}

    def refresh(self, ds: Optional[Dataset]) -> None:
        """Refresh this widget from the given dataset."""
        self.setEnabled(bool(self.sp))

    def trigger_replot(self) -> None:
        """Emit the :attr:`replot` signal to replot the project."""
        self.replot.emit(self.plotmethod)

    def trigger_reset(self):
        """Emit the :attr:`reset` signal to reinitialize the project."""
        self.array_info = self.sp.array_info(
            standardize_dims=False)[self.sp[0].psy.arr_name]
        self.reset.emit(self.plotmethod)

    def trigger_refresh(self):
        """Emit the :attr:`changed` signal to notify changes in the plot."""
        self.changed.emit(self.plotmethod)

    def get_slice(
            self, x: float, y: float
        ) -> Optional[Dict[Hashable, Union[int, slice]]]:
        """Get the slice for the selected coordinates.

        This method is called when the user clicks on the coordinates in the
        plot.

        See Also
        --------
        psy_view.ds_widget.DatasetWidget.display_line

        Notes
        -----
        This is reimplemented in the :class:`MapPlotWidget`.
        """
        return None

    def valid_variables(self, ds: Dataset) -> List[Hashable]:
        """Get a list of variables that can be visualized with this plotmethod.

        Parameters
        ----------
        ds: xarray.Dataset
            The dataset to use

        Returns
        -------
        list of str
            List of variable names to plot
        """
        ret = []
        plotmethod = getattr(ds.psy.plot, self.plotmethod)
        for v in list(ds):
            init_kws = self.init_dims(ds[v])  # type: ignore
            dims = init_kws.get('dims', {})
            decoder = init_kws.get('decoder')
            if plotmethod.check_data(ds, v, dims, decoder)[0][0]:
                ret.append(v)
        return ret


class QHLine(QtWidgets.QFrame):
    """A horizontal seperation line."""
    def __init__(self):
        super().__init__()
        self.setMinimumWidth(1)
        self.setFixedHeight(20)
        self.setFrameShape(QtWidgets.QFrame.HLine)
        self.setFrameShadow(QtWidgets.QFrame.Sunken)
        self.setSizePolicy(
            QtWidgets.QSizePolicy.Preferred,
            QtWidgets.QSizePolicy.Minimum
        )


class MapPlotWidget(PlotMethodWidget):
    """A widget to control the mapplot plotmethod."""

    plotmethod = 'mapplot'

    def get_rows(self, func: Callable) -> List[List[GridCell]]:
        """Get the rows of the formatoption widgets.

        This method should take callable from the :attr:`fmt_setup_functions`
        list and return the rows corresponding to :attr:`formatoption_rows`.
        """
        if func == self.setup_color_buttons:
            row = [
                GridCell(QtWidgets.QLabel("Colormap")),
                GridCell(self.btn_cmap),
                GridCell(self.btn_cmap_settings, stretch=True),
            ]
        elif func == self.setup_plot_buttons:
            row = [
                GridCell(QtWidgets.QLabel("Plot type")),
                GridCell(self.combo_plot),
                GridCell(self.btn_datagrid, stretch=True),
            ]
        elif func == self.setup_projection_buttons:
            row = [
                GridCell(QtWidgets.QLabel("Projection")),
                GridCell(self.btn_proj),
                GridCell(self.btn_proj_settings, stretch=True),
            ]
        elif func == self.setup_labels_button:
            row = [GridCell(self.btn_labels, colspan=3)]
        elif func == self.setup_separation_line:
            row = [GridCell(QHLine(), colspan=3)]
        elif func == self.setup_dimension_box:
            row = [GridCell(self.dimension_box, colspan=3)]
        else:
            raise ValueError(f"Unknown function {func}")
        return [row]

    @property
    def fmt_setup_functions(self) -> List[Callable]:
        """Get a list of rows for formatoptions.

        This property returns a list of callable. Each callable should setup
        a horizonal (or widget) that is added to the :attr:`layout` vbox.
        """
        return [
            self.setup_color_buttons, self.setup_plot_buttons,
            self.setup_projection_buttons, self.setup_labels_button,
            self.setup_separation_line,
            self.setup_dimension_box,
        ]

    def setup_labels_button(self) -> None:
        """Add a button to modify the text labels."""
        self.btn_labels = utils.add_pushbutton(
            "Edit labels", self.edit_labels, "Edit title, colorbar labels, etc."
        )

    def setup_plot_buttons(self) -> None:
        """Setup the second row of formatoption widgets."""
        self.combo_plot = QtWidgets.QComboBox()
        self.plot_types: List[Optional[PlotType]] = [
            PlotType.mesh,
            PlotType.contourf,
            PlotType.contour,
            PlotType.poly,
            None
        ]
        self.combo_plot.setEditable(False)
        self.combo_plot.addItems([
            "Default", "Filled contours", "Contours", "Gridcell polygons",
            "Disable"
        ])
        self.combo_plot.currentIndexChanged.connect(self._set_plot_type)

        self.btn_datagrid = utils.add_pushbutton(
            "Gridcell boundaries", self.toggle_datagrid,
            "Toggle the visibility of grid cell boundaries")
        self.btn_datagrid.setCheckable(True)

        return

    def setup_color_buttons(self) -> None:
        """Set up the buttons to change the colormap, etc."""
        self.btn_cmap = pswc.CmapButton()
        self.btn_cmap.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.btn_cmap.setToolTip("Select a different colormap")

        self.btn_cmap.colormap_changed.connect(self.set_cmap)
        self.btn_cmap.colormap_changed[mcol.Colormap].connect(self.set_cmap)
        self.setup_cmap_menu()

        self.btn_cmap_settings = utils.add_pushbutton(
            utils.get_icon('color_settings'), self.edit_color_settings,
            "Edit color settings",
            icon=True)

    def setup_cmap_menu(self) -> QtWidgets.QMenu:
        """Set up the menu to change the colormaps."""
        menu = self.btn_cmap.cmap_menu

        menu.addSeparator()
        self.select_cmap_action = menu.addAction(
            'More colormaps', self.open_cmap_dialog)

        self.color_settings_action = menu.addAction(
            QtGui.QIcon(utils.get_icon('color_settings')), 'More options',
            self.edit_color_settings)

        return menu

    def open_cmap_dialog(self, N: int = 10) -> None:
        """Open the dialog to change the colormap.

        Parameters
        ----------
        N: int
            The number of colormaps to show

        See Also
        --------
        psy_simple.widgets.colors.CmapButton
        """
        if self.plotter:
            N = self.plotter.plot.mappable.get_cmap().N
        else:
            N = 10
        self.btn_cmap.open_cmap_dialog(N)

    def setup_projection_menu(self) -> QtWidgets.QMenu:
        """Set up the menu to modify the basemap."""
        menu = QtWidgets.QMenu()
        for projection in rcParams['projections']:
            menu.addAction(
                projection_map.get(projection, projection),
                partial(self.set_projection, projection),
            )
        menu.addSeparator()
        self.proj_settings_action = menu.addAction(
            QtGui.QIcon(utils.get_icon('proj_settings')),
            "Customize basemap...", self.edit_basemap_settings)
        return menu

    def get_projection_label(self, proj: str) -> str:
        """Get the label for a projection in the GUI.

        Parameters
        ----------
        proj: str
            The projection value for the
            :attr:`~psy_maps.plotters.FieldPlotter.plot` formatoption

        Returns
        -------
        str
            The label of the projection in the GUI

        See Also
        --------
        get_projection_label
        projection_map
        psy_maps.plotters.FieldPlotter.plot
        """
        return projection_map.get(proj, proj)

    def get_projection_value(self, label: str) -> str:
        """Get the value for the `projection` formatoption.

        This method is the inverse of :meth:`get_projection_label`.

        Parameters
        ----------
        label: str
            The projection label that is used in the GUI
            :attr:`~psy_maps.plotters.FieldPlotter.plot` formatoption

        Returns
        -------
        str
            The value to use for the ``projection`` formatoption

        See Also
        --------
        get_projection_label
        projection_map
        psy_maps.plotters.FieldPlotter.plot
        """
        inv_map = {lbl: proj for proj, lbl in projection_map.items()}
        return inv_map.get(label, rcParams["projections"][0])

    def setup_projection_buttons(self) -> None:
        """Set up the buttons to modify the basemap."""
        self.btn_proj = utils.add_pushbutton(
            self.get_projection_label(rcParams["projections"][0]),
            self.choose_next_projection, "Change the basemap projection",
            toolbutton=True)
        self.btn_proj.setMenu(self.setup_projection_menu())

        self.btn_proj.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.btn_proj.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

        self.btn_proj_settings = utils.add_pushbutton(
            utils.get_icon('proj_settings'), self.edit_basemap_settings,
            "Edit basemap settings",
            icon=True)

    def setup_dimension_box(self) -> None:
        """Set up a box to control, what is the x and y-dimension."""
        self.dimension_box = QtWidgets.QGridLayout()

        self.dimension_box.addWidget(QtWidgets.QLabel('x-Dimension:'), 0, 0)
        self.combo_xdim = QtWidgets.QComboBox()
        self.dimension_box.addWidget(self.combo_xdim, 0, 1)

        self.dimension_box.addWidget(QtWidgets.QLabel('y-Dimension:'), 0, 2)
        self.combo_ydim = QtWidgets.QComboBox()
        self.dimension_box.addWidget(self.combo_ydim, 0, 3)

        self.dimension_box.addWidget(QtWidgets.QLabel('x-Coordinate:'), 1, 0)
        self.combo_xcoord = QtWidgets.QComboBox()
        self.dimension_box.addWidget(self.combo_xcoord, 1, 1)

        self.dimension_box.addWidget(QtWidgets.QLabel('y-Coordinate:'), 1, 2)
        self.combo_ycoord = QtWidgets.QComboBox()
        self.dimension_box.addWidget(self.combo_ycoord, 1, 3)

        self.combo_xdim.currentTextChanged.connect(self.set_xcoord)
        self.combo_ydim.currentTextChanged.connect(self.set_ycoord)

        for combo in self.coord_combos:
            combo.currentIndexChanged.connect(self.trigger_refresh)

    def set_xcoord(self, text: str) -> None:
        """Set the name of the x-coordinate."""
        self.set_combo_text(self.combo_xcoord, text)

    def set_ycoord(self, text: str) -> None:
        """Set the name of the y-coordinate."""
        self.set_combo_text(self.combo_ycoord, text)

    def set_combo_text(self, combo: QtWidgets.QComboBox, text: str) -> None:
        """Convenience function to update set the current text of a combobox.

        Parameters
        ----------
        combo: PyQt5.QtWidgets.QComboBox
            The combobox to modify
        text: str
            The item to use"""
        items = list(map(combo.itemText, range(combo.count())))
        if text in items:
            combo.setCurrentIndex(items.index(text))

    def init_dims(
            self, var: DataArray
        ) -> Dict[Union[Hashable, str, Any], Any]:
        """Get the formatoptions for a new plot.

        This method updates the coordinates combo boxes with the
        x- and y-coordinate of the variable.

        Parameters
        ----------
        var: xarray.Variable
            The variable in the base dataset

        Returns
        -------
        dict
            A mapping from formatoption or dimension to the corresponding value
            for the plotmethod.
        """
        ret = super().init_dims(var)

        dims: Dict[Hashable, Union[int, slice]] = {}
        xdim = ydim = None

        if self.combo_xdim.currentIndex():
            xdim = self.combo_xdim.currentText()
            if xdim in var.dims:
                dims[xdim] = slice(None)

        if self.combo_ydim.currentIndex():
            ydim = self.combo_ydim.currentText()
            if ydim in var.dims:
                dims[ydim] = slice(None)

        if dims:
            missing = [dim for dim in var.dims if dim not in dims]
            for dim in missing:
                dims[dim] = 0
            if len(dims) == 1 and xdim != ydim:
                if xdim is None:
                    xdim = missing[-1]
                else:
                    ydim = missing[-1]
                dims[missing[-1]] = slice(None)  # keep the last dimension
            ret['dims'] = dims


        if self.combo_xcoord.currentIndex():
            xcoord = self.combo_xcoord.currentText()
            ret['decoder'] = {'x': {xcoord}}
        if self.combo_ycoord.currentIndex():
            ycoord = self.combo_ycoord.currentText()
            ret.setdefault('decoder', {})
            ret['decoder']['y'] = {ycoord}

        if (xdim is not None and xdim in var.dims and
                ydim is not None and ydim in var.dims):
            ret['transpose'] = var.dims.index(xdim) < var.dims.index(ydim)

        return ret

    def valid_variables(self, ds: Dataset) -> List[Hashable]:
        """Get a list of variables that can be visualized with this plotmethod.

        Parameters
        ----------
        ds: xarray.Dataset
            The dataset to use

        Returns
        -------
        list of str
            List of variable names to plot
        """
        valid = super().valid_variables(ds)
        if (not any(combo.count() for combo in self.coord_combos) or
                not any(combo.currentIndex() for combo in self.coord_combos)):
            return valid
        if self.combo_xdim.currentIndex():
            xdim = self.combo_xdim.currentText()
            valid = [v for v in valid if xdim in ds[v].dims]
        if self.combo_ydim.currentIndex():
            ydim = self.combo_xdim.currentText()
            valid = [v for v in valid if ydim in ds[v].dims]
        if self.combo_xcoord.currentIndex():
            xc_dims = set(ds[self.combo_xcoord.currentText()].dims)
            valid = [v for v in valid
                     if xc_dims.intersection(ds[v].dims)]
        if self.combo_ycoord.currentIndex():
            yc_dims = set(ds[self.combo_ycoord.currentText()].dims)
            valid = [v for v in valid
                     if yc_dims.intersection(ds[v].dims)]
        return valid

    @property
    def coord_combos(self) -> List[QtWidgets.QComboBox]:
        """Get the combo boxes for x- and y-dimension and -coordinates."""
        return [self.combo_xdim, self.combo_ydim, self.combo_xcoord,
                self.combo_ycoord]

    @contextlib.contextmanager
    def block_combos(self) -> Iterator[None]:
        """Temporarilly block any signal of the :attr:`coord_combos`."""
        for combo in self.coord_combos:
            combo.blockSignals(True)
        yield
        for combo in self.coord_combos:
            combo.blockSignals(False)

    def setEnabled(self, b: bool) -> None:
        """Enable or disable the projection and color buttons.

        Parameters
        ----------
        b: bool
            If True, enable the buttons, else disable.
        """
        self.btn_proj_settings.setEnabled(b)
        self.proj_settings_action.setEnabled(b)
        self.btn_datagrid.setEnabled(b)
        self.color_settings_action.setEnabled(b)
        self.btn_cmap_settings.setEnabled(b)
        self.btn_labels.setEnabled(b)

    def set_cmap(self, cmap: str) -> None:
        """Update the plotter with the given colormap.

        Parameters
        ----------
        cmap: str
            The colormap name.
        """
        plotter = self.plotter
        if plotter and 'cmap' in plotter:
            plotter.update(cmap=cmap)

    def toggle_datagrid(self) -> None:
        """Toggle the visibility of the grid cell boundaries."""
        if self.plotter:
            if self.btn_datagrid.isChecked():
                self.plotter.update(datagrid='k-')
            else:
                self.plotter.update(datagrid=None)

    def edit_labels(self) -> None:
        """Open the dialog to edit the text labels in the plot."""
        dialogs.LabelDialog.update_project(
            self.sp, 'figtitle', 'title', 'clabel')

    def edit_color_settings(self) -> None:
        """Open the dialog to edit the color settings."""
        if self.sp and self.plotter:
            dialogs.CmapDialog.update_project(self.sp)
            if isinstance(self.plotter.cmap.value, str):
                self.btn_cmap.setText(self.plotter.cmap.value)
            else:
                self.btn_cmap.setText('Custom')

    def choose_next_projection(self) -> None:
        """Choose the next projection from the rcParams `projection` value."""
        select = False
        nprojections = len(rcParams['projections'])
        current = self.get_projection_value(self.btn_proj.text())

        for i, proj in enumerate(cycle(rcParams['projections'])):
            if proj == current:
                select = True
            elif select or i == nprojections:
                break
        self.set_projection(proj)

    def set_projection(self, proj: str) -> None:
        """Update the projection of the plot with the given projection.

        Parameters
        ----------
        projection: str
            The projection name for the
            :attr:`~psy_maps.plotters.FieldPlotter.projection` formatoption.
        """
        self.btn_proj.setText(self.get_projection_label(proj))
        plotter = self.plotter
        if plotter and 'projection' in plotter:
            plotter.update(projection=proj)

    def _set_plot_type(self, i: int) -> None:
        """Set the plot type from the index in :attr:`combo_plot`."""
        self.set_plot_type(self.plot_types[i])

    def set_plot_type(self, plot_type: Optional[PlotType]) -> None:
        """Update the value for the ``plot`` formatoption

        Parameters
        ----------
        ploy_type: :class:`PlotType` or None
            The value for the :attr:`~psy_simple.plotters.Simple2DPlotter.plot`
            formatoption.
        """
        plotter = self.plotter
        if plotter:
            plotter.update(plot=plot_type)

    def edit_basemap_settings(self) -> None:
        """Open a dialog to edit the basemap and projection settings."""
        if self.plotter:
            dialogs.BasemapDialog.update_plotter(self.plotter)

    def get_fmts(
            self, var: DataArray,
            init: bool = False
        ) -> Dict[Union[Hashable, str, Any], Any]:
        """Get the formatoptions for a new plot.

        Parameters
        ----------
        var: xarray.Variable
            The variable in the base dataset
        init: bool
            If True, call the :meth:`init_dims` method to inject necessary
            formatoptions and dimensions for the initialization.

        Returns
        -------
        dict
            A mapping from formatoption or dimension to the corresponding value
            for the plotmethod.
        """
        fmts: Dict[Union[Hashable, str, Any], Any] = {}

        fmts['cmap'] = self.btn_cmap.text()

        if 'projection' in self.formatoptions:
            fmts['projection'] = self.get_projection_value(
                self.btn_proj.text()
            )

        if 'time' in var.dims:
            fmts['title'] = '%(time)s'

        if 'long_name' in var.attrs:
            fmts['clabel'] = '%(long_name)s'
        else:
            fmts['clabel'] = '%(name)s'
        if 'units' in var.attrs:
            fmts['clabel'] += ' %(units)s'

        fmts['plot'] = self.plot_types[self.combo_plot.currentIndex()]
        if fmts['plot'] == 'contour':
            # we need to set a global map extend, see
            # https://github.com/SciTools/cartopy/issues/1673
            fmts['map_extent'] = 'global'

        if init:
            fmts.update(self.init_dims(var))

        return fmts

    def refresh(self, ds: Optional[Dataset]) -> None:
        """Refresh this widget from the given dataset."""
        self.setEnabled(bool(self.sp))

        auto = 'Set automatically'

        self.refresh_from_sp()

        with self.block_combos():

            if ds is None:
                ds = xr.Dataset()

            current_dims = set(map(
                self.combo_xdim.itemText, range(1, self.combo_xdim.count())))
            ds_dims = list(
                map(str, (dim for dim, n in ds.dims.items() if n > 1)))
            if current_dims != set(ds_dims):
                self.combo_xdim.clear()
                self.combo_ydim.clear()
                self.combo_xdim.addItems([auto] + ds_dims)
                self.combo_ydim.addItems([auto] + ds_dims)

            current_coords = set(map(
                self.combo_xcoord.itemText, range(1, self.combo_xcoord.count())))
            ds_coords = list(
                map(str, (c for c, arr in ds.coords.items() if arr.ndim)))
            if current_coords != set(ds_coords):
                self.combo_xcoord.clear()
                self.combo_ycoord.clear()
                self.combo_xcoord.addItems([auto] + ds_coords)
                self.combo_ycoord.addItems([auto] + ds_coords)

            enable_combos = not bool(self.sp)

            if not enable_combos and self.combo_xdim.isEnabled():
                self.reset_combos = [combo.currentIndex() == 0
                                    for combo in self.coord_combos]
            elif enable_combos and not self.combo_xdim.isEnabled():
                for reset, combo in zip(self.reset_combos, self.coord_combos):
                    if reset:
                        combo.setCurrentIndex(0)
                self.reset_combos = [False] * len(self.coord_combos)

            for combo in self.coord_combos:
                combo.setEnabled(enable_combos)

            if not enable_combos:
                data = self.data
                xdim = str(data.psy.get_dim('x'))
                ydim = str(data.psy.get_dim('y'))
                self.combo_xdim.setCurrentText(xdim)
                self.combo_ydim.setCurrentText(ydim)
                xcoord = data.psy.get_coord('x')
                xcoord = xcoord.name if xcoord is not None else xdim
                ycoord = data.psy.get_coord('y')
                ycoord = ycoord.name if ycoord is not None else ydim

                self.combo_xcoord.setCurrentText(xcoord)
                self.combo_ycoord.setCurrentText(ycoord)

    def refresh_from_sp(self) -> None:
        """Refresh this widget from the plotters project."""
        plotter = self.plotter
        if plotter:
            if isinstance(plotter.projection.value, str):
                self.btn_proj.setText(
                    self.get_projection_label(plotter.projection.value)
                )
            else:
                self.btn_proj.setText('Custom')
            if isinstance(plotter.cmap.value, str):
                self.btn_cmap.setText(plotter.cmap.value)
            else:
                self.btn_cmap.setText('Custom')

    def transform(self, x: float, y: float) -> Tuple[float, float]:
        """Transform coordinates of a point to the plots projection.

        Parameters
        ----------
        x: float
            The x-coordinate in axes coordinates
        y: float
            The y-coordinate in axes coordinates

        Returns
        -------
        float
            The transformed x-coordinate `x`
        float
            The transformed y-coordinate `y`
        """
        import cartopy.crs as ccrs
        import numpy as np
        plotter = self.plotter
        if not plotter:
            raise ValueError(
                "Cannot transform the coordinates as no plot is shown "
                "currently!")
        x, y = plotter.transform.projection.transform_point(
            x, y, plotter.ax.projection)
        # shift if necessary
        if isinstance(plotter.transform.projection, ccrs.PlateCarree):
            coord = plotter.plot.xcoord
            if coord.min() >= 0 and x < 0:
                x -= 360
            elif coord.max() <= 180 and x > 180:
                x -= 360
            if 'rad' in coord.attrs.get('units', '').lower():
                x = np.deg2rad(x)
                y = np.deg2rad(y)
        return x, y

    def get_slice(
            self, x: float, y: float
        ) -> Optional[Dict[Hashable, Union[int, slice]]]:
        """Get the slice for the selected coordinates.

        This method is called when the user clicks on the coordinates in the
        plot.

        See Also
        --------
        psy_view.ds_widget.DatasetWidget.display_line

        Notes
        -----
        This is reimplemented in the :class:`MapPlotWidget`.
        """
        import numpy as np
        data = self.data.psy.base.psy[self.data.name]
        x, y = self.transform(x, y)
        plotter = self.plotter

        if not plotter:
            raise ValueError(
                "Cannot transform the coordinates as no plot is shown "
                "currently!")

        fmto = plotter.plot

        xcoord = fmto.xcoord
        ycoord = fmto.ycoord
        if fmto.decoder.is_unstructured(fmto.raw_data) or xcoord.ndim == 2:
            xy = xcoord.values.ravel() + 1j * ycoord.values.ravel()
            dist = np.abs(xy - (x + 1j * y))
            imin = np.nanargmin(dist)
            if xcoord.ndim == 2:
                ncols = data.shape[-2]
                return dict(zip(data.dims[-2:],
                                [imin // ncols, imin % ncols]))
            else:
                return {data.dims[-1]: imin}
        else:
            ix: int = xcoord.indexes[xcoord.name].get_loc(x, method='nearest')
            iy: int = ycoord.indexes[ycoord.name].get_loc(y, method='nearest')
            return dict(zip(data.dims[-2:], [iy, ix]))


class Plot2DWidget(MapPlotWidget):
    """A widget to control the plot2d plotmethod."""

    plotmethod = 'plot2d'

    @property
    def fmt_setup_functions(self) -> List[Callable]:
        """Get a list of rows for formatoptions.

        This property returns a list of callable. Each callable should setup
        a horizonal (or widget) that is added to the :attr:`layout` vbox.
        """
        ret = super().fmt_setup_functions
        ret.remove(self.setup_projection_buttons)
        return ret

    def setEnabled(self, b: bool) -> None:
        """Enable or disable the datagrid and color buttons.

        Parameters
        ----------
        b: bool
            If True, enable the buttons, else disable.
        """
        self.btn_datagrid.setEnabled(b)
        self.btn_cmap_settings.setEnabled(b)
        self.btn_labels.setEnabled(b)

    def edit_labels(self) -> None:
        """Open the dialog to edit the text labels in the plot."""
        dialogs.LabelDialog.update_project(
            self.sp, 'figtitle', 'title', 'clabel', 'xlabel', 'ylabel')

    def transform(self, x: float, y: float) -> Tuple[float, float]:
        """Reimplemented to not transform the coordinates."""
        return x, y

    def refresh_from_sp(self) -> None:
        """Refresh this widget from the plotters project."""
        plotter = self.plotter
        if plotter:
            if isinstance(plotter.cmap.value, str):
                self.btn_cmap.setText(plotter.cmap.value)


class LinePlotWidget(PlotMethodWidget):
    """A widget to control the lineplot plotmethod."""

    plotmethod = 'lineplot'

    @property
    def fmt_setup_functions(self) -> List[Callable]:
        return [
            self.setup_dimension_combo,
            self.setup_line_selection,
            self.setup_labels_button,
        ]

    def get_rows(self, func: Callable) -> List[List[GridCell]]:
        """Get the rows of the formatoption widgets.

        This method should take callable from the :attr:`fmt_setup_functions`
        list and return the rows corresponding to :attr:`formatoption_rows`.
        """
        if func == self.setup_dimension_combo:
            row = [
                GridCell(QtWidgets.QLabel('x-Dimension:')),
                GridCell(self.combo_dims)
            ]
        elif func == self.setup_line_selection:
            row = [
                GridCell(QtWidgets.QLabel('Active line:')),
                GridCell(self.combo_lines),
                GridCell(self.btn_add),
                GridCell(self.btn_del)
            ]
        elif func == self.setup_labels_button:
            row = [GridCell(self.btn_labels, colspan=4)]
        else:
            raise ValueError(f"Unknown function {func}")
        return [row]

    def setup_dimension_combo(self) -> None:
        """Set up the combobox for selecting the x-dimension."""
        self.combo_dims = QtWidgets.QComboBox()
        self.combo_dims.setEditable(False)
        self.combo_dims.currentIndexChanged.connect(self.trigger_reset)
        self.combo_dims.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )

    def setup_line_selection(self) -> None:
        """Setup the row for selecting new lines."""
        self.combo_lines = QtWidgets.QComboBox()
        self.combo_lines.setEditable(False)

        self.combo_lines.setSizePolicy(
            QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding
        )
        self.combo_lines.currentIndexChanged.connect(self.trigger_refresh)

        self.btn_add = utils.add_pushbutton(
            QtGui.QIcon(get_psy_icon('plus')), lambda: self.add_line(),
            "Add a line to the plot", icon=True)
        self.btn_del = utils.add_pushbutton(
            QtGui.QIcon(get_psy_icon('minus')), self.remove_line,
            "Add a line to the plot", icon=True)

    def setup_labels_button(self) -> None:
        """Add a button to modify the text labels."""
        self.btn_labels = utils.add_pushbutton(
            "Edit labels", self.edit_labels,
            "Edit title, x-label, legendlabels, etc.")

    @property
    def xdim(self) -> str:
        """Get the x-dimension for the plot."""
        return self.combo_dims.currentText()

    @xdim.setter
    def xdim(self, xdim: Hashable) -> None:
        if xdim != self.combo_dims.currentText():
            self.combo_dims.setCurrentText(str(xdim))

    @property
    def data(self) -> DataArray:
        """The first array in the list."""
        data = super().data
        if len(data) - 1 < self.combo_lines.currentIndex():
            return data[0]
        else:
            return data[self.combo_lines.currentIndex()]

    def add_line(self, name: Hashable = None, **sl) -> None:
        """Add a line to the plot.

        This method adds a new line for the plot specified by the given
        `name` of the variable and the slices.

        Parameters
        ----------
        name: str
            The variable name to display
        ``**sl``
            The slices to turn the `name` variable into a 1D-array.
        """
        if not self.sp:
            raise ValueError("No plot has yet been initialized!")
        ds = self.data.psy.base
        xdim = self.xdim
        if name is None:
            name, ok = QtWidgets.QInputDialog.getItem(
                self, 'New line', 'Select a variable',
                [key for key, var in ds.items()
                 if xdim in var.dims])
            if not ok:
                return
        arr = ds.psy[name]
        for key, val in self.data.psy.idims.items():
            if key in arr.dims:
                sl.setdefault(key, val)
        for dim in arr.dims:
            if dim != xdim:
                sl.setdefault(dim, 0)
        self.sp[0].append(arr.psy[sl], new_name=True)
        item = self.item_texts[-1]
        self.sp.update(replot=True)
        self.combo_lines.addItem(item)
        self.combo_lines.setCurrentText(item)
        self.trigger_refresh()

    def remove_line(self) -> None:
        """Remove the current line from the plot."""
        if not self.sp:
            raise ValueError(
                "No plot has yet been initialized, so I cannot remove any line!"
            )
        i = self.combo_lines.currentIndex()
        self.sp[0].pop(i)
        self.sp.update(replot=True)
        self.combo_lines.setCurrentText(self.item_texts[i - 1 if i else 0])
        self.changed.emit(self.plotmethod)

    @property
    def item_texts(self) -> List[str]:
        """Get the labels for the individual lines."""
        if not self.sp:
            return []
        return [f'Line {i}: {arr.psy._short_info()}'
                for i, arr in enumerate(self.sp[0])]

    def init_dims(
            self, var: DataArray
        ) -> Dict[Union[Hashable, str, Any], Any]:
        """Get the formatoptions for a new plot.

        Parameters
        ----------
        var: xarray.Variable
            The variable in the base dataset

        Returns
        -------
        dict
            A mapping from formatoption or dimension to the corresponding value
            for the plotmethod.

        """
        ret: Dict[Union[Hashable, str, Any], Any] = {}
        xdim: Union[None, Hashable, str] = self.xdim or next(
            (d for d in var.dims if var[d].size > 1), None  # type: ignore
        )
        if self.array_info:
            arr_names = {}
            for arrname, d in self.array_info.items():
                if arrname != 'attrs':
                    dims = d['dims'].copy()
                    if xdim in dims:
                        for dim, sl in dims.items():
                            if not isinstance(sl, int):
                                dims[dim] = 0
                        dims[xdim] = slice(None)
                    dims['name'] = d['name']
                    arr_names[arrname] = dims
            ret['arr_names'] = arr_names
            del self.array_info
        else:
            if xdim not in var.dims:
                xdim = next((d for d in var.dims if var[d].size > 1), None)
            if xdim is None:
                raise ValueError(
                    f"Cannot plot variable {var.name} with size smaller than "
                    "2")
            ret[xdim] = slice(None)
            for d in var.dims:
                if d != xdim:
                    ret[d] = 0
        return ret

    def edit_labels(self) -> None:
        """Open the dialog to edit the text labels in the plot."""
        dialogs.LabelDialog.update_project(
            self.sp, 'figtitle', 'title', 'xlabel', 'ylabel', 'legendlabels')

    @contextlib.contextmanager
    def block_combos(self) -> Iterator[None]:
        """Temporarilly block any signal of the combo boxes."""
        self.combo_dims.blockSignals(True)
        self.combo_lines.blockSignals(True)
        yield
        self.combo_dims.blockSignals(False)
        self.combo_lines.blockSignals(False)

    def valid_variables(self, ds: Dataset) -> List[Hashable]:
        """Get a list of variables that can be visualized with this plotmethod.

        Parameters
        ----------
        ds: xarray.Dataset
            The dataset to use

        Returns
        -------
        list of str
            List of variable names to plot
        """
        valid = list(ds)
        if not self.sp or len(self.sp[0]) < 2:
            return valid
        else:
            current_dim = self.combo_dims.currentText()
            return [v for v in valid if current_dim in ds[v].dims]

    def setEnabled(self, b: bool) -> None:
        """Enable or disable the datagrid and color buttons.

        Parameters
        ----------
        b: bool
            If True, enable the buttons, else disable.
        """
        self.btn_add.setEnabled(b)
        self.btn_del.setEnabled(b and self.sp and len(self.sp[0]) > 1)
        self.btn_labels.setEnabled(b)

    def refresh(self, ds) -> None:
        """Refresh this widget from the given dataset."""
        self.setEnabled(bool(self.sp))

        if self.sp:
            with self.block_combos():
                self.combo_dims.clear()
                all_dims = list(chain.from_iterable(
                    [[d for i, d in enumerate(a.dims) if a.shape[i] > 1]
                     for a in arr.psy.iter_base_variables]
                    for arr in self.sp[0]))
                intersection = set(all_dims[0])
                for dims in all_dims[1:]:
                    intersection.intersection_update(dims)
                new_dims = list(
                    filter(lambda d: d in intersection,
                           unique_everseen(chain.from_iterable(all_dims))))

                self.combo_dims.addItems(new_dims)
                self.combo_dims.setCurrentIndex(
                    new_dims.index(self.data.dims[-1]))

                # fill lines combo
                current = self.combo_lines.currentIndex()
                self.combo_lines.clear()
                descriptions = self.item_texts
                short_descs = [textwrap.shorten(s, 50) for s in descriptions]
                self.combo_lines.addItems(short_descs)
                for i, desc in enumerate(descriptions):
                    self.combo_lines.setItemData(i, desc, QtCore.Qt.ToolTipRole)
                if current < len(descriptions):
                    self.combo_lines.setCurrentText(short_descs[current])
        else:
            with self.block_combos():
                self.combo_dims.clear()
                self.combo_lines.clear()
