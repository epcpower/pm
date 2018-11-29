import textwrap

import graham

import epcpm.project

import pathlib

import epyqlib.pm

reference_string = textwrap.dedent('''\
{
    "_type": "project",
    "paths": {
        "_type": "models",
        "parameters": "parameters.json",
        "can": "can.json",
        "sunspec": "sunspec.json"
    }
}''')

reference_project = epcpm.project.Project()
reference_project.paths.parameters = 'parameters.json'
reference_project.paths.can = 'can.json'
reference_project.paths.sunspec = 'sunspec.json'


def test_save():
    assert reference_string == graham.dumps(reference_project, indent=4).data


def test_load():
    assert reference_project == (
        graham.schema(epcpm.project.Project).loads(reference_string).data
    )


def test_model_iterable():
    model = epcpm.project.Models()

    assert tuple(model) == ('parameters', 'can', 'sunspec')


def test_model_set_all():
    model = epcpm.project.Models()

    value = object()

    model.set_all(value)

    assert all(v is value for v in model.values())


def test_model_items():
    model = epcpm.project.Models()

    expected = (
        ('parameters', None),
        ('can', None),
        ('sunspec', None),
    )

    assert tuple(model.items()) == expected


def test_model_values():
    model = epcpm.project.Models()

    for name in model:
        model[name] = name + '_'

    assert tuple(model.values()) == ('parameters_', 'can_', 'sunspec_')


def test_model_getitem():
    model = epcpm.project.Models()

    values = []
    for name in model:
        values.append(model[name])

    assert values == [None, None, None]


def test_model_proper_selection_roots():
    project = epcpm.project.loadp(
        pathlib.Path(__file__).with_name('example_project.pmp')
    )

    expected = epyqlib.pm.parametermodel.types.list_selection_roots()
    
    assert set(project.models.parameters.list_selection_roots.keys()) == expected
