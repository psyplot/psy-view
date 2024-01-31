"""Test the formatoption dialogs."""

# SPDX-FileCopyrightText: 2020-2021 Helmholtz-Zentrum Geesthacht
# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only
from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from psy_view.dialogs import BasemapDialog


@pytest.fixture
def test_project(test_ds):
    sp = test_ds.psy.plot.mapplot(name="t2m")
    yield sp
    sp.close()


@pytest.fixture
def cmap_dialog(qtbot, test_project):
    from psy_view.dialogs import CmapDialog

    dialog = CmapDialog(test_project)
    qtbot.addWidget(dialog)
    return dialog


@pytest.fixture
def basemap_dialog(qtbot, test_project):
    from psy_view.dialogs import BasemapDialog

    dialog = BasemapDialog(test_project.plotters[0])
    qtbot.addWidget(dialog)
    return dialog


def test_colorbar_preview_valid_bounds(cmap_dialog):
    """Test whether the update to a new bounds setting works"""
    bounds = [240, 270, 310]
    cmap_dialog.bounds_widget.editor.set_obj(bounds)

    assert list(cmap_dialog.cbar_preview.cbar.norm.boundaries) == bounds


def test_colorbar_preview_valid_cmap(cmap_dialog):
    """Test whether the update to a new cmap setting works"""
    cmap = "Blues"
    cmap_dialog.cmap_widget.editor.set_obj(cmap)

    assert cmap_dialog.cbar_preview.cbar.cmap.name == cmap


def test_colorbar_preview_valid_ticks(cmap_dialog):
    """Test whether the update to a new cticks setting works"""
    ticks = [285, 290]
    cmap_dialog.cticks_widget.editor.set_obj(ticks)

    assert list(cmap_dialog.cbar_preview.cbar.get_ticks()) == ticks


def test_colorbar_preview_invalid_bounds(cmap_dialog):
    """Test whether the update to a invalid bounds setting works"""
    bounds = list(cmap_dialog.cbar_preview.cbar.norm.boundaries)

    # set invalid bounds
    cmap_dialog.bounds_widget.editor.text = "[1, 2, 3"

    assert list(cmap_dialog.cbar_preview.cbar.norm.boundaries) == bounds


def test_colorbar_preview_invalid_cmap(cmap_dialog):
    """Test whether the update to a invalued cmap setting works"""
    cmap = cmap_dialog.cbar_preview.cbar.cmap.name

    # set invalid cmap
    cmap_dialog.cmap_widget.editor.text = "Blue"

    assert cmap_dialog.cbar_preview.cbar.cmap.name == cmap


def test_colorbar_preview_invalid_ticks(cmap_dialog):
    """Test whether the update to a new color setting works"""
    ticks = list(cmap_dialog.cbar_preview.cbar.get_ticks())

    # set invalid ticks
    cmap_dialog.cticks_widget.editor.text = "[1, 2, 3"

    assert list(cmap_dialog.cbar_preview.cbar.get_ticks()) == ticks


def test_cmap_dialog_fmts(cmap_dialog):
    """Test the updating of formatoptions"""
    assert not cmap_dialog.fmts

    cmap_dialog.bounds_widget.editor.set_obj("minmax")

    assert cmap_dialog.fmts == {"bounds": "minmax"}


def test_basemap_dialog_background_image_default(
    basemap_dialog: BasemapDialog,
):
    """Test the updating of the basemap stock image"""
    assert not basemap_dialog.background_img_box.isChecked()
    fmts = basemap_dialog.value

    assert "stock_img" in fmts
    assert not fmts["stock_img"]

    assert "google_map_detail" in fmts
    assert fmts["google_map_detail"] is None


def test_basemap_dialog_background_image_stock_img(
    basemap_dialog: BasemapDialog,
):
    # test checking the stock img
    basemap_dialog.background_img_box.setChecked(True)
    basemap_dialog.opt_stock_img.setChecked(True)

    fmts = basemap_dialog.value

    assert "stock_img" in fmts
    assert fmts["stock_img"]

    assert "google_map_detail" in fmts
    assert fmts["google_map_detail"] is None


def test_basemap_dialog_background_image_google_image(
    basemap_dialog: BasemapDialog,
):
    # test checking the stock img
    basemap_dialog.background_img_box.setChecked(True)
    basemap_dialog.opt_google_image.setChecked(True)

    fmts = basemap_dialog.value

    assert "stock_img" in fmts
    assert not fmts["stock_img"]

    assert "google_map_detail" in fmts
    assert fmts["google_map_detail"] == basemap_dialog.sb_google_image.value()
