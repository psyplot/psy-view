from PyQt5 import QtWidgets, QtCore, QtGui


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
