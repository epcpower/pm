import itertools

import attr
import graham
import marshmallow
import typing
import logging

import epyqlib.attrsmodel
import epyqlib.checkresultmodel
import epyqlib.pm.parametermodel
import epyqlib.utils
import epyqlib.utils.qt

import mpm.canmodel

from PyQt5 import QtWidgets


class ConsistencyError(Exception):
    pass


class MismatchedSizeAndTypeError(Exception):
    pass


class TypeNotFoundError(Exception):
    pass


def build_staticmodbus_types_enumeration():
    enumeration = epyqlib.pm.parametermodel.Enumeration(
        name="StaticModbusTypes",
        uuid="5a768d49-565d-4ffd-9c4d-f937d29f18bf",
    )

    enumerators = [
        epyqlib.pm.parametermodel.Enumerator(
            name="int16", value=1, uuid="ead5f606-8846-4dfb-bd30-d50100f29389"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="uint16", value=1, uuid="ff23a077-3d9c-4dc2-be8a-51a077058d14"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="int32", value=2, uuid="f93514e2-f173-46f9-a8c2-1a4cd15c6904"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="uint32", value=2, uuid="5ef749cd-ea55-44c9-85d7-1d574c350a84"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="staticmodbussf", value=1, uuid="2b2c843b-4f80-4822-a806-1e3cc4342ee3"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="enum16", value=1, uuid="45e7fe5e-dcb5-4a43-8455-861be6b45cbc"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="bitfield16", value=1, uuid="7d02a033-0295-417f-bc5c-838e798f938d"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="bitfield32", value=2, uuid="47755118-41dc-48ab-8e20-00f9f80d1096"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="string", value=0, uuid="fa216e96-9fea-4240-a876-1d1ed7d67c0c"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="acc16", value=1, uuid="952b419d-828d-4949-8e08-8cbd5fee6b62"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="acc32", value=2, uuid="2a948a8d-e766-4ab1-88b9-16f7c32cfe9e"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="acc64", value=4, uuid="1c98382d-11b6-4ee8-9447-3834f6f103fb"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="count", value=1, uuid="0c40dc3d-77be-481d-a3f4-784a89e0cf84"
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name="pad", value=1, uuid="ed0c4a1e-777a-4423-bccc-3a4ac0a3f5be"
        ),
    ]

    for enumerator in enumerators:
        enumeration.append_child(enumerator)

    return enumeration


def create_size_attribute(default=0):
    return attr.ib(
        default=default,
        converter=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    )


def create_address_attribute(default=0):
    return attr.ib(
        default=default,
        converter=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    )


def create_name_attribute():
    return attr.ib(
        default="",
        converter=str,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )

def create_parameter_uuid_attribute():
    return epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
        human_name="Parameter",
        data_display=name_from_uuid_and_parent,
        editable=False,
    )


# TODO: CAMPid 8695426542167924656654271657917491654
def name_from_uuid(node, value, model):
    if value is None:
        return None

    try:
        target_node = model.node_from_uuid(value)
    except epyqlib.attrsmodel.NotFoundError:
        return str(value)

    return model.node_from_uuid(target_node.parameter_uuid).abbreviation


# TODO: CAMPid 8695426542167924656654271657917491654
def name_from_uuid_and_parent(node, value, model):
    if value is None:
        return None

    try:
        target_node = model.node_from_uuid(value)
    except epyqlib.attrsmodel.NotFoundError:
        return str(value)

    # Attempt to find CAN node for this static modbus entry
    # If it exists, use that for naming instead of parameter name
    try:
        for droppable in model.droppable_from:
            if droppable.root.name == "CAN":
                can_signals = droppable.root.nodes_by_attribute(
                    attribute_value=value, attribute_name="parameter_uuid"
                )
                if len(can_signals) == 1:
                    target_node = can_signals.pop()
                break
    except:
        pass

    return "{}:{}".format(target_node.tree_parent.name, target_node.name)


def bits_to_words(bits):
    return int(bits / 16) + (1 if bits % 16 else 0)


def find_can_signals(root) -> list:
    """
    Recursively finds CAN signals from the given root node.

    Args:
        root: Root node where the search starts
    Returns:
        List of CAN signals found from the root
    """
    results = []
    if isinstance(root, mpm.canmodel.Signal):
        results.append(root)
    elif hasattr(root, "children"):
        for c in root.children:
            results += find_can_signals(c)
    return results


class ScaleFactorDelegate(QtWidgets.QStyledItemDelegate):
    def __init__(self, text_column_name, root, parent):
        super().__init__(parent)

        self.root = root

    def createEditor(self, parent, option, index):
        return QtWidgets.QListWidget(parent=parent)

    def setEditorData(self, editor, index):
        model_index = epyqlib.attrsmodel.to_source_model(index)
        model = model_index.model()

        item = model.itemFromIndex(model_index)
        attrs_model = item.data(epyqlib.utils.qt.UserRoles.attrs_model)

        raw = model.data(model_index, epyqlib.utils.qt.UserRoles.raw)

        points = []
        for pt in self.root.children:
            if hasattr(pt, "type_uuid"):
                type_node = attrs_model.node_from_uuid(pt.type_uuid)
                if type_node.name == "staticmodbussf":
                    points.append(pt)

        it = QtWidgets.QListWidgetItem(editor)
        it.setText("")
        it.setData(epyqlib.utils.qt.UserRoles.raw, "")
        it.setSelected(True)
        for p in points:
            it = QtWidgets.QListWidgetItem(editor)
            param = attrs_model.node_from_uuid(p.parameter_uuid)
            it.setText(param.abbreviation)
            it.setData(epyqlib.utils.qt.UserRoles.raw, p.uuid)
            if p.uuid == raw:
                it.setSelected(True)

        editor.setMinimumHeight(editor.sizeHint().height())
        editor.itemClicked.connect(
            lambda: epyqlib.attrsmodel.hide_popup(editor),
        )
        editor.show()

    def setModelData(self, editor, model, index):
        selected_item = editor.currentItem()
        datum = str(selected_item.data(epyqlib.utils.qt.UserRoles.raw))
        model.setData(index, datum)


@graham.schemify(tag="function_data", register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class FunctionData(epyqlib.treenode.TreeNode):
    name = create_name_attribute()
    parameter_uuid = create_parameter_uuid_attribute()
    address = create_address_attribute()
    size = create_size_attribute()
    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return isinstance(
            node, (epyqlib.pm.parametermodel.Parameter, mpm.canmodel.Signal)
        )

    def child_from(self, node):
        if isinstance(node, mpm.canmodel.Signal):
            self.parameter_uuid = node.parameter_uuid
            self.size = bits_to_words(node.bits)
            self.address = self.find_root().find_avail_address()
        else:
            self.parameter_uuid = node.uuid

        return None

    @epyqlib.attrsmodel.check_children
    def check(self, result, models):
        if self.parameter_uuid is None:
            result.append_child(
                epyqlib.checkresultmodel.Result(
                    node=self,
                    severity=epyqlib.checkresultmodel.ResultSeverity.error,
                    message="No parameter connected",
                )
            )
        else:
            root = self.find_root()
            parameter = root.model.node_from_uuid(self.parameter_uuid)

            if not parameter.uses_interface_item():
                result.append_child(
                    epyqlib.checkresultmodel.Result(
                        node=self,
                        severity=(epyqlib.checkresultmodel.ResultSeverity.information),
                        message=("Connected to old-style parameter"),
                    )
                )

                access_level = root.model.node_from_uuid(
                    parameter.access_level_uuid,
                )

                if access_level.value > 0:
                    result.append_child(
                        epyqlib.checkresultmodel.Result(
                            node=self,
                            severity=(epyqlib.checkresultmodel.ResultSeverity.warning),
                            message=("Access level will not be enforced"),
                        )
                    )

        return result

    can_delete = epyqlib.attrsmodel.childless_can_delete
    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move


@graham.schemify(tag="function_data_bitfield_member", register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class FunctionDataBitfieldMember(epyqlib.treenode.TreeNode):
    name = create_name_attribute()
    parameter_uuid = create_parameter_uuid_attribute()

    bit_offset = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_int_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(allow_none=True),
        ),
    )

    bit_length = create_size_attribute(default=1)

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return isinstance(node, epyqlib.pm.parametermodel.Parameter)

    def child_from(self, node):
        self.parameter_uuid = node.uuid

        return None

    can_delete = epyqlib.attrsmodel.childless_can_delete
    all_addable_types = epyqlib.attrsmodel.empty_all_addable_types
    addable_types = epyqlib.attrsmodel.empty_addable_types
    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(tag="function_data_bitfield", register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class FunctionDataBitfield(epyqlib.treenode.TreeNode):
    name = create_name_attribute()
    parameter_uuid = create_parameter_uuid_attribute()

    children = attr.ib(
        factory=list,
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(
                fields=(
                    marshmallow.fields.Nested(
                        graham.schema(FunctionDataBitfieldMember)
                    ),
                )
            ),
        ),
    )

    # TODO: though this only really makes sense as one of the bitfield types
    type_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
        human_name="Type",
        data_display=epyqlib.attrsmodel.name_from_uuid,
        list_selection_root="staticmodbus types",
    )

    address = create_address_attribute()

    size = create_size_attribute()

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return isinstance(
            node,
            (
                FunctionDataBitfieldMember,
                mpm.canmodel.Signal,
                mpm.canmodel.Multiplexer,
                mpm.canmodel.Message,
                mpm.canmodel.MultiplexedMessage,
            ),
        )

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True

    def child_from(self, node):
        if isinstance(
            node,
            (
                mpm.canmodel.Multiplexer,
                mpm.canmodel.Message,
                mpm.canmodel.MultiplexedMessage,
            ),
        ):
            if len(self.children) == 0:
                self.address = self.find_root().find_avail_address()

            offset = (
                max([c.bit_offset + c.bit_length for c in self.children])
                if self.children
                else 0
            )

            can_signals = find_can_signals(node)

            output = []
            for signal in can_signals:
                member = FunctionDataBitfieldMember(
                    parameter_uuid=signal.parameter_uuid,
                    bit_length=signal.bits,
                    bit_offset=offset,
                )
                output.append(member)
                offset += signal.bits
            self.size = bits_to_words(offset)
            return output
        elif isinstance(node, mpm.canmodel.Signal):
            offset = (
                max([c.bit_offset + c.bit_length for c in self.children])
                if self.children
                else 0
            )
            self.size = bits_to_words(offset + node.bits)
            return FunctionDataBitfieldMember(
                parameter_uuid=node.uuid, bit_length=node.bits, bit_offset=offset
            )
        return node

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


def find_avail_address(self) -> int:
    """
    Finds smallest available modbus address on the static modbus root model.
    Address gaps between reserved addresses are considered to be reserved.

    Args:
        self: Root object self-instance.
    Returns:
        Smallest available modbus address.
    """

    def check_children(self, max_addr, children):
        for c in children:
            if hasattr(c, "address") and hasattr(c, "size"):
                max_addr = max(max_addr, c.address + c.size)
            elif hasattr(c, "children"):
                max_addr = max(max_addr, check_children(self, max_addr, c.children))
        return max_addr

    return check_children(self, 0, self.children)



def sort_addresses(self) -> None:
    """
    Sort children by address in ascending order.

    Args:
        self: Root object self-instance.
    Returns:
        None
    """
    children_copy = self.children.copy()
    children_copy.sort(key=lambda x: x.address)
    # Re-add children to trigger the tree update
    self.recursively_remove_children()
    for child in children_copy:
        self.append_child(child)

def update_addresses_below(self, start_node) -> None:
    """
    Sort addresses such that they are in ascending order below given node

    Args:
        self: Root object self-instance.
        start_node: Node where the sorting starts.
    """
    index = -1
    for c in self.children:
        if c == start_node:
            index = c.address + 1
            continue
        # Start node not yet found, skip
        if index < 0:
            continue

        c.address = index
        index += 1


def root_can_drop_on(self, node) -> bool:
    """
    Function that determines which objects can be dropped on static modbus root.

    Args:
        self: Root object self-instance.
        node: Arbitrary typed object that is tested.
    Returns:
        True if dropping is allowed, False otherwise.
    """
    return isinstance(
        node,
        (
            FunctionData,
            FunctionDataBitfield,
            mpm.canmodel.Signal,
            mpm.canmodel.Multiplexer,
            mpm.canmodel.CanTable,
            mpm.canmodel.Message,
            mpm.canmodel.MultiplexedMessage,
        ),
    )


def root_child_from(self, node) -> typing.Union[FunctionData, list]:
    """
    Constructs child object(s) from an input node object dropped on the
    static modbus model root.

    Args:
        self: Root object self-instance.
        node: Input object. Allowed types are defined in root_can_drop_on function.
    Returns:
        A new FunctionData object.
    """
    if isinstance(node, (FunctionData, FunctionDataBitfield)):
        return node
    elif isinstance(node, mpm.canmodel.Signal):
        avail_addr = self.find_avail_address()
        return FunctionData(
            parameter_uuid=node.parameter_uuid,
            size=bits_to_words(node.bits),
            address=avail_addr,
        )
    elif isinstance(
        node,
        (
            mpm.canmodel.Message,
            mpm.canmodel.MultiplexedMessage,
            mpm.canmodel.CanTable,
            mpm.canmodel.Multiplexer,
        ),
    ):
        can_signals = find_can_signals(node)

        # Convert to FunctionData entries
        avail_addr = self.find_avail_address()
        output = []
        for signal in can_signals:

            if not signal.parameter_uuid:
                continue

            # Find corresponding parameter
            par = self.find_root().model.node_from_uuid(signal.parameter_uuid)

            # Determine its access level
            if hasattr(par, "access_level_uuid"):
                access_level = par.access_level_uuid
            elif hasattr(par, "original"):
                access_level = (
                    self.find_root()
                    .model.node_from_uuid(par.original)
                    .access_level_uuid
                )

            # List all access levels
            (access_levels,) = par.find_root().nodes_by_filter(
                filter=(
                    lambda node: isinstance(
                        node, epyqlib.pm.parametermodel.AccessLevels
                    )
                ),
            )

            # Append to output if on correct access level and signal is not empty
            if (
                access_level == access_levels.by_name("Service_Tech").uuid
                and signal.bits > 0
            ):
                output.append(
                    FunctionData(
                        parameter_uuid=signal.parameter_uuid,
                        size=bits_to_words(signal.bits),
                        address=avail_addr,
                    )
                )
                avail_addr += bits_to_words(signal.bits)
            else:
                logging.debug(
                    "Did not drop anything due to wrong access level or zero bit length"
                )
        return output
    return FunctionData(parameter_uuid=node.uuid)


Root = epyqlib.attrsmodel.Root(
    default_name="Static Modbus",
    valid_types=(
        FunctionData,
        FunctionDataBitfield,
    ),
)
Root.can_drop_on = root_can_drop_on
Root.child_from = root_child_from
Root.find_avail_address = find_avail_address
Root.sort_addresses = sort_addresses
Root.update_addresses_below = update_addresses_below

types = epyqlib.attrsmodel.Types(
    types=(
        Root,
        FunctionData,
        FunctionDataBitfield,
        FunctionDataBitfieldMember,
    ),
)


# TODO: CAMPid 943896754217967154269254167
def merge(name, *types):
    return tuple((x, name) for x in types)


columns = epyqlib.attrsmodel.columns(
    (
        merge(
            "name",
            FunctionData,
        )
        + merge(
            "parameter_uuid",
            FunctionData,
            FunctionDataBitfield,
            FunctionDataBitfieldMember,
        )
    ),
    merge("address", FunctionData, FunctionDataBitfield),
    merge("size", FunctionData, FunctionDataBitfield),
    merge("bit_length", FunctionDataBitfieldMember),
    merge("bit_offset", FunctionDataBitfieldMember),
    merge("uuid", *types.types.values()),
)


# TODO: CAMPid 075454679961754906124539691347967
@attr.s
class ReferencedUuidNotifier:
    changed = epyqlib.utils.qt.Signal("PyQt_PyObject")

    view = attr.ib(default=None)
    selection_model = attr.ib(default=None)

    def __attrs_post_init__(self):
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

        parameter_uuid = getattr(node, "parameter_uuid", None)

        if parameter_uuid is not None:
            self.changed.emit(parameter_uuid)
