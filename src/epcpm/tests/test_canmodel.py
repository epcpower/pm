import collections
import json
import pathlib

import attr
import graham
import pytest

import epyqlib.attrsmodel
import epyqlib.pm.parametermodel
import epyqlib.tests.pm.test_parametermodel
import epyqlib.tests.test_attrsmodel

import epcpm.canmodel
import epcpm.project

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


here = pathlib.Path(__file__).parent

with open(here/'project'/'can.json') as f:
    serialized_sample = f.read()


@attr.s
class SampleModelFromFile:
    root = attr.ib()
    parameter_root = attr.ib()
    model = attr.ib()
    parameter_model = attr.ib()
    table = attr.ib()
    parameter_table = attr.ib()
    project = attr.ib()

    @classmethod
    def build(cls):
        project = epcpm.project.loadp(here / 'project' / 'project.pmp')
        can_table, = project.models.can.root.nodes_by_attribute(
            attribute_value='First Table',
            attribute_name='name',
        )
        parameter_table = project.models.parameters.node_from_uuid(
            can_table.table_uuid,
        )

        sample_model = cls(
            root=project.models.can.root,
            parameter_root=project.models.parameters.root,
            model=project.models.can,
            parameter_model=project.models.parameters,
            table=can_table,
            parameter_table=parameter_table,
            project=project,
        )

        return sample_model


@pytest.fixture
def sample():
    sample_model = SampleModelFromFile.build()
    sample_model.parameter_table.update()
    sample_model.table.update()

    return sample_model


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


TestAttrsModel = epyqlib.attrsmodel.build_tests(
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


# TODO: CAMPid 094329054780541680163054608431067542971349
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


def test_table_update_same_uuid(sample):
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

    sample.table.update()

    original = collect(sample.table)

    sample.table.update()

    after_update = collect(sample.table)

    assert after_update == original


def test_sample_dumps_consistently(sample):
    dumped = graham.dumps(sample.root, indent=4)

    def load(s):
        return json.loads(s, object_pairs_hook=collections.OrderedDict)

    print()
    print(dumped.data)

    assert load(dumped.data) == load(serialized_sample)


def test_add_enumerator_update_table(sample):
    enumeration, = sample.parameter_root.nodes_by_attribute(
        attribute_value='Enumeration Two',
        attribute_name='name',
    )

    enumeration.append_child(epyqlib.pm.parametermodel.Enumerator(
        name='ET_New',
        value=42,
        uuid='173ba72c-bf2a-42a1-aab6-3e5fc49f10e7',
    ))

    sample.parameter_table.update()
    sample.table.update()
