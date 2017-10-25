import collections
import contextlib
import functools
import io
import logging
import os
import pathlib

import attr
import graham
import pycparser.c_ast
import pycparser.c_generator
import PyQt5.QtCore
from PyQt5 import QtCore, QtGui, QtWidgets
import PyQt5.uic

import epyqlib.attrsmodel
import epyqlib.utils.qt

import epcpm.parametermodel
import epcpm.parameterstoc
import epcpm.project
import epcpm.symbolmodel
import epcpm.symbolstosym

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@attr.s
class ModelView:
    view = attr.ib()
    # filename = attr.ib()
    droppable_from = attr.ib()
    columns = attr.ib()
    types = attr.ib()
    root_factory = attr.ib()
    extras = attr.ib(default=attr.Factory(collections.OrderedDict))
    model = attr.ib(default=None)
    proxy = attr.ib(default=None)
    selection = attr.ib(default=None)


class Window:
    def __init__(self, title, ui_file, icon_path):
        # # TODO: CAMPid 980567566238416124867857834291346779
        # ico_file = os.path.join(QtCore.QFileInfo.absolutePath(QtCore.QFileInfo(__file__)), 'icon.ico')
        # ico = QtGui.QIcon(ico_file)
        # self.setWindowIcon(ico)

        logging.debug('Loading UI from: {}'.format(ui_file))

        self.ui = PyQt5.uic.loadUi(pathlib.Path(
            pathlib.Path(__file__).parents[0],
            ui_file,
        ))

        self.ui.action_new.triggered.connect(lambda _: self.open())
        self.ui.action_open.triggered.connect(lambda _: self.open_from_dialog())
        self.ui.action_save.triggered.connect(lambda _: self.save())
        self.ui.action_save_as.triggered.connect(self.save_as)

        self.ui.setWindowTitle(title)

        self.ui.setWindowIcon(QtGui.QIcon(str(icon_path)))

        self.project_filters = [
            ('Parameter Project', ['pmp']),
            ('All Files', ['*'])
        ]

        self.data_filters = [
            ('JSON', ['json']),
            ('All Files', ['*'])
        ]

        self.view_models = {}

        self.uuid_notifier = epcpm.symbolmodel.ReferencedUuidNotifier()
        self.uuid_notifier.changed.connect(self.symbol_uuid_changed)

        self.project = None

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

    def open_from_dialog(self):
        filename = epyqlib.utils.qt.file_dialog(self.project_filters, parent=self.ui)

        if filename is None:
            return

        self.open(filename=filename)

    def open(self, filename=None):
        if filename is None:
            self.project = epcpm.project.Project()
        else:
            with open(filename) as f:
                self.project = graham.schema(epcpm.project.Project).loads(
                    f.read(),
                ).data

            self.project.filename = pathlib.Path(filename).resolve()

        self.project.models.parameters = ModelView(
            view=self.ui.parameter_view,
            droppable_from=('parameters',),
            columns=epcpm.parametermodel.columns,
            types=epcpm.parametermodel.types,
            root_factory=epcpm.parametermodel.Root,
            extras=collections.OrderedDict((
                ('Generate code...', self.generate_code),
            )),
        )

        self.project.models.symbols = ModelView(
            view=self.ui.symbol_view,
            droppable_from=('parameters', 'symbols'),
            columns=epcpm.symbolmodel.columns,
            types=epcpm.symbolmodel.types,
            root_factory=epcpm.symbolmodel.Root,
            extras=collections.OrderedDict((
                ('Generate .sym...', self.generate_symbol_file),
            )),
        )

        self.uuid_notifier.disconnect_view()

        i = zip(self.project.models.items(), self.project.paths.values())
        for (name, model), path in i:
            view = model.view

            view.setSelectionBehavior(view.SelectRows)
            view.setSelectionMode(view.SingleSelection)
            view.setDropIndicatorShown(True)
            view.setDragEnabled(True)
            view.setAcceptDrops(True)

            if path is None:
                model.model = epyqlib.attrsmodel.Model(
                    root=model.root_factory(),
                    columns=model.columns,
                )
            else:
                with open(self.project.filename.parents[0] / path) as f:
                    raw = f.read()
                    # TODO: should be a root_type if we are doing this
                    root_schema = graham.schema(model.root_factory)
                    root = root_schema.loads(raw).data

                    model.model = epyqlib.attrsmodel.Model(
                        root=root,
                        columns=model.columns,
                    )

            self.set_model(name=name, view_model=model)
            view.expandAll()
            for i in range(model.model.columnCount(QtCore.QModelIndex())):
                view.resizeColumnToContents(i)

            view.setContextMenuPolicy(
                QtCore.Qt.CustomContextMenu)
            m = functools.partial(
                self.context_menu,
                view_model=model
            )

            with contextlib.suppress(TypeError):
                view.customContextMenuRequested.disconnect()

            view.customContextMenuRequested.connect(m)

        self.uuid_notifier.set_view(self.ui.symbol_view)

        for view_model in self.project.models.values():
            view_model.model.add_drop_sources(*(
                self.project.models[d].model.root
                for d in view_model.droppable_from
            ))

        return

    def save(self):
        self.project.save(parent=self.ui)

    def save_as(self):
        project = attr.evolve(self.project)
        project.filename = None
        # TODO: this is still going to mutate the same object as the
        #       original project is referencing
        project.paths.set_all(None)

        project.save(parent=self.ui)
        self.project = project

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

        if node.can_delete():
            delete = menu.addAction('Delete')

        menu.addSeparator()

        extra_actions = {
            menu.addAction(name): function
            for name, function in view_model.extras.items()
        }

        action = menu.exec(
            view_model.view.viewport().mapToGlobal(position)
        )

        if action is not None:
            extra = extra_actions.get(action)
            if extra is not None:
                extra(node)
            elif action is delete:
                node.tree_parent.remove_child(child=node)
            else:
                node.append_child(actions[action]())

    def generate_code(self, node):
        builder = epcpm.parameterstoc.builders.wrap(node)
        ast = pycparser.c_ast.FileAST(builder.definition())
        generator = pycparser.c_generator.CGenerator()
        s = generator.visit(ast)
        epyqlib.utils.qt.dialog(
            parent=self.ui,
            message=s,
            modal=False,
        )

    def generate_symbol_file(self, node):
        builder = epcpm.symbolstosym.builders.wrap(node)

        epyqlib.utils.qt.dialog(
            parent=self.ui,
            message=builder.gen(),
            modal=False,
        )

    def selection_changed(self, selected, deselected):
        pass

    def symbol_uuid_changed(self, uuid):
        view_model = self.view_models['parameters']
        model = view_model.model
        view = view_model.view

        try:
            node = model.node_from_uuid(uuid)
        except epyqlib.attrsmodel.NotFoundError:
            return

        index = model.index_from_node(node)
        index = epyqlib.utils.qt.resolve_index_from_model(
            model=model,
            view=view,
            index=index,
        )

        view.setCurrentIndex(index)
        view.selectionModel().select(
            index,
            QtCore.QItemSelectionModel.ClearAndSelect,
        )
