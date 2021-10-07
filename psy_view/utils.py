"""Utility functions for psy-view."""

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

from __future__ import annotations
import os.path as osp

from typing import Callable, Optional, Union, List, cast, TYPE_CHECKING

from PyQt5 import QtWidgets, QtCore, QtGui

if TYPE_CHECKING:
    from PyQt5.QtCore import QEvent  # pylint: disable=no-name-in-module


def get_icon(name: str, ending: str = '.png') -> str:
    return osp.join(osp.dirname(__file__), 'icons', name + ending)


def add_pushbutton(
        label: str,
        connections: Optional[Union[List[Callable], Callable]] = None,
        tooltip: Optional[str] = None,
        layout: Optional[QtWidgets.QLayout] = None,
        icon: bool = False, toolbutton: bool = False, *args, **kwargs
    ) -> Union[QtWidgets.QPushButton, QtWidgets.QToolButton]:
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
            iter(connections)  # type: ignore
        except TypeError:
            connections = [connections]  # type: ignore
        connections = cast(List[Callable], connections)
        for con in connections:
            btn.clicked.connect(con)
    if layout is not None:
        layout.addWidget(btn)
    return btn


class QRightPushButton(QtWidgets.QPushButton):
    """A push button that acts differently when right-clicked"""

    rightclicked = QtCore.pyqtSignal()

    def mousePressEvent(self, event: QEvent):
        if event.button() == QtCore.Qt.RightButton:
            self.rightclicked.emit()
            event.accept()
        else:
            return super().mousePressEvent(event)
