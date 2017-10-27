import pathlib

import click

import epcpm.project
import epcpm.symbolstosym


def relative_path(target, reference):
    reference = pathlib.Path(reference)
    if reference.is_file():
        reference = reference.parents[0]

    return pathlib.Path(target).resolve().relative_to(reference.resolve())


@click.command()
@click.option('--project', 'project_file', type=click.File(), required=True)
@click.option('--sym', 'sym_file', type=click.File('w'), required=True)
def cli(project_file, sym_file):
    project = epcpm.project.load(project_file)

    builder = epcpm.symbolstosym.builders.wrap(
        wrapped=project.models.symbols.root,
        parameter_uuid_finder=project.models.symbols.node_from_uuid,
    )

    sym_file.write(builder.gen())
