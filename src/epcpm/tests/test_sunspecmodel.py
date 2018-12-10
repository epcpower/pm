import epyqlib.tests.test_attrsmodel

import epcpm.sunspecmodel


# See file COPYING in this source tree
__copyright__ = 'Copyright 2018, EPC Power Corp.'
__license__ = 'GPLv2+'


TestAttrsModel = epyqlib.attrsmodel.build_tests(
    types=epcpm.sunspecmodel.types,
    root_type=epcpm.sunspecmodel.Root,
    columns=epcpm.sunspecmodel.columns,
)


def test_model_has_header():
    model = epcpm.sunspecmodel.Model()

    assert model.children[0].name == 'ID'
    assert model.children[1].name == 'L'
