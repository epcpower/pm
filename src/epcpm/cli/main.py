import os
import pathlib
import subprocess

import click

import epcpm.__main__
import epcpm.cli.utils
import epcpm.importexport
import epcpm.importexportdialog


@click.group()
def main():
    """Parameter manager"""


main.add_command(epcpm.__main__._entry_point, name='gui')


@main.command()
@epcpm.cli.utils.project_option(required=True)
@epcpm.cli.utils.project_path_option(required=True)
def export(project, project_path):
    """Export PM data to embedded project directory"""
    project = epcpm.project.loadp(project)
    paths = epcpm.importexportdialog.paths_from_directory(project_path)

    epcpm.importexport.full_export(
        project=project,
        paths=paths,
        first_time=True,
    )

    click.echo()
    click.echo('done')


@main.command()
@epcpm.cli.utils.project_path_option(required=True)
def transition(project_path):
    """Don't use this unless you know"""
    project_path = pathlib.Path(project_path)

    click.echo('Working in: {}'.format(project_path))
    value = click.prompt(
        'This will wipe out changes in the above project path, continue? ',
        prompt_suffix='',
    )

    if value != 'yep':
        click.echo('Sorry, that response is not acceptable to continue.')
        return

    library_path = project_path/'embedded-library'

    original_spreadsheet = library_path/'MODBUS_SunSpec-EPC.xls'
    new_spreadsheet = original_spreadsheet.with_suffix('.xlsx')

    subprocess.run(['git', 'reset', '.'], check=True, cwd=library_path)
    subprocess.run(['git', 'checkout', '--', '.'], check=True, cwd=library_path)
    subprocess.run(['git', 'clean', '-fdx'], check=True, cwd=library_path)
    subprocess.run(
        [
            'libreoffice',
            '--convert-to', 'xlsx',
            '--outdir', os.fspath(library_path),
            os.fspath(original_spreadsheet)],
        check=True,
        cwd=library_path,
    )
    subprocess.run(
        ['git', 'rm', os.fspath(original_spreadsheet)],
        check=True,
        cwd=library_path,
    )
    subprocess.run(
        ['git', 'add', os.fspath(new_spreadsheet)],
        check=True,
        cwd=library_path,
    )

    subprocess.run(['git', 'reset', '.'], check=True, cwd=project_path)
    subprocess.run(['git', 'checkout', '--', '.'], check=True, cwd=project_path)
    subprocess.run(
        ['git', 'clean', '-fdx', '--exclude', 'venv'],
        check=True,
        cwd=project_path,
    )
    subprocess.run(
        ['python', os.fspath(project_path / 'create_venv.py'), 'ensure'],
        check=True,
        cwd=project_path,
    )
    subprocess.run(
        [os.fspath(project_path / 'gridtied'), 'build', '--target', 'Release'],
        check=False,
        cwd=project_path,
    )

    paths = epcpm.importexportdialog.paths_from_directory(project_path)

    project = epcpm.importexport.full_import(
        paths=paths,
    )

    pm_directory = project_path/'interface'/'pm'
    pm_directory.mkdir(exist_ok=True)
    project.filename = pm_directory/'project.pmp'
    project.save()

    subprocess.run(
        ['git', 'add', os.fspath(pm_directory)],
        check=True,
        cwd=project_path,
    )

    epcpm.importexport.full_export(
        project=project,
        paths=paths,
        first_time=True,
    )

    click.echo()
    click.echo('done')
