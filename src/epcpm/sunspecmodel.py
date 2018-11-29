import attr
import graham
import marshmallow

import epyqlib.attrsmodel

# sunspec enumerations will be stored in parametermodel.Enumeration and be
# mappable into the sunspec interface


# need a parametermodel.Enumeration of sunspec types


@graham.schemify(tag='data_point', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s
class DataPoint(epyqlib.treenode.TreeNode):
    factor = attr.ib(
        default=0,
        converter=int,
        metadata=graham.create_metadata(
            field=marshmallow.fields.Integer(),
        ),
    ) # referencing another data point uuid
    units = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )
    description = attr.ib(
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
            field=marshmallow.fields.Dict(),
        ),
    )
    enumeration_uuid = epyqlib.attrsmodel.attr_uuid()  # probably to parametermodel.Enumeration (applicable point)
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
            field=marshmallow.fields.String(),
        ),
    )  # long name, short description, somewhere between name and description
    description = attr.ib(
        default='New label',
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )
    notes = attr.ib(
        default=None,
        convert=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )

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


@graham.schemify(tag='sunspec_enumeration', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s
class Enumeration:
    enumeration_uuid = epyqlib.attrsmodel.attr_uuid() # references to parametermodel.Enumeration

    def __attrs_post_init__(self):
        super().__init__()


@graham.schemify(tag='sunspec_bit_field', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s
class BitField:
    pass


@graham.schemify(tag='sunspec_model', register=True)
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s
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

    def __attrs_post_init__(self):
        super().__init__()


#class Repeating...?


Root = epyqlib.attrsmodel.Root(
    default_name='SunSpec',
    valid_types=(Model,),
)


types = epyqlib.attrsmodel.Types(
    types=(Root,),
)


# TODO: CAMPid 943896754217967154269254167
def merge(name, *types):
    return tuple((x, name) for x in types)


columns = epyqlib.attrsmodel.columns(
    merge('name', *types.types.values()),
    merge('uuid', *types.types.values()),
)
