import collections

import attr

import epyqlib.treenode
import epyqlib.utils.general

import epcpm.attrsmodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


@epcpm.attrsmodel.add_addable_types()
@attr.s(hash=False)
class Parameter(epyqlib.treenode.TreeNode):
    type = attr.ib(default='parameter', init=False)
    name = attr.ib(default='New Parameter')
    default = attr.ib(default=None, convert=epcpm.attrsmodel.to_decimal_or_none)
    minimum = attr.ib(default=None, convert=epcpm.attrsmodel.to_decimal_or_none)
    maximum = attr.ib(default=None, convert=epcpm.attrsmodel.to_decimal_or_none)
    nv = attr.ib(default=False, convert=epcpm.attrsmodel.two_state_checkbox)
    read_only = attr.ib(default=False, convert=epcpm.attrsmodel.two_state_checkbox)
    factory = attr.ib(default=False, convert=epcpm.attrsmodel.two_state_checkbox)
    uuid = epcpm.attrsmodel.attr_uuid()

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


@epcpm.attrsmodel.add_addable_types()
@attr.s(hash=False)
class ArrayGroup(epyqlib.treenode.TreeNode):
    type = attr.ib(default='array_group', init=False)
    name = attr.ib(default='New Array Group')
    _length = attr.ib(
        default=1,
        convert=int,
        # metadata={'property': 'length'},
    )
    children = attr.ib(
        default=attr.Factory(list),
        cmp=False,
        init=False,
        metadata={'valid_types': ()}
    )
    uuid = epcpm.attrsmodel.attr_uuid()

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


@epcpm.attrsmodel.add_addable_types()
@attr.s(hash=False)
class EnumerationParameter(epyqlib.treenode.TreeNode):
    type = attr.ib(
        default='parameter.enumeration',
        init=False,
        metadata={'ignore': True}
    )
    name = attr.ib()
    minimum = attr.ib(default=None, convert=epcpm.attrsmodel.to_decimal_or_none)
    maximum = attr.ib(default=None, convert=epcpm.attrsmodel.to_decimal_or_none)
    factory = attr.ib(default=False, convert=epcpm.attrsmodel.two_state_checkbox)

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self):
        return False


@epcpm.attrsmodel.add_addable_types()
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
    uuid = epcpm.attrsmodel.attr_uuid()

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


Root = epcpm.attrsmodel.Root(
    default_name='Parameters',
    valid_types=(Parameter, Group)
)

types = (Root, Parameter, EnumerationParameter, Group, ArrayGroup)

columns = epcpm.attrsmodel.columns(
    (
        (Parameter, Parameter.name),
        (Group, Group.name),
        (ArrayGroup, ArrayGroup.name),
    ),
    ((ArrayGroup, ArrayGroup._length),),
    ((Parameter, Parameter.default),),
    ((Parameter, Parameter.minimum),),
    ((Parameter, Parameter.maximum),),
    ((Parameter, Parameter.nv),),
    ((Parameter, Parameter.read_only),),
    ((Parameter, Parameter.factory),)
)

