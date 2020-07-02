"""Plotmethod widgets.

This module defines the widgets to interface with the mapplot, plot2d and
lineplot plotmethods"""
import os.path as osp
from functools import partial
from itertools import chain, cycle
import contextlib
import xarray as xr
from psyplot.utils import unique_everseen

from PyQt5 import QtWidgets, QtCore, QtGui
import psy_view.dialogs as dialogs
import psy_view.utils as utils
from psy_view.rcsetup import rcParams

from psyplot_gui.common import get_icon as get_psy_icon
import psy_simple.widgets.colors as pswc
import matplotlib.colors as mcol


class PlotMethodWidget(QtWidgets.QWidget):

    plotmethod = None

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
        ret = []
        plotmethod = getattr(ds.psy.plot, self.plotmethod)
        for v in list(ds):
            init_kws = self.init_dims(ds[v])
            dims = init_kws.get('dims', {})
            decoder = init_kws.get('decoder')
            if plotmethod.check_data(ds, v, dims, decoder)[0][0]:
                ret.append(v)
        return ret


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
        self.btn_cmap = pswc.CmapButton()
        self.btn_cmap.setToolTip("Select a different colormap")
        self.formatoptions_box.addWidget(self.btn_cmap)
        self.btn_cmap.colormap_changed.connect(self.set_cmap)
        self.btn_cmap.colormap_changed[mcol.Colormap].connect(self.set_cmap)
        self.setup_cmap_menu()

        self.btn_cmap_settings = utils.add_pushbutton(
            utils.get_icon('color_settings'), self.edit_color_settings,
            "Edit color settings", self.formatoptions_box,
            icon=True)

    def setup_cmap_menu(self):
        menu = self.btn_cmap.cmap_menu

        menu.addSeparator()
        self.select_cmap_action = menu.addAction(
            'More colormaps', self.open_cmap_dialog)

        self.color_settings_action = menu.addAction(
            QtGui.QIcon(utils.get_icon('color_settings')), 'More options',
            self.edit_color_settings)

        return menu

    def open_cmap_dialog(self, N=10):
        if self.sp:
            N = self.plotter.plot.mappable.get_cmap().N
        else:
            N = 10
        self.btn_cmap.open_cmap_dialog(N)

    def setup_projection_menu(self):
        menu = QtWidgets.QMenu()
        for projection in rcParams['projections']:
            menu.addAction(
                projection, partial(self.set_projection, projection))
        menu.addSeparator()
        self.proj_settings_action = menu.addAction(
            QtGui.QIcon(utils.get_icon('proj_settings')),
            "Customize basemap...", self.edit_basemap_settings)
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
            utils.get_icon('proj_settings'), self.edit_basemap_settings,
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
        self.color_settings_action.setEnabled(b)
        self.btn_cmap_settings.setEnabled(b)
        self.btn_labels.setEnabled(b)

    def set_cmap(self, cmap):
        if self.sp and 'cmap' in self.sp.plotters[0]:
            self.plotter.update(cmap=cmap)

    def toggle_datagrid(self):
        if self.btn_datagrid.isChecked():
            self.plotter.update(datagrid='k--')
        else:
            self.plotter.update(datagrid=None)

    def edit_labels(self):
        dialogs.LabelDialog.update_project(
            self.sp, 'figtitle', 'title', 'clabel')

    def edit_color_settings(self):
        dialogs.CmapDialog.update_project(self.sp)
        if isinstance(self.plotter.cmap.value, str):
            self.btn_cmap.setText(self.plotter.cmap.value)
        else:
            self.btn_cmap.setText('Custom')

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
        dialogs.BasemapDialog.update_plotter(self.plotter)

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
            else:
                self.btn_proj.setText('Custom')
            if isinstance(plotter.cmap.value, str):
                self.btn_cmap.setText(plotter.cmap.value)
            else:
                self.btn_cmap.setText('Custom')

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
        dialogs.LabelDialog.update_project(
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
        dialogs.LabelDialog.update_project(
            self.sp, 'figtitle', 'title', 'xlabel', 'ylabel', 'legendlabels')

    @contextlib.contextmanager
    def block_combos(self):
        self.combo_dims.blockSignals(True)
        self.combo_lines.blockSignals(True)
        yield
        self.combo_dims.blockSignals(False)
        self.combo_lines.blockSignals(False)

    def valid_variables(self, ds):
        valid = list(ds)
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
