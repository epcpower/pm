import collections

import attr
import graham

import epyqlib.attrsmodel
import epyqlib.tests.pm.test_parametermodel
import epyqlib.tests.test_attrsmodel

import epcpm.canmodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


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


def assert_incomplete_types(name):
    assert [] == [
        cls
        for cls in epcpm.canmodel.types.types.values()
        if not hasattr(cls, name)
    ]


def test_all_have_can_drop_on():
    assert_incomplete_types('can_drop_on')


def test_all_have_can_delete():
    assert_incomplete_types('can_delete')


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
    parameter_model = epyqlib.tests.pm.test_parametermodel.SampleModel.build()
    parameter_model.fill()

    can_model = SampleModel.build()
    can_model.fill()
    can_model.model.add_drop_sources(parameter_model.model)

    can_table = can_model.parameters_message.child_from(parameter_model.table)
    can_model.parameters_message.append_child(can_table)

    assert count_types(can_table.children) == {}

    expected_counts = {
        epcpm.canmodel.Signal: 2,
        epcpm.canmodel.Multiplexer: 8,
    }

    can_table.update()
    for child, bits in zip(can_table.children, (8, 16)):
        child.bits = bits

    can_table.update()
    assert count_types(can_table.children) == expected_counts

    can_table.update()
    assert count_types(can_table.children) == expected_counts

    can_table.table_uuid = None
    can_table.update()

    assert count_types(can_table.children) == {}
