# -*- coding: utf-8 -*-
"""Dataset widget to display the contents of a dataset"""
from itertools import cycle
import os.path as osp
import os
import contextlib
import yaml
from functools import partial
from itertools import chain
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtCore import Qt
import psy_view.utils as utils
from psyplot_gui.content_widget import (
    DatasetTree, DatasetTreeItem, escape_html)
from psyplot_gui.common import (
    DockMixin, get_icon as get_psy_icon, PyErrorMessage)
import xarray as xr
import psyplot.data as psyd
from psyplot.utils import unique_everseen
from psy_view.rcsetup import rcParams

from matplotlib.animation import FuncAnimation

NOTSET = object


def get_icon(name, ending='.png'):
    return osp.join(osp.dirname(__file__), 'icons', name + ending)


def get_dims_to_iterate(arr):
    base_var = next(arr.psy.iter_base_variables)
    return [dim for dim, size in zip(base_var.dims, base_var.shape)
            if size > 1 and arr[dim].ndim == 0]



class DatasetWidget(QtWidgets.QSplitter):
    """A widget to control the visualization of the variables in a dataset"""

    #: The title of the widget
    title = 'Stratigraphic plots'

    #: Display the dock widget at the right side of the GUI
    dock_position = Qt.RightDockWidgetArea

    _animating = False

    _ani = None

    variable_frame = None

    ds_attr_columns = ['long_name', 'dims', 'shape']

    def __init__(self, ds=None, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.ds = ds

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
            "◀◀", self.animate_backward,
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
            "▶▶", self.animate_forward,
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

        # -- Export button
        self.btn_export = QtWidgets.QToolButton()
        self.btn_export.setText('Export')
        self.btn_export.setMenu(self.setup_export_menu())
        self.navigation_box.addWidget(self.btn_export)

        self.addLayout(self.navigation_box)

        # fourth row: plot interface
        self.plot_tabs = QtWidgets.QTabWidget()
        self.setup_plot_tabs()
        self.plot_tabs.currentChanged.connect(self.switch_tab)

        self.addWidget(self.plot_tabs)

        # sixth row: variables
        self.setup_variable_buttons()
        self.addWidget(self.variable_frame)

        # seventh row: dimensions
        self.dimension_table = QtWidgets.QTableWidget()
        self.addWidget(self.dimension_table)

        self.disable_navigation()

        self.cids = {}

    def setup_ds_tree(self):
        self.ds_tree = tree = QtWidgets.QTreeWidget()
        tree.setColumnCount(len(self.ds_attr_columns) + 1)
        tree.setHeaderLabels([''] + self.ds_attr_columns)

    def excepthook(self, type, value, traceback):
        """A method to replace the sys.excepthook"""
        self.error_msg.excepthook(type, value, traceback)

    def change_ds(self, ds_item):
        ds_items = self.ds_items
        if ds_item in ds_items:
            with self.block_tree():
                self.ds = ds_item.ds()
                self.expand_ds_item(ds_item)
                self.setup_variable_buttons()
                self.refresh()

    def expand_ds_item(self, ds_item):
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

    def _open_dataset(self):
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
            return
        ds = psyd.open_dataset(fname)
        return ds

    @contextlib.contextmanager
    def block_tree(self):
        self.ds_tree.blockSignals(True)
        yield
        self.ds_tree.blockSignals(False)

    def set_dataset(self, ds=None):
        """Ask for a file name and open the dataset."""
        if ds is None:
            ds = self._open_dataset()
        if ds is None:
            return
        self.ds = ds
        with self.block_tree():
            self.add_ds_item()
            self.setup_variable_buttons()

    def add_ds_item(self):
        ds = self.ds
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

    @property
    def ds_items(self):
        tree = self.ds_tree
        return list(map(tree.topLevelItem, range(tree.topLevelItemCount())))

    @property
    def ds_item(self):
        tree = self.ds_tree
        ds = self.ds
        for item in self.ds_items:
            if item.ds() is ds:
                return item

    def expand_current_variable(self):
        tree = self.ds_tree
        top = self.ds_item
        tree.expandItem(top)
        tree.expandItem(top.child(0))
        for var_item in map(top.child(0).child,
                            range(top.child(0).childCount())):
            if var_item.text(0) == self.variable:
                tree.expandItem(var_item)
            else:
                tree.collapseItem(var_item)

    def setup_variable_buttons(self, ncols=4):
        variable_frame = QtWidgets.QGroupBox('Variables')

        if self.variable_frame is not None:
            self.replaceWidget(self.indexOf(self.variable_frame),
                               variable_frame)
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

    def load_variable_desc(self, item):
        # if we are not at the lowest level or the item has already label, pass
        if item.child(0).childCount() or self.ds_tree.itemWidget(
                item.child(0), 0):
            return

        top = item
        while top.parent() and top.parent() is not self.ds_tree:
            top = top.parent()
        ds = top.ds()
        if ds is None:
            return
        widget = QtWidgets.QScrollArea()
        label = QtWidgets.QLabel(
            '<pre>' + escape_html(str(ds.variables[item.text(0)])) + '</pre>')
        label.setTextFormat(Qt.RichText)
        widget.setWidget(label)
        self.ds_tree.setItemWidget(item.child(0), 0, widget)
        item.child(0).setFirstColumnSpanned(True)

    def clear_table(self):
        self.dimension_table.clear()
        self.dimension_table.setColumnCount(5)
        self.dimension_table.setHorizontalHeaderLabels(
            ['Type', 'First', 'Current', 'Last', 'Units'])
        self.dimension_table.setRowCount(0)

    def addLayout(self, layout):
        widget = QtWidgets.QWidget()
        widget.setLayout(layout)
        self.addWidget(widget)
        return widget

    def go_to_previous_step(self):
        dim = self.combo_dims.currentText()
        self.increase_dim(dim, -1)()

    def go_to_next_step(self):
        dim = self.combo_dims.currentText()
        self.increase_dim(dim)()

    def animate_backward(self):
        if self._animating:
            self.stop_animation()
            self.btn_animate_backward.setText('◀◀')
            self.enable_navigation()
        else:
            self._animate_forward = False
            self.btn_animate_backward.setText('■')
            self.disable_navigation(self.btn_animate_backward)
            self.start_animation()

    def animate_forward(self, event=None):
        if self._animating:
            self.stop_animation()
            self.btn_animate_forward.setText('▶▶')
            self.enable_navigation()
        else:
            self._animate_forward = True
            self.btn_animate_forward.setText('■')
            self.disable_navigation(self.btn_animate_forward)
            self.start_animation()

    def setup_plot_tabs(self):
        self.plot_tabs.addTab(MapPlotWidget(self.get_sp, self.ds), 'mapplot')
        self.plot_tabs.addTab(Plot2DWidget(self.get_sp, self.ds), 'plot2d')
        lineplot_widget = LinePlotWidget(self.get_sp, self.ds)
        self.plot_tabs.addTab(lineplot_widget, 'lineplot')

        for w in map(self.plot_tabs.widget, range(self.plot_tabs.count())):
            w.replot.connect(self.replot)
            w.reset.connect(self.reset)
            w.changed.connect(self.refresh)

    def replot(self, plotmethod):
        self.plotmethod = plotmethod
        self.make_plot()
        self.refresh()

    def reset(self, plotmethod):
        self.plotmethod = plotmethod
        self.close_sp()
        self.make_plot()
        self.refresh()

    def disable_navigation(self, but=None):
        for item in map(self.navigation_box.itemAt,
                        range(self.navigation_box.count())):
            w = item.widget()
            if w is not but and w is not self.sl_interval:
                w.setEnabled(False)

    def enable_navigation(self):
        for item in map(self.navigation_box.itemAt,
                        range(self.navigation_box.count())):
            w = item.widget()
            w.setEnabled(True)

    def disable_variables(self):
        for btn in self.variable_buttons.values():
            btn.setEnabled(False)

    def enable_variables(self):
        for btn in self.variable_buttons.values():
            btn.setEnabled(True)

    def start_animation(self):
        self._animating = True
        self.disable_variables()
        self.plot_tabs.setEnabled(False)
        if self.animation is None or self.animation.event_source is None:
            self.animation = FuncAnimation(
                self.fig, self.update_dims, frames=self.animation_frames(),
                init_func=self.sp.draw, interval=self.sl_interval.value())
            # HACK: Make sure that the animation starts although the figure
            # is already shown
            self.animation._draw_frame(next(self.animation_frames()))
        else:
            self.animation.event_source.start()

    def reset_timer_interval(self, value):
        self.lbl_interval.setText('%i ms' % value)
        if self.animation is None or self.animation.event_source is None:
            pass
        else:
            self.animation.event_source.stop()
            self.animation._interval = value
            self.animation.event_source.interval = value
            self.animation.event_source.start()

    def stop_animation(self):
        self._animating = False
        try:
            self.animation.event_source.stop()
        except AttributeError:
            pass
        self.plot_tabs.setEnabled(True)
        self.enable_variables()
        self.refresh()

    def animation_frames(self):
        while self._animating:
            dim = self.combo_dims.currentText()
            i = self.data.psy.idims[dim]
            imax = self.ds.dims[dim] - 1
            if self._animate_forward:
                i += -i if i == imax else 1
            else:
                i += imax if i == 0 else -1
            yield {dim: i}

    def update_dims(self, dims):
        self.sp.update(dims=dims)

    def setup_export_menu(self):
        self.export_menu = menu = QtWidgets.QMenu()
        menu.addAction('image (PDF, PNG, etc.)', self.export_image)
        menu.addAction('animation (GIF, MP4, etc.', self.export_animation)
        menu.addAction('psyplot project (.pkl file)', self.export_project)
        menu.addAction('psyplot project with data',
                       self.export_project_with_data)
        menu.addAction('python script (.py)', self.export_python)
        return menu

    def export_image(self):
        fname, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export image", os.getcwd(),
            "Images (*.png *.pdf *.jpg *.svg)")
        if ok:
            self.sp.export(fname, rcParams['savefig_kws'])

    def export_animation(self):
        fname, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export animation", os.getcwd(),
            "Movie (*.mp4 *.mov *.gif)")
        if ok:
            self.animate_forward()
            self.animation.save(fname, **rcParams['animations.export_kws'],
                           fps=round(1000. / self.sl_interval.value()))
            self.animate_forward()

    def export_project(self):
        fname, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export project", os.getcwd(),
            "Psyplot projects (*.pkl)")
        if ok:
            self.sp.save_project(fname)

    def export_project_with_data(self):
        fname, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export project", os.getcwd(),
            "Psyplot projects (*.pkl)")
        if ok:
            self.sp.save_project(fname, ds_description={"ds"})

    def export_python(self):
        pass

    def _draw_variable(self, v):
        def func():
            """Visualize variable v"""
            btn = self.variable_buttons[v]
            if not btn.isChecked():
                self.close_sp()
            else:
                with self.silence_variable_buttons():
                    for var, btn in self.variable_buttons.items():
                        if var != v:
                            btn.setChecked(False)
                self.make_plot()
            self.refresh()

        return func

    @contextlib.contextmanager
    def silence_variable_buttons(self):
        for btn in self.variable_buttons.values():
            btn.blockSignals(True)
        yield
        for btn in self.variable_buttons.values():
            btn.blockSignals(False)

    @property
    def variable(self):
        """The current variable"""
        for v, btn in self.variable_buttons.items():
            if btn.isChecked():
                return v
        return NOTSET

    @variable.setter
    def variable(self, value):
        with self.silence_variable_buttons():
            for v, btn in self.variable_buttons.items():
                btn.setChecked(v == value)

    @property
    def available_plotmethods(self):
        v = self.variable
        if v is NOTSET:
            return []
        ret = []
        plot = self.ds.psy.plot
        for plotmethod in self.plotmethods:
            if plotmethod in plot._plot_methods:
                if getattr(plot, plotmethod).check_data(self.ds, v, {})[0]:
                    ret.append(plotmethod)
        return ret

    @property
    def plot(self):
        return getattr(self.ds.psy.plot, self.plotmethod)

    @property
    def plot_options(self):
        return self.plotmethod_widget.get_fmts(
            self.ds.psy[self.variable], True)

    @property
    def plotmethod(self):
        return self.plot_tabs.tabText(self.plot_tabs.currentIndex())

    @plotmethod.setter
    def plotmethod(self, label):
        i = next((i for i in range(self.plot_tabs.count())
                  if self.plot_tabs.tabText(i) == label), None)
        if i is not None:
            self.plot_tabs.setCurrentIndex(i)

    @property
    def plotmethods(self):
        return list(map(self.plot_tabs.tabText, range(self.plot_tabs.count())))

    @property
    def plotmethod_widget(self):
        label = self.plotmethod
        i = next((i for i in range(self.plot_tabs.count())
                  if self.plot_tabs.tabText(i) == label), None)
        return self.plot_tabs.widget(i)

    @property
    def plotmethod_widgets(self):
        return dict(zip(self.plotmethods, map(self.plot_tabs.widget,
                                              range(self.plot_tabs.count()))))

    _sp = None

    def get_sp(self):
        if self._sp is None:
            return self._sp
        return self.filter_sp(self._sp)

    def filter_sp(self, sp):
        """Filter the psyplot project to only include the arrays of :attr:`ds`
        """
        if self.ds is None:
            return sp
        num = self.ds.psy.num
        ret = sp[:0]
        for i in range(len(sp)):
            if list(sp[i:i+1].datasets) == [num]:
                ret += sp[i:i+1]
        return ret

    @property
    def sp(self):
        return self.plotmethod_widget.sp or None

    @sp.setter
    def sp(self, sp):
        if sp is None and (not self._sp or not not getattr(
                self._sp, self.plotmethod)):
            pass
        else:
            # first remove the current arrays
            if self._sp and getattr(self._sp, self.plotmethod):
                to_remove = getattr(self.get_sp(), self.plotmethod).arr_names
                for i in list(reversed(range(len(self._sp)))):
                    if self._sp[i].psy.arr_name in to_remove:
                        self._sp.pop(i)
            # then add the new arrays
            if sp:
                if self._sp:
                    self._sp.extend(list(sp), new_name=True)
                else:
                    self._sp = sp

    @property
    def data(self):
        return self.plotmethod_widget.data

    @property
    def plotter(self):
        return self.plotmethod_widget.plotter

    @property
    def fig(self):
        if self.sp:
            return list(self.sp.figs)[0]

    _animations = {}

    @property
    def animation(self):
        return self._animations.get(self.plotmethod)

    @animation.setter
    def animation(self, ani):
        if ani is None:
            self._animations.pop(self.plotmethod, None)
        else:
            self._animations[self.plotmethod] = ani

    def make_plot(self):
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
        fmts = {}
        dims = {}
        if self.sp:
            if not set(self.data.dims) <= set(self.ds[new_v].dims):
                self.close_sp()
            else:
                for dim in set(self.ds[new_v].dims) - set(self.data.psy.idims):
                    dims[dim] = 0
                for dim in set(self.data.psy.idims) - set(self.ds[new_v].dims):
                    del self.data.psy.idims[dim]
        if self.sp:
            if self.data.psy.plotter is None:
                self.data.psy.update(name=self.variable)
                self.data.psy.update(dims=dims, **fmts)
                self.sp.update(replot=True)
            else:
                self.sp.update(name=self.variable, dims=dims, **fmts)
            self.show_fig()
        else:
            self.ani = None
            self.sp = sp = self.plot(name=self.variable, **self.plot_options)
            cid = sp.plotters[0].ax.figure.canvas.mpl_connect(
                'button_press_event', self.display_line)
            self.cids[self.plotmethod] = cid
            self.show_fig()
        self.expand_current_variable()
        self.enable_navigation()

    def display_line(self, event):
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
                raw_data.ndim == 2):
                return
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


    def close_sp(self):
        self.sp.close(figs=True, data=True, ds=False)
        self.sp = None

    def show_fig(self):
        try:
            self.fig.canvas.window().show()
        except AttributeError:
            self.sp.show()

    def switch_tab(self):
        with self.silence_variable_buttons():
            if self.sp:
                name = self.data.name
            else:
                name = NOTSET
            for v, btn in self.variable_buttons.items():
                btn.setChecked(v == name)
        self.refresh()

    def refresh(self):
        self.clear_table()
        if self.sp:
            variable = self.data.name
        else:
            variable = self.variable

        # refresh variable buttons
        with self.silence_variable_buttons():
            for v, btn in self.variable_buttons.items():
                btn.setChecked(v == variable)

        # refresh tabs
        for i in range(self.plot_tabs.count()):
            w = self.plot_tabs.widget(i)
            w.refresh(self.ds)
        valid_variables = self.plotmethod_widget.valid_variables(self.ds)
        for v, btn in self.variable_buttons.items():
            btn.setEnabled(v in valid_variables)
        if variable is NOTSET or not self.sp:
            return

        data = self.data
        ds_data = self.ds[self.variable]

        with self.silence_variable_buttons():
            self.variable_buttons[self.variable].setChecked(True)

        table = self.dimension_table
        dims = ds_data.dims
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
                coord = list(map("{:1.4f}".format, coord.values))
            except (ValueError, TypeError):
                try:
                    coord = coord.to_pandas().dt.to_pydatetime()
                except AttributeError:
                    coord = list(map(str, coord.values))
                else:
                    coord = [t.isoformat() for t in coord]
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

        table.resizeColumnsToContents()

        # update animation checkbox
        dims_to_animate = get_dims_to_iterate(data)

        current_dims_to_animate = list(map(
            self.combo_dims.itemText,
            range(self.combo_dims.count())))
        if dims_to_animate != current_dims_to_animate:
            self.combo_dims.clear()
            self.combo_dims.addItems(dims_to_animate)

    def new_dimension_button(self, dim, label):
        btn = utils.QRightPushButton(label)
        btn.clicked.connect(self.increase_dim(dim))
        btn.rightclicked.connect(self.increase_dim(dim, -1))
        btn.setToolTip(f"Increase dimension {dim} with left-click, and "
                       "decrease with right-click.")
        return btn

    def update_project(self, *args, **kwargs):
        self.sp.update(*args, **kwargs)
        self.refresh()

    def increase_dim(self, dim, increase=1):
        def update():
            i = self.data.psy.idims[dim]
            self.data.psy.update(dims={dim: (i+increase) % self.ds.dims[dim]})
            if self.data.psy.plotter is None:
                self.sp.update(replot=True)
            self.refresh()
        return update


class PlotMethodWidget(QtWidgets.QWidget):

    plotmethod = NOTSET

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

    layout = None

    def __init__(self, get_sp, ds):
        super().__init__()
        self._get_sp = get_sp

        self.setup()

        if self.layout is not None:
            self.setLayout(self.layout)

        self.refresh(ds)

    def setup(self):
        pass

    @property
    def sp(self):
        return getattr(self._get_sp(), self.plotmethod, None)

    @property
    def data(self):
        return self.sp[0]

    @property
    def plotter(self):
        try:
            return self.sp.plotters[0]
        except (IndexError, AttributeError):
            return None

    @property
    def formatoptions(self):
        if self.plotter is not None:
            return list(self.plotter)
        else:
            import psyplot.project as psy
            return list(getattr(psy.plot, self.plotmethod).plotter_cls())

    def get_fmts(self, var, init=False):
        ret = {}
        if init:
            ret.update(self.init_dims(var))
        return ret

    def init_dims(self, var):
        return {}

    def refresh(self, ds):
        self.setEnabled(bool(self.sp))

    def trigger_replot(self):
        self.replot.emit(self.plotmethod)

    def trigger_reset(self):
        self.array_info = self.sp.array_info(
            standardize_dims=False)[self.sp[0].psy.arr_name]
        self.reset.emit(self.plotmethod)

    def trigger_refresh(self):
        self.changed.emit(self.plotmethod)

    def get_slice(self, x, y):
        return None

    def valid_variables(self, ds):
        return list(ds)


class MapPlotWidget(PlotMethodWidget):

    plotmethod = 'mapplot'

    def setup(self):
        self.layout = vbox = QtWidgets.QVBoxLayout()

        self.formatoptions_box = QtWidgets.QHBoxLayout()
        self.setup_color_buttons()
        self.setup_projection_buttons()
        self.btn_labels = utils.add_pushbutton(
            "Labels", self.edit_labels, "Edit title, colorbar labels, etc.",
            self.formatoptions_box)

        vbox.addLayout(self.formatoptions_box)

        self.dimension_box = QtWidgets.QGridLayout()
        self.setup_dimension_box()

        vbox.addLayout(self.dimension_box)

    def setup_color_buttons(self):
        self.btn_cmap = utils.add_pushbutton(
            rcParams["cmaps"][0], self.choose_next_colormap,
            "Select a different colormap", self.formatoptions_box)

        self.btn_cmap_settings = utils.add_pushbutton(
            get_icon('color_settings'), self.edit_color_settings,
            "Edit color settings", self.formatoptions_box,
            icon=True)

    def setup_projection_menu(self):
        menu = QtWidgets.QMenu()
        for projection in rcParams['projections']:
            menu.addAction(
                projection, partial(self.set_projection, projection))
        menu.addSeparator()
        self.proj_settings_action = menu.addAction(
            QtGui.QIcon(get_icon('proj_settings')), "Customize basemap...",
            self.edit_basemap_settings)
        return menu

    def setup_projection_buttons(self):
        self.btn_proj = utils.add_pushbutton(
            rcParams["projections"][0], self.choose_next_projection,
            "Change the basemap projection", self.formatoptions_box,
            toolbutton=True)
        self.btn_proj.setMenu(self.setup_projection_menu())
        max_width = max(map(self.btn_proj.fontMetrics().width,
                            rcParams['projections'])) * 2
        self.btn_proj.setMinimumWidth(max_width)
        self.btn_proj.setPopupMode(QtWidgets.QToolButton.MenuButtonPopup)

        self.btn_proj_settings = utils.add_pushbutton(
            get_icon('proj_settings'), self.edit_basemap_settings,
            "Edit basemap settings", self.formatoptions_box,
            icon=True)

        self.btn_datagrid = utils.add_pushbutton(
            "Cells", self.toggle_datagrid,
            "Show the grid cell boundaries", self.formatoptions_box)
        self.btn_datagrid.setCheckable(True)

    def setup_dimension_box(self):
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

    def set_xcoord(self, text):
        self.set_combo_text(self.combo_xcoord, text)

    def set_ycoord(self, text):
        self.set_combo_text(self.combo_ycoord, text)

    def set_combo_text(self, combo, text):
        items = list(map(combo.itemText, range(combo.count())))
        if text in items:
            combo.setCurrentIndex(items.index(text))

    def init_dims(self, var):
        ret = super().init_dims(var)

        dims = {}
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
            if len(dims) == 1:
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

        if xdim is not None and xdim in var.dims:
            ret['transpose'] = var.dims.index(xdim) < var.dims.index(ydim)

        return ret

    def valid_variables(self, ds):
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
    def coord_combos(self):
        return [self.combo_xdim, self.combo_ydim, self.combo_xcoord,
                self.combo_ycoord]

    @contextlib.contextmanager
    def block_combos(self):
        for combo in self.coord_combos:
            combo.blockSignals(True)
        yield
        for combo in self.coord_combos:
            combo.blockSignals(False)

    def setEnabled(self, b):
        self.btn_proj_settings.setEnabled(b)
        self.proj_settings_action.setEnabled(b)
        self.btn_datagrid.setEnabled(b)
        self.btn_cmap_settings.setEnabled(b)
        self.btn_labels.setEnabled(b)

    def choose_next_colormap(self):
        select = False
        nmaps = len(rcParams['cmaps'])
        current = self.btn_cmap.text()
        if self.sp and 'cmap' in self.sp.plotters[0]:
            invert_cmap = self.plotter.cmap.value.endswith('_r')
        else:
            invert_cmap = False
        for i, cmap in enumerate(cycle(rcParams['cmaps'])):
            if cmap == current:
                select = True
            elif select or i == nmaps:
                break
        self.btn_cmap.setText(cmap)
        if invert_cmap:
            cmap = cmap + '_r'
        if self.sp and 'cmap' in self.sp.plotters[0]:
            self.plotter.update(cmap=cmap)

    def toggle_datagrid(self):
        if self.btn_datagrid.isChecked():
            self.plotter.update(datagrid='k--')
        else:
            self.plotter.update(datagrid=None)

    def edit_labels(self):
        LabelDialog.update_project(self.sp, 'figtitle', 'title', 'clabel')

    def edit_color_settings(self):
        CmapDialog.update_plotter(self.plotter)

    def choose_next_projection(self):
        select = False
        nprojections = len(rcParams['projections'])
        current = self.btn_proj.text()
        for i, proj in enumerate(cycle(rcParams['projections'])):
            if proj == current:
                select = True
            elif select or i == nprojections:
                break
        self.set_projection(proj)

    def set_projection(self, proj):
        self.btn_proj.setText(proj)
        if self.sp and 'projection' in self.sp.plotters[0]:
            self.plotter.update(projection=proj)

    def edit_basemap_settings(self):
        BasemapDialog.update_plotter(self.plotter)

    def get_fmts(self, var, init=False):
        fmts = {}

        fmts['cmap'] = self.btn_cmap.text()

        if 'projection' in self.formatoptions:
            fmts['projection'] = self.btn_proj.text()

        if 'time' in var.dims:
            fmts['title'] = '%(time)s'

        if 'long_name' in var.attrs:
            fmts['clabel'] = '%(long_name)s'
        else:
            fmts['clabel'] = '%(name)s'
        if 'units' in var.attrs:
            fmts['clabel'] += ' %(units)s'

        if init:
            fmts.update(self.init_dims(var))

        return fmts

    def refresh(self, ds):
        self.setEnabled(bool(self.sp))

        auto = 'Set automatically'

        self.refresh_from_sp()

        with self.block_combos():

            if ds is None:
                ds = xr.Dataset()

            current_dims = set(map(
                self.combo_xdim.itemText, range(1, self.combo_xdim.count())))
            ds_dims = list(dim for dim, n in ds.dims.items() if n > 1)
            if current_dims != set(ds_dims):
                self.combo_xdim.clear()
                self.combo_ydim.clear()
                self.combo_xdim.addItems([auto] + ds_dims)
                self.combo_ydim.addItems([auto] + ds_dims)

            current_coords = set(map(
                self.combo_xcoord.itemText, range(1, self.combo_xcoord.count())))
            ds_coords = list(c for c, arr in ds.coords.items() if arr.ndim)
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

    def refresh_from_sp(self):
        if self.sp:
            plotter = self.plotter
            if isinstance(plotter.projection.value, str):
                self.btn_proj.setText(plotter.projection.value)
            if isinstance(plotter.cmap.value, str):
                self.btn_cmap.setText(plotter.cmap.value)

    def transform(self, x, y):
        import cartopy.crs as ccrs
        import numpy as np
        x, y = self.plotter.transform.projection.transform_point(
            x, y, self.plotter.ax.projection)
        # shift if necessary
        if isinstance(self.plotter.transform.projection, ccrs.PlateCarree):
            coord = self.plotter.plot.xcoord
            if coord.min() >= 0 and x < 0:
                x -= 360
            elif coord.max() <= 180 and x > 180:
                x -= 360
            if 'rad' in coord.attrs.get('units', '').lower():
                x = np.deg2rad(x)
                y = np.deg2rad(y)
        return x, y

    def get_slice(self, x, y):
        import numpy as np
        data = self.data.psy.base.psy[self.data.name]
        x, y =  self.transform(x, y)
        fmto = self.plotter.plot

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
            x = xcoord.indexes[xcoord.name].get_loc(x, method='nearest')
            y = ycoord.indexes[ycoord.name].get_loc(y, method='nearest')
            return dict(zip(data.dims[-2:], [y, x]))


class DatasetWidgetPlugin(DatasetWidget, DockMixin):

    #: The title of the widget
    title = 'psy-view Dataset viewer'

    #: Display the dock widget at the right side of the GUI
    dock_position = Qt.RightDockWidgetArea

    @property
    def _sp(self):
        import psyplot.project as psy
        return psy.gcp()

    @_sp.setter
    def _sp(self, value):
        pass

    @property
    def sp(self):
        return self.plotmethod_widget.sp or None

    @sp.setter
    def sp(self, sp):
        current = self.get_sp()
        if sp is None:
            return
        if getattr(current, self.plotmethod):

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

    def setup_ds_tree(self):
        self.ds_tree = tree = DatasetTree()
        tree.setColumnCount(len(self.ds_attr_columns) + 1)
        tree.setHeaderLabels([''] + self.ds_attr_columns)

    def position_dock(self, main, *args, **kwargs):
        height = main.help_explorer.dock.size().height()
        main.splitDockWidget(main.help_explorer.dock, self.dock, Qt.Vertical)
        if hasattr(main, 'resizeDocks'):  # qt >= 5.6
            main.resizeDocks([main.help_explorer.dock, self.dock],
                             [height // 2, height // 2], Qt.Vertical)


class Plot2DWidget(MapPlotWidget):

    plotmethod = 'plot2d'

    def setup_projection_buttons(self):
        self.btn_datagrid = utils.add_pushbutton(
            "Cells", self.toggle_datagrid,
            "Show the grid cell boundaries", self.formatoptions_box)
        self.btn_datagrid.setCheckable(True)

    def setEnabled(self, b):
        self.btn_datagrid.setEnabled(b)
        self.btn_cmap_settings.setEnabled(b)
        self.btn_labels.setEnabled(b)

    def edit_labels(self):
        LabelDialog.update_project(
            self.sp, 'figtitle', 'title', 'clabel', 'xlabel', 'ylabel')

    def transform(self, x, y):
        return x, y

    def refresh_from_sp(self):
        if self.sp:
            plotter = self.plotter
            if isinstance(plotter.cmap.value, str):
                self.btn_cmap.setText(plotter.cmap.value)


class LinePlotWidget(PlotMethodWidget):

    plotmethod = 'lineplot'

    def setup(self):
        self.layout = self.formatoptions_box = QtWidgets.QHBoxLayout()

        # TODO: Implement a button to choose the dimension
        self.formatoptions_box.addWidget(QtWidgets.QLabel('x-Dimension:'))
        self.combo_dims = QtWidgets.QComboBox()
        self.combo_dims.setEditable(False)
        self.combo_dims.currentIndexChanged.connect(self.trigger_reset)
        self.formatoptions_box.addWidget(self.combo_dims)

        self.combo_lines = QtWidgets.QComboBox()
        self.combo_lines.setEditable(False)
        self.formatoptions_box.addWidget(self.combo_lines)
        self.combo_lines.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToContents)
        self.formatoptions_box.addStretch(0)

        self.btn_add = utils.add_pushbutton(
            QtGui.QIcon(get_psy_icon('plus')), lambda: self.add_line(),
            "Add a line to the plot", self.formatoptions_box, icon=True)
        self.btn_del = utils.add_pushbutton(
            QtGui.QIcon(get_psy_icon('minus')), self.remove_line,
            "Add a line to the plot", self.formatoptions_box, icon=True)

        self.btn_labels = utils.add_pushbutton(
            "Labels", self.edit_labels,
            "Edit title, x-label, legendlabels, etc.", self.formatoptions_box)

    @property
    def xdim(self):
        return self.combo_dims.currentText()

    @xdim.setter
    def xdim(self, xdim):
        if xdim != self.combo_dims.currentText():
            self.combo_dims.setCurrentText(xdim)

    @property
    def data(self):
        data = super().data
        if len(data) - 1 < self.combo_lines.currentIndex():
            return data[0]
        else:
            return data[self.combo_lines.currentIndex()]

    def add_line(self, name=None, **sl):
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

    def remove_line(self):
        i = self.combo_lines.currentIndex()
        self.sp[0].pop(i)
        self.sp.update(replot=True)
        self.combo_lines.setCurrentText(self.item_texts[i - 1 if i else 0])
        self.changed.emit(self.plotmethod)

    @property
    def item_texts(self):
        return [f'Line {i}: {arr.psy._short_info()}'
                for i, arr in enumerate(self.sp[0])]

    def init_dims(self, var):
        ret = {}
        xdim = self.xdim or next((d for d in var.dims if var[d].size > 1),
                                 None)
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

    def edit_labels(self):
        LabelDialog.update_project(
            self.sp, 'figtitle', 'title', 'xlabel', 'ylabel', 'legendlabels')

    @contextlib.contextmanager
    def block_combos(self):
        self.combo_dims.blockSignals(True)
        self.combo_lines.blockSignals(True)
        yield
        self.combo_dims.blockSignals(False)
        self.combo_lines.blockSignals(False)

    def valid_variables(self, ds):
        valid = super().valid_variables(ds)
        if not self.sp or len(self.sp[0]) < 2:
            return valid
        else:
            current_dim = self.combo_dims.currentText()
            return [v for v in valid if current_dim in ds[v].dims]

    def refresh(self, ds):
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
                self.combo_lines.addItems(descriptions)
                if current < len(descriptions):
                    self.combo_lines.setCurrentText(descriptions[current])
        else:
            with self.block_combos():
                self.combo_dims.clear()
                self.combo_lines.clear()
        self.btn_add.setEnabled(bool(self.sp))
        self.btn_del.setEnabled(bool(self.sp) and len(self.sp[0]) > 1)


class BasemapDialog(QtWidgets.QDialog):
    """A dialog to modify the basemap settings"""

    def __init__(self, plotter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self)
        vbox = QtWidgets.QVBoxLayout(self)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        proj_box = QtWidgets.QGroupBox("Projection settings")
        layout = QtWidgets.QFormLayout(proj_box)

        self.txt_clon = QtWidgets.QLineEdit()
        self.txt_clon.setPlaceholderText('auto')
        self.txt_clon.setToolTip('Central longitude in degrees East')
        self.txt_clon.setValidator(QtGui.QDoubleValidator(-360, 360, 7))
        layout.addRow('Central longitude: ', self.txt_clon)

        self.txt_clat = QtWidgets.QLineEdit()
        self.txt_clat.setPlaceholderText('auto')
        self.txt_clat.setToolTip('Central latitude in degrees North')
        self.txt_clat.setValidator(QtGui.QDoubleValidator(-90, 90, 7))
        layout.addRow('Central latitude: ', self.txt_clat)

        vbox.addWidget(proj_box)

        self.lsm_box = QtWidgets.QGroupBox('Coastlines')
        self.lsm_box.setCheckable(True)
        hbox = QtWidgets.QHBoxLayout(self.lsm_box)
        hbox.addWidget(QtWidgets.QLabel("Resolution:"))
        self.opt_110 = QtWidgets.QRadioButton("110m")
        self.opt_50 = QtWidgets.QRadioButton("50m")
        self.opt_10 = QtWidgets.QRadioButton("10m")
        hbox.addWidget(self.opt_110)
        hbox.addWidget(self.opt_50)
        hbox.addWidget(self.opt_10)

        vbox.addWidget(self.lsm_box)

        self.meridionals_box = QtWidgets.QGroupBox('Meridionals')
        self.meridionals_box.setCheckable(True)
        self.opt_meri_auto = QtWidgets.QRadioButton("auto")

        self.opt_meri_at = QtWidgets.QRadioButton("At:")
        self.txt_meri_at = QtWidgets.QLineEdit()
        self.txt_meri_at.setPlaceholderText("30, 60, 90, 120, ... °E")
        # TODO: Add validator

        self.opt_meri_every = QtWidgets.QRadioButton("Every:")
        self.txt_meri_every = QtWidgets.QLineEdit()
        self.txt_meri_every.setPlaceholderText("30 °E")
        self.txt_meri_every.setValidator(QtGui.QDoubleValidator(-360, 360, 7))

        self.opt_meri_num = QtWidgets.QRadioButton("Number:")
        self.txt_meri_num = QtWidgets.QLineEdit()
        self.txt_meri_num.setPlaceholderText("5")
        self.txt_meri_num.setValidator(QtGui.QIntValidator(1, 360))

        form = QtWidgets.QFormLayout(self.meridionals_box)
        form.addRow(self.opt_meri_auto)
        form.addRow(self.opt_meri_at, self.txt_meri_at)
        form.addRow(self.opt_meri_every, self.txt_meri_every)
        form.addRow(self.opt_meri_num, self.txt_meri_num)

        vbox.addWidget(self.meridionals_box)

        self.parallels_box = QtWidgets.QGroupBox('Parallels')
        self.parallels_box.setCheckable(True)
        self.opt_para_auto = QtWidgets.QRadioButton("auto")

        self.opt_para_at = QtWidgets.QRadioButton("At:")
        self.txt_para_at = QtWidgets.QLineEdit()
        self.txt_para_at.setPlaceholderText("-60, -30, 0, 30, ... °N")
        # TODO: Add validator

        self.opt_para_every = QtWidgets.QRadioButton("Every:")
        self.txt_para_every = QtWidgets.QLineEdit()
        self.txt_para_every.setPlaceholderText("30 °N")
        self.txt_para_every.setValidator(QtGui.QDoubleValidator(-90, 90, 7))

        self.opt_para_num = QtWidgets.QRadioButton("Number:")
        self.txt_para_num = QtWidgets.QLineEdit()
        self.txt_para_num.setPlaceholderText("5")
        self.txt_para_num.setValidator(QtGui.QIntValidator(1, 180))

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

    def fill_from_plotter(self, plotter):
        if plotter.clon.value is not None:
            self.txt_clon.setText(str(plotter.clon.value))
        if plotter.clat.value is not None:
            self.txt_clat.setText(str(plotter.clat.value))

        if not plotter.lsm.value[0]:
            self.lsm_box.setChecked(False)
        else:
            try:
                res = plotter.lsm.value[0][:-1]
            except TypeError:
                res = '110'
            getattr(self, 'opt_' + res).setChecked(True)

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
            self.xgrid_value = value[:2]
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
            self.ygrid_value = value[:2]
            self.opt_para_num.setChecked(True)
            steps = 11 if len(value) == 2 else value[3]
            self.txt_para_num.setText(str(steps))
        else:
            self.opt_para_at.setChecked(True)
            self.txt_para_at.setText(', '.join(map(str, value)))

    def update_forms(self):
        if self.meridionals_box.isChecked():
            self.txt_meri_at.setEnabled(self.opt_meri_at.isChecked())
            self.txt_meri_every.setEnabled(self.opt_meri_every.isChecked())
            self.txt_meri_num.setEnabled(self.opt_meri_num.isChecked())
        if self.parallels_box.isChecked():
            self.txt_para_at.setEnabled(self.opt_para_at.isChecked())
            self.txt_para_every.setEnabled(self.opt_para_every.isChecked())
            self.txt_para_num.setEnabled(self.opt_para_num.isChecked())

    @property
    def value(self):
        import numpy as np
        ret = {}
        ret['clon'] = None if not self.txt_clon.text().strip() else float(
            self.txt_clon.text().strip())
        ret['clat'] = None if not self.txt_clat.text().strip() else float(
            self.txt_clat.text().strip())

        if self.lsm_box.isChecked():
            if self.opt_110.isChecked():
                ret['lsm'] = '110m'
            elif self.opt_50.isChecked():
                ret['lsm'] = '50m'
            elif self.opt_10.isChecked():
                ret['lsm'] = '10m'
        else:
            ret['lsm'] = False

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
    def update_plotter(cls, plotter):
        dialog = cls(plotter)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec_()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            plotter.update(
                **dialog.value)


class CmapDialog(QtWidgets.QDialog):
    """A dialog to modify color bounds"""

    def __init__(self, plotter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.tabs = QtWidgets.QTabWidget()
        self.bounds_widget = BoundaryWidget(
            plotter.cmap.value, plotter.bounds.value)
        self.tabs.addTab(self.bounds_widget, "Colormap boundaries")

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.tabs)
        vbox.addWidget(self.button_box)

    @classmethod
    def update_plotter(cls, plotter):
        dialog = cls(plotter)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec_()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            plotter.update(
                **dialog.bounds_widget.value)


class BoundaryWidget(QtWidgets.QWidget):
    """A widget to select colormap boundaries"""

    def __init__(self, cmap_value, init_value, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QtWidgets.QGridLayout(self)

        self.type_box = QtWidgets.QGroupBox()
        vbox = QtWidgets.QVBoxLayout(self.type_box)
        self.opt_rounded = QtWidgets.QRadioButton("Rounded")
        self.opt_minmax = QtWidgets.QRadioButton("Exact")
        self.opt_custom = QtWidgets.QRadioButton("Custom")
        vbox.addWidget(self.opt_rounded)
        vbox.addWidget(self.opt_minmax)
        vbox.addWidget(self.opt_custom)

        layout.addWidget(self.type_box, 0, 0, 3, 1)

        self.min_box = QtWidgets.QGroupBox()
        hbox = QtWidgets.QHBoxLayout(self.min_box)
        self.opt_min = QtWidgets.QRadioButton("Minimum")
        self.opt_min_pctl = QtWidgets.QRadioButton("Percentile")
        self.txt_min_pctl = QtWidgets.QLineEdit()
        self.txt_min_pctl.setValidator(QtGui.QDoubleValidator(0., 100., 5))
        hbox.addWidget(self.opt_min)
        hbox.addWidget(self.opt_min_pctl)
        hbox.addWidget(self.txt_min_pctl)

        layout.addWidget(self.min_box, 0, 1, 1, 2)

        self.max_box = QtWidgets.QGroupBox()
        hbox = QtWidgets.QHBoxLayout(self.max_box)
        self.opt_max = QtWidgets.QRadioButton("Maximum")
        self.opt_max_pctl = QtWidgets.QRadioButton("Percentile")
        self.txt_max_pctl = QtWidgets.QLineEdit()
        self.txt_max_pctl.setValidator(QtGui.QDoubleValidator(0., 100., 5))
        hbox.addWidget(self.opt_max)
        hbox.addWidget(self.opt_max_pctl)
        hbox.addWidget(self.txt_max_pctl)

        layout.addWidget(self.max_box, 1, 1, 1, 2)

        self.txt_custom = QtWidgets.QLineEdit()
        self.txt_custom.setPlaceholderText('1, 2, 3, 4, 5, ...')
        # TODO: Add validator
        layout.addWidget(self.txt_custom, 2, 1, 1, 2)

        self.cb_symmetric = QtWidgets.QCheckBox("symmetric")
        layout.addWidget(self.cb_symmetric, 3, 0)

        self.cb_inverted = QtWidgets.QCheckBox("inverted")
        layout.addWidget(self.cb_inverted, 3, 1)
        self.cb_inverted.setChecked(cmap_value.endswith('_r'))
        self.init_cmap = cmap_value

        self.txt_levels = QtWidgets.QLineEdit()
        self.txt_levels.setInputMask(r"\B\o\u\n\d\s\: 900")
        self.txt_levels.setMaxLength(len('Bounds: 256'))
        layout.addWidget(self.txt_levels)

        self.fill_form(init_value)

        for button in [self.opt_minmax, self.opt_rounded, self.opt_custom,
                       self.opt_min, self.opt_max,
                       self.opt_min_pctl, self.opt_max_pctl]:
            button.clicked.connect(self.update_type)

    def update_type(self):
        custom = self.opt_custom.isChecked()
        self.txt_custom.setEnabled(custom)
        self.opt_min.setEnabled(not custom)
        self.opt_max.setEnabled(not custom)
        self.opt_min_pctl.setEnabled(not custom)
        self.opt_max_pctl.setEnabled(not custom)
        self.txt_min_pctl.setEnabled(self.opt_min_pctl.isChecked())
        self.txt_max_pctl.setEnabled(self.opt_max_pctl.isChecked())

    @property
    def value(self):
        cmap = self.init_cmap
        if self.cb_inverted.isChecked() and not cmap.endswith('_r'):
            cmap = cmap + '_r'
        elif not self.cb_inverted.isChecked() and cmap.endswith('_r'):
            cmap = cmap[:-2]
        if self.opt_custom.isChecked():
            bounds = list(map(float, self.txt_custom.text().split(',')))
            if not bounds:
                bounds = ['rounded', None]
        else:
            if self.opt_minmax.isChecked():
                val = 'minmax' if not self.cb_symmetric.isChecked() else 'sym'
            else:
                val = ('rounded' if not self.cb_symmetric.isChecked() else
                       'roundedsym')
            bounds = [val]
            levels = self.txt_levels.text()[len('Bounds: '):]
            bounds.append(int(levels) if levels.strip() else None)
            bounds.append(0 if self.opt_min.isChecked() else
                          float(self.txt_min_pctl.text().strip() or 0))
            bounds.append(100 if self.opt_max.isChecked() else
                          float(self.txt_max_pctl.text().strip() or 100))

        return {'bounds': bounds, 'cmap': cmap}



    def fill_form(self, value):

        if value[0] == 'rounded' or value[0] == 'roundedsym':
            self.opt_rounded.setChecked(True)
        elif value[0] == 'minmax' or value[0] == 'sym':
            self.opt_minmax.setChecked(True)
        else:
            self.opt_custom.setChecked(True)
            self.txt_custom.setText(', '.join(map(str, value)))
            self.txt_levels.setText('Bounds: %i' % len(value))
            return
        self.txt_levels.setText('Bounds: %s' % (value[1] or ''))
        self.txt_custom.setEnabled(False)

        min_pctl = 0 if len(value) <= 2 else value[2]
        if min_pctl == 0:
            self.opt_min.setChecked(True)
            self.txt_min_pctl.setText('0')
            self.txt_min_pctl.setEnabled(False)
        else:
            self.opt_min_pctl.setChecked(True)
            self.txt_min_pctl.setText(str(min_pctl))

        max_pctl = 100 if len(value) <= 3 else value[3]
        if max_pctl == 100:
            self.opt_max.setChecked(True)
            self.txt_max_pctl.setText('100')
            self.txt_max_pctl.setEnabled(False)
        else:
            self.opt_max_pctl.setChecked(True)
            self.txt_max_pctl.setText(str(max_pctl))

        self.cb_symmetric.setChecked(value[0].endswith('sym'))


class FormatoptionsEditor(QtWidgets.QWidget):
    """A widget to update a formatoption"""

    def __init__(self, fmto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QtWidgets.QHBoxLayout()

        self.line_edit = QtWidgets.QLineEdit()
        layout.addWidget(self.line_edit)
        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setVisible(False)
        layout.addWidget(self.text_edit)

        self.btn_multiline = QtWidgets.QToolButton()
        self.btn_multiline.setText('⌵')
        self.btn_multiline.setCheckable(True)
        self.btn_multiline.setToolTip("Toggle multiline editor")
        self.btn_multiline.clicked.connect(self.toggle_multiline)
        layout.addWidget(self.btn_multiline)

        self.insert_obj(fmto.value)
        self.initial_value = self.line_edit.text()
        self.setLayout(layout)

    def changed(self):
        return self.text != self.initial_value

    def toggle_multiline(self):
        multiline = self.multiline
        self.text_edit.setVisible(multiline)
        self.line_edit.setVisible(not multiline)
        if multiline:
            self.text_edit.setPlainText(self.line_edit.text())
        else:
            self.line_edit.setText(self.text_edit.toPlainText())

    @property
    def multiline(self):
        return self.btn_multiline.isChecked()

    @property
    def text(self):
        return (self.text_edit.toPlainText() if self.multiline else
                self.line_edit.text())

    @property
    def value(self):
        text = self.text
        return yaml.load(text, Loader=yaml.Loader)

    def clear_text(self):
        if self.multiline:
            self.text_edit.clear()
        else:
            self.line_edit.clear()

    def insert_obj(self, obj):
        """Add a string to the formatoption widget"""
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
    """A widget to change the labels"""

    def __init__(self, fmto, project, *args, **kwargs):
        from psy_simple.widgets.texts import LabelWidget
        super().__init__(f'{fmto.name} ({fmto.key})', *args, **kwargs)
        self.editor = FormatoptionsEditor(fmto)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(LabelWidget(self.editor, fmto, project,
                                   properties=False))
        vbox.addWidget(self.editor)
        self.setLayout(vbox)

class LabelDialog(QtWidgets.QDialog):
    """A widget to change labels"""

    def __init__(self, project, *fmts):
        super().__init__()
        self.project = project
        layout = QtWidgets.QVBoxLayout()
        plotter = project.plotters[0]
        self.fmt_widgets = {}
        for fmt in fmts:
            fmto = getattr(plotter, fmt)
            fmt_widget = LabelWidgetLine(fmto, project)
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
    def fmts(self):
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
    def update_project(cls, project, *fmts):
        dialog = cls(project, *fmts)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec_()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            project.update(
                **dialog.fmts)
