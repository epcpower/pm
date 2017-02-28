import collections
import decimal

import attr
from PyQt5 import QtCore

import epyqlib.treenode
import epyqlib.utils.general

import pm.attrsmodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@epyqlib.utils.general.indexable_attrs(
    ignore=pm.attrsmodel.ignored_attribute_filter)
@attr.s
class Parameter(epyqlib.treenode.TreeNode):
    _type = attr.ib(default='parameter', init=False, metadata={'ignore': True})
    name = attr.ib(default='New Parameter')
    default = attr.ib(default=None, convert=pm.attrsmodel.to_decimal_or_none)
    minimum = attr.ib(default=None, convert=pm.attrsmodel.to_decimal_or_none)
    maximum = attr.ib(default=None, convert=pm.attrsmodel.to_decimal_or_none)
    nv = attr.ib(default=False, convert=pm.attrsmodel.two_state_checkbox)
    read_only = attr.ib(default=False, convert=pm.attrsmodel.two_state_checkbox)
    factory = attr.ib(default=False, convert=pm.attrsmodel.two_state_checkbox)

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

    def can_drop_on(self):
        return False


@epyqlib.utils.general.indexable_attrs(
    ignore=pm.attrsmodel.ignored_attribute_filter)
@attr.s
class EnumerationParameter(epyqlib.treenode.TreeNode):
    _type = attr.ib(
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


@epyqlib.utils.general.indexable_attrs(
    ignore=pm.attrsmodel.ignored_attribute_filter)
@attr.s
class Group(epyqlib.treenode.TreeNode):
    _type = attr.ib(default='group', init=False, metadata={'ignore': True})
    name = attr.ib(default='New Group')
    fill0 = epyqlib.utils.general.filler_attribute()
    fill1 = epyqlib.utils.general.filler_attribute()
    fill2 = epyqlib.utils.general.filler_attribute()
    fill3 = epyqlib.utils.general.filler_attribute()
    fill4 = epyqlib.utils.general.filler_attribute()
    fill5 = epyqlib.utils.general.filler_attribute()
    children = attr.ib(
        default=attr.Factory(list),
        hash=False,
        metadata={
            'ignore': True,
            'valid_types': (Parameter, None)
        }
    )

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

    def can_drop_on(self):
        return True


types = (Parameter, EnumerationParameter, Group)
