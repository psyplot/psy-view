"""Dialogs for manipulating formatoptions."""
import yaml
from PyQt5 import QtWidgets, QtGui
from matplotlib.backends.backend_qt5agg import (
    FigureCanvasQTAgg as FigureCanvas)
from matplotlib.figure import Figure


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
        self.txt_meri_every.setValidator(QtGui.QDoubleValidator(0, 360, 7))

        self.opt_meri_num = QtWidgets.QRadioButton("Number:")
        self.txt_meri_num = QtWidgets.QLineEdit()
        self.txt_meri_num.setPlaceholderText("5")
        self.txt_meri_num.setValidator(QtGui.QIntValidator(1, 720))

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
        self.txt_para_every.setValidator(QtGui.QDoubleValidator(0, 90, 7))

        self.opt_para_num = QtWidgets.QRadioButton("Number:")
        self.txt_para_num = QtWidgets.QLineEdit()
        self.txt_para_num.setPlaceholderText("5")
        self.txt_para_num.setValidator(QtGui.QIntValidator(1, 360))

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

    def __init__(self, project, *args, **kwargs):
        import psy_simple.widgets.colors as pswc
        super().__init__(*args, **kwargs)
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel,
            self)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.fmt_widgets = {}
        plotter = project(fmts=['cmap', 'bounds']).plotters[0]

        self.cmap_widget = self.fmt_widgets['cmap'] = LabelWidgetLine(
            plotter.cmap, project, pswc.CMapFmtWidget,
            widget_kws=dict(properties=False))
        self.cmap_widget.editor.setVisible(False)
        self.cmap_widget.editor.line_edit.textChanged.connect(
            self.update_preview)

        self.tabs = QtWidgets.QTabWidget()

        self.bounds_widget = self.fmt_widgets['bounds'] = LabelWidgetLine(
            plotter.bounds, project, pswc.BoundsFmtWidget,
            widget_kws=dict(properties=False))
        self.bounds_widget.editor.line_edit.textChanged.connect(
            self.update_preview)
        self.tabs.addTab(self.bounds_widget, "Colormap boundaries")

        self.cticks_widget = self.fmt_widgets['cticks'] = LabelWidgetLine(
            plotter.cticks, project, pswc.CTicksFmtWidget,
            widget_kws=dict(properties=False))
        self.cticks_widget.editor.line_edit.textChanged.connect(
            self.update_preview)
        self.tabs.addTab(self.cticks_widget, "Colorbar ticks")

        self.cbar_preview = ColorbarPreview(plotter)
        self.cbar_preview.setMaximumHeight(self.tabs.sizeHint().height() // 3)

        vbox = QtWidgets.QVBoxLayout(self)
        vbox.addWidget(self.cmap_widget)
        vbox.addWidget(self.tabs)
        vbox.addWidget(self.cbar_preview)
        vbox.addWidget(self.button_box)

    @property
    def plotter(self):
        return self.bounds_widget.editor.fmto.plotter

    def update_preview(self):
        try:
            bounds = self.bounds_widget.editor.value
        except Exception:
            bounds = self.plotter.bounds.value
        try:
            cticks = self.cticks_widget.editor.value
        except Exception:
            cticks = self.plotter.cticks.value
        try:
            cmap = self.cmap_widget.editor.value
        except Exception:
            cmap = self.plotter.cmap.value
        self.cbar_preview.update_colorbar(
            bounds=bounds, cticks=cticks, cmap=cmap)

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
    def update_project(cls, project):
        dialog = cls(project)
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()
        dialog.exec_()
        if dialog.result() == QtWidgets.QDialog.Accepted:
            project.update(**dialog.fmts)


class ColorbarPreview(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, plotter, parent=None, *args, **kwargs):
        fig = Figure(*args, **kwargs)

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QtWidgets.QSizePolicy.Expanding,
                                   QtWidgets.QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)
        self.axes_counter = 0

        self.plotter = plotter
        self.init_colorbar(plotter)

    def resizeEvent(self, event):
        h = event.size().height()
        if h <= 0:
            return
        return super().resizeEvent(event)

    def init_colorbar(self, plotter):
        from matplotlib.cm import ScalarMappable
        norm = plotter.bounds.norm
        cmap = plotter.cmap.get_cmap(self.plotter.plot.array)

        self.mappable = sm = ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])

        self.cax = self.figure.add_axes([0.1, 0.5, 0.8, 0.5],
                                        label=self.axes_counter)

        self.cbar = self.figure.colorbar(
            sm, norm=norm, cmap=cmap, cax=self.cax, orientation='horizontal')

    @property
    def fake_plotter(self):
        from psyplot.plotter import Plotter

        class FakePlotter(Plotter):
            bounds = self.plotter.bounds.__class__('bounds')
            cmap = self.plotter.cmap.__class__('cmap')
            cticks = self.plotter.cticks.__class__('cticks')
            cbar = self.plotter.cbar.__class__('cbar')

            _rcparams_string = self.plotter._get_rc_strings()

        ref = self.plotter
        fig = Figure()
        ax = fig.add_subplot()

        plotter = FakePlotter(
            ref.data.copy(), make_plot=False, bounds=ref['bounds'],
            cmap=ref['cmap'], cticks=ref['cticks'], cbar='', ax=ax)

        plotter.cticks._colorbar = self.cbar

        plotter.plot_data = ref.plot_data
        return plotter

    def update_colorbar(self, **kwargs):
        plotter = self.fake_plotter

        try:
            for key, val in kwargs.items():
                plotter[key] = val
        except (ValueError, TypeError):
            return

        plotter.initialize_plot(ax=plotter.ax)

        current_norm = self.mappable.norm
        current_cmap = self.mappable.get_cmap()
        current_locator = self.cbar.locator


        try:
            try:
                plotter.bounds.norm._check_vmin_vmax()
            except (AttributeError, TypeError):
                pass
            try:
                plotter.bounds.norm.autoscale_None(plotter.bounds.array)
            except AttributeError:
                pass
            self.mappable.set_norm(plotter.bounds.norm)
            self.mappable.set_cmap(plotter.cmap.get_cmap(
                self.plotter.plot.array))
            plotter.cticks.colorbar = self.cbar
            plotter.cticks.default_locator = \
                self.plotter.cticks.default_locator
            plotter.cticks.update_axis(plotter.cticks.value)
            self.draw()

        except Exception:
            self.mappable.set_norm(current_norm)
            self.mappable.set_cmap(current_cmap)
            self.cbar.locator = current_locator
            self.cbar.update_ticks()


class FormatoptionsEditor(QtWidgets.QWidget):
    """A widget to update a formatoption"""

    def __init__(self, fmto, *args, **kwargs):
        super().__init__(*args, **kwargs)
        layout = QtWidgets.QHBoxLayout()

        self.fmto = fmto

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

    @property
    def changed(self):
        return self.fmto.diff(self.fmto.validate(self.get_obj()))

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

    @text.setter
    def text(self, s):
        self.clear_text()
        if self.multiline:
            self.text_edit.insertPlainText(s)
        else:
            self.line_edit.insert(s)

    @property
    def value(self):
        text = self.text
        return yaml.load(text, Loader=yaml.Loader)

    def clear_text(self):
        if self.multiline:
            self.text_edit.clear()
        else:
            self.line_edit.clear()

    def set_obj(self, obj):
        self.clear_text()
        self.insert_obj(obj)

    def get_obj(self):
        return self.value

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

    def __init__(self, fmto, project, fmto_widget,
                 widget_kws={}, *args, **kwargs):
        super().__init__(f'{fmto.name} ({fmto.key})', *args, **kwargs)
        self.editor = FormatoptionsEditor(fmto)
        vbox = QtWidgets.QVBoxLayout()
        vbox.addWidget(
            fmto_widget(self.editor, fmto, project, **widget_kws))
        vbox.addWidget(self.editor)
        self.setLayout(vbox)


class LabelDialog(QtWidgets.QDialog):
    """A widget to change labels"""

    def __init__(self, project, *fmts):
        from psy_simple.widgets.texts import LabelWidget
        super().__init__()
        self.project = project
        layout = QtWidgets.QVBoxLayout()
        plotter = project.plotters[0]
        self.fmt_widgets = {}
        for fmt in fmts:
            fmto = getattr(plotter, fmt)
            fmt_widget = LabelWidgetLine(
                fmto, project, LabelWidget, widget_kws=dict(properties=False))
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
