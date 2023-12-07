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

    uuid = epyqlib.attrsmodel.attr_uuid()

    code = epyqlib.attrsmodel.create_integer_attribute(default=0)

    response_level_I = epyqlib.attrsmodel.create_integer_attribute(default=0)

    response_level_A = epyqlib.attrsmodel.create_integer_attribute(default=0)

    trigger_type = epyqlib.attrsmodel.create_integer_attribute(default=0)

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
    merge("code", Anomaly),
    merge("response_level_I", Anomaly),
    merge("response_level_A", Anomaly),
    merge("trigger_type", Anomaly),
    merge("comment", Anomaly),
    merge("uuid", Anomaly, AnomalyTable),
)
