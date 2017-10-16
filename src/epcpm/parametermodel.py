import collections
import uuid

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
    type_name = attr.ib(default=None, convert=epyqlib.attrsmodel.to_str_or_none)
    # TODO: CAMPid 1342975467516679768543165421
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

    can_delete = epyqlib.attrsmodel.childless_can_delete


@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Group(epyqlib.treenode.TreeNode):
    type = attr.ib(default='group', init=False)
    name = attr.ib(default='New Group')
    type_name = attr.ib(default=None, convert=epyqlib.attrsmodel.to_str_or_none)
    children = attr.ib(
        default=attr.Factory(list),
        cmp=False,
        init=False,
        metadata={'valid_types': (Parameter, 'Array', None)}
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

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True


@epyqlib.utils.qt.pyqtify()
@epyqlib.utils.qt.pyqtify_passthrough_properties(
    original='original',
    field_names=('nv',),
)
@attr.s(hash=False)
class ArrayParameterElement(epyqlib.treenode.TreeNode):
    type = attr.ib(default='array_parameter_element', init=False)
    name = attr.ib(default='New Array Parameter Element')
    # TODO: CAMPid 1342975467516679768543165421
    default = attr.ib(default=None, convert=epyqlib.attrsmodel.to_decimal_or_none)
    minimum = attr.ib(default=None, convert=epyqlib.attrsmodel.to_decimal_or_none)
    maximum = attr.ib(default=None, convert=epyqlib.attrsmodel.to_decimal_or_none)
    nv = attr.ib(
        default=False,
        init=False,
        convert=epyqlib.attrsmodel.two_state_checkbox,
        metadata={'to_file': False},
    )
    metadata = {'valid_types': ()}
    uuid = epyqlib.attrsmodel.attr_uuid()
    original = attr.ib(default=None, metadata={'to_file': False})

    def __attrs_post_init__(self):
        super().__init__()

    @classmethod
    def from_json(cls, obj):
        instance = cls(**obj)
        # TODO: seems like at least the uuid.UUID stuff should be inside
        #       the model to makes sure the right uuid type etc are used.
        instance.original = uuid.UUID(instance.original)

        return instance

    def to_json(self):
        d = attr.asdict(
            self,
            recurse=False,
            dict_factory=collections.OrderedDict,
            filter=lambda a, _: a.metadata.get('to_file', True)
        )

        d['original'] = self.original.uuid

        return d

    def can_drop_on(self, node):
        return False

    can_delete = epyqlib.attrsmodel.childless_can_delete


@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class ArrayGroupElement(epyqlib.treenode.TreeNode):
    type = attr.ib(default='array_group_element', init=False)
    name = attr.ib(default='New Array Group Element')
    metadata = {'valid_types': ()}
    uuid = epyqlib.attrsmodel.attr_uuid()
    original = attr.ib(default=None)

    def __attrs_post_init__(self):
        super().__init__()

    @classmethod
    def from_json(cls, obj):
        instance = cls(**obj)
        # TODO: seems like at least the uuid.UUID stuff should be inside
        #       the model to makes sure the right uuid type etc are used.
        instance.original = uuid.UUID(instance.original)

        return instance

    def to_json(self):
        d = attr.asdict(
            self,
            recurse=False,
            dict_factory=collections.OrderedDict,
            filter=lambda a, _: a.metadata.get('to_file', True)
        )

        d['original'] = self.original.uuid

        return d

    def can_drop_on(self, node):
        return False

    can_delete = epyqlib.attrsmodel.childless_can_delete


class InvalidArrayLength(Exception):
    pass


@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Array(epyqlib.treenode.TreeNode):
    type = attr.ib(default='array', init=False)
    name = attr.ib(default='New Array')
    length = attr.ib(
        default=1,
        convert=int,
    )
    named_enumerators = attr.ib(
        default=True,
        convert=epyqlib.attrsmodel.two_state_checkbox,
    )
    children = attr.ib(
        default=attr.Factory(list),
        cmp=False,
        init=False,
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    element_types = {
        Parameter: ArrayParameterElement,
        Group: ArrayGroupElement,
    }

    def __attrs_post_init__(self):
        super().__init__()

    @property
    def pyqtify_length(self):
        return epyqlib.utils.qt.pyqtify_get(self, 'length')

    @pyqtify_length.setter
    def pyqtify_length(self, value):
        if value < 1:
            raise InvalidArrayLength('Length must be at least 1')

        if self.children is not None:
            if value < len(self.children):
                for row in range(len(self.children) - 1, value - 1, - 1):
                    self.remove_child(row=row)
            elif value > len(self.children):
                for _ in range(value - len(self.children)):
                    original = self.children[0]
                    type_ = self.element_types[type(original)]
                    self.append_child(type_(original=original))

        epyqlib.utils.qt.pyqtify_set(self, 'length', value)

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types(
            [*cls.element_types.keys(), *cls.element_types.values()],
        )

    def addable_types(self):
        child_types = {type(child) for child in self.children}

        value_types = self.element_types.keys()

        if len(child_types.intersection(set(value_types))) == 0:
            types = value_types
        else:
            # types = (ArrayElement,)
            types = ()

        return epyqlib.attrsmodel.create_addable_types(types)

    @classmethod
    def from_json(cls, obj):
        children = obj.pop('children')
        node = cls(**obj)

        node.append_child(children[0])

        for child in children[1:]:
            if children[0].uuid != child.original:
                raise epyqlib.attrsmodel.ConsistencyError(
                    'UUID mismatch: {} != {}'.format(
                        children[0].uuid,
                        child.original,
                    )
                )

            child.original = children[0]
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

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        if node not in self.children:
            raise epyqlib.attrsmodel.ConsistencyError(
                'Specified node not found in children'
            )

        if len(self.children) > 1:
            return False

        return True


@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class EnumerationParameter(epyqlib.treenode.TreeNode):
    type = attr.ib(
        default='parameter.enumeration',
        init=False,
        metadata={'ignore': True}
    )
    name = attr.ib(default='New Enumeration')
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

    def can_drop_on(self):
        return False

    can_delete = epyqlib.attrsmodel.childless_can_delete


Root = epyqlib.attrsmodel.Root(
    default_name='Parameters',
    valid_types=(Parameter, Group)
)

types = epyqlib.attrsmodel.Types(
    types=(
        Root,
        Parameter,
        EnumerationParameter,
        Group,
        Array,
        ArrayGroupElement,
        ArrayParameterElement,
    ),
)

columns = epyqlib.attrsmodel.columns(
    (
        (Parameter, 'name'),
        (Group, 'name'),
        (Array, 'name'),
        (ArrayParameterElement, 'name'),
        (ArrayGroupElement, 'name'),
        (EnumerationParameter, 'name'),
    ),
    ((Group, 'type_name'), (Parameter, 'type_name')),
    ((Array, 'length'),),
    ((Array, 'named_enumerators'),),
    ((Parameter, 'default'), (ArrayParameterElement, 'default')),
    ((Parameter, 'minimum'), (ArrayParameterElement, 'minimum')),
    ((Parameter, 'maximum'), (ArrayParameterElement, 'maximum')),
    ((Parameter, 'nv'), (ArrayParameterElement, 'nv')),
    ((Parameter, 'read_only'),),
    ((Parameter, 'factory'),)
)
