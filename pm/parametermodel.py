import collections
import decimal
import functools

import attr
from PyQt5 import QtCore

import epyqlib.treenode
import epyqlib.utils.general

import pm.attrsmodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@pm.attrsmodel.add_addable_types()
@attr.s
class Parameter(epyqlib.treenode.TreeNode):
    type = attr.ib(default='parameter', init=False)
    name = attr.ib(default='New Parameter')
    default = attr.ib(default=None, convert=pm.attrsmodel.to_decimal_or_none)
    minimum = attr.ib(default=None, convert=pm.attrsmodel.to_decimal_or_none)
    maximum = attr.ib(default=None, convert=pm.attrsmodel.to_decimal_or_none)
    nv = attr.ib(default=False, convert=pm.attrsmodel.two_state_checkbox)
    read_only = attr.ib(default=False, convert=pm.attrsmodel.two_state_checkbox)
    factory = attr.ib(default=False, convert=pm.attrsmodel.two_state_checkbox)
    uuid = pm.attrsmodel.attr_uuid()

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


@pm.attrsmodel.add_addable_types()
@attr.s
class EnumerationParameter(epyqlib.treenode.TreeNode):
    type = attr.ib(
        default='parameter.enumeration',
        init=False,
        metadata={'ignore': True}
    )
    name = attr.ib()
    minimum = attr.ib(default=None, convert=pm.attrsmodel.to_decimal_or_none)
    maximum = attr.ib(default=None, convert=pm.attrsmodel.to_decimal_or_none)
    factory = attr.ib(default=False, convert=pm.attrsmodel.two_state_checkbox)

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self):
        return False


@pm.attrsmodel.add_addable_types()
@attr.s
class Group(epyqlib.treenode.TreeNode):
    type = attr.ib(default='group', init=False)
    name = attr.ib(default='New Group')
    children = attr.ib(
        default=attr.Factory(list),
        hash=False,
        cmp=False,
        metadata={'valid_types': (Parameter, None)}
    )
    uuid = pm.attrsmodel.attr_uuid()

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


Root = pm.attrsmodel.Root(
    default_name='Parameters',
    valid_types=(Parameter, Group)
)

types = (Root, Parameter, EnumerationParameter, Group)

columns = pm.attrsmodel.columns(
    ((Parameter, Parameter.name), (Group, Group.name)),
    ((Parameter, Parameter.default),),
    ((Parameter, Parameter.minimum),),
    ((Parameter, Parameter.maximum),),
    ((Parameter, Parameter.nv),),
    ((Parameter, Parameter.read_only),),
    ((Parameter, Parameter.factory),)
)

