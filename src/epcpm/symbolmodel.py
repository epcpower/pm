import collections

import attr
import PyQt5.QtCore

import epyqlib.attrsmodel
import epyqlib.treenode
import epyqlib.utils.general
import epyqlib.utils.qt

import epcpm.parametermodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Signal(epyqlib.treenode.TreeNode):
    type = attr.ib(default='signal', init=False)
    name = attr.ib(default='New Signal')
    parameter_uuid = epyqlib.attrsmodel.attr_uuid(
        metadata={'human name': 'Parameter UUID'})
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    @classmethod
    def from_json(cls, obj):
        return cls(**obj)

    def to_json(self):
        return attr.asdict(
            self,
            recurse=False,
            dict_factory=collections.OrderedDict,
            filter=lambda a, _: a.metadata.get('to_file', True)
        )

    def can_drop_on(self, node):
        return False


@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Message(epyqlib.treenode.TreeNode):
    type = attr.ib(default='message', init=False, metadata={'ignore': True})
    name = attr.ib(default='New Message')
    identifier = attr.ib(default='0x1fffffff')
    extended = attr.ib(default=True,
                       convert=epyqlib.attrsmodel.two_state_checkbox)
    cycle_time = attr.ib(default=None,
                         convert=epyqlib.attrsmodel.to_decimal_or_none)
    children = attr.ib(
        default=attr.Factory(list),
        metadata={'valid_types': (Signal,)}
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    @classmethod
    def from_json(cls, obj):
        children = obj.pop('children')
        node = cls(**obj)

        for child in children:
            node.append_child(child)

        return node

    def to_json(self):
        return attr.asdict(
            self,
            recurse=False,
            dict_factory=collections.OrderedDict,
            filter=lambda a, _: a.metadata.get('to_file', True)
        )

    def can_drop_on(self, node):
        x = (*self.addable_types().values(), epcpm.parametermodel.Parameter)

        return isinstance(node, x)

    def child_from(self, node):
        return Signal(name=node.name, parameter_uuid=str(node.uuid))


Root = epyqlib.attrsmodel.Root(
    default_name='Symbols',
    valid_types=(Message,)
)

types = epyqlib.attrsmodel.Types(
    types=(Root, Message, Signal),
)

columns = epyqlib.attrsmodel.columns(
    ((Message, 'name'), (Signal, 'name')),
    ((Message, 'identifier'),),
    ((Message, 'extended'),),
    ((Message, 'cycle_time'),),
    ((Signal, 'parameter_uuid'),)
)


@attr.s
class ReferencedUuidNotifier(PyQt5.QtCore.QObject):
    changed = PyQt5.QtCore.pyqtSignal('PyQt_PyObject')

    view = attr.ib(default=None)
    selection_model = attr.ib(default=None)

    def __attrs_post_init__(self):
        super().__init__()

        if self.view is not None:
            self.set_view(self.view)

    def set_view(self, view):
        self.disconnect_view()

        self.view = view
        self.selection_model = self.view.selectionModel()
        self.selection_model.currentChanged.connect(
            self.current_changed,
        )

    def disconnect_view(self):
        if self.selection_model is not None:
            self.selection_model.currentChanged.disconnect(
                self.current_changed,
            )
        self.view = None
        self.selection_model = None

    def current_changed(self, current, previous):
        index, model = epyqlib.utils.qt.resolve_index_to_model(
            view=self.view,
            index=current,
        )
        node = model.node_from_index(index)
        if isinstance(node, Signal):
            self.changed.emit(node.parameter_uuid)
