import pathlib

import click
import graham

import epyqlib.attrsmodel

import epcpm.project
import epcpm.symbolstosym
import epcpm.symtoproject


def relative_path(target, reference):
    reference = pathlib.Path(reference)
    if reference.is_file():
        reference = reference.parents[0]

    return pathlib.Path(target).resolve().relative_to(reference.resolve())


@click.command()
@click.option('--project', 'project_file', type=click.File(), required=True)
@click.option('--sym', 'sym_file', type=click.File('w'), required=True)
def cli(project_file, sym_file):
    project = graham.schema(epcpm.project.Project).loads(
        project_file.read(),
    ).data
    project.filename = pathlib.Path(project_file.name).absolute()

    parameter_model = load_model(
        project=project,
        path=project.paths.parameters,
        root_type=epcpm.parametermodel.Root,
        columns=epcpm.parametermodel.columns,
    )

    symbol_model = load_model(
        project=project,
        path=project.paths.symbols,
        root_type=epcpm.symbolmodel.Root,
        columns=epcpm.symbolmodel.columns,
    )

    symbol_model.droppable_from.add(parameter_model.root)
    symbol_model.droppable_from.add(symbol_model.root)

    builder = epcpm.symbolstosym.builders.wrap(
        wrapped=symbol_model.root,
        parameter_uuid_finder=symbol_model.node_from_uuid,
    )

    sym_file.write(builder.gen())


def load_model(project, path, root_type, columns):
    with open(project.filename.parents[0] / path) as f:
        raw = f.read()

    root_schema = graham.schema(root_type)
    root = root_schema.loads(raw).data

    return epyqlib.attrsmodel.Model(root=root, columns=columns)
