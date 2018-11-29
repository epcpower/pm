import pathlib

import click
import graham

import epyqlib.pm.valuesetmodel

import epcpm.project
import epcpm.symtoproject


def relative_path(target, reference):
    reference = pathlib.Path(reference)
    if reference.is_file():
        reference = reference.parents[0]

    return pathlib.Path(target).resolve().relative_to(reference.resolve())


@click.command()
@click.option('--sym', type=click.File('rb'), required=True)
@click.option('--hierarchy', type=click.File(), required=True)
@click.option('--project', type=click.File('w'), required=True)
@click.option('--parameters', type=click.File('w'), required=True)
@click.option('--can', type=click.File('w'), required=True)
@click.option('--epyq-value-set', type=click.File('w'))
@click.option('--add-tables/--no-add-tables', default=False)
def cli(sym, hierarchy, project, parameters, can, epyq_value_set, add_tables):
    parameters_root, can_root = epcpm.symtoproject.load_can_file(
        can_file=sym,
        file_type=str(pathlib.Path(sym.name).suffix[1:]),
        parameter_hierarchy_file=hierarchy,
    )

    project_path = pathlib.Path(project.name).parents[0]
    project_path.mkdir(parents=True, exist_ok=True)

    project_model = epcpm.project.Project(
        paths = epcpm.project.Models(
            parameters=relative_path(parameters.name, project_path),
            can=relative_path(can.name, project_path),
        ),
        models = epcpm.project.Models(
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

    epcpm.project._post_load(project_model)

    if add_tables:
        epcpm.symtoproject.go_add_tables(
            parameters_root=project_model.models.parameters.root,
            can_root=project_model.models.can.root,
        )

    project.write(graham.dumps(project_model, indent=4).data)
    parameters.write(graham.dumps(parameters_root, indent=4).data)
    can.write(graham.dumps(can_root, indent=4).data)

    if epyq_value_set is not None:
        value_set = epyqlib.pm.valuesetmodel.create_blank(
            parameter_model=project_model.models.parameters,
        )

        parameters_root, = [
            node
            for node in value_set.parameter_model.root.children
            if node.name == 'Parameters'
        ]

        epyqlib.pm.valuesetmodel.copy_parameter_data(
            value_set=value_set,
            human_names=False,
            base_node=parameters_root,
            calculate_unspecified_min_max=True,
            symbol_root=can_root,
        )

        epyq_value_set.write(graham.dumps(value_set.model.root, indent=4).data)
