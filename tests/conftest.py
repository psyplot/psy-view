import os.path as osp
import pytest


test_dir = osp.dirname(__file__)


@pytest.fixture(scope='session')
def app():
    # to make sure, QtWebEngineWidgets are imported prior to app creation we
    # import qtcompat here
    from psyplot_gui.compat import qtcompat
    from PyQt5 import QtWidgets
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
        app.setQuitOnLastWindowClosed(False)
        yield app
        app.quit()
    else:
        yield app


@pytest.fixture(params=["test-t2m-u-v.nc", "icon_test.nc"])
def test_ds(request):
    import psyplot.data as psyd
    with psyd.open_dataset(osp.join(test_dir, request.param)) as ds:
        yield ds


@pytest.fixture
def ds_widget(app, test_ds):
    from psy_view.ds_widget import DatasetWidget
    w = DatasetWidget(test_ds)
    yield w
    w.close()

