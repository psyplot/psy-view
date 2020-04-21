"""Test the main functionality of the psy-view package, namely the widget"""
import os.path as osp
from PyQt5.QtCore import Qt
from PyQt5 import QtWidgets
import pytest


def test_variables(ds_widget, test_ds):
    """Test existence of variables in netCDF file"""
    for v in test_ds:
        assert v in ds_widget.variable_buttons
        assert ds_widget.variable_buttons[v].text() == v


def test_mapplot(qtbot, ds_widget):
    """Test plotting and closing with mapplot"""
    ds_widget.plotmethod = 'mapplot'
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    assert ds_widget.sp
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    assert not ds_widget.sp

@pytest.mark.parametrize('plotmethod', ['mapplot', 'plot2d'])
def test_variable_switch(qtbot, ds_widget, plotmethod):
    """Test switching of variables"""
    ds_widget.plotmethod = plotmethod
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    assert len(ds_widget.sp) == 1
    assert ds_widget.data.name == 't2m'
    qtbot.mouseClick(ds_widget.variable_buttons['v'], Qt.LeftButton)
    assert len(ds_widget.sp) == 1
    assert ds_widget.data.name == 'v'
    qtbot.mouseClick(ds_widget.variable_buttons['v_2d'], Qt.LeftButton)
    assert len(ds_widget.sp) == 1
    assert ds_widget.data.name == 'v_2d'
    qtbot.mouseClick(ds_widget.variable_buttons['v'], Qt.LeftButton)
    assert len(ds_widget.sp) == 1
    assert ds_widget.data.name == 'v'
    qtbot.mouseClick(ds_widget.variable_buttons['v'], Qt.LeftButton)
    assert not ds_widget.sp


def test_plot2d(qtbot, ds_widget):
    """Test plotting and closing with plot2d"""
    ds_widget.plotmethod = 'plot2d'
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    assert ds_widget.sp
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    assert not ds_widget.sp


def test_plot2d_dim_switch(qtbot, ds_widget, test_ds, test_file):
    arr = test_ds['t2m']

    ds_widget.plotmethod = 'plot2d'

    pm_widget = ds_widget.plotmethod_widget

    pm_widget.combo_xdim.setCurrentText(arr.dims[0])
    pm_widget.combo_ydim.setCurrentText(arr.dims[1])

    assert pm_widget.combo_xcoord.currentText() == arr.dims[0]
    assert pm_widget.combo_ycoord.currentText() == arr.dims[1]

    fmts = pm_widget.init_dims(arr)

    assert fmts['transpose']

    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)

    assert not pm_widget.combo_xdim.isEnabled()

    assert ds_widget.sp
    assert ds_widget.plotter.plot_data.dims == arr.dims[:2]


@pytest.mark.parametrize('plotmethod', ['mapplot', 'plot2d'])
def test_plot2d_coord(qtbot, ds_widget, test_ds, test_file, plotmethod):
    arr = test_ds.psy['t2m']

    if osp.basename(test_file) != "rotated-pole-test.nc":
        return pytest.skip("Testing rotated coords only")

    ydim, xdim = arr.dims[-2:]

    test_ds[xdim].attrs.pop('axis', None)
    test_ds[ydim].attrs.pop('axis', None)

    assert 'coordinates' in arr.encoding

    ds_widget.plotmethod = plotmethod

    pm_widget = ds_widget.plotmethod_widget

    assert pm_widget.combo_xcoord.isEnabled()

    # make the plot with default setting
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)

    assert not pm_widget.combo_xcoord.isEnabled()

    assert pm_widget.data.psy.get_coord('x').name != xdim
    assert pm_widget.data.psy.get_coord('y').name != ydim

    # remove the plot
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)

    assert pm_widget.combo_xcoord.isEnabled()

    # tell to use the dimensions
    pm_widget.combo_xcoord.setCurrentText(xdim)
    pm_widget.combo_ycoord.setCurrentText(ydim)

    # make the plot with the changed settings
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)

    assert not pm_widget.combo_xcoord.isEnabled()

    assert pm_widget.data.psy.get_coord('x').name == xdim
    assert pm_widget.data.psy.get_coord('y').name == ydim


def test_lineplot(qtbot, ds_widget):
    """Test plotting and closing with lineplot"""
    ds_widget.plotmethod = 'lineplot'
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    assert ds_widget.sp
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    assert not ds_widget.sp


def test_lineplot_switch(qtbot, ds_widget):
    """Test switching of variables"""
    ds_widget.plotmethod = 'lineplot'
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    assert len(ds_widget.sp) == 1
    assert ds_widget.data.name == 't2m'
    qtbot.mouseClick(ds_widget.variable_buttons['v'], Qt.LeftButton)
    assert len(ds_widget.sp) == 1
    assert ds_widget.data.name == 'v'
    qtbot.mouseClick(ds_widget.variable_buttons['v'], Qt.LeftButton)
    assert not ds_widget.sp


@pytest.mark.parametrize('plotmethod', ['mapplot', 'plot2d'])
def test_cmap(qtbot, ds_widget, plotmethod):
    ds_widget.plotmethod = plotmethod
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    cmap = ds_widget.plotter.cmap.value
    assert ds_widget.plotter.plot.mappable.get_cmap().name == cmap
    qtbot.mouseClick(ds_widget.plotmethod_widget.btn_cmap, Qt.LeftButton)
    assert ds_widget.plotter.cmap.value != cmap
    assert ds_widget.plotter.plot.mappable.get_cmap().name != cmap
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)


def test_add_and_remove_line(qtbot, ds_widget, monkeypatch):
    "Test adding and removing lines"
    ds_widget.plotmethod = 'lineplot'

    monkeypatch.setattr(
        QtWidgets.QInputDialog, "getItem",
        lambda *args: ('t2m', True))

    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    assert ds_widget.sp
    assert len(ds_widget.sp[0]) == 1
    qtbot.mouseClick(ds_widget.plotmethod_widget.btn_add, Qt.LeftButton)
    assert len(ds_widget.sp[0]) == 2
    qtbot.mouseClick(ds_widget.plotmethod_widget.btn_del, Qt.LeftButton)
    assert len(ds_widget.sp[0]) == 1
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    assert not ds_widget.sp


@pytest.mark.parametrize('plotmethod', ['mapplot', 'plot2d', 'lineplot'])
def test_btn_step(qtbot, ds_widget, plotmethod):
    """Test clicking the next time button"""
    ds_widget.plotmethod = plotmethod
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    dim = ds_widget.combo_dims.currentText()
    assert dim
    assert ds_widget.data.psy.idims[dim] == 0

    # increase time
    qtbot.mouseClick(ds_widget.btn_next, Qt.LeftButton)
    assert ds_widget.data.psy.idims[dim] == 1

    # decrease time
    qtbot.mouseClick(ds_widget.btn_prev, Qt.LeftButton)
    assert ds_widget.data.psy.idims[dim] == 0

@pytest.mark.parametrize('plotmethod', ['mapplot', 'plot2d', 'lineplot'])
def test_dimension_button(qtbot, ds_widget, plotmethod):
    """Test clicking on a button in the dimension table"""
    ds_widget.plotmethod = plotmethod
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)

    btn = ds_widget.dimension_table.cellWidget(1, 2)

    dim = ds_widget.dimension_table.verticalHeaderItem(1).text()

    assert ds_widget.data.psy.idims[dim] == 0

    qtbot.mouseClick(btn, Qt.LeftButton)

    assert ds_widget.data.psy.idims[dim] == 1

    qtbot.mouseClick(btn, Qt.RightButton)

    assert ds_widget.data.psy.idims[dim] == 0


@pytest.mark.parametrize('plotmethod', ['mapplot', 'plot2d', 'lineplot'])
@pytest.mark.parametrize('direction', ['forward', 'backward'])
def test_animate(qtbot, ds_widget, plotmethod, direction):
    """Test clicking the next time button"""

    def animation_finished():
        current = ds_widget.data.psy.idims[dim]
        if steps and current in steps:
            steps.remove(current)
            return False
        elif steps:
            return False
        else:
            return True


    ds_widget.plotmethod = plotmethod
    ds_widget.sl_interval.setValue(10)
    qtbot.mouseClick(ds_widget.variable_buttons['t2m'], Qt.LeftButton)
    dim = ds_widget.combo_dims.currentText()

    assert dim

    steps = set(range(ds_widget.ds.dims[dim]))

    btn = getattr(ds_widget, 'btn_animate_' + direction)

    assert not ds_widget._animating

    # start animation
    qtbot.mouseClick(btn, Qt.LeftButton)
    assert ds_widget._animating
    qtbot.waitUntil(animation_finished, timeout=30000)

    # stop animation
    qtbot.mouseClick(btn, Qt.LeftButton)
    assert not ds_widget._animating

    # restart animation
    steps = set(range(ds_widget.ds.dims[dim]))
    qtbot.mouseClick(btn, Qt.LeftButton)
    assert ds_widget._animating
    qtbot.waitUntil(animation_finished, timeout=30000)

    # stop animation
    qtbot.mouseClick(btn, Qt.LeftButton)
    assert not ds_widget._animating


def test_enable_disable_variables(test_ds, qtbot):
    from psy_view.ds_widget import DatasetWidget
    import numpy as np
    test_ds['line'] = ('xtest', np.zeros(7))
    test_ds['xtest'] = ('xtest', np.arange(7))

    ds_widget = DatasetWidget(test_ds)
    qtbot.addWidget(ds_widget)

    assert ds_widget.variable_buttons['t2m'].isEnabled()
    assert not ds_widget.variable_buttons['line'].isEnabled()

    ds_widget.plotmethod = 'lineplot'

    assert ds_widget.variable_buttons['t2m'].isEnabled()
    assert ds_widget.variable_buttons['line'].isEnabled()

    ds_widget.plotmethod = 'plot2d'

    assert ds_widget.variable_buttons['t2m'].isEnabled()
    assert not ds_widget.variable_buttons['line'].isEnabled()
