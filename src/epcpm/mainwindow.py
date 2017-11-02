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
import epcpm.symtoproject

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@attr.s
class ModelView:
    view = attr.ib()
    # filename = attr.ib()
    types = attr.ib()
    extras = attr.ib(default=attr.Factory(collections.OrderedDict))
    model = attr.ib(default=None)
    proxy = attr.ib(default=None)
    selection = attr.ib(default=None)


class Window:
    def __init__(self, title, ui_file, icon_path):
        logging.debug('Loading UI from: {}'.format(ui_file))

        self.ui = PyQt5.uic.loadUi(pathlib.Path(
            pathlib.Path(__file__).parents[0],
            ui_file,
        ))

        self.ui.action_new.triggered.connect(lambda _: self.open())
        self.ui.action_open.triggered.connect(lambda _: self.open_from_dialog())
        self.ui.action_save.triggered.connect(lambda _: self.save())
        self.ui.action_save_as.triggered.connect(self.save_as)
        self.ui.action_import_sym.triggered.connect(self.import_sym)
        self.ui.action_export_sym.triggered.connect(self.generate_symbol_file)

        self.ui.action_about.triggered.connect(self.about_dialog)

        self.ui.setWindowTitle(title)

        logging.debug('Loading icon from: {}'.format(icon_path))
        self.ui.setWindowIcon(QtGui.QIcon(str(icon_path)))

        self.project_filters = [
            ('Parameter Project', ['pmp']),
            ('All Files', ['*'])
        ]

        self.data_filters = [
            ('JSON', ['json']),
            ('All Files', ['*'])
        ]
        self.hierarchy_filters = self.data_filters

        self.can_filters = [
            ('CAN Symbols', ['sym']),
            ('All Files', ['*'])
        ]

        self.view_models = {}

        self.uuid_notifier = epcpm.symbolmodel.ReferencedUuidNotifier()
        self.uuid_notifier.changed.connect(self.symbol_uuid_changed)

        self.project = None

        self.set_title()

    def set_title(self, detail=None):
        title = 'Parameter Manager v{}'.format(epcpm.__version__)

        if detail is not None:
            title = ' - '.join((title, detail))

        self.ui.setWindowTitle(title)

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

    def import_sym(self):
        sym_path = epyqlib.utils.qt.file_dialog(
            filters=self.can_filters,
            parent=self.ui,
        )

        if sym_path is None:
            return

        hierarchy_path = epyqlib.utils.qt.file_dialog(
            filters=self.hierarchy_filters,
            parent=self.ui,
            caption='Open Parameter Hierarchy',
        )

        if hierarchy_path is None:
            return

        with open(sym_path, 'rb') as sym, open(hierarchy_path) as hierarchy:
            parameters_root, symbols_root = epcpm.symtoproject.load_can_file(
                can_file=sym,
                file_type=str(pathlib.Path(sym.name).suffix[1:]),
                parameter_hierarchy_file=hierarchy,
            )

        project = epcpm.project.Project()

        project.models.parameters = epyqlib.attrsmodel.Model(
            root=parameters_root,
            columns=epcpm.parametermodel.columns,
        )
        project.models.symbols = epyqlib.attrsmodel.Model(
            root=symbols_root,
            columns=epcpm.symbolmodel.columns,
        )

        epcpm.project._post_load(project)

        self.open(project=project)

    def open(self, filename=None, project=None):
        if project is not None:
            self.project = project
        else:
            if filename is None:
                self.project = epcpm.project.create_blank()
            else:
                self.project = epcpm.project.loadp(filename)

        model_views = epcpm.project.Models()

        model_views.parameters = ModelView(
            view=self.ui.parameter_view,
            types=epcpm.parametermodel.types,
            extras=collections.OrderedDict((
                ('Generate code...', self.generate_code),
            )),
        )

        model_views.symbols = ModelView(
            view=self.ui.symbol_view,
            types=epcpm.symbolmodel.types,
        )

        self.uuid_notifier.disconnect_view()

        i = zip(model_views.items(), self.project.models.values())
        for (name, model_view), model in i:
            view = model_view.view

            view.setSelectionBehavior(view.SelectRows)
            view.setSelectionMode(view.SingleSelection)
            view.setDropIndicatorShown(True)
            view.setDragEnabled(True)
            view.setAcceptDrops(True)

            if model is None:
                model_view.model = epyqlib.attrsmodel.Model(
                    root=model_view.root_factory(),
                    columns=model_view.columns,
                )
            else:
                model_view.model = model

            self.set_model(name=name, view_model=model_view)
            view.expandAll()
            for i in range(model_view.model.columnCount(QtCore.QModelIndex())):
                view.resizeColumnToContents(i)

            view.setContextMenuPolicy(
                QtCore.Qt.CustomContextMenu)
            m = functools.partial(
                self.context_menu,
                view_model=model_view
            )

            with contextlib.suppress(TypeError):
                view.customContextMenuRequested.disconnect()

            view.customContextMenuRequested.connect(m)

        self.uuid_notifier.set_view(self.ui.symbol_view)

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

        if len(extra_actions) > 0:
            menu.addSeparator()

        expand_all = menu.addAction('Expand All')
        collapse_all = menu.addAction('Collapse All')

        action = menu.exec(
            view_model.view.viewport().mapToGlobal(position)
        )

        if action is not None:
            extra = extra_actions.get(action)
            if extra is not None:
                extra(node)
            elif action is delete:
                node.tree_parent.remove_child(child=node)
            elif action is expand_all:
                view_model.view.expandAll()
            elif action is collapse_all:
                view_model.view.collapseAll()
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

    def generate_symbol_file(self):
        finder = self.view_models['symbols'].model.node_from_uuid
        builder = epcpm.symbolstosym.builders.wrap(
            wrapped=self.view_models['symbols'].model.root,
            parameter_uuid_finder=finder,
            parameter_model=self.view_models['parameters'].model,
        )

        epyqlib.utils.qt.dialog(
            parent=self.ui,
            message=builder.gen(),
            modal=False,
            save_filters=(
                ('CAN Symbols', ['sym']),
                ('All Files', ['*'])
            ),
            save_caption='Save CAN Symbols',
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

    def about_dialog(self):
        message = [
            __copyright__,
            __license__,
            f'Version Tag: {epcpm.__version_tag__}',
            f'Commit SHA: {epcpm.__sha__}',
            f'Build Tag: {epcpm.__build_tag__}',
        ]

        message = '\n'.join(message)

        epyqlib.utils.qt.dialog(
            parent=self.ui,
            title='About',
            message=message,
        )
