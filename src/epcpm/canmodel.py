import itertools
import string
import uuid

import attr
import graham
import marshmallow
import PyQt5.QtCore

import epyqlib.attrsmodel
import epyqlib.checkresultmodel
import epyqlib.pm.parametermodel
import epyqlib.treenode
import epyqlib.utils.general
import epyqlib.utils.qt

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


class ConsistencyError(Exception):
    pass


class IncompleteTableDefinitionError(Exception):
    pass


def based_int(v):
    if isinstance(v, str):
        return int(v, 0)

    return int(v)


def hex_upper(_, value, width=8, prefix='0x', model=None):
    return f'{prefix}{value:0{width}X}'


class HexadecimalIntegerField(marshmallow.fields.Field):
    def _serialize(self, value, attr, obj):
        if self.allow_none and value is None:
            return None

        return hex(value)

    def _deserialize(self, value, attr, data):
        if self.allow_none and value is None:
            return None

        return int(value, 0)


def create_child_signal_from(node):
    name = epyqlib.attrsmodel.fields(Signal).name.converter.suggest(
        node.name,
    )

    return Signal(name=name, parameter_uuid=node.uuid)


@graham.schemify(tag='signal')
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Signal(epyqlib.treenode.TreeNode):
    name = epyqlib.attrsmodel.create_code_identifier_string_attribute(
        default='NewSignal',
    )
    bits = epyqlib.attrsmodel.create_integer_attribute(default=0)
    signed = attr.ib(
        default=False,
        converter=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    factor = attr.ib(
        default=1,
        converter=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(as_string=True),
        ),
    )
    start_bit = epyqlib.attrsmodel.create_integer_attribute(default=0)

    parameter_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
    )
    epyqlib.attrsmodel.attrib(
        attribute=parameter_uuid,
        human_name='Parameter UUID',
    )

    enumeration_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
    )
    epyqlib.attrsmodel.attrib(
        attribute=enumeration_uuid,
        human_name='Enumeration',
        data_display=epyqlib.attrsmodel.name_from_uuid,
        delegate=epyqlib.attrsmodel.RootDelegateCache(
            list_selection_root='enumerations',
        )
    )

    path = attr.ib(
        factory=tuple,
    )
    epyqlib.attrsmodel.attrib(
        attribute=path,
        no_column=True,
    )
    graham.attrib(
        attribute=path,
        field=graham.fields.Tuple(marshmallow.fields.UUID()),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return isinstance(node, epyqlib.pm.parametermodel.Parameter)

    def child_from(self, node):
        self.parameter_uuid = node.uuid

        return None

    can_delete = epyqlib.attrsmodel.childless_can_delete

    def calculated_min_max(self):
        bits = self.bits

        if self.signed:
            bits -= 1

        r = 2 ** bits

        if self.signed:
            minimum = -r
            maximum = r - 1
        else:
            minimum = 0
            maximum = r - 1

        minimum *= self.factor
        maximum *= self.factor

        return minimum, maximum

    @epyqlib.attrsmodel.check_children
    def check(self, result, models):
        results = []

        if self.bits < 1:
            results.append(
                f'Bit length should be greater than zero: {self.bits}',
            )

        for r in results:
            result.append_child(epyqlib.checkresultmodel.Result(
                node=self,
                severity=epyqlib.checkresultmodel.ResultSeverity.warning,
                message=r,
            ))

        return result

    def multiplexer_id_nodes(self):
        return []

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move


@graham.schemify(tag='message')
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Message(epyqlib.treenode.TreeNode):
    name = epyqlib.attrsmodel.create_code_identifier_string_attribute(
        default='NewMessage',
    )

    identifier = attr.ib(
        default=0x1fffffff,
        converter=based_int,
        metadata=graham.create_metadata(
            field=HexadecimalIntegerField(),
        ),
    )
    epyqlib.attrsmodel.attrib(
        data_display=hex_upper,
        attribute=identifier,
    )

    extended = attr.ib(
        default=True,
        converter=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    length = epyqlib.attrsmodel.create_integer_attribute(default=0)
    cycle_time = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(allow_none=True, as_string=True),
        ),
    )
    sendable = attr.ib(
        default=True,
        converter=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    receivable = attr.ib(
        default=True,
        converter=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    comment = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(Signal)),
            )),
        ),
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    @staticmethod
    def child_from(node):
        return create_child_signal_from(node=node)

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types((Signal,))

    def addable_types(self):
        return {}

    def can_drop_on(self, node):
        return isinstance(
            node,
            (
                epyqlib.pm.parametermodel.Parameter,
                Signal,
            ),
        )

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True

    def multiplexer_id_nodes(self):
        return [self]

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(tag='multiplexer')
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Multiplexer(epyqlib.treenode.TreeNode):
    name = epyqlib.attrsmodel.create_code_identifier_string_attribute(
        default='NewMultiplexer',
    )
    identifier = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_int_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(allow_none=True),
        )
    )
    length = epyqlib.attrsmodel.create_integer_attribute(default=0)
    cycle_time = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_decimal_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Decimal(allow_none=True, as_string=True),
        ),
    )
    on_write = epyqlib.attrsmodel.create_str_or_none_attribute()
    comment = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(Signal)),
            )),
        ),
    )

    path = attr.ib(
        factory=tuple,
    )
    epyqlib.attrsmodel.attrib(
        attribute=path,
        no_column=True,
    )
    graham.attrib(
        attribute=path,
        field=graham.fields.Tuple(marshmallow.fields.UUID()),
    )

    path_children = attr.ib(
        factory=tuple,
    )
    epyqlib.attrsmodel.attrib(
        attribute=path_children,
        no_column=True,
    )
    graham.attrib(
        attribute=path_children,
        field=graham.fields.Tuple(marshmallow.fields.UUID()),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def child_from(self, node):
        return create_child_signal_from(node=node)

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types((Signal,))

    def addable_types(self):
        return {}

    def can_drop_on(self, node):
        return isinstance(
            node,
            (
                epyqlib.pm.parametermodel.Parameter,
                Signal,
            ),
        )

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True

    @epyqlib.attrsmodel.check_children
    def check(self, result, models):
        # TODO: we should really get all the mux id's passed in here.
        #       searching for them all from each place is wasteful

        multiplexer_message = self.tree_parent
        while not isinstance(multiplexer_message, MultiplexedMessage):
            multiplexer_message = multiplexer_message.tree_parent

        for other in multiplexer_message.multiplexer_id_nodes():
            if other is self:
                continue

            if other.identifier != self.identifier:
                continue

            result.append_child(epyqlib.checkresultmodel.Result(
                node=other,
                severity=epyqlib.checkresultmodel.ResultSeverity.error,
                message=f'MUX ID {self.identifier} is in use by {other.name}',
            ))

        x = set()
        for signal in self.children:
            parameter = models['parameters'].node_from_uuid(
                u=signal.parameter_uuid,
            )
            x.add(parameter.uses_interface_item())

        if len(x) > 1:
            result.append_child(epyqlib.checkresultmodel.Result(
                node=self,
                severity=epyqlib.checkresultmodel.ResultSeverity.error,
                message=f'uses both new-style interface items and old',
            ))

        return result

    def multiplexer_id_nodes(self):
        return [self]

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move


@graham.schemify(tag='multiplexed_message')
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class MultiplexedMessage(epyqlib.treenode.TreeNode):
    name = epyqlib.attrsmodel.create_code_identifier_string_attribute(
        default='NewMultiplexedMessage',
    )

    identifier = attr.ib(
        default=0x1fffffff,
        converter=based_int,
        metadata=graham.create_metadata(
            field=HexadecimalIntegerField(),
        ),
    )
    epyqlib.attrsmodel.attrib(
        data_display=hex_upper,
        attribute=identifier,
    )

    extended = attr.ib(
        default=True,
        converter=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    length = epyqlib.attrsmodel.create_integer_attribute(default=0)
    sendable = attr.ib(
        default=True,
        converter=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    receivable = attr.ib(
        default=True,
        converter=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    comment = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(Signal)),
                marshmallow.fields.Nested(graham.schema(Multiplexer)),
                marshmallow.fields.Nested('CanTable'),
            )),
        ),
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return isinstance(
            node,
            (
                *self.addable_types().values(),
                epyqlib.pm.parametermodel.Table,
            ),
        )

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types(
            (
                Signal,
                Multiplexer,
                CanTable,
            ),
        )

    def addable_types(self):
        types = (Signal,)

        if len(self.children) > 0:
            types += (Multiplexer, CanTable)

        return epyqlib.attrsmodel.create_addable_types(types)

    @staticmethod
    def child_from(node):
        if isinstance(node, epyqlib.pm.parametermodel.Parameter):
            return create_child_signal_from(node=node)

        if isinstance(node, epyqlib.pm.parametermodel.Table):
            return CanTable(table_uuid=node.uuid)

        return node

    def multiplexer_id_nodes(self):
        return list(itertools.chain.from_iterable(
            child.multiplexer_id_nodes()
            for child in self.children
        ))

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(tag='multiplexed_message_clone')
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class MultiplexedMessageClone(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Multiplexed Message Clone',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )

    identifier = attr.ib(
        default=0x1fffffff,
        converter=based_int,
        metadata=graham.create_metadata(
            field=HexadecimalIntegerField(),
        ),
    )
    epyqlib.attrsmodel.attrib(
        data_display=hex_upper,
        attribute=identifier,
    )

    original = attr.ib(
        default=None,
        metadata=graham.create_metadata(
            field=epyqlib.attrsmodel.Reference(allow_none=True),
        ),
    )
    epyqlib.attrsmodel.attrib(
        data_display=lambda node, value, model: node.original.name,
        attribute=original,
    )
    sendable = attr.ib(
        default=True,
        converter=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    receivable = attr.ib(
        default=True,
        converter=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )
    comment = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
            )),
        ),
    )
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return isinstance(node, MultiplexedMessage)

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types(())

    @staticmethod
    def addable_types():
        return epyqlib.attrsmodel.create_addable_types(())

    def child_from(self, node):
        self.original = node

        return None

    @staticmethod
    def remove_old_on_drop(node):
        return False

    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(tag='table', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class CanTable(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Table',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    multiplexer_range_first = attr.ib(
        default=0,
        converter=based_int,
        metadata=graham.create_metadata(
            field=HexadecimalIntegerField(),
        ),
    )
    multiplexer_range_last = attr.ib(
        default=0x100,
        converter=based_int,
        metadata=graham.create_metadata(
            field=HexadecimalIntegerField(),
        ),
    )

    table_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
    )
    epyqlib.attrsmodel.attrib(
        attribute=table_uuid,
        human_name='Table UUID',
    )

    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(Multiplexer)),
                marshmallow.fields.Nested(graham.schema(Signal)),
            )),
        ),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types(())

    def addable_types(self):
        return {}

    def can_drop_on(self, node):
        return (
            isinstance(node, epyqlib.pm.parametermodel.Table)
            or (
                isinstance(node, Signal)
                and node.tree_parent is self
            )
        )

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True

    def update(self, table=None, warn=False):
        array_uuid_to_signal = {
            child.parameter_uuid: child
            for child in self.children
            if isinstance(child, Signal)
        }

        existing_signal_order = [
            node
            for node in self.children
            if isinstance(node, Signal)
        ]

        for signal in array_uuid_to_signal.values():
            self.remove_child(child=signal)

        nodes = self.recursively_remove_children()

        if self.table_uuid is None:
            return

        root = self.find_root()
        model = root.model

        if table is None:
            table = model.node_from_uuid(self.table_uuid)
        elif table.uuid != self.table_uuid:
            raise ConsistencyError()

        old_by_path = {}
        for node in nodes:
            if isinstance(node, Multiplexer):
                path = (*node.path, node.path_children)
            else:
                path = node.path
            old_by_path[path] = node

        arrays = [
            child
            for child in table.children
            if isinstance(child, epyqlib.pm.parametermodel.Array)
        ]

        groups = [
            child
            for child in table.children
            if isinstance(child, epyqlib.pm.parametermodel.Group)
        ]

        for array in arrays:
            signal = array_uuid_to_signal.get(array.uuid)

            if signal is None:
                signal = Signal(
                    name=array.name,
                    parameter_uuid=array.uuid,
                )
                array_uuid_to_signal[array.uuid] = signal
            else:
                signal.name = array.name
                signal.parameter_uuid = array.uuid

            self.append_child(signal)

        manually_ordered = [
            model.node_from_uuid(node.parameter_uuid)
            for node in existing_signal_order
            if isinstance(node, Signal)
        ]

        for group in groups:
            orderer = epyqlib.utils.general.Orderer.build(
                ordered=manually_ordered,
            )
            for parameter in sorted(group.children, key=orderer):
                signal = array_uuid_to_signal.get(parameter.uuid)

                if signal is None:
                    signal = Signal(
                        name=parameter.name,
                        parameter_uuid=parameter.uuid,
                    )
                    array_uuid_to_signal[parameter.uuid] = signal
                else:
                    signal.name = parameter.name
                    signal.parameter_uuid = parameter.uuid

                self.append_child(signal)

        # TODO: backmatching
        def my_sorted(sequence, order):
            s = sequence
            for o, r in reversed(order):
                d = {c: i for i, c in enumerate(r)}
                s = sorted(s, key=lambda x: d[model.node_from_uuid(x.path[o]).name])

            return s

        # TODO: backmatching
        leaves = table.group.leaves()
        if table.uuid == uuid.UUID('ed3bf0c2-9eed-4203-929b-d85f2e7300c5'): # Frequency
            leaves = my_sorted(
                leaves,
                (
                    (1, ('RideThrough', 'Trip')),
                    (0, ('Low', 'High')),
                    (2, ('0', '1', '2', '3')),
                    (3, ('Before', 'seconds', 'hertz', 'After')),
                ),
            )
        elif table.uuid == uuid.UUID('b148f2a8-6605-4aac-a235-9c66581c213b'):  # Voltage
            leaves = my_sorted(
                leaves,
                (
                    (1, ('RideThrough', 'Trip')),
                    (0, ('Low', 'High')),
                    (2, ('0', '1', '2', '3')),
                    (3, ('Before', 'seconds', 'percent', 'After')),
                ),
            )
        elif table.uuid == uuid.UUID('b1c598b8-1a56-42eb-94b8-85c3b434d7a7'):  # VoltVar
            leaves = my_sorted(
                leaves,
                (
                    (0, ('0', '1', '2', '3')),
                    (1, ('Before', 'Settings', 'percent_nominal_volts',
                         'percent_nominal_var', 'After')),
                ),
            )
        elif table.uuid == uuid.UUID('6ea3bd0d-3799-4d2d-8998-a45dc80eb0bd'):  # HertzWatts  (was incorrectly HertzWatts instead of HzWatts that would never have been reached)
            leaves = my_sorted(
                leaves,
                (
                    (0, ('0', '1', '2', '3')),
                    (1, ('Before', 'Settings', 'hertz', 'percent_nominal_pwr', 'After')),
                ),
            )
        elif table.uuid == uuid.UUID('3e435024-5cad-4af0-81f8-dac56fbcc629'):  # VoltWatts  (was incorrectly HertzWatts duplicate that would never have been reached)
            leaves = my_sorted(
                leaves,
                (
                    (0, ('0', '1', '2', '3')),
                    (1, ('Before', 'Settings', 'percent_nominal_volts', 'percent_nominal_pwr', 'After')),
                ),
            )

        # TODO: this is arrays and groups...
        leaf_groups = [
            list(group[1])
            for group in itertools.groupby(
                leaves,
                key=lambda leaf: leaf.path[:-1],
            )
        ]

        mux_value = self.multiplexer_range_first

        warned_signals = set()

        for leaf_group in leaf_groups:
            is_group = False
            type_reference = leaf_group[0].original.tree_parent
            if isinstance(type_reference, epyqlib.pm.parametermodel.Array):
                signal = array_uuid_to_signal[leaf_group[0].path[-2]]
            elif isinstance(type_reference, epyqlib.pm.parametermodel.Group):
                signal = array_uuid_to_signal[leaf_group[0].path[-1]]
                is_group = True
                orderer = epyqlib.utils.general.Orderer.build(
                    ordered=manually_ordered,
                    key=lambda item: item.original
                )
                leaf_group = sorted(leaf_group, key=orderer)
            else:
                if warn:
                    # TODO: this really needs to be done through a logging
                    #       mechanism of some sort
                    from PyQt5 import QtWidgets

                    nodes = []
                    parent = self
                    while parent != None:
                        nodes.append(parent)
                        parent = parent.tree_parent

                    s = '/'.join(node.name for node in reversed(nodes))
                    message = (
                        f'{s} has no arrays or groups, these are required'
                    )
                    if PyQt5.QtCore.QCoreApplication.instance() is None:
                        print(message)
                    else:
                        epyqlib.utils.qt.dialog(
                            # parent=_parent,
                            parent=None,
                            title='Table Error',
                            message=message,
                            icon=QtWidgets.QMessageBox.Warning,
                        )

                return

            if not is_group:
                # TODO: actually calculate space to use
                per_message = int(48 / signal.bits)
            else:
                # TODO: yeah...
                per_message = 9999

            chunks = list(
                epyqlib.utils.general.chunker(leaf_group, n=per_message),
            )
            for chunk, letter in zip(chunks, string.ascii_uppercase):
                path = chunk[0].path

                path_nodes = [model.node_from_uuid(u) for u in path]

                enumerators = []
                other = []
                for node in path_nodes[:-1]:
                    if len(other) > 0:
                        other.append(node.name)
                        continue

                    # TODO: backmatching
                    if node.tree_parent.name != 'Curves' and isinstance(node, epyqlib.pm.parametermodel.Enumerator):
                        enumerators.append(node.name)
                        continue

                    other.append(node.name)

                path_string = '_'.join([
                    ''.join(name for name in enumerators),
                    *other,
                    *([letter] if len(chunks) > 1 else []),
                ])
                multiplexer_path = chunk[0].path[:-1]
                multiplexer_path_children = tuple(
                    element.path[-1]
                    for element in chunk
                )
                multiplexer = old_by_path.get(
                    (*multiplexer_path, multiplexer_path_children)
                )
                if multiplexer is None:
                    multiplexer = Multiplexer(
                        name=path_string,
                        identifier=mux_value,
                        path=multiplexer_path,
                        path_children=multiplexer_path_children,
                    )
                else:
                    multiplexer.name = path_string
                    multiplexer.identifier = mux_value
                    multiplexer.path = multiplexer_path
                    multiplexer.path_children = multiplexer_path_children

                multiplexer.length = 8

                mux_value += 1

                stripped_chunk = []
                for element in chunk:
                    # TODO: CAMPid 095477901347190347070134
                    if is_group:
                        reference_signal = array_uuid_to_signal[element.path[-1]]
                    else:
                        reference_signal = signal

                    if reference_signal.bits == 0:
                        if warn:
                            # TODO: this really needs to be done through a logging
                            #       mechanism of some sort
                            from PyQt5 import QtWidgets

                            if reference_signal not in warned_signals:
                                nodes = []
                                parent = reference_signal
                                while parent != None:
                                    nodes.append(parent)
                                    parent = parent.tree_parent

                                s = '/'.join(
                                    node.name for node in reversed(nodes))
                                message = (
                                    f'{s} has bit length of {reference_signal.bits}'
                                    f', must be nonzero'
                                )
                                if PyQt5.QtCore.QCoreApplication.instance() is None:
                                    print(message)
                                else:
                                    epyqlib.utils.qt.dialog(
                                        # parent=_parent,
                                        parent=None,
                                        title='Table Error',
                                        message=message,
                                        icon=QtWidgets.QMessageBox.Warning,
                                    )
                                warned_signals.add(signal)
                        continue

                    stripped_chunk.append(element)

                # TODO: backmatching
                if not is_group:
                    start_bit = 64 - per_message * signal.bits
                    if signal.name == 'Settings':
                        start_bit = 64 - len(stripped_chunk) * signal.bits
                else:
                    total_bits = sum(
                        array_uuid_to_signal[element.path[-1]].bits
                        for element in stripped_chunk
                    )
                    start_bit = 64 - total_bits

                for array_element in stripped_chunk:
                    # TODO: CAMPid 095477901347190347070134
                    if is_group:
                        reference_signal = array_uuid_to_signal[array_element.path[-1]]
                    else:
                        reference_signal = signal
                    signal_path = array_element.path

                    new_signal = old_by_path.get(signal_path)
                    if new_signal is None:
                        new_signal = Signal(
                            name=array_element.name,
                            # TODO: backmatching
                            start_bit=(
                                start_bit
                                if array_element.name != 'YScale'
                                else 16
                            ),
                            bits=reference_signal.bits,
                            factor=reference_signal.factor,
                            signed=reference_signal.signed,
                            enumeration_uuid=reference_signal.enumeration_uuid,
                            parameter_uuid=array_element.uuid,
                            path=signal_path,
                        )
                    else:
                        new_signal.name = array_element.name
                        # TODO: backmatching
                        new_signal.start_bit = (
                            start_bit
                            if array_element.name != 'YScale'
                            else 16
                        )
                        new_signal.bits = reference_signal.bits
                        new_signal.factor = reference_signal.factor
                        new_signal.signed = reference_signal.signed
                        new_signal.enumeration_uuid = reference_signal.enumeration_uuid
                        new_signal.parameter_uuid = array_element.uuid
                        new_signal.path = signal_path

                    multiplexer.append_child(new_signal)
                    start_bit += new_signal.bits

                self.append_child(multiplexer)

    def child_from(self, node):
        if isinstance(node, epyqlib.pm.parametermodel.Table):
            self.table_uuid = node.uuid
            return None

        if isinstance(node, Signal):
            return node

        raise Exception('unexpected')

    def multiplexer_id_nodes(self):
        return list(itertools.chain.from_iterable(
            child.multiplexer_id_nodes()
            for child in self.children
        ))

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


Root = epyqlib.attrsmodel.Root(
    default_name='CAN',
    valid_types=(
        Message,
        MultiplexedMessage,
        MultiplexedMessageClone,
        CanTable,
    ),
)

types = epyqlib.attrsmodel.Types(
    types=(
        Root,
        Message,
        Signal,
        MultiplexedMessage,
        MultiplexedMessageClone,
        Multiplexer,
        CanTable,
    ),
)


# TODO: CAMPid 943896754217967154269254167
def merge(name, *types):
    return tuple((x, name) for x in types)


columns = epyqlib.attrsmodel.columns(
    merge('name', *types.types.values()),
    merge(
        'identifier',
        Message,
        MultiplexedMessage,
        MultiplexedMessageClone,
        Multiplexer,
    ),
    merge('multiplexer_range_first', CanTable),
    merge('multiplexer_range_last', CanTable),
    (
        merge('length', Message, Multiplexer, MultiplexedMessage)
        + merge('bits', Signal)
    ),
    merge('extended', Message, MultiplexedMessage),

    merge('enumeration_uuid', Signal),

    merge('cycle_time', Message, Multiplexer),

    merge('table_uuid', CanTable),

    merge('signed', Signal),
    merge('factor', Signal),

    merge(
        'sendable', 
        Message, 
        MultiplexedMessage, 
        MultiplexedMessageClone,
        ),
    merge(
        'receivable', 
        Message, 
        MultiplexedMessage,
        MultiplexedMessageClone,
        ),
    merge('start_bit', Signal),
    merge('on_write', Multiplexer),
    merge(
        'comment', 
        Message, 
        Multiplexer, 
        MultiplexedMessage,
        MultiplexedMessageClone,
        ),

    merge('original', MultiplexedMessageClone),

    merge('parameter_uuid', Signal),
    merge('uuid', *types.types.values()),
)


# TODO: CAMPid 075454679961754906124539691347967
@attr.s
class ReferencedUuidNotifier(PyQt5.QtCore.QObject):
    changed = PyQt5.QtCore.pyqtSignal('PyQt_PyObject')

    view = attr.ib(default=None)
    selection_model = attr.ib(default=None)

    def __attrs_post_init__(self):
        super().__init__()

        if self.view is not None:
            self.set_view(self.view)

    def set_view(self, view):
        self.disconnect_view()

        self.view = view
        self.selection_model = self.view.selectionModel()
        self.selection_model.currentChanged.connect(
            self.current_changed,
        )

    def disconnect_view(self):
        if self.selection_model is not None:
            self.selection_model.currentChanged.disconnect(
                self.current_changed,
            )
        self.view = None
        self.selection_model = None

    def current_changed(self, current, previous):
        if not current.isValid():
            return

        index = epyqlib.utils.qt.resolve_index_to_model(
            index=current,
        )
        model = index.data(epyqlib.utils.qt.UserRoles.attrs_model)
        node = model.node_from_index(index)
        if isinstance(node, Signal):
            self.changed.emit(node.parameter_uuid)
