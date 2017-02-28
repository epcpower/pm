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
class Message(epyqlib.treenode.TreeNode):
    _type = attr.ib(default='message', init=False, metadata={'ignore': True})
    name = attr.ib()
    identifier = attr.ib()
    extended = attr.ib(default=True,
                       convert=pm.attrsmodel.two_state_checkbox)
    cycle_time = attr.ib(default=None,
                         convert=pm.attrsmodel.to_decimal_or_none)
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

    def can_drop_on(self):
        return False


Root = pm.attrsmodel.Root(
    default_name='Symbols',
    valid_types=(None, Message,)
)

types = (Root, Message,)
