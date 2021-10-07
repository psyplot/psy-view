"""pytest configuration file for psy-view."""

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

import os.path as osp
import pytest
import psyplot_gui.compat.qtcompat


_test_dir = osp.dirname(__file__)


@pytest.fixture
def test_dir() -> str:
    return _test_dir


@pytest.fixture(params=["regular-test.nc", "regional-icon-test.nc",
                        "rotated-pole-test.nc", "icon-test.nc"])
def test_file(test_dir, request):
    return osp.join(test_dir, request.param)


@pytest.fixture
def test_ds(test_file):
    import psyplot.data as psyd
    with psyd.open_dataset(test_file) as ds:
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
