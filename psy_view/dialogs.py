"""Dialogs for manipulating formatoptions."""
import yaml

from PyQt5 import QtWidgets, QtGui


class BasemapDialog(QtWidgets.QDialog):
    """A dialog to modify the basemap settings"""

    def __init__(self, plotter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self)
        vbox = QtWidgets.QVBoxLayout(self)

        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        proj_box = QtWidgets.QGroupBox("Projection settings")
        layout = QtWidgets.QFormLayout(proj_box)

        self.txt_clon = QtWidgets.QLineEdit()
        self.txt_clon.setPlaceholderText('auto')
        self.txt_clon.setToolTip('Central longitude in degrees East')
        self.txt_clon.setValidator(QtGui.QDoubleValidator(-360, 360, 7))
        layout.addRow('Central longitude: ', self.txt_clon)

        self.txt_clat = QtWidgets.QLineEdit()
        self.txt_clat.setPlaceholderText('auto')
        self.txt_clat.setToolTip('Central latitude in degrees North')
        self.txt_clat.setValidator(QtGui.QDoubleValidator(-90, 90, 7))
        layout.addRow('Central latitude: ', self.txt_clat)

        vbox.addWidget(proj_box)

        self.lsm_box = QtWidgets.QGroupBox('Coastlines')
        self.lsm_box.setCheckable(True)
        hbox = QtWidgets.QHBoxLayout(self.lsm_box)
        hbox.addWidget(QtWidgets.QLabel("Resolution:"))
        self.opt_110 = QtWidgets.QRadioButton("110m")
        self.opt_50 = QtWidgets.QRadioButton("50m")
        self.opt_10 = QtWidgets.QRadioButton("10m")
        hbox.addWidget(self.opt_110)
        hbox.addWidget(self.opt_50)
        hbox.addWidget(self.opt_10)

        vbox.addWidget(self.lsm_box)

        self.meridionals_box = QtWidgets.QGroupBox('Meridionals')
        self.meridionals_box.setCheckable(True)
        self.opt_meri_auto = QtWidgets.QRadioButton("auto")

        self.opt_meri_at = QtWidgets.QRadioButton("At:")
        self.txt_meri_at = QtWidgets.QLineEdit()
        self.txt_meri_at.setPlaceholderText("30, 60, 90, 120, ... °E")
        # TODO: Add validator

        self.opt_meri_every = QtWidgets.QRadioButton("Every:")
        self.txt_meri_every = QtWidgets.QLineEdit()
        self.txt_meri_every.setPlaceholderText("30 °E")
        self.txt_meri_every.setValidator(QtGui.QDoubleValidator(-360, 360, 7))

        self.opt_meri_num = QtWidgets.QRadioButton("Number:")
        self.txt_meri_num = QtWidgets.QLineEdit()
        self.txt_meri_num.setPlaceholderText("5")
        self.txt_meri_num.setValidator(QtGui.QIntValidator(1, 360))

        form = QtWidgets.QFormLayout(self.meridionals_box)
        form.addRow(self.opt_meri_auto)
        form.addRow(self.opt_meri_at, self.txt_meri_at)
        form.addRow(self.opt_meri_every, self.txt_meri_every)
        form.addRow(self.opt_meri_num, self.txt_meri_num)

        vbox.addWidget(self.meridionals_box)

        self.parallels_box = QtWidgets.QGroupBox('Parallels')
        self.parallels_box.setCheckable(True)
        self.opt_para_auto = QtWidgets.QRadioButton("auto")

        self.opt_para_at = QtWidgets.QRadioButton("At:")
        self.txt_para_at = QtWidgets.QLineEdit()
        self.txt_para_at.setPlaceholderText("-60, -30, 0, 30, ... °N")
        # TODO: Add validator

        self.opt_para_every = QtWidgets.QRadioButton("Every:")
        self.txt_para_every = QtWidgets.QLineEdit()
        self.txt_para_every.setPlaceholderText("30 °N")
        self.txt_para_every.setValidator(QtGui.QDoubleValidator(-90, 90, 7))

        self.opt_para_num = QtWidgets.QRadioButton("Number:")
        self.txt_para_num = QtWidgets.QLineEdit()
        self.txt_para_num.setPlaceholderText("5")
        self.txt_para_num.setValidator(QtGui.QIntValidator(1, 180))

        form = QtWidgets.QFormLayout(self.parallels_box)
        form.addRow(self.opt_para_auto)
        form.addRow(self.opt_para_at, self.txt_para_at)
        form.addRow(self.opt_para_every, self.txt_para_every)
        form.addRow(self.opt_para_num, self.txt_para_num)

        vbox.addWidget(self.parallels_box)

        vbox.addWidget(self.button_box)

        self.fill_from_plotter(plotter)

        for button in [self.opt_meri_at, self.opt_meri_auto, self.opt_meri_num,
                       self.opt_meri_every, self.opt_para_at,
                       self.opt_para_auto, self.opt_para_num,
                       self.opt_para_every]:
            button.clicked.connect(self.update_forms)

    def fill_from_plotter(self, plotter):
        if plotter.clon.value is not None:
            self.txt_clon.setText(str(plotter.clon.value))
        if plotter.clat.value is not None:
            self.txt_clat.setText(str(plotter.clat.value))

        if not plotter.lsm.value[0]:
            self.lsm_box.setChecked(False)
        else:
            try:
                res = plotter.lsm.value[0][:-1]
            except TypeError:
                res = '110'
            getattr(self, 'opt_' + res).setChecked(True)

        self.xgrid_value = None
        value = plotter.xgrid.value
        if not value:
            self.meridionals_box.setChecked(False)
        elif value is True:
            self.opt_meri_auto.setChecked(True)
        elif isinstance(value[0], str):
            self.xgrid_value = value[0]
            self.opt_meri_num.setChecked(True)
            self.txt_meri_num.setText(str(value[1]))
        elif isinstance(value, tuple):
            self.xgrid_value = value[:2]
            self.opt_meri_num.setChecked(True)
            steps = 11 if len(value) == 2 else value[3]
            self.txt_meri_num.setText(str(steps))
        else:
            self.opt_meri_at.setChecked(True)
            self.txt_meri_at.setText(', '.join(map(str, value)))

        self.ygrid_value = None
        value = plotter.ygrid.value
        if not value:
            self.parallels_box.setChecked(False)
        elif value is True:
            self.opt_para_auto.setChecked(True)
        elif isinstance(value[0], str):
            self.opt_para_num.setChecked(True)
            self.txt_para_num.setText(str(value[1]))
            self.ygrid_value = value[0]
        elif isinstance(value, tuple):
            self.ygrid_value = value[:2]
            self.opt_para_num.setChecked(True)
            steps = 11 if len(value) == 2 else value[3]
            self.txt_para_num.setText(str(steps))
        else:
            self.opt_para_at.setChecked(True)
            self.txt_para_at.setText(', '.join(map(str, value)))

    def update_forms(self):
        if self.meridionals_box.isChecked():
            self.txt_meri_at.setEnabled(self.opt_meri_at.isChecked())
            self.txt_meri_every.setEnabled(self.opt_meri_every.isChecked())
            self.txt_meri_num.setEnabled(self.opt_meri_num.isChecked())
        if self.parallels_box.isChecked():
            self.txt_para_at.setEnabled(self.opt_para_at.isChecked())
            self.txt_para_every.setEnabled(self.opt_para_every.isChecked())
            self.txt_para_num.setEnabled(self.opt_para_num.isChecked())

    @property
    def value(self):
        import numpy as np
        ret = {}
        ret['clon'] = None if not self.txt_clon.text().strip() else float(
            self.txt_clon.text().strip())
        ret['clat'] = None if not self.txt_clat.text().strip() else float(
            self.txt_clat.text().strip())

        if self.lsm_box.isChecked():
            if self.opt_110.isChecked():
                ret['lsm'] = '110m'
            elif self.opt_50.isChecked():
                ret['lsm'] = '50m'
            elif self.opt_10.isChecked():
                ret['lsm'] = '10m'
        else:
            ret['lsm'] = False

        if not self.meridionals_box.isChecked():
            ret['xgrid'] = False
        elif self.opt_meri_auto.isChecked():
            ret['xgrid'] = True
        elif self.opt_meri_every.isChecked():
            ret['xgrid'] = np.arange(
                -180, 180, float(self.txt_meri_every.text().strip() or 30))
        elif self.opt_meri_at.isChecked():
            ret['xgrid'] = list(map(
                float, self.txt_meri_at.text().split(','))) or False
        elif self.opt_meri_num.isChecked():
            if self.xgrid_value is None:
                ret['xgrid'] = ['rounded', int(self.txt_meri_num.text() or 5)]
            elif isinstance(self.xgrid_value, str):
                ret['xgrid'] = [self.xgrid_value,
                                int(self.txt_meri_num.text() or 5)]
            else:
                ret['xgrid'] = tuple(self.xgrid_value) + (
                    int(self.txt_meri_num.text() or 5), )

        if not self.parallels_box.isChecked():
            ret['ygrid'] = False
        elif self.opt_para_auto.isChecked():
            ret['ygrid'] = True
        elif self.opt_para_every.isChecked():
            ret['ygrid'] = np.arange(
                -180, 180, float(self.txt_para_every.text().strip() or 30))
        elif self.opt_para_at.isChecked():
            ret['ygrid'] = list(map(
                float, self.txt_para_at.text().split(','))) or False
        elif self.opt_para_num.isChecked():
            if self.ygrid_value is None:
                ret['ygrid'] = ['rounded', int(self.txt_para_num.text() or 5)]
            elif isinstance(self.ygrid_value, str):
                ret['ygrid'] = [self.ygrid_value,
                                int(self.txt_para_num.text() or 5)]
            else:
                ret['ygrid'] = tuple(self.ygrid_value) + (
                    int(self.txt_para_num.text() or 5), )
        return ret

    @classmethod
    def update_plotter(cls, plotter):
        dialog = cls(plotter)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec_()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            plotter.update(
                **dialog.value)


class CmapDialog(QtWidgets.QDialog):
    """A dialog to modify color bounds"""

    def __init__(self, plotter, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.tabs = QtWidgets.QTabWidget()
        self.bounds_widget = BoundaryWidget(
            plotter.cmap.value, plotter.bounds.value)
        self.tabs.addTab(self.bounds_widget, "Colormap boundaries")

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.tabs)
        vbox.addWidget(self.button_box)

    @classmethod
    def update_plotter(cls, plotter):
        dialog = cls(plotter)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec_()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            plotter.update(
                **dialog.bounds_widget.value)


class BoundaryWidget(QtWidgets.QWidget):
    """A widget to select colormap boundaries"""

    def __init__(self, cmap_value, init_value, *args, **kwargs):
        super().__init__(*args, **kwargs)

        layout = QtWidgets.QGridLayout(self)

        self.type_box = QtWidgets.QGroupBox()
        vbox = QtWidgets.QVBoxLayout(self.type_box)
        self.opt_rounded = QtWidgets.QRadioButton("Rounded")
        self.opt_minmax = QtWidgets.QRadioButton("Exact")
        self.opt_custom = QtWidgets.QRadioButton("Custom")
        vbox.addWidget(self.opt_rounded)
        vbox.addWidget(self.opt_minmax)
        vbox.addWidget(self.opt_custom)

        layout.addWidget(self.type_box, 0, 0, 3, 1)

        self.min_box = QtWidgets.QGroupBox()
        hbox = QtWidgets.QHBoxLayout(self.min_box)
        self.opt_min = QtWidgets.QRadioButton("Minimum")
        self.opt_min_pctl = QtWidgets.QRadioButton("Percentile")
        self.txt_min_pctl = QtWidgets.QLineEdit()
        self.txt_min_pctl.setValidator(QtGui.QDoubleValidator(0., 100., 5))
        hbox.addWidget(self.opt_min)
        hbox.addWidget(self.opt_min_pctl)
        hbox.addWidget(self.txt_min_pctl)

        layout.addWidget(self.min_box, 0, 1, 1, 2)

        self.max_box = QtWidgets.QGroupBox()
        hbox = QtWidgets.QHBoxLayout(self.max_box)
        self.opt_max = QtWidgets.QRadioButton("Maximum")
        self.opt_max_pctl = QtWidgets.QRadioButton("Percentile")
        self.txt_max_pctl = QtWidgets.QLineEdit()
        self.txt_max_pctl.setValidator(QtGui.QDoubleValidator(0., 100., 5))
        hbox.addWidget(self.opt_max)
        hbox.addWidget(self.opt_max_pctl)
        hbox.addWidget(self.txt_max_pctl)

        layout.addWidget(self.max_box, 1, 1, 1, 2)

        self.txt_custom = QtWidgets.QLineEdit()
        self.txt_custom.setPlaceholderText('1, 2, 3, 4, 5, ...')
        # TODO: Add validator
        layout.addWidget(self.txt_custom, 2, 1, 1, 2)

        self.cb_symmetric = QtWidgets.QCheckBox("symmetric")
        layout.addWidget(self.cb_symmetric, 3, 0)

        self.cb_inverted = QtWidgets.QCheckBox("inverted")
        layout.addWidget(self.cb_inverted, 3, 1)
        self.cb_inverted.setChecked(cmap_value.endswith('_r'))
        self.init_cmap = cmap_value

        self.txt_levels = QtWidgets.QLineEdit()
        self.txt_levels.setInputMask(r"\B\o\u\n\d\s\: 900")
        self.txt_levels.setMaxLength(len('Bounds: 256'))
        layout.addWidget(self.txt_levels)

        self.fill_form(init_value)

        for button in [self.opt_minmax, self.opt_rounded, self.opt_custom,
                       self.opt_min, self.opt_max,
                       self.opt_min_pctl, self.opt_max_pctl]:
            button.clicked.connect(self.update_type)

    def update_type(self):
        custom = self.opt_custom.isChecked()
        self.txt_custom.setEnabled(custom)
        self.opt_min.setEnabled(not custom)
        self.opt_max.setEnabled(not custom)
        self.opt_min_pctl.setEnabled(not custom)
        self.opt_max_pctl.setEnabled(not custom)
        self.txt_min_pctl.setEnabled(self.opt_min_pctl.isChecked())
        self.txt_max_pctl.setEnabled(self.opt_max_pctl.isChecked())

    @property
    def value(self):
        cmap = self.init_cmap
        if self.cb_inverted.isChecked() and not cmap.endswith('_r'):
            cmap = cmap + '_r'
        elif not self.cb_inverted.isChecked() and cmap.endswith('_r'):
            cmap = cmap[:-2]
        if self.opt_custom.isChecked():
            bounds = list(map(float, self.txt_custom.text().split(',')))
            if not bounds:
                bounds = ['rounded', None]
        else:
            if self.opt_minmax.isChecked():
                val = 'minmax' if not self.cb_symmetric.isChecked() else 'sym'
            else:
                val = ('rounded' if not self.cb_symmetric.isChecked() else
                       'roundedsym')
            bounds = [val]
            levels = self.txt_levels.text()[len('Bounds: '):]
            bounds.append(int(levels) if levels.strip() else None)
            bounds.append(0 if self.opt_min.isChecked() else
                          float(self.txt_min_pctl.text().strip() or 0))
            bounds.append(100 if self.opt_max.isChecked() else
                          float(self.txt_max_pctl.text().strip() or 100))

        return {'bounds': bounds, 'cmap': cmap}



    def fill_form(self, value):

        if value[0] == 'rounded' or value[0] == 'roundedsym':
            self.opt_rounded.setChecked(True)
        elif value[0] == 'minmax' or value[0] == 'sym':
            self.opt_minmax.setChecked(True)
        else:
            self.opt_custom.setChecked(True)
            self.txt_custom.setText(', '.join(map(str, value)))
            self.txt_levels.setText('Bounds: %i' % len(value))
            return
        self.txt_levels.setText('Bounds: %s' % (value[1] or ''))
        self.txt_custom.setEnabled(False)

        min_pctl = 0 if len(value) <= 2 else value[2]
        if min_pctl == 0:
            self.opt_min.setChecked(True)
            self.txt_min_pctl.setText('0')
            self.txt_min_pctl.setEnabled(False)
        else:
            self.opt_min_pctl.setChecked(True)
            self.txt_min_pctl.setText(str(min_pctl))

        max_pctl = 100 if len(value) <= 3 else value[3]
        if max_pctl == 100:
            self.opt_max.setChecked(True)
            self.txt_max_pctl.setText('100')
            self.txt_max_pctl.setEnabled(False)
        else:
            self.opt_max_pctl.setChecked(True)
            self.txt_max_pctl.setText(str(max_pctl))

        self.cb_symmetric.setChecked(value[0].endswith('sym'))


class FormatoptionsEditor(QtWidgets.QWidget):
    """A widget to update a formatoption"""

    def __init__(self, fmto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QtWidgets.QHBoxLayout()

        self.line_edit = QtWidgets.QLineEdit()
        layout.addWidget(self.line_edit)
        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setVisible(False)
        layout.addWidget(self.text_edit)

        self.btn_multiline = QtWidgets.QToolButton()
        self.btn_multiline.setText('⌵')
        self.btn_multiline.setCheckable(True)
        self.btn_multiline.setToolTip("Toggle multiline editor")
        self.btn_multiline.clicked.connect(self.toggle_multiline)
        layout.addWidget(self.btn_multiline)

        self.insert_obj(fmto.value)
        self.initial_value = self.line_edit.text()
        self.setLayout(layout)

    def changed(self):
        return self.text != self.initial_value

    def toggle_multiline(self):
        multiline = self.multiline
        self.text_edit.setVisible(multiline)
        self.line_edit.setVisible(not multiline)
        if multiline:
            self.text_edit.setPlainText(self.line_edit.text())
        else:
            self.line_edit.setText(self.text_edit.toPlainText())

    @property
    def multiline(self):
        return self.btn_multiline.isChecked()

    @property
    def text(self):
        return (self.text_edit.toPlainText() if self.multiline else
                self.line_edit.text())

    @property
    def value(self):
        text = self.text
        return yaml.load(text, Loader=yaml.Loader)

    def clear_text(self):
        if self.multiline:
            self.text_edit.clear()
        else:
            self.line_edit.clear()

    def insert_obj(self, obj):
        """Add a string to the formatoption widget"""
        current = self.text
        use_line_edit = not self.multiline
        # strings are treated separately such that we consider quotation marks
        # at the borders
        if isinstance(obj, str) and current:
            if use_line_edit:
                pos = self.line_edit.cursorPosition()
            else:
                pos = self.text_edit.textCursor().position()
            if pos not in [0, len(current)]:
                s = obj
            else:
                if current[0] in ['"', "'"]:
                    current = current[1:-1]
                self.clear_text()
                if pos == 0:
                    s = '"' + obj + current + '"'
                else:
                    s = '"' + current + obj + '"'
                current = ''
        elif isinstance(obj, str):  # add quotation marks
            s = '"' + obj + '"'
        else:
            s = yaml.dump(obj, default_flow_style=True).strip()
            if s.endswith('\n...'):
                s = s[:-4]
        if use_line_edit:
            self.line_edit.insert(s)
        else:
            self.text_edit.insertPlainText(s)


class LabelWidgetLine(QtWidgets.QGroupBox):
    """A widget to change the labels"""

    def __init__(self, fmto, project, *args, **kwargs):
        from psy_simple.widgets.texts import LabelWidget
        super().__init__(f'{fmto.name} ({fmto.key})', *args, **kwargs)
        self.editor = FormatoptionsEditor(fmto)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(LabelWidget(self.editor, fmto, project,
                                   properties=False))
        vbox.addWidget(self.editor)
        self.setLayout(vbox)

class LabelDialog(QtWidgets.QDialog):
    """A widget to change labels"""

    def __init__(self, project, *fmts):
        super().__init__()
        self.project = project
        layout = QtWidgets.QVBoxLayout()
        plotter = project.plotters[0]
        self.fmt_widgets = {}
        for fmt in fmts:
            fmto = getattr(plotter, fmt)
            fmt_widget = LabelWidgetLine(fmto, project)
            self.fmt_widgets[fmt] = fmt_widget
            layout.addWidget(fmt_widget)

        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        self.setLayout(layout)

    @property
    def fmts(self):
        ret = {}
        for fmt, widget in self.fmt_widgets.items():
            if widget.editor.changed:
                try:
                    value = widget.editor.value
                except:
                    raise IOError(f"{fmt}-value {widget.editor.text} could "
                                  "not be parsed to python!")
                else:
                    ret[fmt] = value
        return ret

    @classmethod
    def update_project(cls, project, *fmts):
        dialog = cls(project, *fmts)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec_()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            project.update(
                **dialog.fmts)
