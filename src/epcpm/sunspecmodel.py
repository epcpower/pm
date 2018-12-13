import attr
import graham
import marshmallow

import epyqlib.attrsmodel
import epyqlib.pm.parametermodel
from PyQt5 import QtCore


class MismatchedSizeAndTypeError(Exception):
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


# TODO: CAMPid 8695426542167924656654271657917491654
def name_from_uuid(node, value, model):
    if value is None:
        return None

    try:
        target_node = model.node_from_uuid(value)
    except NotFoundError:
        return str(value)

    return model.node_from_uuid(target_node.parameter_uuid).abbreviation


@graham.schemify(tag='data_point', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class DataPoint(epyqlib.treenode.TreeNode):
    factor_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        human_name='Scale Factor',
        allow_none=True,
        data_display=name_from_uuid,
    )
    parameter_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
        human_name='Parameter',
        data_display=epyqlib.attrsmodel.name_from_uuid,
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
        block = self.tree_parent

        if block is None:
            return None

        return block.offset + self.block_offset

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

    size = attr.ib(
        default=0,
        converter=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()
    # value  doesn't make sense here, this is interface definition, not a
    #       value set


    # mandatory is a thing where we will just check existence when validating
    # againt the sunspec def

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


@graham.schemify(tag='sunspec_enumeration', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Enumeration:
    enumeration_uuid = epyqlib.attrsmodel.attr_uuid() # references to parametermodel.Enumeration

    uuid = epyqlib.attrsmodel.attr_uuid()

    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        #isintance(node, DictPair)?
        return False

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)


@graham.schemify(tag='sunspec_bit_field', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class BitField:
    enumeration_uuid = epyqlib.attrsmodel.attr_uuid() #maybe this should be a bitfield_uuid?  IDK
    #how we plan to use it, but I can see how an enum could be used to define a bitfield
    uuid = epyqlib.attrsmodel.attr_uuid()
    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        #isintance(node, DictPair)?
        return False

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)


def check_block_offsets_and_length(self):
    length = 0

    root = self.find_root()

    for point in self.children:
        type_ = root.model.node_from_uuid(point.type_uuid)
        if type_.name != 'string' and point.size != type_.value:
            raise MismatchedSizeAndTypeError(
                f'Expected {type_.value} for {type_.name}'
                f', is {point.size} for {point.name}'
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

    def can_delete(self, node):
        return False

    check_offsets_and_length = check_block_offsets_and_length

    def add_data_points(self, uint16_uuid, model_id):
        parameters = [
            epyqlib.pm.parametermodel.Parameter(
                name=model_id,
                abbreviation='ID',
            ),
            epyqlib.pm.parametermodel.Parameter(
                name='',
                abbreviation='L',
                comment='Model Length',
            ),
        ]
        points = [
            DataPoint(
                block_offset=0,
                size=1,
                type_uuid=uint16_uuid,
                parameter_uuid=parameters[0].uuid,
            ),
            DataPoint(
                block_offset=1,
                size=1,
                type_uuid=uint16_uuid,
                parameter_uuid=parameters[1].uuid,
            ),
        ]

        for point in points:
            self.append_child(point)

        return parameters


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

    def can_delete(self, node):
        return False

    check_offsets_and_length = check_block_offsets_and_length


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
                marshmallow.fields.Nested(graham.schema(Enumeration)),
                marshmallow.fields.Nested(graham.schema(BitField)),
            )),
        ),
    )

    uuid = epyqlib.attrsmodel.attr_uuid()
    
    def __attrs_post_init__(self):
        super().__init__()

    def can_drop_on(self, node):
        return False

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

    def check_offsets_and_length(self):
        length = 0

        for block in self.children:
            length += block.check_offsets_and_length()

        return length


#class Repeating...?


Root = epyqlib.attrsmodel.Root(
    default_name='SunSpec',
    valid_types=(Model, DataPoint),
)


types = epyqlib.attrsmodel.Types(
    types=(
        Root,
        Model,
        DataPoint,
        Enumeration,
        BitField,
        HeaderBlock,
        FixedBlock,
    ),
)


# TODO: CAMPid 943896754217967154269254167
def merge(name, *types):
    return tuple((x, name) for x in types)


columns = epyqlib.attrsmodel.columns(
    merge('name', HeaderBlock, FixedBlock) + merge('id', Model),
    merge('length', Model) + merge('size', DataPoint),
    merge('factor_uuid', DataPoint),
    merge('parameter_uuid', DataPoint),
    merge('type_uuid', DataPoint),
    merge('enumeration_uuid', Enumeration, BitField),
    merge('offset', DataPoint, HeaderBlock, FixedBlock),
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
