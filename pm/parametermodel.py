import collections
import decimal
import json

import attr
from PyQt5 import QtCore

import epyqlib.abstractcolumns
import epyqlib.pyqabstractitemmodel
import epyqlib.treenode

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


def to_decimal_or_none(s):
    if s is None:
        return None

    return decimal.Decimal(s)


@attr.s
class Parameter(epyqlib.treenode.TreeNode):
    name = attr.ib()
    minimum = attr.ib(default=None, convert=to_decimal_or_none)
    maximum = attr.ib(default=None, convert=to_decimal_or_none)

    columns = (a.name for a in (name, minimum, maximum))

    def __attrs_post_init__(self):
        super().__init__()

    def get(self, index):
        names = [a.name for a in attr.fields(type(self))
                 if not a.metadata.get('ignore', False)]

        return getattr(self, names[index])

    def set_data(self, column_index, value):
        names = [a.name for a in attr.fields(type(self))
                 if not a.metadata.get('ignore', False)]

        setattr(self, names[column_index], value)


@attr.s
class Group(epyqlib.treenode.TreeNode):
    name = attr.ib()
    children = attr.ib(default=attr.Factory(list), metadata={'ignore': True})

    def __attrs_post_init__(self):
        super().__init__()

    def get(self, index):
        names = [a.name for a in attr.fields(type(self))
                 if not a.metadata.get('ignore', False)]

        return getattr(self, names[index])

    def set_data(self, column_index, value):
        names = [a.name for a in attr.fields(type(self))
                 if not a.metadata.get('ignore', False)]

        setattr(self, names[column_index], value)


class Decoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook,
                         parse_float=decimal.Decimal,
                         parse_int=decimal.Decimal,
                         *args,
                         **kwargs)

    def object_hook(self, obj):
        obj_type = obj.get('type', None)

        if isinstance(obj, list):
            return obj

        elif obj_type == 'parameter':
            obj.pop('type')
            return Parameter(**obj)

        elif obj_type == 'group':
            obj.pop('type')
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

        elif isinstance(obj, Parameter):
            d = attr.asdict(obj, recurse=False, dict_factory=collections.OrderedDict)

            d['type'] = 'parameter'
            d.move_to_end('type', last=False)

        elif isinstance(obj, Group):
            d = attr.asdict(obj, recurse=False, dict_factory=collections.OrderedDict)

            if obj.tree_parent is None:
                return [self.default(c) for c in d['children']]

            d['type'] = 'group'
            d.move_to_end('type', last=False)

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

        self.headers = [a.name.title() for a in attr.fields(Parameter)
                        if not a.metadata.get('ignore', False)]

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

        flags |= QtCore.Qt.ItemIsEditable

        return flags

    def data_display(self, index):
        result = super().data_display(index)

        return str(result)

    def data_edit(self, index):
        result = super().data_edit(index)

        return str(result)

    def setData(self, index, data, role=None):
        if role == QtCore.Qt.EditRole:
            node = self.node_from_index(index)
            try:
                node.set_data(index.column(), data)
            except ValueError:
                return False
            else:
                self.dataChanged.emit(index, index)
                return True

        return False
