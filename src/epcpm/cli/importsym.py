import pathlib

import click
import graham

import epcpm.project
import epcpm.symtoproject


def relative_path(target, reference):
    reference = pathlib.Path(reference)
    if reference.is_file():
        reference = reference.parents[0]

    return pathlib.Path(target).resolve().relative_to(reference.resolve())


@click.command()
@click.option('--sym', type=click.File('rb'), required=True)
@click.option('--project', type=click.File('w'), required=True)
@click.option('--parameters', type=click.File('w'), required=True)
@click.option('--symbols', type=click.File('w'), required=True)
def cli(sym, project, parameters, symbols):
    parameters_root, symbols_root = epcpm.symtoproject.load_can_file(
        f=sym,
        file_type=str(pathlib.Path(sym.name).suffix[1:]),
    )

    project_path = pathlib.Path(project.name).parents[0]
    project_path.mkdir(parents=True, exist_ok=True)

    project_root = epcpm.project.Project()
    project_root.paths.parameters = relative_path(parameters.name, project_path)
    project_root.paths.symbols= relative_path(symbols.name, project_path)

    project.write(graham.dumps(project_root, indent=4).data)
    parameters.write(graham.dumps(parameters_root, indent=4).data)
    symbols.write(graham.dumps(symbols_root, indent=4).data)
