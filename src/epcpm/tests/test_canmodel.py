import collections
import json
import pathlib

import attr
import graham

import epyqlib.attrsmodel
import epyqlib.tests.pm.test_parametermodel
import epyqlib.tests.test_attrsmodel

import epcpm.canmodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


here = pathlib.Path(__file__).parent

with open(here/'project'/'can.json') as f:
    serialized_sample = f.read()


def test_hex_field():
    @graham.schemify(tag='test')
    @attr.s(hash=False)
    class Test:
        field = attr.ib(
            metadata=graham.create_metadata(
                field=epcpm.canmodel.HexadecimalIntegerField(),
            ),
        )
        none = attr.ib(
            default=None,
            metadata=graham.create_metadata(
                field=epcpm.canmodel.HexadecimalIntegerField(
                    allow_none=True,
                ),
            ),
        )

    t = Test(field=0x123)

    serialized = '{"_type": "test", "field": "0x123", "none": null}'

    assert graham.dumps(t).data == serialized
    assert graham.schema(Test).loads(serialized).data == t


def test_all_addable_also_in_types():
    # Since addable types is dynamic and could be anything... this
    # admittedly only checks the addable types on default instances.
    for cls in epcpm.canmodel.types.types.values():
        addable_types = cls.all_addable_types().values()
        assert set(addable_types) - set(epcpm.canmodel.types) == set()


def test_all_have_can_drop_on():
    epyqlib.tests.test_attrsmodel.all_have_can_drop_on(
        types=epcpm.canmodel.types,
    )


def test_all_have_can_delete():
    epyqlib.tests.test_attrsmodel.all_have_can_delete(
        types=epcpm.canmodel.types,
    )


def test_all_fields_in_columns():
    epyqlib.tests.test_attrsmodel.all_fields_in_columns(
        types=epcpm.canmodel.types,
        root_type=epcpm.canmodel.Root,
        columns=epcpm.canmodel.columns,
    )


@attr.s
class SampleModel:
    root = attr.ib(
        factory=lambda: epcpm.canmodel.Root(
            uuid='b92665a4-6deb-4faf-8747-3aa20cf0bcf2',
        ),
    )
    model = attr.ib(default=None)
    parameters_message = attr.ib(default=None)
    parameters_multiplexer = attr.ib(default=None)

    @classmethod
    def build(cls):
        sample_model = cls()
        sample_model.model = epyqlib.attrsmodel.Model(
            root=sample_model.root,
            columns=epcpm.canmodel.columns,
        )

        return sample_model

    def fill(self):
        self.parameters_message = epcpm.canmodel.MultiplexedMessage(
            uuid='e5228583-1e7f-4a8a-a529-bbd84b2d0fca',
        )
        self.root.append_child(self.parameters_message)

        self.parameters_multiplexer = epcpm.canmodel.Multiplexer(
            uuid='70a1ab55-09eb-4617-b6a4-19ec821e7dfe',
        )
        self.parameters_message.append_child(self.parameters_multiplexer)

        self.model.update_nodes()


def count_types(sequence):
    counts = collections.defaultdict(int)

    for element in sequence:
        counts[type(element)] += 1


    return counts


def test_table_update_unlinked():
    expected_counts = {
        epcpm.canmodel.Signal: 2,
        epcpm.canmodel.Multiplexer: 24,
    }

    project = epcpm.project.loadp(here/'project'/'project.pmp')
    can_table, = project.models.can.root.nodes_by_attribute(
        attribute_value='First Table',
        attribute_name='name',
    )
    parameter_table = project.models.parameters.node_from_uuid(
        can_table.table_uuid,
    )
    parameter_table.update()

    assert count_types(can_table.children) == expected_counts

    can_table.update()
    assert count_types(can_table.children) == expected_counts

    can_table.table_uuid = None
    can_table.update()

    assert count_types(can_table.children) == {}


def test_table_update_same_uuid():
    project = epcpm.project.loadp(here/'project'/'project.pmp')
    can_table, = project.models.can.root.nodes_by_attribute(
        attribute_value='First Table',
        attribute_name='name',
    )
    parameter_table = project.models.parameters.node_from_uuid(
        can_table.table_uuid,
    )
    parameter_table.update()

    # TODO: CAMPid 9784566547216435136479765479163496731
    def collect(node):
        def collect(node, payload):
            payload[node.uuid] = node.name

        results = {}

        node.traverse(
            call_this=collect,
            internal_nodes=True,
            payload=results,
        )

        return results

    can_table.update()

    original = collect(can_table)

    can_table.update()

    after_update = collect(can_table)

    assert after_update == original


def test_sample_dumps_consistently():
    project = epcpm.project.loadp(here/'project'/'project.pmp')
    can_table, = project.models.can.root.nodes_by_attribute(
        attribute_value='First Table',
        attribute_name='name',
    )
    parameter_table = project.models.parameters.node_from_uuid(
        can_table.table_uuid,
    )
    parameter_table.update()
    can_table.update()

    dumped = graham.dumps(project.models.can.root, indent=4)

    def load(s):
        return json.loads(s, object_pairs_hook=collections.OrderedDict)

    print()
    print(dumped.data)

    assert load(dumped.data) == load(serialized_sample)
