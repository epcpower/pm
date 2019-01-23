import collections
import pathlib

import epyqlib.tests.test_attrsmodel

import epcpm.project
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
    project = epcpm.project.loadp(here/'project'/'project.pmp')

    parameter_model = project.models.parameters
    enumerations = parameter_model.list_selection_roots['enumerations']
    sunspec_types = epcpm.sunspecmodel.build_sunspec_types_enumeration()
    enumerations.append_child(sunspec_types)
    parameter_model.list_selection_roots['sunspec types'] = sunspec_types

    types = project.models.parameters.list_selection_roots['sunspec types']

    model = epcpm.sunspecmodel.Model()
    parameters = model.children[0].add_data_points(
        uint16_uuid=types.child_by_name('uint16').uuid,
        model_id=1,
    )

    header_block = model.children[0]

    assert isinstance(header_block, epcpm.sunspecmodel.HeaderBlock)

    assert len(header_block.children) == len(parameters)
    for point, parameter in zip(header_block.children, parameters):
        assert point.parameter_uuid == parameter.uuid

    assert parameters[0].abbreviation == 'ID'
    assert parameters[1].abbreviation == 'L'

    assert header_block.offset == 0

    fixed_block = model.children[1]

    assert fixed_block.offset == 2


# TODO: CAMPid 094329054780541680163054608431067542971349
def count_types(sequence):
    counts = collections.defaultdict(int)

    for element in sequence:
        counts[type(element)] += 1

    return counts


def test_table_update_unlinked():
    expected_counts = {
        epcpm.sunspecmodel.TableRepeatingBlock: 8,
        epcpm.sunspecmodel.DataPoint: 2,
    }

    project = epcpm.project.loadp(here/'project'/'project.pmp')
    sunspec_table, = project.models.sunspec.root.nodes_by_attribute(
        attribute_value='First Table',
        attribute_name='name',
    )
    parameter_table = project.models.parameters.node_from_uuid(
        sunspec_table.parameter_table_uuid,
    )
    parameter_table.update()

    assert count_types(sunspec_table.children) == expected_counts

    sunspec_table.update()
    assert count_types(sunspec_table.children) == expected_counts

    print()
    print(epyqlib.utils.qt.indented_text_from_model(project.models.sunspec.model))

    sunspec_table.parameter_table_uuid = None
    sunspec_table.update()

    assert count_types(sunspec_table.children) == {}
