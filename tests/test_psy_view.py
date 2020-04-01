"""Test the main functionality of the psy-view package, namely the widget"""


def test_variables(ds_widget, test_ds):
    for v in test_ds:
        assert any(button.text() == v for button in ds_widget.variable_buttons)

