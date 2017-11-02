import attr
import graham

import epyqlib.attrsmodel

import epcpm.symbolmodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


def test_hex_field():
    @graham.schemify(tag='test')
    @attr.s(hash=False)
    class Test:
        field = attr.ib(
            metadata=graham.create_metadata(
                field=epcpm.symbolmodel.HexadecimalIntegerField(),
            ),
        )
        none = attr.ib(
            default=None,
            metadata=graham.create_metadata(
                field=epcpm.symbolmodel.HexadecimalIntegerField(
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
    for cls in epcpm.symbolmodel.types.types.values():
        addable_types = cls.all_addable_types().values()
        assert set(addable_types) - set(epcpm.symbolmodel.types) == set()


def assert_incomplete_types(name):
    assert [] == [
        cls
        for cls in epcpm.symbolmodel.types.types.values()
        if not hasattr(cls, name)
    ]


def test_all_have_can_drop_on():
    assert_incomplete_types('can_drop_on')


def test_all_have_can_delete():
    assert_incomplete_types('can_delete')


def test_all_fields_in_columns():
    epyqlib.tests.test_attrsmodel.all_fields_in_columns(
        types=epcpm.symbolmodel.types,
        root_type=epcpm.symbolmodel.Root,
        columns=epcpm.symbolmodel.columns,
    )
