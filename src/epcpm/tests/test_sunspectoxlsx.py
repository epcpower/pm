import csv
import pathlib

import epcpm.project
import epcpm.smdxtosunspec
import epcpm.sunspectoxlsx


this = pathlib.Path(__file__).resolve()
here = this.parent


smdx_path = here/'sunspec'


def test_x():
    project = epcpm.project.loadp(here/'project'/'project.pmp')

    model = project.models.sunspec
    parameter_model = project.models.parameters

    enumerations = parameter_model.list_selection_roots['enumerations']
    sunspec_types = epcpm.sunspecmodel.build_sunspec_types_enumeration()
    enumerations.append_child(sunspec_types)
    parameter_model.list_selection_roots['sunspec types'] = sunspec_types

    requested_models = [1, 17, 103, 65534]
    sunspec_models = epcpm.smdxtosunspec.import_models(
        *requested_models,
        parameter_model=parameter_model,
        paths=[smdx_path],
    )

    for sunspec_model in sunspec_models:
        model.root.append_child(sunspec_model)

    project.filename = here/'project_with_sunspec'/'project.pmp'
    project.paths['sunspec'] = 'sunspec.json'
    project.save()

    builder = epcpm.sunspectoxlsx.builders.wrap(
        wrapped=model.root,
        parameter_uuid_finder=model.node_from_uuid,
        parameter_model=project.models.parameters,
    )

    workbook = builder.gen()

    assert workbook.sheetnames == ['1', '17', '103', '65534']

    workbook.save('test_sunspectoxlsx.xlsx')

    with open('test_sunspectoxlsx.csv', 'w', newline='') as file:
        writer = csv.writer(file)

        for sheet in workbook.worksheets:
            for row in sheet.rows:
                writer.writerow(cell.value for cell in row)
