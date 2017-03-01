import collections
import decimal
import json
import logging
import uuid

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


class add_addable_types:
    def __init__(self, attribute='children'):
        self.attribute_name = attribute

    def __call__(self, class_to_decorate):
        @classmethod
        def addable_types(cls):
            if not hasattr(cls, self.attribute_name):
                return {}

            print(cls)
            types = tuple(
                cls if t is None else t
                for t in getattr(attr.fields(cls), self.attribute_name)
                    .metadata['valid_types']
            )

            d = collections.OrderedDict()

            for t in types:
                type_attribute = attr.fields(t)._type
                name = type_attribute.default.title()
                name = type_attribute.metadata.get('human name', name)
                d[name] = t

            return d

        class_to_decorate.addable_types = addable_types

        return class_to_decorate


def Root(default_name, valid_types):
    valid_types = tuple(valid_types)

    @add_addable_types()
    @epyqlib.utils.general.indexable_attrs(
        ignore=ignored_attribute_filter)
    @attr.s
    class Root(epyqlib.treenode.TreeNode):
        _type = attr.ib(default='root', init=False, metadata={'ignore': True})
        name = attr.ib(default=default_name)
        children = attr.ib(
            default=attr.Factory(list),
            hash=False,
            metadata={
                'ignore': True,
                'valid_types': valid_types
            }
        )
        uuid = attr_uuid()

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
            return isinstance(node, tuple(self.addable_types().values()))

    return Root


def attr_uuid(ignore=True):
    return attr.ib(
        default=None,
        convert=lambda x: x if x is None else uuid.UUID(x),
        metadata={'ignore': ignore}
    )


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


class Decoder(json.JSONDecoder):
    types = ()

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

        for t in self.types:
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

        if isinstance(obj, decimal.Decimal):
            i = int(obj)
            if i == obj:
                d = i
            else:
                d = float(obj)
        elif isinstance(obj, uuid.UUID):
            d = str(obj)
        else:
            d = obj.to_json()

        return d


def check_uuids(*roots):
    def collect(node, uuids):
        if node.uuid is not None:
            if node.uuid in uuids:
                raise Exception('Duplicate uuid found: {}'.format(node.uuid))

            uuids.add(node.uuid)

    def set_nones(node, uuids):
        if node.uuid is None:
            while node.uuid is None:
                u = uuid.uuid4()
                if u not in uuids:
                    node.uuid = u
                    uuids.add(node.uuid)

    uuids = set()

    for root in set(roots):
        root.traverse(call_this=collect, payload=uuids, internal_nodes=True)

    for root in set(roots):
        root.traverse(call_this=set_nones, payload=uuids, internal_nodes=True)


class Model(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    def __init__(self, root, header_type, parent=None):
        super().__init__(root=root, attrs=True, parent=parent)

        self.headers = [a.name.replace('_', ' ').title()
                        for a in header_type.public_fields]

        self.droppable_from = set()

        check_uuids(self.root)

    @classmethod
    def from_json_string(cls, s, header_type, types,
                         decoder=Decoder):
        # Ugly but maintains the name 'types' both for the parameter
        # and in D.
        t = types
        del types

        class D(Decoder):
            types = t

        root = json.loads(s, cls=D)

        return cls(
            root=root,
            header_type=header_type
        )

    def to_json_string(self):
        return json.dumps(self.root, cls=Encoder, indent=4)

    def add_drop_sources(self, *sources):
        self.droppable_from.update(sources)
        check_uuids(self.root, *self.droppable_from)

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

    def add_child(self, parent, child):
        row = len(parent.children)
        self.begin_insert_rows(parent, row, row)
        parent.append_child(child)
        if child.uuid is None:
            check_uuids(self.root)

        self.end_insert_rows()

    def delete(self, node):
        row = node.tree_parent.row_of_child(node)
        self.begin_remove_rows(node.tree_parent, row, row)
        node.tree_parent.remove_child(child=node)
        self.end_remove_rows()

    def supportedDropActions(self):
        return QtCore.Qt.MoveAction

    def mimeData(self, indexes):
        [node] = {self.node_from_index(i) for i in indexes}
        m = QtCore.QMimeData()
        m.setData('mine', node.uuid.bytes)

        return m

    def dropMimeData(self, data, action, row, column, parent):
        logger.debug('entering dropMimeData()')
        logger.debug((data, action, row, column, parent))

        node, new_parent, row = self.source_target_for_drop(
            column, data, parent, row)

        if action == QtCore.Qt.MoveAction:
            logger.debug('node name: {}'.format(node.name))
            logger.debug((data, action, row, column, parent))
            logger.debug('dropped on: {}'.format(new_parent.name))

            local = node.find_root() == self.root

            if local:
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
            else:
                new_child = new_parent.child_from(node)
                self.add_child(new_parent, new_child)

        return False

    def source_target_for_drop(self, column, data, parent, row):
        new_parent = self.node_from_index(parent)
        if row == -1 and column == -1:
            if parent.isValid():
                row = 0
            else:
                row = len(self.root.children)
        u = uuid.UUID(bytes=bytes(data.data('mine')))
        source = self.node_from_uuid(u)
        return source, new_parent, row

    def node_from_uuid(self, u):
        def uuid_matches(node, matches):
            if node.uuid == u:
                matches.add(node)

        nodes = set()
        logger.debug('searching for uuid: {}'.format(u))
        for root in self.droppable_from:
            logger.debug('searching in {}'.format(root))
            root.traverse(
                call_this=uuid_matches,
                payload=nodes,
                internal_nodes=True
            )

        [node] = nodes

        return node

    def canDropMimeData(self, mime, action, row, column, parent):
        node, new_parent, _ = self.source_target_for_drop(
            column, mime, parent, row)
        logger.debug('canDropMimeData: {}: {}'.format(new_parent.name, row))
        return new_parent.can_drop_on(node=node)
