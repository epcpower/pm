import io
import logging
import os

from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.uic

import epyqlib.utils.qt

import pm.parametermodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


class Window:
    def __init__(self, ui_file):
        # # TODO: CAMPid 980567566238416124867857834291346779
        # ico_file = os.path.join(QtCore.QFileInfo.absolutePath(QtCore.QFileInfo(__file__)), 'icon.ico')
        # ico = QtGui.QIcon(ico_file)
        # self.setWindowIcon(ico)

        logging.debug('Loading UI from: {}'.format(ui_file))

        ui = ui_file
        # TODO: CAMPid 9549757292917394095482739548437597676742
        if not QtCore.QFileInfo(ui).isAbsolute():
            ui_file = os.path.join(
                QtCore.QFileInfo.absolutePath(QtCore.QFileInfo(__file__)), ui)
        else:
            ui_file = ui
        ui_file = QtCore.QFile(ui_file)
        ui_file.open(QtCore.QFile.ReadOnly | QtCore.QFile.Text)
        ts = QtCore.QTextStream(ui_file)
        sio = io.StringIO(ts.readAll())
        self.ui = PyQt5.uic.loadUi(sio)

        self.ui.action_open.triggered.connect(self.open)
        self.ui.action_save_as.triggered.connect(self.save_as)

        self.filters = [
            ('JSON', ['json']),
            ('All Files', ['*'])
        ]


        self.set_model(pm.parametermodel.Model())

    def set_model(self, model):
        self.model = model

        self.proxy = QtCore.QSortFilterProxyModel()
        self.proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxy.setSourceModel(self.model)
        self.ui.tree_view.setModel(self.proxy)

    def open(self):
        filename = epyqlib.utils.qt.file_dialog(self.filters, parent=self.ui)

        if filename is not None:
            with open(filename) as f:
                s = f.read()

            self.set_model(pm.parametermodel.Model.from_json_string(s))

    def save_as(self):
        filename = epyqlib.utils.qt.file_dialog(
            self.filters, parent=self.ui, save=True)

        if filename is not None:
            s = self.model.to_json_string()

            with open(filename, 'w') as f:
                f.write(s)
