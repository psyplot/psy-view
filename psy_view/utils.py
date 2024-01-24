"""Utility functions for psy-view."""

# SPDX-FileCopyrightText: 2020-2021 Helmholtz-Zentrum Geesthacht
# SPDX-FileCopyrightText: 2021-2024 Helmholtz-Zentrum hereon GmbH
#
# SPDX-License-Identifier: LGPL-3.0-only

from __future__ import annotations

import os.path as osp
from typing import TYPE_CHECKING, Callable, List, Optional, Union, cast

from PyQt5 import QtCore, QtGui, QtWidgets

if TYPE_CHECKING:
    from PyQt5.QtCore import QEvent  # pylint: disable=no-name-in-module


def get_icon(name: str, ending: str = ".png") -> str:
    return osp.join(osp.dirname(__file__), "icons", name + ending)


def add_pushbutton(
    label: str,
    connections: Optional[Union[List[Callable], Callable]] = None,
    tooltip: Optional[str] = None,
    layout: Optional[QtWidgets.QLayout] = None,
    icon: bool = False,
    toolbutton: bool = False,
    *args,
    **kwargs,
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
