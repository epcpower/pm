import pathlib

import epyqlib.tests.test_attrsmodel

import epcpm.sunspecmodel


# See file COPYING in this source tree
__copyright__ = 'Copyright 2018, EPC Power Corp.'
__license__ = 'GPLv2+'


this = pathlib.Path(__file__).resolve()
here = this.parent


TestAttrsModel = epyqlib.attrsmodel.build_tests(
    types=epcpm.sunspecmodel.types,
    root_type=epcpm.sunspecmodel.Root,
    columns=epcpm.sunspecmodel.columns,
)


def test_model_has_header():
    project = epcpm.project.loadp(here / 'project' / 'project.pmp')
    types = project.models.parameters.list_selection_roots['sunspec types']

    model = epcpm.sunspecmodel.Model()
    model.children[0].add_data_points(
        uint16_uuid=types.child_by_name('uint16').uuid,
    )

    header_block = model.children[0]

    assert isinstance(header_block, epcpm.sunspecmodel.HeaderBlock)

    assert header_block.children[0].name == 'ID'
    assert header_block.children[1].name == 'L'

    assert header_block.offset == 0

    fixed_block = model.children[1]

    assert fixed_block.offset == 2
