import attr
import graham
import marshmallow

import epyqlib.attrsmodel
import epyqlib.pm.parametermodel
from PyQt5 import QtCore

# sunspec enumerations will be stored in parametermodel.Enumeration and be
# mappable into the sunspec interface


# need a parametermodel.Enumeration of sunspec types


@graham.schemify(tag='data_point', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class DataPoint(epyqlib.treenode.TreeNode):
    factor_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        human_name='Scale Factor',
        allow_none=True,
        data_display=epyqlib.attrsmodel.name_from_uuid,
    )
    units = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    parameter_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
        human_name='Parameter',
        data_display=epyqlib.attrsmodel.name_from_uuid,
    )
    type = attr.ib( #TODO enumeration reference/list_selection_root something something ... words
        default='uint16',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    enumeration_uuid = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
        human_name='Enumeration',
        data_display=epyqlib.attrsmodel.name_from_uuid,
        list_selection_root='enumerations',
    )  # probably to parametermodel.Enumeration (applicable point)

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

    # size is purely calculated from the type

    name = attr.ib(
        default='New data point',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    label = attr.ib(
        default='New label',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )  # long name, short description, somewhere between name and description
    description = attr.ib(
        default='New description',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    notes = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
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

    @property
    def size(self):
        # TODO: something based on self.type
        return None


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


def header_data_points():
    return [
        DataPoint(
            name='ID',
            block_offset=0,
        ),
        DataPoint(
            name='L',
            block_offset=1,
            label=None,
            description='Model Length',
        ),
    ]


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
        factory=header_data_points,
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
    merge('name', HeaderBlock, FixedBlock, DataPoint) + merge('id', Model),
    merge('label', DataPoint),
    merge('length', Model),
    merge('factor_uuid', DataPoint),
    merge('units', DataPoint),
    merge('parameter_uuid', DataPoint),
    merge('type', DataPoint),
    merge('enumeration_uuid', DataPoint, Enumeration, BitField),
    merge('offset', DataPoint, HeaderBlock, FixedBlock),
    merge('block_offset', DataPoint),
    merge('description', DataPoint),
    merge('notes', DataPoint),
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
