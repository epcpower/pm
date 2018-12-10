import pathlib

import epcpm.project
import epcpm.sunspectoxlsx

here = pathlib.Path(__file__).parent


def test_x():
    project = epcpm.project.loadp(here/'project'/'project.pmp')

    model = project.models.sunspec

    builder = epcpm.sunspectoxlsx.builders.wrap(
        wrapped=model.root,
        parameter_uuid_finder=model.node_from_uuid,
        parameter_model=project.models.parameters,
    )

    workbook = builder.gen()

    assert workbook.sheetnames == ['1', '17', '103', '65534']

    workbook.save('test_sunspectoxlsx.xlsx')
