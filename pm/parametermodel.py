import collections
import decimal
import json
import logging

import attr
from PyQt5 import QtCore

import epyqlib.abstractcolumns
import epyqlib.pyqabstractitemmodel
import epyqlib.treenode
import epyqlib.utils.general

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


logger = logging.getLogger()


def to_decimal_or_none(s):
    if s is None:
        return None

    try:
        result = decimal.Decimal(s)
    except decimal.InvalidOperation as e:
        raise ValueError('Invalid number: {}'.format(repr(s))) from e

    return result


def two_state_checkbox(v):
    return v in (QtCore.Qt.Checked, True)


def ignored_attribute_filter(attribute):
    return not attribute.metadata.get('ignore', False)


@epyqlib.utils.general.indexable_attrs(ignore=ignored_attribute_filter)
@attr.s
class Parameter(epyqlib.treenode.TreeNode):
    _type = attr.ib(default='parameter', init=False, metadata={'ignore': True})
    name = attr.ib()
    default = attr.ib(default=None, convert=to_decimal_or_none)
    minimum = attr.ib(default=None, convert=to_decimal_or_none)
    maximum = attr.ib(default=None, convert=to_decimal_or_none)
    nv = attr.ib(default=False, convert=two_state_checkbox)
    read_only = attr.ib(default=False, convert=two_state_checkbox)
    factory = attr.ib(default=False, convert=two_state_checkbox)

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

    def can_drop_on(self):
        return False


@epyqlib.utils.general.indexable_attrs(ignore=ignored_attribute_filter)
@attr.s
class EnumerationParameter(epyqlib.treenode.TreeNode):
    _type = attr.ib(
        default='parameter.enumeration',
        init=False,
        metadata={'ignore': True}
    )
    name = attr.ib()
    minimum = attr.ib(default=None, convert=to_decimal_or_none)
    maximum = attr.ib(default=None, convert=to_decimal_or_none)
    factory = attr.ib(default=False, convert=two_state_checkbox)

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self):
        return False


@epyqlib.utils.general.indexable_attrs(ignore=ignored_attribute_filter)
@attr.s
class Group(epyqlib.treenode.TreeNode):
    _type = attr.ib(default='group', init=False, metadata={'ignore': True})
    name = attr.ib()
    fill0 = epyqlib.utils.general.filler_attribute()
    fill1 = epyqlib.utils.general.filler_attribute()
    fill2 = epyqlib.utils.general.filler_attribute()
    fill3 = epyqlib.utils.general.filler_attribute()
    fill4 = epyqlib.utils.general.filler_attribute()
    fill5 = epyqlib.utils.general.filler_attribute()
    children = attr.ib(default=attr.Factory(list), hash=False,
                       metadata={'ignore': True})

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

    def can_drop_on(self):
        return True


types = (Parameter, EnumerationParameter, Group)


class Decoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook,
                         parse_float=decimal.Decimal,
                         parse_int=decimal.Decimal,
                         *args,
                         **kwargs)

    def object_hook(self, obj):
        obj_type = obj.get('_type', None)

        if isinstance(obj, list):
            return obj

        for t in types:
            if obj_type == t._type.default:
                obj.pop('_type')
                return t.from_json(obj)

        raise Exception('Unexpected object found: {}'.format(obj))


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, list):
            return obj

        elif type(obj) == epyqlib.treenode.TreeNode:
            if obj.tree_parent is None:
                return [self.default(c) for c in obj.children]

        elif isinstance(obj, types):
            d = obj.to_json()

        elif isinstance(obj, decimal.Decimal):
            i = int(obj)
            if i == obj:
                d = i
            else:
                d = float(obj)

        return d


class Model(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    def __init__(self, root, parent=None):
        super().__init__(root=root, attrs=True, parent=parent)

        self.headers = [a.name.replace('_', ' ').title()
                        for a in types[0].public_fields]

        self.mime_map = {}

    @classmethod
    def from_json_string(cls, s):
        root = epyqlib.treenode.TreeNode()

        children = json.loads(s, cls=Decoder)
        for child in children:
            root.append_child(child)

        return cls(root=root)

    def to_json_string(self):
        return json.dumps(self.root, cls=Encoder, indent=4)

    def flags(self, index):
        flags = super().flags(index)

        node = self.node_from_index(index)

        checkable = False

        if node.public_fields[index.column()].convert is two_state_checkbox:
            checkable = True

        if checkable:
            flags |= QtCore.Qt.ItemIsUserCheckable
        elif node.public_fields[index.column()].metadata.get('editable', True):
            flags |= QtCore.Qt.ItemIsEditable

        flags |= QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsDropEnabled

        return flags

    def data_display(self, index):
        node = self.node_from_index(index)

        if node.public_fields[index.column()].convert is two_state_checkbox:
            return ''

        result = super().data_display(index)

        return str(result)

    def data_edit(self, index):
        result = super().data_edit(index)

        return str(result)

    def data_check_state(self, index):
        node = self.node_from_index(index)

        if node.public_fields[index.column()].convert is two_state_checkbox:
            if node[index.column()]:
                return QtCore.Qt.Checked
            else:
                return QtCore.Qt.Unchecked

        return None

    def setData(self, index, data, role=None):
        node = self.node_from_index(index)

        if role == QtCore.Qt.EditRole:
            convert = node.public_fields[index.column()].convert
            if convert is not None:
                try:
                    converted = convert(data)
                except ValueError:
                    return False
            else:
                converted = data

            node[index.column()] = converted

            self.dataChanged.emit(index, index)
            return True
        elif role == QtCore.Qt.CheckStateRole:
            node[index.column()] = node.public_fields[index.column()].convert(data)

            return True

        return False

    def add_group(self, parent, group=None):
        if group is None:
            group = Group(name='New Group')

        self.add_child(parent=parent, child=group)

    def add_parameter(self, parent, parameter=None):
        if parameter is None:
            parameter = Parameter(name='New Parameter')

        self.add_child(parent=parent, child=parameter)

    def add_child(self, parent, child):
        row = len(parent.children)
        self.begin_insert_rows(parent, row, row)
        parent.append_child(child)
        self.end_insert_rows()

    def delete(self, node):
        row = node.tree_parent.row_of_child(node)
        self.begin_remove_rows(node.tree_parent, row, row)
        node.tree_parent.remove_child(child=node)
        self.end_remove_rows()

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def mimeData(self, indexes):
        import random

        data = bytearray()

        for index in indexes:
            while True:
                key = random.randrange(2**(4*8))

                if key not in self.mime_map:
                    logger.debug('create: {}'.format(key))
                    self.mime_map[key] = index
                    data.extend(key.to_bytes(4, 'big'))
                    break

        m = QtCore.QMimeData()
        m.setData('mine', data)

        return m

    def dropMimeData(self, data, action, row, column, parent):
        logger.debug('\nentering dropMimeData()')
        logger.debug((data, action, row, column, parent))
        new_parent = self.node_from_index(parent)
        if row == -1 and column == -1:
            if parent.isValid():
                row = 0
            else:
                row = len(self.root.children)

        decoded = self.decode_data(bytes(data.data('mine')))
        node = decoded[0]
        if action == QtCore.Qt.MoveAction:
            logger.debug('node name: {}'.format(node.name))
            logger.debug(data, action, row, column, parent)
            logger.debug('dropped on: {}'.format(new_parent.name))

            from_row = node.tree_parent.row_of_child(node)

            success = self.beginMoveRows(
                self.index_from_node(node.tree_parent),
                from_row,
                from_row,
                self.index_from_node(new_parent),
                row
            )

            if not success:
                return False

            node.tree_parent.remove_child(child=node)
            new_parent.insert_child(row, node)

            self.endMoveRows()

            return True

        return False

    def canDropMimeData(self, mime, action, row, column, parent):
        parent = self.node_from_index(parent)
        logger.debug('canDropMimeData: {}: {}'.format(parent.name, row))
        return parent.can_drop_on()

    def decode_data(self, data):
        keys = tuple(int.from_bytes(key, 'big') for key
                     in epyqlib.utils.general.grouper(data, 4))

        nodes = tuple(self.node_from_index(self.mime_map[key])
                      for key in keys)

        return nodes
