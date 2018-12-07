import attr
import graham
import marshmallow

import epyqlib.attrsmodel
import epyqlib.pm.parametermodel

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
    )
    epyqlib.attrsmodel.attrib(
        attribute=parameter_uuid,
        human_name='Parameter UUID',
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
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    ) # this is somewhat redundant with the position in the list of data
            # points but helpful for keeping things from incidentally floating
            # around especially in custom models where we have no sunspec
            # model to be validating against
            # for now, yes, this is vaguely nondescript of address vs block offset

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
        return False

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
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(fields=(
                marshmallow.fields.Nested(graham.schema(DataPoint)),
                marshmallow.fields.Nested(graham.schema(Enumeration)),
                marshmallow.fields.Nested(graham.schema(BitField)),
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
        if node is None:
            return self.tree_parent.can_delete(node=self)

#class Repeating...?


Root = epyqlib.attrsmodel.Root(
    default_name='SunSpec',
    valid_types=(Model, DataPoint),
)


types = epyqlib.attrsmodel.Types(
    types=(Root, Model, DataPoint, Enumeration, BitField),
)


# TODO: CAMPid 943896754217967154269254167
def merge(name, *types):
    return tuple((x, name) for x in types)


columns = epyqlib.attrsmodel.columns(
    merge('name', DataPoint) + merge('id', Model),
    merge('label', DataPoint),
    merge('length', Model),
    merge('factor_uuid', DataPoint),
    merge('units', DataPoint),
    merge('parameter_uuid', DataPoint),
    merge('type', DataPoint),
    merge('enumeration_uuid', DataPoint, Enumeration, BitField),
    merge('offset', DataPoint),
    merge('description', DataPoint),
    merge('notes', DataPoint),
    merge('uuid', *types.types.values()),
)
