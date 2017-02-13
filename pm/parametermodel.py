import collections
import decimal
import json

import attr
from PyQt5 import QtCore

import epyqlib.abstractcolumns
import epyqlib.pyqabstractitemmodel
import epyqlib.treenode
import epyqlib.utils.general

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


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
    minimum = attr.ib(default=None, convert=to_decimal_or_none)
    maximum = attr.ib(default=None, convert=to_decimal_or_none)
    factory = attr.ib(default=False, convert=two_state_checkbox)

    def __attrs_post_init__(self):
        super().__init__()


@epyqlib.utils.general.indexable_attrs(ignore=ignored_attribute_filter)
@attr.s
class Group(epyqlib.treenode.TreeNode):
    _type = attr.ib(default='group', init=False, metadata={'ignore': True})
    name = attr.ib()
    fill0 = epyqlib.utils.general.filler_attribute()
    fill1 = epyqlib.utils.general.filler_attribute()
    fill2 = epyqlib.utils.general.filler_attribute()
    children = attr.ib(default=attr.Factory(list), metadata={'ignore': True})

    def __attrs_post_init__(self):
        super().__init__()


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

        elif obj_type == 'parameter':
            obj.pop('_type')
            return Parameter(**obj)

        elif obj_type == 'group':
            obj.pop('_type')
            children = obj.pop('children')
            node = Group(**obj)

            for child in children:
                node.append_child(child)

            return node

        raise Exception('Unexpected object found: {}'.format(obj))


class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, list):
            return obj

        elif isinstance(obj, (Parameter, Group)):
            d = attr.asdict(obj,
                            recurse=False,
                            dict_factory=collections.OrderedDict,
                            filter=lambda a, _: a.metadata.get('to_file', True))

            if isinstance(obj, Group):
                if obj.tree_parent is None:
                    return [self.default(c) for c in d['children']]

        elif isinstance(obj, decimal.Decimal):
            i = int(obj)
            if i == obj:
                d = i
            else:
                d = float(obj)

        return d


class Model(epyqlib.pyqabstractitemmodel.PyQAbstractItemModel):
    def __init__(self, root=None, parent=None):
        if root is None:
            root = Group(name='root')

        super().__init__(root=root, attrs=True, parent=parent)

        self.headers = [a.name.title() for a in Parameter('').public_fields]

    @classmethod
    def from_json_string(cls, s):
        root = Group(name='root')

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

        if isinstance(node, Parameter):
            if node.public_fields[index.column()].convert is two_state_checkbox:
                checkable = True

        if checkable:
            flags |= QtCore.Qt.ItemIsUserCheckable
        elif node.public_fields[index.column()].metadata.get('editable', True):
            flags |= QtCore.Qt.ItemIsEditable

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
            try:
                node[index.column()] = data
            except ValueError:
                return False
            else:
                self.dataChanged.emit(index, index)
                return True
        elif role == QtCore.Qt.CheckStateRole:
            node[index.column()] = node.public_fields[index.column()].convert(data)

            return True

        return False
