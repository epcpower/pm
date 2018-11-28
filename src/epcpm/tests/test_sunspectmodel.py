import epyqlib.tests.test_attrsmodel

import epcpm.sunspecmodel


# See file COPYING in this source tree
__copyright__ = 'Copyright 2018, EPC Power Corp.'
__license__ = 'GPLv2+'


def test_all_addable_also_in_types():
    # Since addable types is dynamic and could be anything... this
    # admittedly only checks the addable types on default instances.
    for cls in epcpm.sunspecmodel.types.types.values():
        addable_types = cls.all_addable_types().values()
        assert set(addable_types) - set(epcpm.sunspecmodel.types) == set()


def test_all_have_can_drop_on():
    epyqlib.tests.test_attrsmodel.all_have_can_drop_on(
        types=epcpm.sunspecmodel.types,
    )


def test_all_have_can_delete():
    epyqlib.tests.test_attrsmodel.all_have_can_delete(
        types=epcpm.sunspecmodel.types,
    )


def test_all_fields_in_columns():
    epyqlib.tests.test_attrsmodel.all_fields_in_columns(
        types=epcpm.sunspecmodel.types,
        root_type=epcpm.sunspecmodel.Root,
        columns=epcpm.sunspecmodel.columns,
    )
