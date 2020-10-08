# -*- coding: utf-8 -*-
"""Dataset widget to display the contents of a dataset

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

import os.path as osp
import os

from typing import (
    List,
    TYPE_CHECKING,
    Optional,
    Union,
    Dict,
    Iterator,
    Type,
    Any,
    Callable,
    Hashable,
    Tuple,
)

import contextlib

import yaml
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt  # pylint: disable=no-name-in-module
import psy_view.utils as utils
from psyplot_gui.content_widget import (
    DatasetTree, DatasetTreeItem, escape_html)
from psyplot_gui.common import (
    DockMixin, get_icon as get_psy_icon, PyErrorMessage)
import psyplot.data as psyd
from psy_view.rcsetup import rcParams
from psy_view.plotmethods import (
    PlotMethodWidget,
    MapPlotWidget,
    Plot2DWidget,
    LinePlotWidget,
)
from psyplot.config.rcsetup import get_configdir

from matplotlib.animation import FuncAnimation

if TYPE_CHECKING:
    from xarray import DataArray, Dataset
    from psyplot.project import PlotterInterface, Project
    from psyplot.plotter import Plotter
    from matplotlib.figure import Figure
    from matplotlib.backend_bases import MouseEvent
    from psyplot_gui.main import MainWindow

NOTSET_T = Type[object]
NOTSET: NOTSET_T = object


def get_dims_to_iterate(arr: DataArray) -> List[str]:
    """Get the dimensions of an array to iterate over

    This function takes a data array and returns the dimension in the base
    dataset that one can interator over.

    Parameters
    ----------
    arr: xarray.DataArray
        The data array to iterate over

    Returns
    -------
    list of strings
        The dimension strings
    """
    base_var = next(arr.psy.iter_base_variables)
    return [dim for dim, size in zip(base_var.dims, base_var.shape)
            if size > 1 and arr[dim].ndim == 0]

TOO_MANY_FIGURES_WARNING = """
Multiple figures are open but you specified only {} filenames: {}.<br>

Saving the figures will cause that not all images are saved! We recommend to
export to a single PDF (that then includes multiple pages), or modify your
filename with strings like

<ul>
<li> <code>%i</code> for a continuous counter of the images</li>
<li><code>%(name)s</code> for variable names</li>
<li>or other netCDF attributes (see the
  <a href="https://psyplot.readthedocs.io/en/latest/api/psyplot.project.html#psyplot.project.Project.export">
  examples of exporting psyplot projects</a>)</li>
</ul>

Shall I continue anyway and save the figures?
"""


class DatasetWidget(QtWidgets.QSplitter):
    """A widget to control the visualization of the variables in a dataset"""

    #: The title of the widget
    title: str = 'psy-view Plot Control'

    #: Display the dock widget at the right side of the GUI
    dock_position = Qt.RightDockWidgetArea

    _animating: bool = False

    _ani: Optional[FuncAnimation] = None

    _init_step: int = 0

    #: A :class:`PyQt5.QtWidgets.QGroupBox` that contains the variable buttons
    variable_frame: Optional[QtWidgets.QGroupBox] = None

    _new_plot: bool = False

    _preset: Optional[Union[str, Dict]] = None

    #: Attributes to use in the dataset tree
    ds_attr_columns: List[str] = ['long_name', 'dims', 'shape']

    def __init__(self, ds: Optional[Dataset] = None, *args, **kwargs) -> None:
        """
        Parameters
        ----------
        ds: xarray.Dataset
            A dataset to visualize with this widget
        """
        super().__init__(*args, **kwargs)

        self._ds_nums: Dict[int, Dataset] = {}

        self.setChildrenCollapsible(False)

        self.ds: Optional[Dataset] = ds

        self.setOrientation(Qt.Vertical)

        self.error_msg = PyErrorMessage(self)

        # first row: dataset name
        self.open_box = QtWidgets.QHBoxLayout()
        self.lbl_ds = QtWidgets.QLineEdit()
        self.open_box.addWidget(self.lbl_ds)
        self.btn_open = utils.add_pushbutton(
            get_psy_icon('run_arrow.png'), lambda: self.set_dataset(),
            "Select and open a netCDF dataset", self.open_box, icon=True)
        self.open_widget = QtWidgets.QWidget()
        self.open_widget.setLayout(self.open_box)
        self.addWidget(self.open_widget)


        # second row: dataset representation
        self.setup_ds_tree()
        if ds is not None:
            self.add_ds_item()

        self.ds_tree.itemExpanded.connect(self.change_ds)
        self.ds_tree.itemExpanded.connect(self.load_variable_desc)

        self.addWidget(self.ds_tree)

        # third row, navigation
        self.navigation_box = QtWidgets.QHBoxLayout()

        # -- animate backwards button
        self.btn_animate_backward = utils.add_pushbutton(
            "◀◀", lambda: self.animate_backward(),
            "Animate the time dimension backwards", self.navigation_box)
        self.btn_animate_backward.setCheckable(True)

        # -- go to previous button
        self.btn_prev = utils.add_pushbutton(
            '◀', self.go_to_previous_step,
            "Go to previous time step", self.navigation_box)

        # -- dimension menu for animation
        self.combo_dims = QtWidgets.QComboBox()
        self.navigation_box.addWidget(self.combo_dims)

        # -- go to next button
        self.btn_next = utils.add_pushbutton(
            '▶', self.go_to_next_step,
            "Go to next time step", self.navigation_box)

        # -- animate forward button
        self.btn_animate_forward = utils.add_pushbutton(
            "▶▶", lambda: self.animate_forward(),
            "Animate the time dimension", self.navigation_box)
        self.btn_animate_forward.setCheckable(True)

        # -- interval slider
        self.sl_interval = QtWidgets.QSlider(Qt.Horizontal)
        self.sl_interval.setMinimum(40)  # 24 fps
        self.sl_interval.setMaximum(10000)
        self.sl_interval.setSingleStep(50)
        self.sl_interval.setPageStep(500)
        self.sl_interval.setValue(500)
        self.sl_interval.valueChanged.connect(self.reset_timer_interval)
        self.navigation_box.addWidget(self.sl_interval)

        # -- interval label
        self.lbl_interval = QtWidgets.QLabel('500 ms')
        self.navigation_box.addWidget(self.lbl_interval)

        # --- export/import menus
        self.export_box = QtWidgets.QHBoxLayout()

        # -- Export button
        self.btn_export = QtWidgets.QToolButton()
        self.btn_export.setText('Export')
        self.btn_export.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_export.setMenu(self.setup_export_menu())
        self.btn_export.setEnabled(False)
        self.export_box.addWidget(self.btn_export)

        # --- Presets button
        self.frm_preset = QtWidgets.QFrame()
        self.frm_preset.setFrameStyle(QtWidgets.QFrame.StyledPanel)
        hbox = QtWidgets.QHBoxLayout(self.frm_preset)

        self.btn_preset = QtWidgets.QToolButton()
        self.btn_preset.setText('Preset')
        self.btn_preset.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_preset.setMenu(self.setup_preset_menu())
        hbox.addWidget(self.btn_preset)

        # --- presets label
        self.lbl_preset = QtWidgets.QLabel('')
        self.lbl_preset.setVisible(False)
        hbox.addWidget(self.lbl_preset)

        # --- unset preset button
        self.btn_unset_preset = utils.add_pushbutton(
            get_psy_icon('invalid.png'), self.unset_preset,
            "Unset the current preset", hbox, icon=True)
        self.btn_unset_preset.setVisible(False)

        self.export_box.addWidget(self.frm_preset)

        self.export_box.addStretch(0)

        vbox = QtWidgets.QVBoxLayout()
        vbox.addLayout(self.navigation_box)
        vbox.addLayout(self.export_box)

        self.addLayout(vbox)

        # fourth row: array selector

        self.array_frame = QtWidgets.QGroupBox('Current plot')
        hbox = QtWidgets.QHBoxLayout()

        self.combo_array = QtWidgets.QComboBox()
        self.combo_array.setEditable(False)
        self.combo_array.currentIndexChanged.connect(lambda: self.refresh())
        self.combo_array.currentIndexChanged.connect(self.show_current_figure)
        hbox.addWidget(self.combo_array)

        self.btn_add = utils.add_pushbutton(
            QtGui.QIcon(get_psy_icon('plus')), self.new_plot,
            "Create a new plot", hbox, icon=True)
        self.btn_add.setEnabled(ds is not None)
        self.btn_del = utils.add_pushbutton(
            QtGui.QIcon(get_psy_icon('minus')), self.close_current_plot,
            "Remove the current plot", hbox, icon=True)
        self.btn_del.setEnabled(False)

        hbox.addWidget(self.btn_add)
        hbox.addWidget(self.btn_del)
        self.array_frame.setLayout(hbox)
        self.addWidget(self.array_frame)

        # fifth row: plot interface
        self.plot_tabs = QtWidgets.QTabWidget()
        self.setup_plot_tabs()
        self.plot_tabs.currentChanged.connect(self.switch_tab)

        self.addWidget(self.plot_tabs)

        # sixth row: variables
        self.variable_scroll = QtWidgets.QScrollArea()
        self.variable_scroll.setWidgetResizable(True)
        self.setup_variable_buttons()
        self.addWidget(self.variable_scroll)

        # seventh row: dimensions
        self.dimension_table = QtWidgets.QTableWidget()
        self.addWidget(self.dimension_table)

        self.disable_navigation()

        if self.ds is not None:
            self.refresh()

        self.cids: Dict[str, int] = {}

    def setup_ds_tree(self) -> None:
        """Setup the number of columns and the header of the dataset tree."""
        self.ds_tree = tree = QtWidgets.QTreeWidget()
        tree.setColumnCount(len(self.ds_attr_columns) + 1)
        tree.setHeaderLabels([''] + self.ds_attr_columns)

    def showEvent(self, event):
        ret = super().showEvent(event)
        current_size = self.size()
        current_sizes = self.sizes()
        new_sizes = list(current_sizes)
        itree = self.indexOf(self.ds_tree)
        itable = self.indexOf(self.dimension_table)
        diff = 0
        if current_sizes[itree] < 400:
            diff += 400 - current_sizes[itree]
            current_sizes[itree] = 400
        if current_sizes[itable] < 300:
            diff += 300 - current_sizes[itable]
            current_sizes[itable] = 300
        if diff:
            self.resize(current_size.width(), current_size.height() + diff)
            self.setSizes(current_sizes)
        return ret

    def close_current_plot(self) -> None:
        """Close the figure of the current variable."""
        self.variable_buttons[self.variable].click()

    def excepthook(self, type, value, traceback) -> None:
        """A method to replace the sys.excepthook"""
        self.error_msg.excepthook(type, value, traceback)

    @property
    def arr_name(self) -> Optional[str]:
        """Get the name of the array of the current plot (if there is one)."""
        if not self.combo_array.count():
            return None
        else:
            return self.combo_array.currentText().split(':')[0]

    def change_ds(self, ds_item: DatasetTreeItem) -> None:
        """Change the current dataset to another one.

        Parameters
        ----------
        ds_item: psyplot_gui.content_widget.DatasetTreeItem
            The item in the tree of the new dataset to use
        """
        ds_items = self.ds_items
        if ds_item in ds_items:
            with self.block_tree():
                self.ds = ds_item.ds()
                self.expand_ds_item(ds_item)
                self.setup_variable_buttons()
                self.change_combo_array()
                self.refresh(reset_combo=False)

    def expand_ds_item(self, ds_item: DatasetTreeItem) -> None:
        """Expand an item of a dataset.

        Parameters
        ----------
        ds_item: DatasetTreeItem
            The item to expand
        """
        tree = self.ds_tree

        tree.collapseAll()

        tree.expandItem(ds_item)

        ds = ds_item.ds()
        if len(ds) <= 10:
            tree.expandItem(ds_item.child(0))
        if len(ds.coords) <= 10:
            tree.expandItem(ds_item.child(1))
        if len(ds.attrs) <= 10:
            tree.expandItem(ds_item.attrs)

    def _open_dataset(self) -> Optional[Dataset]:
        """Open a dialog to open a new dataset from disk.

        Returns
        -------
        xarray.Dataset or None
            The :class:`xarray.Dataset` of the selected file, or None if the
            user aborted the dialog.
        """
        current = self.lbl_ds.text()
        if not current or not osp.exists(current):
            current = os.getcwd()
        fname, ok = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Open dataset', current,
            'NetCDF files (*.nc *.nc4);;'
            'Shape files (*.shp);;'
            'All files (*)'
            )
        if not ok:
            return None
        ds = psyd.open_dataset(fname)
        return ds

    @contextlib.contextmanager
    def block_tree(self) -> Iterator[None]:
        """Block all signals of a tree temporarily.

        Use this via::

            with self.block_tree():
                do_something
        """
        self.ds_tree.blockSignals(True)
        yield
        self.ds_tree.blockSignals(False)

    def set_dataset(self, ds: Optional[Dataset] = None) -> None:
        """Ask for a file name and open the dataset."""
        if ds is None:
            ds = self._open_dataset()
        if ds is None:
            return
        self.ds = ds
        with self.block_tree():
            self.add_ds_item()
            self.setup_variable_buttons()
            self.btn_add.setEnabled(True)
            self.btn_del.setEnabled(True)

    def add_ds_item(self) -> None:
        """Add a new :class:`DatasetTreeItem` for the current :attr:`ds`."""
        ds: Dataset = self.ds  # type: ignore
        tree = self.ds_tree
        ds_item = DatasetTreeItem(ds, self.ds_attr_columns, 0)
        fname = psyd.get_filename_ds(ds, False)[0]
        if fname is not None:
            self.lbl_ds.setText(fname)
            fname = osp.basename(fname)
        else:
            self.lbl_ds.setText('')
            fname = ''
        ds_item.setText(0, fname)
        tree.addTopLevelItem(ds_item)

        self.expand_ds_item(ds_item)

        tree.resizeColumnToContents(0)

        if ds.psy.num not in self.open_datasets:
            # make sure we do not loose track of open datasets
            self._ds_nums[ds.psy.num] = ds

    @property
    def open_datasets(self) -> Dict[int, Dataset]:
        """Get a mapping from path to dataset number of the open datasets."""
        return self._ds_nums

    @property
    def ds_items(self) -> List[DatasetTreeItem]:
        """Get the :class:`DatasetTreeItems` for the open datasets."""
        tree = self.ds_tree
        return list(map(tree.topLevelItem, range(tree.topLevelItemCount())))

    @property
    def ds_item(self) -> Optional[DatasetTreeItem]:
        """Get the current dataset item (if there is one)."""
        ds = self.ds
        for item in self.ds_items:
            if item.ds() is ds:
                return item
        return None

    def expand_current_variable(
            self, variable: Optional[Union[Any, Hashable]] = None) -> None:
        """Expand the item in the dataset tree of variable.

        Parameters
        ----------
        variable: str
            The name of the variable to expand. If None, the current variable is
            used.
        """
        tree = self.ds_tree
        top: DatasetTreeItem = self.ds_item  # type: ignore
        tree.expandItem(top)
        tree.expandItem(top.child(0))
        if variable is None:
            variable: str = self.variable  # type: ignore
        for var_item in map(top.child(0).child,
                            range(top.child(0).childCount())):
            if var_item.text(0) == variable:
                tree.expandItem(var_item)
            else:
                tree.collapseItem(var_item)

    def setup_variable_buttons(self, ncols: int = 4) -> None:
        """Setup the variable buttons for the current dataset."""
        variable_frame = QtWidgets.QGroupBox('Variables')

        self.variable_scroll.setWidget(variable_frame)
        self.variable_frame = variable_frame
        self.variable_layout = QtWidgets.QGridLayout(self.variable_frame)
        self.variable_buttons = {}

        ds = self.ds

        if ds is not None:

            for i, v in enumerate(ds):
                btn = utils.add_pushbutton(
                    v, self._draw_variable(v), f"Visualize variable {v}")
                btn.setCheckable(True)
                self.variable_buttons[v] = btn
                self.variable_layout.addWidget(btn, i // ncols, i % ncols)

            if len(ds):
                rows = len(ds) // ncols
                minrows = max(1, min(3, rows))
                self.variable_scroll.setMinimumHeight(
                        (minrows + 2) * btn.sizeHint().height())

    def load_variable_desc(self, item: QtWidgets.QTreeWidgetItem) -> None:
        """Load the description of the variable of a given tree item.

        Parameters
        ----------
        item: PyQt5.QtWidget.QTreeWidgetItem
            The item of the variable in the :attr:`ds_tree`. If this is not an
            item of a variable, nothing is done.
        """
        parent = item.parent()

        tree = self.ds_tree

        if parent is tree or parent is None or not (
                DatasetTree.is_variable(item) or DatasetTree.is_coord(item)):
            return

        if tree.isColumnHidden(1):
            tree.showColumn(1)
            tree.resizeColumnToContents(0)

        top = item
        while top.parent() and top.parent() is not self:
            top = top.parent()
        ds = top.ds()
        if ds is None:
            return
        desc = escape_html(str(ds.variables[item.text(0)]))
        item.setToolTip(0, '<pre>' + desc + '</pre>')

    def clear_table(self) -> None:
        """Clear the table that shows the available dimensions."""
        self.dimension_table.clear()
        self.dimension_table.setColumnCount(5)
        self.dimension_table.setHorizontalHeaderLabels(
            ['Type', 'First', 'Current', 'Last', 'Units'])
        self.dimension_table.setRowCount(0)

    def addLayout(self, layout: QtWidgets.QLayout) -> QtWidgets.QWidget:
        """Add a layout to the splitter.

        This convenience function creates a new QWidget that wraps the given
        layout and returns it.

        Parameters
        ----------
        layout: QtWidget.QLayout
            The layout to add

        Returns
        -------
        QtWidgets.QWidget
            The widget that wraps the given layout
        """
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.addWidget(widget)
        return widget

    def go_to_previous_step(self) -> None:
        """Decrease the movie dimension to the previous step."""
        dim = self.combo_dims.currentText()
        self.increase_dim(dim, -1)()

    def go_to_next_step(self) -> None:
        """Increase the movie dimension to the next step."""
        dim = self.combo_dims.currentText()
        self.increase_dim(dim)()

    def animate_backward(self) -> None:
        """Start the current animation in backward direction, or stop it."""
        if self._animating:
            self.stop_animation()
            self.btn_animate_backward.setText('◀◀')
            self.enable_navigation()
        else:
            self._animate_forward = False
            self.btn_animate_backward.setText('■')
            self.disable_navigation(self.btn_animate_backward)
            self.start_animation()

    def animate_forward(self, nframes=None):
        """Start the current animation in forward direction, or stop it."""
        if self._animating:
            self.stop_animation()
            self.btn_animate_forward.setText('▶▶')
            self.enable_navigation()
        else:
            self._animate_forward = True
            self.btn_animate_forward.setText('■')
            self.disable_navigation(self.btn_animate_forward)
            self.start_animation(nframes)

    def setup_plot_tabs(self) -> None:
        """Setup the tabs of the various plot methods."""
        self.plot_tabs.addTab(MapPlotWidget(self.get_sp, self.ds),
                              'mapplot')
        self.plot_tabs.addTab(Plot2DWidget(self.get_sp, self.ds),
                              'plot2d')
        lineplot_widget = LinePlotWidget(self.get_sp, self.ds)
        self.plot_tabs.addTab(lineplot_widget, 'lineplot')

        for w in map(self.plot_tabs.widget, range(self.plot_tabs.count())):
            w.replot.connect(self.replot)
            w.reset.connect(self.reset)
            w.changed.connect(lambda: self.refresh())

    def replot(self, plotmethod: str) -> None:
        """Regenerate the plot of a given plotmethod, without closing it.

        Parameters
        ----------
        plotmethod: str
            The name of the plotmethod

        See Also
        --------
        reset: The same method, but closes the plot before genereting a new one.
        """
        self.plotmethod = plotmethod
        self.make_plot()
        self.refresh()

    def reset(self, plotmethod: str) -> None:
        """Close the plot of the given plotmethod and regenerate it.

        The same as :meth:`replot`, but closes the plot.

        Parameters
        ----------
        plotmethod: str
            The name of the plotmethod

        See Also
        --------
        reset: The same method, but closes the plot before genereting a new one.
        """
        self.plotmethod = plotmethod
        self.close_sp()
        self.make_plot()
        self.refresh()

    def disable_navigation(
            self, but: Optional[QtWidgets.QPushButton] = None
        ) -> None:
        """Disable the navigation buttons.

        This function disables all navigation buttons but the one you specify.

        Parameters
        ----------
        but: PyQt5.QtWidgets.QPushButton
            If not None, this button is not disabled.
        """
        for item in map(self.navigation_box.itemAt,
                        range(self.navigation_box.count())):
            w = item.widget()
            if w is not but and w is not self.sl_interval:
                w.setEnabled(False)

    def enable_navigation(self) -> None:
        """Enable all navigation buttons again."""
        for item in map(self.navigation_box.itemAt,
                        range(self.navigation_box.count())):
            w = item.widget()
            w.setEnabled(True)

    def disable_variables(self):
        """Disable all variable selection buttons."""
        for btn in self.variable_buttons.values():
            btn.setEnabled(False)

    def enable_variables(self):
        """Enable all variable selection buttons again."""
        valid_variables = self.plotmethod_widget.valid_variables(self.ds)
        for v, btn in self.variable_buttons.items():
            btn.setEnabled(v in valid_variables)

    def start_animation(self, nframes: Optional[int] = None):
        """Start the animation along the selected dimension.

        Parameters
        ----------
        nframes: int or None
            If not None, the number of frames to draw

        See Also
        --------
        animation_frames: The iterator to generate the frames
        """
        self._animating = True
        self._animation_frames = nframes
        self._starting_step = 1
        self.disable_variables()
        self.plot_tabs.setEnabled(False)
        if self.sp is not None:
            if self.animation is None or self.animation.event_source is None:
                self.animation = FuncAnimation(
                    self.fig, self.update_dims, frames=self.animation_frames(),
                    init_func=self.sp.draw, interval=self.sl_interval.value(),
                    repeat=False)
                # HACK: Make sure that the animation starts although the figure
                # is already shown
                self.animation._draw_frame(next(self.animation_frames()))
            else:
                self.animation.event_source.start()

    def reset_timer_interval(self, value: int) -> None:
        """Change the interval of the timer."""
        self.lbl_interval.setText('%i ms' % value)
        if self.animation is None or self.animation.event_source is None:
            pass
        else:
            self.animation.event_source.stop()
            self.animation._interval = value
            self.animation.event_source.interval = value
            self.animation.event_source.start()

    def stop_animation(self) -> None:
        """Stop the current animation."""
        self._animating = False
        if (self.animation is not None and
                self.animation.event_source is not None):
            self.animation.event_source.stop()
        self.plot_tabs.setEnabled(True)
        self.enable_variables()
        self.refresh()

    def animation_frames(self) -> Iterator[Dict[str, int]]:
        """Get the animation frames for the :attr:`combo_dims` dimension."""
        while self._animating and self._animation_frames is None or \
                self._animation_frames:
            if self._animation_frames is not None and not self._init_step:
                self._animation_frames -= 1
            dim = self.combo_dims.currentText()
            i = self.data.psy.idims[dim]
            imax = self.ds.dims[dim] - 1  # type: ignore
            if self._init_step:
                self._init_step -= 1
            elif self._starting_step:
                self._starting_step -= 1
            elif self._animate_forward:
                i += -i if i == imax else 1
            else:
                i += imax if i == 0 else -1
            yield {dim: i}

    def update_dims(self, dims: Dict[str, Any]):
        if self.sp is not None:
            self.sp.update(dims=dims)

    def _load_preset(self) -> None:
        """Open a file dialog and load the selected preset."""
        fname, ok = QtWidgets.QFileDialog.getOpenFileName(
            self, 'Load preset', osp.join(get_configdir(), 'presets'),
            'YAML files (*.yml *.yaml);;'
            'All files (*)')
        if ok:
            self.load_preset(fname)

    def load_preset(self, preset: Optional[Union[str, Dict[str, Any]]]):
        """Load a given preset from disk.
        
        Parameters
        ----------
        preset: str or dict
            The name or path to the preset, or a dictionary
        """
        self.preset = preset  # type: ignore
        if self.sp:
            loaded_preset: Dict[str, Any] = self.preset  # now that it's loaded
            if loaded_preset:
                self.sp.load_preset(loaded_preset)
                self.refresh()
        self.maybe_show_preset()

    @property
    def preset(self) -> Dict[str, Any]:
        """Get the currently loaded preset."""
        if self._preset is None:
            return {}
        import psyplot.project as psy
        preset = self._preset
        try:
            preset = psy.Project._load_preset(preset)
        except yaml.constructor.ConstructorError:
            answer = QtWidgets.QMessageBox.question(
                self, "Can I trust this?",
                f"Failed to load the preset at <i>{preset}</i> in safe mode. Can we "
                "trust this preset and load it in unsafe mode?")
            if answer == QtWidgets.QMessageBox.Yes:
                psyd.rcParams['presets.trusted'].append(
                    psy.Project._resolve_preset_path(preset))
                preset = psy.Project._load_preset(preset)
            else:
                preset = {}
        return preset  # type: ignore

    @preset.setter
    def preset(self, value: Optional[Union[str, Dict[str, Any]]]):
        self._preset = value


    def unset_preset(self) -> None:
        """Unset the current preset and do not use it anymore."""
        self.preset = None  # type: ignore
        self.maybe_show_preset()

    def maybe_show_preset(self) -> None:
        """Show the name of the current preset if one is selected."""
        if self._preset is not None and isinstance(self._preset, str):
            self.lbl_preset.setText('<i>' +
                osp.basename(osp.splitext(self._preset)[0]) + '</i>')
            self.lbl_preset.setVisible(True)
            self.btn_unset_preset.setVisible(True)
        elif self._preset is not None:
            self.lbl_preset.setText('<i>custom</i>')
            self.lbl_preset.setVisible(True)
            self.btn_unset_preset.setVisible(True)
        else:
            self.lbl_preset.setVisible(False)
            self.btn_unset_preset.setVisible(False)

    def save_current_preset(self) -> None:
        """Save the preset of the current plot to a file."""
        if self.sp is not None:
            preset_func = self.sp.save_preset
            self._save_preset(preset_func)

    def save_full_preset(self) -> None:
        """Save the preset of all open plots to a file."""
        sp = self._sp
        if sp is not None:
            return self._save_preset(sp.save_preset)
        return None

    def _save_preset(self, save_func: Callable[[str], Any]) -> None:
        """Save the preset to a file.

        Parameters
        ----------
        save_func: function
            The function that is called to save the preset. Must accept the
            path as an argument
        """
        fname, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, 'Save preset', osp.join(get_configdir(), 'presets'),
            'YAML files (*.yml *.yaml);;'
            'All files (*)')
        if not ok:
            return None
        save_func(fname)

    def setup_preset_menu(self) -> QtWidgets.QMenu:
        """Set up the menu to select/load presets."""
        self.preset_menu = menu = QtWidgets.QMenu()
        self._save_preset_actions = []

        self._load_preset_action = menu.addAction(
            "Load preset", self._load_preset)
        self._unset_preset_action = menu.addAction(
            "Unset preset", self.unset_preset)

        menu.addSeparator()

        self._save_preset_actions.append(
            menu.addAction('Save format of current plot as preset',
                           self.save_current_preset))
        self._save_preset_actions.append(
            menu.addAction('Save format of all plots as preset',
                           self.save_full_preset))

        for action in self._save_preset_actions:
            action.setEnabled(False)

        return menu

    def setup_export_menu(self) -> QtWidgets.QMenu:
        """Set up the menu to export the current plot."""
        self.export_menu = menu = QtWidgets.QMenu()
        menu.addAction('image (PDF, PNG, etc.)', self.export_image)
        menu.addAction('all images (PDF, PNG, etc.)', self.export_all_images)
        menu.addAction('animation (GIF, MP4, etc.', self.export_animation)
        menu.addAction('psyplot project (.pkl file)', self.export_project)
        menu.addAction('psyplot project with data',
                       self.export_project_with_data)
        py_action = menu.addAction('python script (.py)', self.export_python)
        py_action.setEnabled(False)  # psyplot does not yet export to python
        return menu

    def export_image(self) -> None:
        """Ask for a filename and export the current plot to a file."""
        if self.sp is not None:
            fname, ok = QtWidgets.QFileDialog.getSaveFileName(
                self, "Export image", os.getcwd(),
                "Images (*.png *.pdf *.jpg *.svg)")
            if ok:
                self.sp.export(fname, **rcParams['savefig_kws'])

    def export_all_images(self) -> None:
        """Ask for a filename and export all plots to one (or more) files."""
        fname, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export image", os.getcwd(),
            "Images (*.png *.pdf *.jpg *.svg)")
        if ok and self._sp:
            # test filenames
            if not osp.splitext(fname)[-1].lower() == '.pdf':
                fnames = [
                    sp.format_string(fname, False, i)
                    for i, sp in enumerate(self._sp.figs.values())]
                if len(fnames) != len(set(fnames)):
                    answer = QtWidgets.QMessageBox.question(
                        self, "Too many figures",
                        TOO_MANY_FIGURES_WARNING.format(
                            len(set(fnames)), ', '.join(set(fnames))))
                    if answer == QtWidgets.QMessageBox.No:
                        return
            self._sp.export(fname, **rcParams['savefig_kws'])

    def export_animation(self) -> None:
        """Ask for a filename and export the animation."""
        fname, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export animation", os.getcwd(),
            "Movie (*.mp4 *.mov *.gif)")
        if ok:
            dim = self.combo_dims.currentText()
            nframes: int = self.ds.dims[dim]  # type: ignore

            self._init_step = 1
            self.animate_forward(nframes)
            if self.animation is not None:
                self.animation.save(
                    fname, **rcParams['animations.export_kws'],
                    fps=round(1000. / self.sl_interval.value()))
            self.animate_forward()
            self.animation = None

    def export_project(self) -> None:
        """Ask for a filename and export the psyplot project as .pkl file."""
        if self.sp is not None:
            fname, ok = QtWidgets.QFileDialog.getSaveFileName(
                self, "Export project", os.getcwd(),
                "Psyplot projects (*.pkl)")
            if ok:
                self.sp.save_project(fname)

    def export_project_with_data(self) -> None:
        """Ask for a filename export project (incl. data) as .pkl file.

        Same as :meth:`export_project`, but adds the data to the pickle dump.
        """
        if self.sp is not None:
            fname, ok = QtWidgets.QFileDialog.getSaveFileName(
                self, "Export project", os.getcwd(),
                "Psyplot projects (*.pkl)")
            if ok:
                self.sp.save_project(fname, ds_description={"ds"})

    def export_python(self):
        """Export the project as python file.

        This method is not yet implemented as the functionality is missing in 
        psyplot.
        """
        pass

    def _draw_variable(self, v):
        def func():
            """Visualize variable v"""
            btn = self.variable_buttons[v]
            if not btn.isChecked():
                self.close_sp()
                if self.combo_array.count() > 1:
                    with self.block_widgets(self.combo_array):
                        current = self.combo_array.currentIndex()
                        self.combo_array.setCurrentIndex(current - 1)

            else:
                with self.silence_variable_buttons():
                    for var, btn in self.variable_buttons.items():
                        if var != v:
                            btn.setChecked(False)
                self.make_plot()
            self.refresh()

        return func

    @contextlib.contextmanager
    def silence_variable_buttons(self) -> Iterator[None]:
        """Context manager to disable variable selection buttons."""
        yield self.block_widgets(*self.variable_buttons.values())  # type: ignore

    @property
    def variable(self) -> Union[str, NOTSET_T]:
        """The current variable"""
        for v, btn in self.variable_buttons.items():
            if btn.isChecked():
                return v
        return NOTSET

    @variable.setter
    def variable(self, value: Union[str, NOTSET_T]) -> None:
        with self.silence_variable_buttons():
            for v, btn in self.variable_buttons.items():
                btn.setChecked(v == value)

    @property
    def available_plotmethods(self) -> List[str]:
        """Get the plotmethods that can visualize the selected variable.
        
        Returns
        -------
        list of str
            A list of plotmethod names that can visualize the current
            :attr:`variable`
        """
        v = self.variable
        if v is NOTSET:
            return []
        ret = []
        ds: Dataset = self.ds  # type: ignore
        plot = ds.psy.plot
        for plotmethod in self.plotmethods:
            if plotmethod in plot._plot_methods:
                if getattr(plot, plotmethod).check_data(ds, v, {})[0]:
                    ret.append(plotmethod)
        return ret

    @property
    def plot(self) -> PlotterInterface:
        """Get the plotting function of the currently selected plotmethod."""
        if self.ds is not None:
            return getattr(self.ds.psy.plot, self.plotmethod)
        else:
            raise ValueError(
                "No dataset has yet been selected, so no plot method!")

    @property
    def plot_options(self) -> Dict[str, Any]:
        """Get further keyword arguments for the :attr:`plot` function."""
        if self.ds is not None:
            ret: Dict[str, Any] = self.plotmethod_widget.get_fmts(  # type: ignore
                self.ds.psy[self.variable], True)
            preset = self.preset
            if preset:
                import psyplot.project as psy
                preset = psy.Project.extract_fmts_from_preset(
                    preset, self.plotmethod)
                ret.update(dict(preset))
            return ret
        return {}

    @property
    def plotmethod(self) -> str:
        """Get the name of the current plotmethod."""
        return self.plot_tabs.tabText(self.plot_tabs.currentIndex())

    @plotmethod.setter
    def plotmethod(self, label: str):
        i = next((i for i in range(self.plot_tabs.count())
                  if self.plot_tabs.tabText(i) == label), None)
        if i is not None:
            self.plot_tabs.setCurrentIndex(i)

    @property
    def plotmethods(self) -> List[str]:
        """Get a list of available plotmethods."""
        return list(map(self.plot_tabs.tabText, range(self.plot_tabs.count())))

    @property
    def plotmethod_widget(self) -> PlotMethodWidget:
        """Get widget of the current plotmethod."""
        label = self.plotmethod
        i = next((i for i in range(self.plot_tabs.count())
                  if self.plot_tabs.tabText(i) == label), None)
        return self.plot_tabs.widget(i)

    @property
    def plotmethod_widgets(self) -> Dict[str, PlotMethodWidget]:
        """Get a list of available plotmethod widgets."""
        return dict(zip(self.plotmethods, map(self.plot_tabs.widget,
                                              range(self.plot_tabs.count()))))

    _sp = None

    def get_sp(self) -> Optional[Project]:
        sp = self._sp
        if sp is None:
            return sp
        return self.filter_sp(sp)

    def filter_sp(self, sp: Project, ds_only: bool = False) -> Project:
        """Filter the psyplot project to only include the arrays of :attr:`ds`
        """
        if self._new_plot:
            return None
        if self.ds is None:
            return sp
        num = self.ds.psy.num
        ret = sp[:0]
        for i in range(len(sp)):
            if list(sp[i:i+1].datasets) == [num]:
                ret += sp[i:i+1]
        if ds_only:
            return ret
        arr_name = self.arr_name
        if arr_name is None:
            return ret
        return ret(arr_name=arr_name)

    def new_plot(self) -> None:
        """Select a new variable and make a plot.
        
        This method asks for a variable and them makes a new plot with the
        selected plotmethod.
        
        See Also
        --------
        make_plot: plot the currently selected variable without asking
        """
        if self.ds is not None:
            name, ok = QtWidgets.QInputDialog.getItem(
                self, 'New plot', 'Select a variable',
                self.plotmethod_widget.valid_variables(self.ds))
            if not ok:
                return
            with self.silence_variable_buttons():
                for v, btn in self.variable_buttons.items():
                    btn.setChecked(v == name)
            with self.creating_new_plot():
                self.make_plot()
            self.btn_del.setEnabled(True)
        self.refresh()

    @contextlib.contextmanager
    def creating_new_plot(self) -> Iterator[None]:
        """Tell that we are making a new plot."""
        self._new_plot = True
        yield
        self._new_plot = False

    @property
    def sp(self) -> Optional[Project]:
        """Get the psyplot project of the current plotmethod."""
        return self.plotmethod_widget.sp or None

    @sp.setter
    def sp(self, sp: Optional[Project]):
        if sp is None and (not self._sp or not getattr(
                self._sp, self.plotmethod)):
            pass
        else:
            # first remove the current arrays
            if self.get_sp() and getattr(self.get_sp(), self.plotmethod):
                to_remove = getattr(self.get_sp(), self.plotmethod).arr_names
                _sp: Project = self._sp  # type: ignore
                for i in list(reversed(range(len(_sp)))):
                    if _sp[i].psy.arr_name in to_remove:
                        _sp.pop(i)
            # then add the new arrays
            if sp:
                if self._sp:
                    self._sp.extend(list(sp), new_name=True)
                else:
                    self._sp = sp

    @property
    def data(self) -> Union[psyd.InteractiveList, DataArray]:
        """Get the raw data of the current plot."""
        return self.plotmethod_widget.data

    @property
    def plotter(self) -> Plotter:
        """Get the psyplot plotter of the current plot."""
        return self.plotmethod_widget.plotter

    @property
    def fig(self) -> Figure:
        """Get the figure of the current plot."""
        if self.sp:
            return list(self.sp.figs)[0]

    _animations: Dict[str, FuncAnimation] = {}

    @property
    def animation(self) -> Optional[FuncAnimation]:
        """Get the animation of the current plotmethod."""
        return self._animations.get(self.plotmethod)

    @animation.setter
    def animation(self, ani: Optional[FuncAnimation]):
        if ani is None:
            self._animations.pop(self.plotmethod, None)
        else:
            self._animations[self.plotmethod] = ani

    def make_plot(self) -> None:
        """Make or update the plot of the current variable.

        See Also
        --------
        new_plot: A function to select the variable first
        """
        plotmethods = self.available_plotmethods
        plotmethod = self.plotmethod
        if plotmethod not in plotmethods:
            if not plotmethods:
                QtWidgets.QMessageBox.critical(
                    self, "Visualization impossible",
                    f"Found no plotmethod for variable {self.variable}")
                return
            plotmethod, ok = QtWidgets.QInputDialog.getItem(
                self, "Choose a plot method", "Plot method:", plotmethods)
            if not ok:
                return
            self.plotmethod = plotmethod
        new_v = self.variable
        fmts: Dict[str, Any] = {}
        dims: Dict[Hashable, int] = {}
        if self.sp:
            ds: Dataset = self.ds  # type: ignore
            if not set(self.data.dims) <= set(ds[new_v].dims):
                self.close_sp()
            else:
                for dim in set(ds[new_v].dims) - set(self.data.psy.idims):
                    dims[dim] = 0
                for dim in set(self.data.psy.idims) - set(ds[new_v].dims):
                    del self.data.psy.idims[dim]
        if self.sp:
            if self.data.psy.plotter is None:
                self.data.psy.update(name=self.variable)
                self.data.psy.update(dims=dims, **fmts)
                self.sp.update(replot=True)
            else:
                self.data.psy.update(name=self.variable, dims=dims, **fmts)
            self.show_fig(self.sp)
        else:
            self.ani = None
            self.sp = sp = self.plot(name=self.variable, **self.plot_options)
            self._preset = None
            cid = sp.plotters[0].ax.figure.canvas.mpl_connect(
                'button_press_event', self.display_line)
            self.cids[self.plotmethod] = cid
            self.show_fig(sp)
            descr = sp[0].psy._short_info()
            with self.block_widgets(self.combo_array):
                self.combo_array.addItem(descr)
                self.combo_array.setCurrentText(descr)
        self.expand_current_variable()
        self.enable_navigation()

    @contextlib.contextmanager
    def block_widgets(self, *widgets: QtWidgets.QWidget) -> Iterator[None]:
        """Temporarilly block all signals for the given widgets."""
        for w in widgets:
            w.blockSignals(True)
        yield
        for w in widgets:
            w.blockSignals(False)

    def display_line(self, event: MouseEvent) -> None:
        """Display the line when clicked on a 2D-plot."""
        if not event.inaxes:
            return
        else:
            sl = None
            for widget in map(self.plot_tabs.widget,
                              range(self.plot_tabs.count())):
                if widget.sp and event.inaxes == widget.plotter.ax:
                    sl = widget.get_slice(event.xdata, event.ydata)
                    break
            variable = widget.data.name
            raw_data = widget.data.psy.base.psy[variable]
            if (sl is None or widget.plotmethod not in ['mapplot', 'plot2d'] or
                raw_data.ndim == 2 or
                widget.plotter.ax.figure.canvas.manager.toolbar.mode != ''):
                return
            # check if the mappable contains the event
            if not self.plotter.plot.mappable.contains(event)[0] and (
                    not hasattr(self.plotter.plot, '_wrapped_plot') or
                    not self.plotter.plot._wrapped_plot.contains(event)[0]):
                return
            current_pm = self.plotmethod
            self.plotmethod = 'lineplot'
            linewidget = self.plotmethod_widget
            xdim = linewidget.xdim
            if xdim is None:
                xdim = self.combo_dims.currentText()

            if not linewidget.sp or (linewidget.xdim and
                                     linewidget.xdim not in raw_data.dims):
                with self.silence_variable_buttons():
                    for v, btn in self.variable_buttons.items():
                        btn.setChecked(v == variable)
                self.make_plot()
                linewidget.xdim = xdim
            else:
                linewidget.xdim = xdim
                linewidget.add_line(variable, **sl)
            self.plotmethod = current_pm


    def close_sp(self) -> None:
        """Close the current subproject."""
        sp = self.sp
        self.sp = None
        if sp is not None:
            sp.close(figs=True, data=True, ds=False)

    def show_current_figure(self) -> None:
        """Show figure of the current plotmethod."""
        if self.sp is not None:
            self.show_fig(self.sp)

    def show_fig(self, sp: Project) -> None:
        """Show the first figure in a psyplot project."""
        if len(sp):
            try:
                fig = sp.plotters[0].ax.figure
                fig.canvas.window().show()
                fig.canvas.window().raise_()
            except AttributeError:
                sp.show()

    def switch_tab(self) -> None:
        """Select a valid variable when switching the plotmethod tabs."""
        with self.silence_variable_buttons():
            if self.sp:
                name = self.data.name
            else:
                name = NOTSET
            for v, btn in self.variable_buttons.items():
                btn.setChecked(v == name)
        self.refresh()

    def change_combo_array(self) -> None:
        """Update the iteration dimension depending on the selected variable."""
        with self.block_widgets(self.combo_array):
            sp = self.filter_sp(self._sp, ds_only=True)
            if sp and self.arr_name not in sp.arr_names:
                new_arr = sp.arr_names[0]
                all_arrays = getattr(self._sp, self.plotmethod)
                try:
                    idx_arr = all_arrays.arr_names.index(new_arr)
                except ValueError:
                    idx_arr = 0
                self.combo_array.setCurrentIndex(idx_arr)
                try:
                    vname = self.data.name
                except Exception:
                    vname = self.variable
                if vname is not NOTSET:
                    self.expand_current_variable(vname)
                    self.show_fig(sp[:1])

    def reset_combo_array(self) -> None:
        """Clear and fill the iteration dimension based on :attr:`ds`."""
        curr_arr_name = self.arr_name
        with self.block_widgets(self.combo_array):
            self.combo_array.clear()
            if self._sp:
                all_arrays = getattr(self._sp, self.plotmethod)
                current_ds = self.ds
                if all_arrays:
                    for arr in all_arrays:
                        self.combo_array.addItem(arr.psy._short_info())
                    if curr_arr_name in all_arrays.arr_names:
                        idx_arr = all_arrays.arr_names.index(curr_arr_name)
                        self.combo_array.setCurrentIndex(idx_arr)
                    else:
                        idx_arr = 0
                    self.ds = list(
                        all_arrays[idx_arr:idx_arr+1].datasets.values())[0]
                    if self.ds is not current_ds:
                        with self.block_tree():
                            self.expand_ds_item(self.ds_item)
                            self.expand_current_variable(self.data.name)

    def refresh(self, reset_combo: bool = True) -> None:
        """Refresh the state of this widget.

        This method refreshes the widget based on the selected project, 
        variable, etc.

        Parameters
        ----------
        reset_combo: bool
            If True (default), the :meth:`reset_combo_array` is called
        """
        self.clear_table()

        if reset_combo:
            self.reset_combo_array()

        if self.sp:
            variable = self.data.name
            for action in self._save_preset_actions:
                action.setEnabled(True)
            self.btn_del.setEnabled(True)
            self.btn_export.setEnabled(True)
        else:
            variable = self.variable
            for action in self._save_preset_actions:
                action.setEnabled(False)
            self.btn_del.setEnabled(False)
            self.btn_export.setEnabled(False)


        # refresh variable buttons
        with self.silence_variable_buttons():
            for v, btn in self.variable_buttons.items():
                btn.setChecked(v == variable)

        # refresh tabs
        for i in range(self.plot_tabs.count()):
            w = self.plot_tabs.widget(i)
            w.refresh(self.ds)
        if self.ds is not None and self.variable_buttons:
            valid_variables = self.plotmethod_widget.valid_variables(self.ds)
            for v, btn in self.variable_buttons.items():
                btn.setEnabled(v in valid_variables)
        elif self.ds is None or variable is NOTSET or not self.sp:
            return

        table = self.dimension_table

        if self.sp:
            data = self.data
            ds_data = self.ds[self.variable]

            with self.silence_variable_buttons():
                self.variable_buttons[self.variable].setChecked(True)

            dims: Tuple[Hashable, ...] = ds_data.dims  # type: ignore
            table.setRowCount(ds_data.ndim)
            table.setVerticalHeaderLabels(ds_data.dims)

            # set time, z, x, y info
            for c in 'XYTZ':
                cname = ds_data.psy.get_dim(c)
                if cname and cname in dims:
                    table.setItem(
                        dims.index(cname), 0, QtWidgets.QTableWidgetItem(c))

            for i, dim in enumerate(dims):
                coord = self.ds[dim]
                if 'units' in coord.attrs:
                    table.setItem(
                        i, 4, QtWidgets.QTableWidgetItem(
                            str(coord.attrs['units'])))
                try:
                    coord = list(map("{:1.4f}".format, coord.values))  # type: ignore
                except (ValueError, TypeError):
                    try:
                        coord = coord.to_pandas().dt.to_pydatetime()  # type: ignore
                    except AttributeError:
                        coord = list(map(str, coord.values))  # type: ignore
                    else:
                        coord = [t.isoformat() for t in coord]  # type: ignore
                first = coord[0]
                last = coord[-1]
                table.setItem(
                    i, 1, QtWidgets.QTableWidgetItem(first))
                table.setItem(
                    i, 3, QtWidgets.QTableWidgetItem(last))

                current = data.psy.idims.get(dim)
                if current is not None and isinstance(current, int):
                    table.setCellWidget(
                        i, 2, self.new_dimension_button(dim, coord[current]))

            # update animation checkbox
            dims_to_animate = get_dims_to_iterate(data)

            current_dims_to_animate = list(map(
                self.combo_dims.itemText,
                range(self.combo_dims.count())))
            if dims_to_animate != current_dims_to_animate:
                self.combo_dims.clear()
                self.combo_dims.addItems(dims_to_animate)

        table.resizeColumnsToContents()

        # update plots items
        for ds_item in self.ds_items:
            for item in map(ds_item.child, range(ds_item.childCount())):
                for child in map(item.child, range(item.childCount())):
                    if DatasetTree.is_variable(child):
                        plots_item = ds_item.get_plots_item(child)
                        ds_item.refresh_plots_item(
                            plots_item, child.text(0), self._sp, self.sp)

    def new_dimension_button(
            self, dim: Hashable, label: Any) -> utils.QRightPushButton:
        """Generate a new button to increase of decrease a dimension."""
        btn = utils.QRightPushButton(label)
        btn.clicked.connect(self.increase_dim(str(dim)))
        btn.rightclicked.connect(self.increase_dim(str(dim), -1))
        btn.setToolTip(f"Increase dimension {dim} with left-click, and "
                       "decrease with right-click.")
        return btn

    def update_project(self, *args, **kwargs) -> None:
        """Update the correct project :attr:`sp` and refresh the widget."""
        sp = self.sp
        if sp is not None:
            sp.update(*args, **kwargs)
            self.refresh()

    def increase_dim(self, dim: str, increase: int = 1) -> Callable[[], None]:
        """Get a function to update a specific dimension.

        Parameters
        ----------
        dim: str
            The dimension name
        increase: int
            The number of steps to increase (or decrease) the given `dim`.
        """
        def update():
            i = self.data.psy.idims[dim]
            self.data.psy.update(dims={dim: (i+increase) % self.ds.dims[dim]})
            if self.data.psy.plotter is None:
                self.sp.update(replot=True)
            self.refresh()
        return update


class DatasetWidgetPlugin(DatasetWidget, DockMixin):
    """A :class:`DatasetWidget` plugin for the psyplot GUI.

    This widget can be embeded in the psyplot GUI. Different from the standalone
    :class:`DatasetWidget` class, this one here uses the current psyplot project
    (:func:`psyplot.project.gcp`)
    """

    #: The title of the widget
    title = 'psy-view Dataset viewer'

    #: Display the dock widget at the right side of the GUI
    dock_position = Qt.RightDockWidgetArea

    def __init__(self, *args, **kwargs):
        import psyplot.project as psy
        super().__init__(*args, **kwargs)
        psy.Project.oncpchange.connect(self.oncpchange)

    @property  # type: ignore
    def _sp(self) -> Project:  # type: ignore
        import psyplot.project as psy
        return psy.gcp(True)

    @_sp.setter
    def _sp(self, value):
        pass

    @property
    def sp(self) -> Optional[Project]:
        """Get the psyplot project of the current plotmethod."""
        return self.plotmethod_widget.sp or None

    @sp.setter
    def sp(self, sp: Optional[Project]):
        current = self.get_sp()
        if sp is None or not current:
            return
        elif getattr(current, self.plotmethod, []):

            if len(current) == 1 and len(sp) == 1:
                pass
            # first remove the current arrays
            if current and getattr(current, self.plotmethod):
                to_remove = getattr(self.get_sp(), self.plotmethod).arr_names
                for i in list(reversed(range(len(current)))):
                    if current[i].psy.arr_name in to_remove:
                        current.pop(i)
            # then add the new arrays
            if sp:
                if current:
                    current.extend(list(sp), new_name=True)
                else:
                    current = sp
            current.oncpchange.emit(current)

    @property
    def open_datasets(self) -> Dict[int, Dataset]:
        """Get a mapping from path to dataset number of the open datasets."""
        ret = self._sp.datasets
        ret.update(self._ds_nums)
        return ret

    def close_sp(self) -> None:
        ds = self.ds
        super().close_sp()
        if ds is not None:
            if ds.psy.num not in self._sp.datasets:
                self.set_dataset(ds)

    def oncpchange(self, sp: Optional[Project]) -> None:
        """Update this widget from the current psyplot main (or sub) project."""
        self.reset_combo_array()
        if self.ds is not None and self.ds.psy.num not in self._sp.datasets:
            self.ds = None
            self.disable_navigation()
            self.setup_variable_buttons()
            self.btn_add.setEnabled(False)
            self.btn_del.setEnabled(False)
        elif self.ds is None and self._sp:
            self.set_dataset(next(iter(self._sp.datasets.values())))

    def show_fig(self, sp: Optional[Project]) -> None:
        """Show the figure of the the current subproject."""
        from psyplot_gui.main import mainwindow
        super().show_fig(sp)
        if mainwindow.figures and sp:
            try:
                dock = sp.plotters[0].ax.figure.canvas.manager.window
                dock.widget().show_plugin()
                dock.raise_()
            except AttributeError:
                pass

    def setup_ds_tree(self) -> None:
        """Setup the number of columns and the header of the dataset tree.
        
        Reimplemented to use the :class:`psyplot_gui.content_widget.DatasetTree`
        """
        self.ds_tree = tree = DatasetTree()
        tree.setColumnCount(len(self.ds_attr_columns) + 1)
        tree.setHeaderLabels([''] + self.ds_attr_columns)

    def position_dock(self, main: MainWindow, *args, **kwargs) -> None:
        height = main.help_explorer.dock.size().height()
        main.splitDockWidget(main.help_explorer.dock, self.dock, Qt.Vertical)
        if hasattr(main, 'resizeDocks'):  # qt >= 5.6
            main.resizeDocks([main.help_explorer.dock, self.dock],
                             [height // 2, height // 2], Qt.Vertical)
