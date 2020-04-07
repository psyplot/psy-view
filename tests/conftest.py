import os.path as osp
import pytest
import psyplot_gui.compat.qtcompat


test_dir = osp.dirname(__file__)


@pytest.fixture(params=["regular-test.nc", "regional-icon-test.nc",
                        "rotated-pole-test.nc", "icon-test.nc"])
def test_ds(request):
    import psyplot.data as psyd
    with psyd.open_dataset(osp.join(test_dir, request.param)) as ds:
        yield ds


@pytest.fixture
def ds_widget(qtbot, test_ds):
    import psyplot.project as psy
    import matplotlib.pyplot as plt
    from psy_view.ds_widget import DatasetWidget
    w = DatasetWidget(test_ds)
    qtbot.addWidget(w)
    yield w
    w._sp = None
    psy.close('all')
    plt.close('all')
