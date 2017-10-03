import collections

import PyQt5.QtCore
import attr

import epyqlib.attrsmodel
import epyqlib.treenode
import epyqlib.utils.general
import epyqlib.utils.qt

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Parameter(epyqlib.treenode.TreeNode):
    type = attr.ib(default='parameter', init=False)
    name = attr.ib(default='New Parameter')
    default = attr.ib(default=None, convert=epyqlib.attrsmodel.to_decimal_or_none)
    minimum = attr.ib(default=None, convert=epyqlib.attrsmodel.to_decimal_or_none)
    maximum = attr.ib(default=None, convert=epyqlib.attrsmodel.to_decimal_or_none)
    nv = attr.ib(default=False, convert=epyqlib.attrsmodel.two_state_checkbox)
    read_only = attr.ib(default=False, convert=epyqlib.attrsmodel.two_state_checkbox)
    factory = attr.ib(default=False, convert=epyqlib.attrsmodel.two_state_checkbox)
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
        return isinstance(node, tuple(self.addable_types().values()))

    @PyQt5.QtCore.pyqtProperty('PyQt_PyObject')
    def pyqtify_minimum(self):
        return epyqlib.utils.qt.pyqtify_get(self, 'minimum')

    @pyqtify_minimum.setter
    def pyqtify_minimum(self, value):
        epyqlib.utils.qt.pyqtify_set(self, 'minimum', value)
        if None not in (value, self.maximum):
            if value > self.maximum:
                self.maximum = value

    @PyQt5.QtCore.pyqtProperty('PyQt_PyObject')
    def pyqtify_maximum(self):
        return epyqlib.utils.qt.pyqtify_get(self, 'maximum')

    @pyqtify_maximum.setter
    def pyqtify_maximum(self, value):
        epyqlib.utils.qt.pyqtify_set(self, 'maximum', value)
        if None not in (value, self.minimum):
            if value < self.minimum:
                self.minimum = value


@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class ArrayGroup(epyqlib.treenode.TreeNode):
    type = attr.ib(default='array_group', init=False)
    name = attr.ib(default='New Array Group')
    length = attr.ib(
        default=1,
        convert=int,
        # metadata={'property': 'length'},
    )
    children = attr.ib(
        default=attr.Factory(list),
        cmp=False,
        init=False,
        metadata={'valid_types': (Parameter, 'Group', None)}
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()
        self.append_child(Parameter(name=''))

    # @classmethod
    # def from_json(cls, obj):
    #     children = obj.pop('children')
    #     node = cls(**obj)
    #
    #     for child in children:
    #         node.append_child(child)
    #
    #     return node
    #
    # def to_json(self):
    #     return attr.asdict(
    #         self,
    #         recurse=False,
    #         dict_factory=collections.OrderedDict,
    #         filter=lambda a, _: a.metadata.get('to_file', True)
    #     )

    def can_drop_on(self, node):
        return isinstance(node, tuple(self.addable_types().values()))


@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class EnumerationParameter(epyqlib.treenode.TreeNode):
    type = attr.ib(
        default='parameter.enumeration',
        init=False,
        metadata={'ignore': True}
    )
    name = attr.ib()
    minimum = attr.ib(default=None, convert=epyqlib.attrsmodel.to_decimal_or_none)
    maximum = attr.ib(default=None, convert=epyqlib.attrsmodel.to_decimal_or_none)
    factory = attr.ib(default=False, convert=epyqlib.attrsmodel.two_state_checkbox)

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self):
        return False


@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Group(epyqlib.treenode.TreeNode):
    type = attr.ib(default='group', init=False)
    name = attr.ib(default='New Group')
    children = attr.ib(
        default=attr.Factory(list),
        cmp=False,
        init=False,
        metadata={'valid_types': (Parameter, ArrayGroup, None)}
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
        return isinstance(node, tuple(self.addable_types().values()))


Root = epyqlib.attrsmodel.Root(
    default_name='Parameters',
    valid_types=(Parameter, Group)
)

types = epyqlib.attrsmodel.Types(
    types=(Root, Parameter, EnumerationParameter, Group, ArrayGroup),
)

columns = epyqlib.attrsmodel.columns(
    (
        (Parameter, 'name'),
        (Group, 'name'),
        (ArrayGroup, 'name'),
    ),
    ((ArrayGroup, 'length'),),
    ((Parameter, 'default'),),
    ((Parameter, 'minimum'),),
    ((Parameter, 'maximum'),),
    ((Parameter, 'nv'),),
    ((Parameter, 'read_only'),),
    ((Parameter, 'factory'),)
)

