"""pytest configuration file for psy-view."""

# SPDX-FileCopyrightText: 2020-2021 Helmholtz-Zentrum Geesthacht
# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

import os.path as osp

# import psyplot_gui.compat to make sure, qt settings are set
import psyplot_gui.compat.qtcompat  # noqa: F401
import pytest

_test_dir = osp.dirname(__file__)


@pytest.fixture
def test_dir() -> str:
    return _test_dir


@pytest.fixture(
    params=[
        "regular-test.nc",
        "regional-icon-test.nc",
        "rotated-pole-test.nc",
        "icon-test.nc",
    ]
)
def test_file(test_dir, request):
    return osp.join(test_dir, request.param)


@pytest.fixture
def test_ds(test_file):
    import psyplot.data as psyd

    with psyd.open_dataset(test_file) as ds:
        yield ds


@pytest.fixture
def ds_widget(qtbot, test_ds):
    import matplotlib.pyplot as plt
    import psyplot.project as psy

    from psy_view.ds_widget import DatasetWidget

    w = DatasetWidget(test_ds)
    qtbot.addWidget(w)
    yield w
    w._sp = None
    psy.close("all")
    plt.close("all")
