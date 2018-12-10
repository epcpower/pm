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

    header_block = model.children[0]

    assert isinstance(header_block, epcpm.sunspecmodel.HeaderBlock)

    assert header_block.children[0].name == 'ID'
    assert header_block.children[1].name == 'L'

    assert header_block.offset == 0

    fixed_block = model.children[1]

    assert fixed_block.offset == 2
