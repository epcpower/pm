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


def merge(name, *types):
    return tuple((x, name) for x in types)


@graham.schemify(tag="anomaly")
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class Anomaly(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default="New Anomaly",
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )

    abbreviation = epyqlib.attrsmodel.create_code_identifier_string_attribute(
        default="NEW_ANOMALY",
    )

    uuid = epyqlib.attrsmodel.attr_uuid()

    code = epyqlib.attrsmodel.create_integer_attribute(default=0)

    response_level_inactive = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
    )
    epyqlib.attrsmodel.attrib(
        attribute=response_level_inactive,
        human_name="Response Level Inactive",
        data_display=epyqlib.attrsmodel.name_from_uuid,
        delegate=epyqlib.attrsmodel.RootDelegateCache(
            list_selection_root="anomaly_response_levels",
        ),
    )

    response_level_active = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
    )
    epyqlib.attrsmodel.attrib(
        attribute=response_level_active,
        human_name="Response Level Active",
        data_display=epyqlib.attrsmodel.name_from_uuid,
        delegate=epyqlib.attrsmodel.RootDelegateCache(
            list_selection_root="anomaly_response_levels",
        ),
    )

    trigger_type = epyqlib.attrsmodel.attr_uuid(
        default=None,
        allow_none=True,
    )
    epyqlib.attrsmodel.attrib(
        attribute=trigger_type,
        human_name="Trigger type",
        data_display=epyqlib.attrsmodel.name_from_uuid,
        delegate=epyqlib.attrsmodel.RootDelegateCache(
            list_selection_root="anomaly_trigger_types",
        ),
    )

    comment = attr.ib(
        default=None,
        converter=epyqlib.attrsmodel.to_str_or_none,
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(allow_none=True),
        ),
    )

    def __attrs_post_init__(self):
        super().__init__()

    can_delete = epyqlib.attrsmodel.childless_can_delete

    # Returns SunSpec enumerator instance for this anomaly.
    def to_enum(self):
        return epyqlib.pm.parametermodel.SunSpecEnumerator(
            name=self.name, value=self.code
        )


@graham.schemify(tag="anomaly_table")
@epyqlib.attrsmodel.ify()
@epyqlib.utils.qt.pyqtify()
@attr.s(hash=False)
class AnomalyTable(epyqlib.treenode.TreeNode):
    name = attr.ib(
        default="New Anomaly Table",
        metadata=graham.create_metadata(
            field=marshmallow.fields.String(),
        ),
    )

    abbreviation = epyqlib.attrsmodel.create_code_identifier_string_attribute(
        default="NEW_ANOMALY_TABLE",
    )

    uuid = epyqlib.attrsmodel.attr_uuid()

    children = attr.ib(
        default=attr.Factory(list),
        metadata=graham.create_metadata(
            field=graham.fields.MixedList(
                fields=(marshmallow.fields.Nested(graham.schema(Anomaly)),)
            ),
        ),
    )

    def __attrs_post_init__(self):
        super().__init__()

    def can_delete(self, node=None):
        if node is None:
            return self.tree_parent.can_delete(node=self)

        return True


Root = epyqlib.attrsmodel.Root(
    default_name="Anomaly Tables",
    valid_types=(AnomalyTable,),
)

types = epyqlib.attrsmodel.Types(
    types=(Root, Anomaly, AnomalyTable),
)

columns = epyqlib.attrsmodel.columns(
    merge("name", Anomaly, AnomalyTable),
    merge("abbreviation", Anomaly, AnomalyTable),
    merge("code", Anomaly),
    merge("response_level_inactive", Anomaly),
    merge("response_level_active", Anomaly),
    merge("trigger_type", Anomaly),
    merge("comment", Anomaly),
    merge("uuid", Anomaly, AnomalyTable),
)
