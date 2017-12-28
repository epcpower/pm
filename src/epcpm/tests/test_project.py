import textwrap

import graham

import epcpm.project


reference_string = textwrap.dedent('''\
{
    "_type": "project",
    "paths": {
        "_type": "models",
        "parameters": "parameters.json",
        "can": "can.json"
    }
}''')

reference_project = epcpm.project.Project()
reference_project.paths.parameters = 'parameters.json'
reference_project.paths.can = 'can.json'


def test_save():
    assert reference_string == graham.dumps(reference_project, indent=4).data


def test_load():
    assert reference_project == (
        graham.schema(epcpm.project.Project).loads(reference_string).data
    )


def test_model_iterable():
    model = epcpm.project.Models()

    assert tuple(model) == ('parameters', 'can')


def test_model_set_all():
    model = epcpm.project.Models()

    value = object()

    model.set_all(value)

    assert all(v is value for v in model.values())


def test_model_items():
    model = epcpm.project.Models()

    assert tuple(model.items()) == (('parameters', None), ('can', None))


def test_model_values():
    model = epcpm.project.Models()

    for name in model:
        model[name] = name + '_'

    assert tuple(model.values()) == ('parameters_', 'can_')


def test_model_getitem():
    model = epcpm.project.Models()

    values = []
    for name in model:
        values.append(model[name])

    assert values == [None, None]
