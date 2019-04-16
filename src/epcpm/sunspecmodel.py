import itertools

import attr
import graham
import marshmallow

import epyqlib.attrsmodel
import epyqlib.checkresultmodel
import epyqlib.pm.parametermodel
import epyqlib.utils
import epyqlib.utils.qt
from PyQt5 import QtCore
from PyQt5 import QtWidgets


class ConsistencyError(Exception):
    pass


class MismatchedSizeAndTypeError(Exception):
    pass


class TypeNotFoundError(Exception):
    pass


def build_sunspec_types_enumeration():
    enumeration = epyqlib.pm.parametermodel.Enumeration(
        name='SunSpecTypes',
        uuid='00b90651-3e3b-4e28-a8c0-7339ae092200',
    )
    
    enumerators = [
        epyqlib.pm.parametermodel.Enumerator(
            name='int16',
            value=1,
            uuid='2cf75e5a-ffc8-422a-bbc6-573d4206a7e1'
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name='uint16',
            value=1,
            uuid='4f856a7e-20f4-43e2-86b1-cc7ee772f919'
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name='int32',
            value=2,
            uuid='4fec39a5-b702-4dbf-8ad1-95f5e01201b6'
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name='uint32',
            value=2,
            uuid='eb8cdc87-05e2-4593-994e-ab3363236168'
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name='sunssf',
            value=1,
            uuid='02e70616-4986-4f3e-8ac4-98ac153e66f9'
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name='enum16',
            value=1,
            uuid='209aebc8-652f-47bf-9952-4c112ced2781'
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name='bitfield16',
            value=1,
            uuid='5d30a559-13fe-42b1-89df-35c3edc237f0'
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name='bitfield32',
            value=2,
            uuid='fc0ad957-2785-4762-b2fc-4db2cf785ca2'
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name='string',
            value=0,
            uuid='5460c860-4aad-476a-908c-83a364b781c9'
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name='acc16',
            value=1,
            uuid='05830309-c61c-41d4-8c66-88ed25187575'
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name='acc32',
            value=2,
            uuid='f9d30fa6-33b2-48a2-8b64-72a4f47c0bd4'
        ),
        epyqlib.pm.parametermodel.Enumerator(
            name='pad',
            value=1,
            uuid='f8090bab-cf12-476c-b96a-1c8bb9848bb5'
        ),
    ]

    for enumerator in enumerators:
        enumeration.append_child(enumerator)

    return enumeration


def create_size_attribute():
    return attr.ib(
        default=0,
        converter=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    )


def create_factor_uuid_attribute():
    return epyqlib.attrsmodel.attr_uuid(
        default=None,
        human_name='Scale Factor',
        allow_none=True,
        data_display=name_from_uuid,
        list_selection_path=('..', '..', 'Fixed Block'),
        override_delegate=ScaleFactorDelegate,
    )


def create_parameter_uuid_attribute():
    return epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
        human_name='Parameter',
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

    return '{} - {}'.format(target_node.tree_parent.name, target_node.name)


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
            type_node = attrs_model.node_from_uuid(pt.type_uuid)
            if type_node.name == 'sunssf':
                points.append(pt)

        it = QtWidgets.QListWidgetItem(editor)
        it.setText('')
        it.setData(epyqlib.utils.qt.UserRoles.raw, '')
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


@graham.schemify(tag='data_point', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class DataPoint(epyqlib.treenode.TreeNode):
    factor_uuid = create_factor_uuid_attribute()
    internal_scale_factor = attr.ib(
        default=0,
        converter=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    )
    parameter_uuid = create_parameter_uuid_attribute()

    not_implemented = epyqlib.attrsmodel.create_checkbox_attribute(
        default=False,
    )

    type_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
        human_name='Type',
        data_display=epyqlib.attrsmodel.name_from_uuid,
        list_selection_root='sunspec types',
    )

    offset = attr.ib(
        default=0,
        converter=int,
    ) # this is somewhat redundant with the position in the list of data
            # points but helpful for keeping things from incidentally floating
            # around especially in custom models where we have no sunspec
            # model to be validating against
            # for now, yes, this is vaguely nondescript of address vs block offset
    @QtCore.pyqtProperty('PyQt_PyObject')
    def pyqtify_offset(self):
        block_offset = getattr(self.tree_parent, 'block_offset', None)

        if block_offset is None:
            return None

        return block_offset + self.block_offset

    # TODO: shouldn't this be read only?
    @pyqtify_offset.setter
    def pyqtify_offset(self, value):
        pass

    block_offset = attr.ib(
        default=0,
        converter=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    )

    size = create_size_attribute()

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

    units = epyqlib.attrsmodel.create_str_or_none_attribute()

    get = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    epyqlib.attrsmodel.attrib(
        attribute=get,
        no_column=True,
    )
    set = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    epyqlib.attrsmodel.attrib(
        attribute=set,
        no_column=True,
    )

    mandatory = attr.ib(
        default=True,
        converter=epyqlib.attrsmodel.two_state_checkbox,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Boolean(),
        ),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()
    # value  doesn't make sense here, this is interface definition, not a
    #       value set


    # ? point_id = attr.ib()
    # ? index = index

    # last access time?
    # time = time

#     getter_code = attr.ib()
#     setter_code = attr.ib()
    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return isinstance(node, epyqlib.pm.parametermodel.Parameter)

    def child_from(self, node):
        self.parameter_uuid = node.uuid

        return None

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

    @epyqlib.attrsmodel.check_children
    def check(self, result, models):
        results = []

        if self.parameter_uuid is None:
            results.append(
                f'No parameter connected',
            )
        else:
            root = self.find_root()
            parameter = root.model.node_from_uuid(self.parameter_uuid)
            if (
                    parameter.tree_parent.name.startswith('SunSpec')
                    and parameter.tree_parent.tree_parent.tree_parent is None
            ):
                results.append(
                    f'Connected to temporary SunSpec imported parameter',
                )

        for r in results:
            result.append_child(epyqlib.checkresultmodel.Result(
                node=self,
                message=r,
            ))

        return result

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move


def check_block_offsets_and_length(self):
    length = 0

    root = self.find_root()

    for point in self.children:
        try:
            type_ = root.model.node_from_uuid(point.type_uuid)
        except epyqlib.attrsmodel.NotFoundError:
            point_name = root.model.node_from_uuid(point.parameter_uuid).name
            raise TypeNotFoundError(
                f'Point {point_name!r}'
                f' has unknown type uuid {point.type_uuid!r}'
            )

        if type_.name != 'string' and point.size != type_.value:
            point_name = root.model.node_from_uuid(point.parameter_uuid).name
            raise MismatchedSizeAndTypeError(
                f'Expected {type_.value} for {type_.name}'
                f', is {point.size} for {point_name}'
            )

        length += point.size

    return length


@graham.schemify(tag='sunspec_header_block', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class HeaderBlock(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='Header',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    offset = attr.ib(
        default=0,
        converter=int,
    )
    children = attr.ib(
        factory=list,
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(DataPoint)),
            )),
        ),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return False

    def can_delete(self, node=None):
        return False

    check_offsets_and_length = check_block_offsets_and_length

    def add_data_points(self, uint16_uuid, model_id):
        parameters = [
            epyqlib.pm.parametermodel.Parameter(
                name=model_id,
                abbreviation='ID',
                read_only=True,
            ),
            epyqlib.pm.parametermodel.Parameter(
                name='',
                abbreviation='L',
                comment='Model Length',
                read_only=True,
            ),
        ]
        points = [
            DataPoint(
                block_offset=0,
                size=1,
                type_uuid=uint16_uuid,
                parameter_uuid=parameters[0].uuid,
                mandatory=True,
            ),
            DataPoint(
                block_offset=1,
                size=1,
                type_uuid=uint16_uuid,
                parameter_uuid=parameters[1].uuid,
                mandatory=True,
            ),
        ]

        for point in points:
            self.append_child(point)

        return parameters

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    child_from = epyqlib.attrsmodel.default_child_from
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(tag='sunspec_fixed_block', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class FixedBlock(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='Fixed Block',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    offset = attr.ib(
        default=2,
        converter=int,
    )
    children = attr.ib(
        factory=list,
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(DataPoint)),
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
                epyqlib.pm.parametermodel.Parameter,
                DataPoint,
            ),
        )

    def can_delete(self, node=None):
        return False

    def child_from(self, node):
        if isinstance(node, epyqlib.pm.parametermodel.Parameter):
            return DataPoint(parameter_uuid=node.uuid)

        return node

    check_offsets_and_length = check_block_offsets_and_length
    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(
    tag='sunspec_table_repeating_block_reference_data_point_reference',
    register=True,
)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@epyqlib.utils.qt.pyqtify_passthrough_properties(
    original='original',
    field_names=(
        'parameter_uuid',
    ),
)
@attr.s(hash=False)
class TableRepeatingBlockReferenceDataPointReference(epyqlib.treenode.TreeNode):
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


@graham.schemify(tag='sunspec_table_repeating_block', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@epyqlib.utils.qt.pyqtify_passthrough_properties(
    original='original',
    field_names=(
        'name',
    ),
)
@attr.s(hash=False)
class TableRepeatingBlockReference(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='Table Repeating Block Reference',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    offset = attr.ib(
        default=2,
        converter=int,
    )
    children = attr.ib(
        factory=list,
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(
                    TableRepeatingBlockReferenceDataPointReference,
                )),
            )),
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

    def check_offsets_and_length(self):
        return self.original.check_block_offsets_and_length()

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    child_from = epyqlib.attrsmodel.default_child_from
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(tag='sunspec_table_repeating_block', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@epyqlib.utils.qt.pyqtify_passthrough_properties(
    original='original',
    field_names=(
        'name',
    ),
)
@attr.s(hash=False)
class TableDataPointReference(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='Table Data Point Reference',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    offset = attr.ib(
        default=2,
        converter=int,
    )
    children = attr.ib(
        factory=list,
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
            )),
        ),
    )

    original = attr.ib(
        default=None,
        metadata=graham.create_metadata(
            field=epyqlib.attrsmodel.Reference(allow_none=True),
        ),
    )
    epyqlib.attrsmodel.attrib(
        attribute=original,
        no_column=True,
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

    def can_drop_on(self, node):
        return False

    def can_delete(self, node=None):
        return False

    check_offsets_and_length = check_block_offsets_and_length
    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    child_from = epyqlib.attrsmodel.default_child_from


@graham.schemify(tag='table_model_reference', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class TableRepeatingBlock(epyqlib.treenode.TreeNode):
    uuid = epyqlib.attrsmodel.attr_uuid()
    name = attr.ib(
        default='Table Reference',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )

    abbreviation = epyqlib.pm.parametermodel.create_abbreviation_attribute()

    children = attr.ib(
        factory=list,
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(DataPoint)),
            )),
        ),
    )

    offset = attr.ib(
        default=2,
        converter=int,
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

    def check_block_offsets_and_length(self):
        return self.repeats * check_block_offsets_and_length(self)

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    child_from = epyqlib.attrsmodel.default_child_from
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(tag='table', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Table(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default='New Table',
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
        human_name='Table UUID',
    )

    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(TableRepeatingBlock)),
                marshmallow.fields.Nested(graham.schema(DataPoint)),
            )),
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
            getattr(node, 'path', getattr(node, 'parameter_uuid', node.uuid)): node
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

        master_array_data_points_by_uuid = {}

        for section in table.arrays_and_groups:
            if isinstance(section, epyqlib.pm.parametermodel.Array):
                array_element = section.children[0]
                node = old_nodes_by_path.get(array_element.uuid)
                if node is None:
                    node = DataPoint(
                        parameter_uuid=array_element.uuid,
                    )
                self.append_child(node)
                master_array_data_points_by_uuid[array_element.uuid] = node
            elif isinstance(section, epyqlib.pm.parametermodel.Group):
                for element in section.children:
                    node = old_nodes_by_path.get(element.uuid)
                    if node is None:
                        node = DataPoint(
                            parameter_uuid=element.uuid,
                        )
                    self.append_child(node)
                    master_array_data_points_by_uuid[element.uuid] = node

        for combination in table.combinations:
            not_first_curve = any(
                (
                    layer.tree_parent.name == 'Curves'
                    and layer.name != layer.tree_parent.children[0].name
                )
                for layer in combination
            )
            if not_first_curve:
                continue

            curve_enumeration_search = [
                layer for layer in combination
                if layer.tree_parent.name == 'Curves'
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
                    name=' - '.join(
                        item.name
                        for item in combination
                        if item.tree_parent.name != 'Curves'
                    ),
                    path=base_path,
                )

            block_node.repeats = curve_count

            self.append_child(block_node)

            in_tree, = table.group.nodes_by_attribute(
                attribute_value=tuple(node.uuid for node in combination),
                attribute_name='path',
            )
            # continue

            block_offset = 0

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
                reference_data_point = master_array_data_points_by_uuid[
                    element.original.uuid
                ]
                if point_node is None:
                    point_node = DataPoint(
                        parameter_uuid=element.uuid,
                    )
                point_node.type_uuid = reference_data_point.type_uuid
                point_node.size = reference_data_point.size
                point_node.enumeration_uuid = (
                    reference_data_point.enumeration_uuid
                )
                point_node.block_offset = block_offset
                block_node.append_child(point_node)
                block_offset += point_node.size

            array_elements = itertools.chain.from_iterable(
                zip(*(
                    array.children
                    for array in in_tree.children
                    if isinstance(array.original, epyqlib.pm.parametermodel.Array)
                )),
            )
            for element in array_elements:
                point_node = old_nodes_by_path.get(element.uuid)
                reference_data_point = master_array_data_points_by_uuid[
                    element.tree_parent.children[0].original.uuid
                ]
                if point_node is None:
                    point_node = DataPoint(
                        parameter_uuid=element.uuid,
                    )
                point_node.type_uuid = reference_data_point.type_uuid
                point_node.size = reference_data_point.size
                point_node.enumeration_uuid = (
                    reference_data_point.enumeration_uuid
                )
                point_node.block_offset = block_offset
                block_node.append_child(point_node)
                block_offset += point_node.size

            # TODO: CAMPid 143707880547014313476753071297360068134
            for element in group_elements[1]:
                point_node = old_nodes_by_path.get(element.uuid)
                reference_data_point = master_array_data_points_by_uuid[
                    element.original.uuid
                ]
                if point_node is None:
                    point_node = DataPoint(
                        parameter_uuid=element.uuid,
                    )
                point_node.type_uuid = reference_data_point.type_uuid
                point_node.size = reference_data_point.size
                point_node.enumeration_uuid = (
                    reference_data_point.enumeration_uuid
                )
                point_node.block_offset = block_offset
                block_node.append_child(point_node)
                block_offset += point_node.size

    remove_old_on_drop = epyqlib.attrsmodel.default_remove_old_on_drop
    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


@graham.schemify(tag='sunspec_model', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Model(epyqlib.treenode.TreeNode):
    id = attr.ib(
        default=0,
        converter=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    ) # 103
    length = attr.ib(
        default=0,
        converter=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    ) # 50, in the spirit of over constraining like how
                        # data points have their offset

    # ?
    # self.model_id = '{}'.format(model_id)
    # self.namespace = namespace
    # self.index = index

    # special children
    # header: id and length

    # self.point_data = []
    children = attr.ib(
        factory=lambda: [HeaderBlock(), FixedBlock()],
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(HeaderBlock)),
                marshmallow.fields.Nested(graham.schema(FixedBlock)),
                marshmallow.fields.Nested(graham.schema(TableRepeatingBlockReference)),
            )),
        ),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def remove_old_on_drop(self, node):
        return False

    def child_from(self, node):
        reference = TableRepeatingBlockReference(original=node)
        for child in node.tree_parent.children:
            if not isinstance(child, DataPoint):
                continue

            reference.append_child(
                TableRepeatingBlockReferenceDataPointReference(
                    original=child,
                ),
            )

        return reference

    def can_drop_on(self, node):
        return (
            isinstance(node, TableRepeatingBlock)
            and not any(
                isinstance(child, TableRepeatingBlockReference)
                for child in self.children
            )
        )

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return not isinstance(node, (HeaderBlock, FixedBlock))

    def check_offsets_and_length(self):
        length = 0

        for block in self.children:
            length += block.check_offsets_and_length()

        return length

    internal_move = epyqlib.attrsmodel.default_internal_move
    check = epyqlib.attrsmodel.check_just_children


#class Repeating...?


Root = epyqlib.attrsmodel.Root(
    default_name='SunSpec',
    valid_types=(Model, Table),
)


types = epyqlib.attrsmodel.Types(
    types=(
        Root,
        Model,
        DataPoint,
        HeaderBlock,
        FixedBlock,
        Table,
        TableRepeatingBlock,
        TableRepeatingBlockReference,
        TableRepeatingBlockReferenceDataPointReference,
    ),
)


# TODO: CAMPid 943896754217967154269254167
def merge(name, *types):
    return tuple((x, name) for x in types)


columns = epyqlib.attrsmodel.columns(
    (
        merge(
            'name',
            HeaderBlock,
            FixedBlock,
            Table,
            TableRepeatingBlock,
            TableRepeatingBlockReference,
        )
        + merge('id', Model)
        + merge(
            'parameter_uuid',
            DataPoint,
            TableRepeatingBlockReferenceDataPointReference,
        )
    ),
    merge('abbreviation', TableRepeatingBlock),
    merge('not_implemented', DataPoint),
    merge('length', Model) + merge('size', DataPoint),
    merge('repeats', TableRepeatingBlock),
    merge(
        'factor_uuid',
        DataPoint,
        TableRepeatingBlockReferenceDataPointReference,
    ),
    merge('internal_scale_factor', DataPoint),
    merge('units', DataPoint),
    merge('enumeration_uuid', DataPoint),
    merge('type_uuid', DataPoint),
    merge('parameter_table_uuid', Table),
    merge('mandatory', DataPoint),
    merge(
        'offset',
        DataPoint,
        HeaderBlock,
        FixedBlock,
        TableRepeatingBlockReference,
        TableRepeatingBlock,
    ),
    merge('block_offset', DataPoint),
    merge('uuid', *types.types.values()),
)


# TODO: CAMPid 075454679961754906124539691347967
@attr.s
class ReferencedUuidNotifier:
    changed = epyqlib.utils.qt.Signal('PyQt_PyObject')

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
        if isinstance(node, DataPoint):
            self.changed.emit(node.parameter_uuid)
