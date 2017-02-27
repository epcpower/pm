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

        self.ui.action_open.triggered.connect(lambda _: self.open())
        self.ui.action_save.triggered.connect(lambda _: self.save())
        self.ui.action_save_as.triggered.connect(self.save_as)

        self.filters = [
            ('JSON', ['json']),
            ('All Files', ['*'])
        ]

        self.model = None
        self.proxy = None
        self.set_model(pm.parametermodel.Model())

        self.ui.tree_view.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.ui.tree_view.customContextMenuRequested.connect(
            self.context_menu
        )

        self.ui.tree_view.setSelectionMode(
            QtWidgets.QAbstractItemView.ExtendedSelection)
        self.ui.tree_view.setDropIndicatorShown(True)
        self.ui.tree_view.setDragEnabled(True)
        self.ui.tree_view.setAcceptDrops(True)
        self.ui.tree_view.setDragDropMode(
            QtWidgets.QAbstractItemView.InternalMove)

        self.selection_model = self.ui.tree_view.selectionModel()
        self.selection_model.selectionChanged.connect(
            self.selection_changed)

        self.filename = None

    def set_model(self, model):
        self.model = model

        self.proxy = QtCore.QSortFilterProxyModel()
        self.proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        self.proxy.setSourceModel(self.model)
        self.ui.tree_view.setModel(self.proxy)

    def open(self, file=None):
        if file is None:
            filename = epyqlib.utils.qt.file_dialog(self.filters, parent=self.ui)

            if filename is None:
                return

            with open(filename) as f:
                s = f.read()
        else:
            s = file.read()
            filename = os.path.abspath(file.name)

        model = pm.parametermodel.Model.from_json_string(s)
        self.set_model(model)
        self.ui.tree_view.expandAll()
        for i, _ in enumerate(model.root):
            self.ui.tree_view.resizeColumnToContents(i)
        self.filename = filename

        return

    def save(self, filename=None):
        if filename is None:
            filename = self.filename

        if filename is None:
            return

        s = self.model.to_json_string()

        with open(filename, 'w') as f:
            f.write(s)

            if not s.endswith('\n'):
                f.write('\n')

    def save_as(self):
        filename = epyqlib.utils.qt.file_dialog(
            self.filters, parent=self.ui, save=True)

        if filename is not None:
            self.save(filename=filename)

    def context_menu(self, position):
        index = self.ui.tree_view.indexAt(position)
        index = self.ui.tree_view.model().mapToSource(index)

        node = self.model.node_from_index(index)

        menu = QtWidgets.QMenu(parent=self.ui.tree_view)

        add_group = menu.addAction('Add Group')
        add_parameter = menu.addAction('Add Parameter')
        delete = menu.addAction('Delete')

        if isinstance(node, pm.parametermodel.Parameter):
            add_group.setEnabled(False)
            add_parameter.setEnabled(False)

        action = menu.exec(self.ui.tree_view.viewport().mapToGlobal(position))

        if action is None:
            pass
        elif action is add_group:
            self.model.add_group(parent=node)
        elif action is add_parameter:
            self.model.add_parameter(parent=node)
        elif action is delete:
            self.model.delete(node=node)

    def selection_changed(self, selected, deselected):
        pass
