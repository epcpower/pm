import itertools

import attr
import graham
import marshmallow

import epyqlib.attrsmodel
import epyqlib.checkresultmodel
import epyqlib.pm.parametermodel
import epyqlib.utils
import epyqlib.utils.qt
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


def create_factor_uuid_attribute():
    return epyqlib.attrsmodel.attr_uuid(
        default=None,
        human_name="Scale Factor",
        allow_none=True,
        data_display=name_from_uuid,
        list_selection_path=("/"),
        override_delegate=ScaleFactorDelegate,
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

    return "{} - {}".format(target_node.tree_parent.name, target_node.name)


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
    factor_uuid = create_factor_uuid_attribute()
    parameter_uuid = create_parameter_uuid_attribute()

    not_implemented = epyqlib.attrsmodel.create_checkbox_attribute(
        default=False,
    )

    type_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
        human_name="Type",
        data_display=epyqlib.attrsmodel.name_from_uuid,
        list_selection_root="staticmodbus types",
    )

    address = create_address_attribute()

    size = create_size_attribute()

    enumeration_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
    )
    epyqlib.attrsmodel.attrib(
        attribute=enumeration_uuid,
        human_name="Enumeration",
        data_display=epyqlib.attrsmodel.name_from_uuid,
        delegate=epyqlib.attrsmodel.RootDelegateCache(
            list_selection_root="enumerations",
        ),
    )

    units = epyqlib.attrsmodel.create_str_or_none_attribute()

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return isinstance(node, epyqlib.pm.parametermodel.Parameter)

    def child_from(self, node):
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
    parameter_uuid = create_parameter_uuid_attribute()

    bit_offset = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_int_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(allow_none=True),
        ),
    )

    bit_length = create_size_attribute(default=1)

    type_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
        human_name="Type",
        data_display=epyqlib.attrsmodel.name_from_uuid,
        list_selection_root="staticmodbus types",
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
                epyqlib.pm.parametermodel.Parameter,
            ),
        )

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True

    def child_from(self, node):
        if isinstance(node, epyqlib.pm.parametermodel.Parameter):
            self.parameter_uuid = node.uuid
            return None

        return node

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(
    tag="staticmodbus_table_repeating_block_reference_function_data_reference",
    register=True,
)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@epyqlib.utils.qt.pyqtify_passthrough_properties(
    original="original",
    field_names=("parameter_uuid",),
)
@attr.s(hash=False)
class TableRepeatingBlockReferenceFunctionDataReference(epyqlib.treenode.TreeNode):
    parameter_uuid = create_parameter_uuid_attribute()

    factor_uuid = create_factor_uuid_attribute()
    original = epyqlib.attrsmodel.create_reference_attribute()

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return False

    can_delete = epyqlib.attrsmodel.childless_can_delete
    all_addable_types = epyqlib.attrsmodel.empty_all_addable_types
    addable_types = epyqlib.attrsmodel.empty_addable_types
    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    child_from = epyqlib.attrsmodel.default_child_from
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(tag="staticmodbus_table_repeating_block", register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@epyqlib.utils.qt.pyqtify_passthrough_properties(
    original="original",
    field_names=("name",),
)
@attr.s(hash=False)
class TableRepeatingBlockReference(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default="Table Repeating Block Reference",
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    children = attr.ib(
        factory=list,
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(
                fields=(
                    marshmallow.fields.Nested(
                        graham.schema(
                            TableRepeatingBlockReferenceFunctionDataReference,
                        )
                    ),
                )
            ),
        ),
    )

    original = epyqlib.attrsmodel.create_reference_attribute()

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types(())

    @staticmethod
    def addable_types():
        return {}

    def can_drop_on(self, node):
        return False

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return False

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    child_from = epyqlib.attrsmodel.default_child_from
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(tag="table_model_reference", register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class TableRepeatingBlock(epyqlib.treenode.TreeNode):
    uuid = epyqlib.attrsmodel.attr_uuid()
    name = attr.ib(
        default="Table Reference",
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )

    children = attr.ib(
        factory=list,
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(
                fields=(marshmallow.fields.Nested(graham.schema(FunctionData)),)
            ),
        ),
    )

    repeats = attr.ib(
        default=0,
        converter=int,
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

    def __attrs_post_init__(self):
        super().__init__()

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types(())

    @staticmethod
    def addable_types():
        return {}

    def can_drop_on(self, node):
        return False

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return False

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    child_from = epyqlib.attrsmodel.default_child_from
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(tag="table", register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Table(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default="New Table",
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )

    parameter_table_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
    )
    epyqlib.attrsmodel.attrib(
        attribute=parameter_table_uuid,
        human_name="Table UUID",
    )

    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(
                fields=(
                    marshmallow.fields.Nested(graham.schema(TableRepeatingBlock)),
                    marshmallow.fields.Nested(graham.schema(FunctionData)),
                )
            ),
        ),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    @classmethod
    def all_addable_types(cls):
        return epyqlib.attrsmodel.create_addable_types(())

    @staticmethod
    def addable_types():
        return {}

    @staticmethod
    def can_drop_on(node):
        return isinstance(node, epyqlib.pm.parametermodel.Table)

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True

    def child_from(self, node):
        self.parameter_table_uuid = node.uuid
        return None

    def update(self, table=None):
        old_nodes = self.recursively_remove_children()
        old_nodes_by_path = {
            getattr(node, "path", getattr(node, "parameter_uuid", node.uuid)): node
            for node in old_nodes
        }

        if self.parameter_table_uuid is None:
            return

        root = self.find_root()
        model = root.model

        if table is None:
            table = model.node_from_uuid(self.parameter_table_uuid)
        elif table.uuid != self.table_uuid:
            raise ConsistencyError()

        master_array_function_data_by_uuid = {}

        for section in table.arrays_and_groups:
            if isinstance(section, epyqlib.pm.parametermodel.Array):
                array_element = section.children[0]
                node = old_nodes_by_path.get(array_element.uuid)
                if node is None:
                    node = FunctionData(
                        parameter_uuid=array_element.uuid,
                    )
                self.append_child(node)
                master_array_function_data_by_uuid[array_element.uuid] = node
            elif isinstance(section, epyqlib.pm.parametermodel.Group):
                for element in section.children:
                    node = old_nodes_by_path.get(element.uuid)
                    if node is None:
                        node = FunctionData(
                            parameter_uuid=element.uuid,
                        )
                    self.append_child(node)
                    master_array_function_data_by_uuid[element.uuid] = node

        for combination in table.combinations:
            not_first_curve = any(
                (
                    layer.tree_parent.name == "Curves"
                    and layer.name != layer.tree_parent.children[0].name
                )
                for layer in combination
            )
            if not_first_curve:
                continue

            curve_enumeration_search = [
                layer for layer in combination if layer.tree_parent.name == "Curves"
            ]
            if len(curve_enumeration_search) == 0:
                curve_count = 0
            elif len(curve_enumeration_search) == 1:
                curve_enumeration = curve_enumeration_search[0].tree_parent
                curve_count = len(curve_enumeration.children)
            else:
                raise blue

            base_path = tuple(node.uuid for node in combination)

            block_node = old_nodes_by_path.get(base_path)

            if block_node is None:
                block_node = TableRepeatingBlock(
                    name=" - ".join(
                        item.name
                        for item in combination
                        if item.tree_parent.name != "Curves"
                    ),
                    path=base_path,
                )

            block_node.repeats = curve_count

            self.append_child(block_node)

            (in_tree,) = table.group.nodes_by_attribute(
                attribute_value=tuple(node.uuid for node in combination),
                attribute_name="path",
            )

            group_elements = [[], []]
            group_of_groups = group_elements[0]

            for child in in_tree.children:
                if isinstance(child.original, epyqlib.pm.parametermodel.Array):
                    group_of_groups = group_elements[1]
                    continue

                group_of_groups.append(child.children)

            for group in group_elements:
                group[:] = itertools.chain.from_iterable(group)

            # TODO: CAMPid 143707880547014313476753071297360068134
            for element in group_elements[0]:
                point_node = old_nodes_by_path.get(element.uuid)
                reference_function_data = master_array_function_data_by_uuid[
                    element.original.uuid
                ]
                if point_node is None:
                    point_node = FunctionData(
                        parameter_uuid=element.uuid,
                    )
                point_node.units = reference_function_data.units
                point_node.type_uuid = reference_function_data.type_uuid
                point_node.size = reference_function_data.size
                point_node.enumeration_uuid = reference_function_data.enumeration_uuid
                block_node.append_child(point_node)

            array_elements = itertools.chain.from_iterable(
                zip(
                    *(
                        array.children
                        for array in in_tree.children
                        if isinstance(array.original, epyqlib.pm.parametermodel.Array)
                    )
                ),
            )
            for element in array_elements:
                point_node = old_nodes_by_path.get(element.uuid)
                reference_function_data = master_array_function_data_by_uuid[
                    element.tree_parent.children[0].original.uuid
                ]
                if point_node is None:
                    point_node = FunctionData(
                        parameter_uuid=element.uuid,
                    )
                point_node.units = reference_function_data.units
                point_node.type_uuid = reference_function_data.type_uuid
                point_node.size = reference_function_data.size
                point_node.enumeration_uuid = reference_function_data.enumeration_uuid
                block_node.append_child(point_node)

            # TODO: CAMPid 143707880547014313476753071297360068134
            for element in group_elements[1]:
                point_node = old_nodes_by_path.get(element.uuid)
                reference_function_data = master_array_function_data_by_uuid[
                    element.original.uuid
                ]
                if point_node is None:
                    point_node = FunctionData(
                        parameter_uuid=element.uuid,
                    )
                point_node.units = reference_function_data.units
                point_node.type_uuid = reference_function_data.type_uuid
                point_node.size = reference_function_data.size
                point_node.enumeration_uuid = reference_function_data.enumeration_uuid
                block_node.append_child(point_node)

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


Root = epyqlib.attrsmodel.Root(
    default_name="Static Modbus",
    valid_types=(
        FunctionData,
        Table,
        TableRepeatingBlockReference,
        FunctionDataBitfield,
    ),
)


types = epyqlib.attrsmodel.Types(
    types=(
        Root,
        FunctionData,
        FunctionDataBitfield,
        FunctionDataBitfieldMember,
        Table,
        TableRepeatingBlock,
        TableRepeatingBlockReference,
        TableRepeatingBlockReferenceFunctionDataReference,
    ),
)


# TODO: CAMPid 943896754217967154269254167
def merge(name, *types):
    return tuple((x, name) for x in types)


columns = epyqlib.attrsmodel.columns(
    (
        merge(
            "name",
            Table,
            TableRepeatingBlock,
            TableRepeatingBlockReference,
        )
        + merge(
            "parameter_uuid",
            FunctionData,
            TableRepeatingBlockReferenceFunctionDataReference,
            FunctionDataBitfield,
            FunctionDataBitfieldMember,
        )
    ),
    merge("not_implemented", FunctionData),
    merge("address", FunctionData, FunctionDataBitfield),
    merge("size", FunctionData, FunctionDataBitfield),
    merge("repeats", TableRepeatingBlock),
    merge(
        "factor_uuid",
        FunctionData,
        TableRepeatingBlockReferenceFunctionDataReference,
    ),
    merge("units", FunctionData),
    merge("enumeration_uuid", FunctionData),
    merge("type_uuid", FunctionData, FunctionDataBitfield, FunctionDataBitfieldMember),
    merge("bit_length", FunctionDataBitfieldMember),
    merge("bit_offset", FunctionDataBitfieldMember),
    merge("parameter_table_uuid", Table),
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
