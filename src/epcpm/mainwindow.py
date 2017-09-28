import contextlib
import functools
import io
import logging
import os

import attr
from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.uic

import epyqlib.attrsmodel
import epyqlib.utils.qt

import epcpm.parametermodel
import epcpm.symbolmodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@attr.s
class ModelView:
    view = attr.ib()
    filename = attr.ib()
    droppable_from = attr.ib()
    columns = attr.ib()
    types = attr.ib()
    model = attr.ib(default=None)
    proxy = attr.ib(default=None)
    selection = attr.ib(default=None)


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

        self.view_models = {}


        self.filename = None

    def set_model(self, name, view_model):
        self.view_models[name] = view_model

        view_model.proxy = QtCore.QSortFilterProxyModel()
        view_model.proxy.setSortCaseSensitivity(QtCore.Qt.CaseInsensitive)
        view_model.proxy.setSourceModel(view_model.model)
        view_model.view.setModel(view_model.proxy)

        view_model.selection = view_model.view.selectionModel()

        with contextlib.suppress(TypeError):
            view_model.selection.selectionChanged.disconnect()

        view_model.selection.selectionChanged.connect(
            self.selection_changed)

    def open(self, file=None):
        if file is None:
            filename = epyqlib.utils.qt.file_dialog(self.filters, parent=self.ui)

            if filename is None:
                return
        else:
            file.close()
            filename = os.path.abspath(file.name)

        view_models = {
            'parameters': ModelView(
                view=self.ui.parameter_view,
                filename=filename,
                droppable_from=('parameters',),
                columns=epcpm.parametermodel.columns,
                types=epcpm.parametermodel.types
            ),
            'symbols': ModelView(
                view=self.ui.symbol_view,
                filename=filename.replace('parameters', 'symbols'),
                droppable_from=('parameters', 'symbols'),
                columns=epcpm.symbolmodel.columns,
                types=epcpm.symbolmodel.types
            )
        }

        for name, view_model in view_models.items():
            view = view_model.view

            view.setSelectionBehavior(view.SelectRows)
            view.setSelectionMode(view.SingleSelection)
            view.setDropIndicatorShown(True)
            view.setDragEnabled(True)
            view.setAcceptDrops(True)

            with open(view_model.filename) as f:
                view_model.model = epyqlib.attrsmodel.Model.from_json_string(
                    f.read(),
                    columns=view_model.columns,
                    types=view_model.types
                )
            self.set_model(name=name, view_model=view_model)
            view.expandAll()
            for i in range(view_model.model.columnCount(QtCore.QModelIndex())):
                view.resizeColumnToContents(i)
            self.filename = filename

            view.setContextMenuPolicy(
                QtCore.Qt.CustomContextMenu)
            m = functools.partial(
                self.context_menu,
                view_model=view_model
            )

            with contextlib.suppress(TypeError):
                view.customContextMenuRequested.disconnect()

            view.customContextMenuRequested.connect(m)

        for view_model in view_models.values():
            view_model.model.add_drop_sources(*(
                view_models[d].model.root for d in view_model.droppable_from
            ))

        return

    def save(self, filename=None):
        if filename is None:
            filename = self.filename

        if filename is None:
            return

        for view_model in self.view_models.values():
            s = view_model.model.to_json_string()

            with open(view_model.filename, 'w') as f:
                f.write(s)

                if not s.endswith('\n'):
                    f.write('\n')

    def save_as(self):
        filename = epyqlib.utils.qt.file_dialog(
            self.filters, parent=self.ui, save=True)

        if filename is not None:
            self.save(filename=filename)

    def context_menu(self, position, view_model):
        index = view_model.view.indexAt(position)
        index = view_model.view.model().mapToSource(index)

        model = view_model.model
        node = model.node_from_index(index)

        menu = QtWidgets.QMenu(parent=view_model.view)

        delete = None
        addable_types = node.addable_types()
        actions = {
            menu.addAction('Add {}'.format(name)): t
            for name, t in addable_types.items()
        }

        if node is not model.root:
            delete = menu.addAction('Delete')

        action = menu.exec(
            view_model.view.viewport().mapToGlobal(position)
        )

        if action is not None:
            if action is delete:
                model.delete(node=node)
            else:
                model.add_child(parent=node, child=actions[action]())

    def selection_changed(self, selected, deselected):
        pass
