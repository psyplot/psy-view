"""Utility functions for psy-view.

**Disclaimer**

Copyright (C) 2020 Philipp S. Sommer

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see https://www.gnu.org/licenses/."""
import os.path as osp
from PyQt5 import QtWidgets, QtCore, QtGui


def get_icon(name, ending='.png'):
    return osp.join(osp.dirname(__file__), 'icons', name + ending)


def add_pushbutton(label, connections=None, tooltip=None, layout=None,
                   icon=False, toolbutton=None, *args, **kwargs):
    if icon or toolbutton:
        btn = QtWidgets.QToolButton(*args, **kwargs)
        if icon:
            btn.setIcon(QtGui.QIcon(label))
        else:
            btn.setText(label)
    else:
        btn = QtWidgets.QPushButton(label, *args, **kwargs)
    if tooltip is not None:
        btn.setToolTip(tooltip)
    if connections is not None:
        try:
            iter(connections)
        except TypeError:
            connections = [connections]
        for con in connections:
            btn.clicked.connect(con)
    if layout is not None:
        layout.addWidget(btn)
    return btn


class QRightPushButton(QtWidgets.QPushButton):
    """A push button that acts differently when right-clicked"""

    rightclicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event):
        if event.button() == QtCore.Qt.RightButton:
            self.rightclicked.emit()
            event.accept()
        else:
            return super().mousePressEvent(event)
