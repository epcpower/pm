import os
import pathlib
import subprocess

import click

import epcpm.__main__
import epcpm.cli.exportdocx
import epcpm.cli.utils
import epcpm.importexport
import epcpm.importexportdialog


@click.group()
def main():
    """Parameter manager"""


main.add_command(epcpm.__main__._entry_point, name='gui')


@main.group()
def export():
    """Export PM data to other formats"""
    pass


export.add_command(epcpm.cli.exportdocx.cli, name='docx')


@export.command()
@epcpm.cli.utils.project_option(required=True)
@epcpm.cli.utils.target_path_option(required=True)
def build(project, target_path):
    """Export PM data to embedded project directory"""
    project = epcpm.project.loadp(project)
    paths = epcpm.importexportdialog.paths_from_directory(target_path)

    epcpm.importexport.full_export(
        project=project,
        paths=paths,
        first_time=True,
    )

    click.echo()
    click.echo('done')


@main.command()
@epcpm.cli.utils.target_path_option(required=True)
def transition(target_path):
    """Don't use this unless you know"""
    target_path = pathlib.Path(target_path)

    click.echo('Working in: {}'.format(target_path))
    value = click.prompt(
        'This will wipe out changes in the above project path, continue? ',
        prompt_suffix='',
    )

    if value != 'yep':
        click.echo('Sorry, that response is not acceptable to continue.')
        return

    library_path = target_path / 'embedded-library'

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

    subprocess.run(['git', 'reset', '.'], check=True, cwd=target_path)
    subprocess.run(['git', 'checkout', '--', '.'], check=True, cwd=target_path)
    subprocess.run(
        ['git', 'clean', '-fdx', '--exclude', 'venv'],
        check=True,
        cwd=target_path,
    )
    subprocess.run(
        ['python', os.fspath(target_path / 'create_venv.py'), 'ensure'],
        check=True,
        cwd=target_path,
    )
    subprocess.run(
        [os.fspath(target_path / 'gridtied'), 'build', '--target', 'Release'],
        check=False,
        cwd=target_path,
    )

    paths = epcpm.importexportdialog.paths_from_directory(target_path)

    project = epcpm.importexport.full_import(
        paths=paths,
    )

    pm_directory = target_path / 'interface' / 'pm'
    pm_directory.mkdir(exist_ok=True)
    project.filename = pm_directory/'project.pmp'
    project.save()

    subprocess.run(
        ['git', 'add', os.fspath(pm_directory)],
        check=True,
        cwd=target_path,
    )

    epcpm.importexport.full_export(
        project=project,
        paths=paths,
        first_time=True,
    )

    click.echo()
    click.echo('done')
