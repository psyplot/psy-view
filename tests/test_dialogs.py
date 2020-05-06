"""Test the formatoption dialogs"""
import pytest


@pytest.fixture
def test_project(test_ds):
    sp = test_ds.psy.plot.mapplot(name='t2m')
    yield sp
    sp.close()


@pytest.fixture
def cmap_dialog(qtbot, test_project):
    from psy_view.dialogs import CmapDialog
    dialog = CmapDialog(test_project)
    qtbot.addWidget(dialog)
    return dialog


def test_colorbar_preview_valid_bounds(cmap_dialog):
    """Test whether the update to a new bounds setting works"""
    bounds = [240, 270, 310]
    cmap_dialog.bounds_widget.editor.set_obj(bounds)

    assert list(cmap_dialog.cbar_preview.cbar.norm.boundaries) == bounds


def test_colorbar_preview_valid_cmap(cmap_dialog):
    """Test whether the update to a new cmap setting works"""
    cmap = 'Blues'
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
    cmap_dialog.bounds_widget.editor.text = '[1, 2, 3'

    assert list(cmap_dialog.cbar_preview.cbar.norm.boundaries) == bounds


def test_colorbar_preview_invalid_cmap(cmap_dialog):
    """Test whether the update to a invalued cmap setting works"""
    cmap = cmap_dialog.cbar_preview.cbar.cmap.name

    # set invalid cmap
    cmap_dialog.cmap_widget.editor.text = 'Blue'

    assert cmap_dialog.cbar_preview.cbar.cmap.name == cmap


def test_colorbar_preview_invalid_ticks(cmap_dialog):
    """Test whether the update to a new color setting works"""
    ticks = list(cmap_dialog.cbar_preview.cbar.get_ticks())

    # set invalid ticks
    cmap_dialog.cticks_widget.editor.text = '[1, 2, 3'

    assert list(cmap_dialog.cbar_preview.cbar.get_ticks()) == ticks


def test_cmap_dialog_fmts(cmap_dialog):
    """Test the updating of formatoptions"""
    assert not cmap_dialog.fmts

    cmap_dialog.bounds_widget.editor.set_obj('minmax')

    assert cmap_dialog.fmts == {'bounds': 'minmax'}