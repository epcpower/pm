import collections
import decimal

import attr
from PyQt5 import QtCore

import epyqlib.treenode
import epyqlib.utils.general

import pm.attrsmodel
import pm.parametermodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@epyqlib.utils.general.indexable_attrs(
    ignore=pm.attrsmodel.ignored_attribute_filter)
@attr.s
class Signal(epyqlib.treenode.TreeNode):
    _type = attr.ib(default='signal', init=False, metadata={'ignore': True})
    name = attr.ib(default='New Signal')
    fill0 = epyqlib.utils.general.filler_attribute()
    fill1 = epyqlib.utils.general.filler_attribute()
    parameter_uuid = pm.attrsmodel.attr_uuid(ignore=False)
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

    @classmethod
    def addable_types(cls):
        return {}

    def can_drop_on(self, node):
        return False


@epyqlib.utils.general.indexable_attrs(
    ignore=pm.attrsmodel.ignored_attribute_filter)
@attr.s
class Message(epyqlib.treenode.TreeNode):
    _type = attr.ib(default='message', init=False, metadata={'ignore': True})
    name = attr.ib(default='New Message')
    identifier = attr.ib(default='0x1fffffff')
    extended = attr.ib(default=True,
                       convert=pm.attrsmodel.two_state_checkbox)
    cycle_time = attr.ib(default=None,
                         convert=pm.attrsmodel.to_decimal_or_none)
    children = attr.ib(
        default=attr.Factory(list),
        hash=False,
        metadata={
            'ignore': True,
            'valid_types': (Signal,)
        }
    )
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

    @classmethod
    def addable_types(cls):
        types = tuple(
            __class__ if t is None else t
            for t in attr.fields(cls).children.metadata['valid_types']
        )

        d = collections.OrderedDict()

        for t in types:
            type_attribute = attr.fields(t)._type
            name = type_attribute.default.title()
            name = type_attribute.metadata.get('human name', name)
            d[name] = t

        return d

    def can_drop_on(self, node):
        print('blue')
        x = (*self.addable_types().values(), pm.parametermodel.Parameter)

        return isinstance(node, x)

    def child_from(self, node):
        return Signal(name=node.name, parameter_uuid=str(node.uuid))



Root = pm.attrsmodel.Root(
    default_name='Symbols',
    valid_types=(Message,)
)

types = (Root, Message, Signal)