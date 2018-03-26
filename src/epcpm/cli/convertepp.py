import json
import pathlib

import click
import graham

import epyqlib.pm.valuesetmodel

import epcpm.project
import epcpm.symtoproject


@click.command()
@click.option('--sym', type=click.File('rb'), required=True)
@click.option('--hierarchy', type=click.File(), required=True)
@click.option('--parameters', type=click.File())
@click.option('--value-set', type=click.File('w'), required=True)
def cli(sym, hierarchy, parameters, value_set):
    value_set_file = value_set

    parameters_root, can_root = epcpm.symtoproject.load_can_file(
        can_file=sym,
        file_type=str(pathlib.Path(sym.name).suffix[1:]),
        parameter_hierarchy_file=hierarchy,
    )

    project_model = epcpm.project.Project(
        models=epcpm.project.Models(
            parameters=epyqlib.attrsmodel.Model(
                root=parameters_root,
                columns=epyqlib.pm.parametermodel.columns,
            ),
            can=epyqlib.attrsmodel.Model(
                root=can_root,
                columns=epcpm.canmodel.columns,
            ),
        ),
    )

    value_set = epyqlib.pm.valuesetmodel.create_blank(
        parameter_model=project_model.models.parameters,
    )

    parameters_root, = (
        node
        for node in value_set.parameter_model.root.children
        if node.name == 'Parameters'
    )

    epyqlib.pm.valuesetmodel.copy_parameter_data(
        value_set=value_set,
        human_names=False,
        base_node=parameters_root,
        calculate_unspecified_min_max=True,
        can_root=can_root,
    )

    value_set_parameters = {
        parameter.name: parameter
        for parameter in value_set.model.root.children
    }

    parameters = json.load(parameters)

    for name, value in parameters.items():
        value_set_parameters[name].value = value

    value_set_file.write(graham.dumps(value_set.model.root, indent=4).data)
