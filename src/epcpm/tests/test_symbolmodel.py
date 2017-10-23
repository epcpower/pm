import epcpm.symbolmodel

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


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
