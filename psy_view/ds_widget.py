# -*- coding: utf-8 -*-
"""Dataset widget to display the contents of a dataset"""
import os.path as osp
import os
import contextlib
from PyQt5 import QtWidgets, QtGui
from PyQt5.QtCore import Qt
import psy_view.utils as utils
from psyplot_gui.content_widget import (
    DatasetTree, DatasetTreeItem, escape_html)
from psyplot_gui.common import (
    DockMixin, get_icon as get_psy_icon, PyErrorMessage)
import psyplot.data as psyd
from psy_view.rcsetup import rcParams
import psy_view.plotmethods as plotmethods

from matplotlib.animation import FuncAnimation

NOTSET = object


def get_dims_to_iterate(arr):
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
    title = 'Stratigraphic plots'

    #: Display the dock widget at the right side of the GUI
    dock_position = Qt.RightDockWidgetArea

    _animating = False

    _ani = None

    variable_frame = None

    _new_plot = False

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
        self.btn_export.setPopupMode(QtWidgets.QToolButton.InstantPopup)
        self.btn_export.setMenu(self.setup_export_menu())
        self.navigation_box.addWidget(self.btn_export)

        self.addLayout(self.navigation_box)

        # fourth row: array selector

        self.array_frame = QtWidgets.QGroupBox('Current plot')
        hbox = QtWidgets.QHBoxLayout()

        self.combo_array = QtWidgets.QComboBox()
        self.combo_array.setEditable(False)
        self.combo_array.currentIndexChanged.connect(self.refresh)
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
        self.setup_variable_buttons()
        self.addWidget(self.variable_frame)

        # seventh row: dimensions
        self.dimension_table = QtWidgets.QTableWidget()
        self.addWidget(self.dimension_table)

        self.disable_navigation()

        if self.ds is not None:
            self.refresh()

        self.cids = {}

    def setup_ds_tree(self):
        self.ds_tree = tree = QtWidgets.QTreeWidget()
        tree.setColumnCount(len(self.ds_attr_columns) + 1)
        tree.setHeaderLabels([''] + self.ds_attr_columns)

    def close_current_plot(self):
        self.variable_buttons[self.variable].click()

    def excepthook(self, type, value, traceback):
        """A method to replace the sys.excepthook"""
        self.error_msg.excepthook(type, value, traceback)

    @property
    def arr_name(self):
        if not self.combo_array.count():
            return None
        else:
            return self.combo_array.currentText().split(':')[0]

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
            self.btn_add.setEnabled(True)
            self.btn_del.setEnabled(True)

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

    def expand_current_variable(self, variable=None):
        tree = self.ds_tree
        top = self.ds_item
        tree.expandItem(top)
        tree.expandItem(top.child(0))
        if variable is None:
            variable = self.variable
        for var_item in map(top.child(0).child,
                            range(top.child(0).childCount())):
            if var_item.text(0) == variable:
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
        self.plot_tabs.addTab(plotmethods.MapPlotWidget(self.get_sp, self.ds),
                              'mapplot')
        self.plot_tabs.addTab(plotmethods.Plot2DWidget(self.get_sp, self.ds),
                              'plot2d')
        lineplot_widget = plotmethods.LinePlotWidget(self.get_sp, self.ds)
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
        valid_variables = self.plotmethod_widget.valid_variables(self.ds)
        for v, btn in self.variable_buttons.items():
            btn.setEnabled(v in valid_variables)

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
        menu.addAction('all images (PDF, PNG, etc.)', self.export_all_images)
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
            self.sp.export(fname, **rcParams['savefig_kws'])

    def export_all_images(self):
        fname, ok = QtWidgets.QFileDialog.getSaveFileName(
            self, "Export image", os.getcwd(),
            "Images (*.png *.pdf *.jpg *.svg)")
        if ok:
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
                if self.combo_array.count() > 1:
                    with self.block_widgets(self.combo_array):
                        current = self.combo_array.currentIndex()
                        self.combo_array.setCurrentIndex(current - 1)
                else:
                    self.btn_del.setEnabled(False)

            else:
                with self.silence_variable_buttons():
                    for var, btn in self.variable_buttons.items():
                        if var != v:
                            btn.setChecked(False)
                self.make_plot()
                self.btn_del.setEnabled(True)
            self.refresh()

        return func

    @contextlib.contextmanager
    def silence_variable_buttons(self):
        yield self.block_widgets(*self.variable_buttons.values())

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
        sp = self._sp
        if sp is None:
            return sp
        return self.filter_sp(sp)

    def filter_sp(self, sp):
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
        arr_name = self.arr_name
        if arr_name is None:
            return ret
        return ret(arr_name=arr_name)

    def new_plot(self):
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
    def creating_new_plot(self):
        self._new_plot = True
        yield
        self._new_plot = False

    @property
    def sp(self):
        return self.plotmethod_widget.sp or None

    @sp.setter
    def sp(self, sp):
        if sp is None and (not self._sp or not getattr(
                self._sp, self.plotmethod)):
            pass
        else:
            # first remove the current arrays
            if self.get_sp() and getattr(self.get_sp(), self.plotmethod):
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
                self.data.psy.update(name=self.variable, dims=dims, **fmts)
            self.show_fig(self.sp)
        else:
            self.ani = None
            self.sp = sp = self.plot(name=self.variable, **self.plot_options)
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
    def block_widgets(self, *widgets):
        for w in widgets:
            w.blockSignals(True)
        yield
        for w in widgets:
            w.blockSignals(False)

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
                raw_data.ndim == 2 or
                widget.plotter.ax.figure.canvas.manager.toolbar.mode != ''):
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


    def close_sp(self):
        sp = self.sp
        self.sp = None
        sp.close(figs=True, data=True, ds=False)

    def show_current_figure(self):
        if self.sp is not None:
            self.show_fig(self.sp)

    def show_fig(self, sp):
        if len(sp):
            try:
                fig = sp.plotters[0].ax.figure
                fig.canvas.window().show()
                fig.canvas.window().raise_()
            except AttributeError:
                sp.show()

    def switch_tab(self):
        with self.silence_variable_buttons():
            if self.sp:
                name = self.data.name
            else:
                name = NOTSET
            for v, btn in self.variable_buttons.items():
                btn.setChecked(v == name)
        self.refresh()

    def reset_combo_array(self):
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


    def refresh(self):

        self.clear_table()

        self.reset_combo_array()

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
        if self.variable_buttons:
            valid_variables = self.plotmethod_widget.valid_variables(self.ds)
            for v, btn in self.variable_buttons.items():
                btn.setEnabled(v in valid_variables)
        if self.ds is None or variable is NOTSET or not self.sp:
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


class DatasetWidgetPlugin(DatasetWidget, DockMixin):

    #: The title of the widget
    title = 'psy-view Dataset viewer'

    #: Display the dock widget at the right side of the GUI
    dock_position = Qt.RightDockWidgetArea

    def __init__(self, *args, **kwargs):
        import psyplot.project as psy
        super().__init__(*args, **kwargs)
        psy.Project.oncpchange.connect(self.oncpchange)

    @property
    def _sp(self):
        import psyplot.project as psy
        return psy.gcp(True)

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
        if getattr(current, self.plotmethod, []):

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

    def close_sp(self):
        ds = self.ds
        super().close_sp()
        if ds.psy.num not in self._sp.datasets:
            self.set_dataset(ds)

    def oncpchange(self, sp):
        self.reset_combo_array()
        if self.ds is not None and self.ds.psy.num not in self._sp.datasets:
            self.ds = None
            self.disable_navigation()
            self.setup_variable_buttons()
            self.btn_add.setEnabled(False)
            self.btn_del.setEnabled(False)
        elif self.ds is None and self._sp:
            self.set_dataset(next(iter(self._sp.datasets.values())))

    def show_fig(self, sp):
        from psyplot_gui.main import mainwindow
        super().show_fig(sp)
        if mainwindow.figures and sp:
            try:
                dock = sp.plotters[0].ax.figure.canvas.manager.window
                dock.widget().show_plugin()
                dock.raise_()
            except AttributeError:
                pass

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
