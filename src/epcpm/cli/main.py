import os
import pathlib
import subprocess
import sys
import textwrap

import click
import lxml.etree

import epcpm.__main__
import epcpm.cli.exportdocx
import epcpm.cli.utils
import epcpm.importexport
import epcpm.importexportdialog
import epcpm.smdx


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


@main.group()
def validate():
    pass


@validate.command()
@click.option(
    '--reference',
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    '--subject',
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    '--schema',
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
)
@click.option('--smdx-glob', default='smdx_*.xml')
def batch(reference, schema, subject, smdx_glob):
    failed = False

    reference_directory_path = pathlib.Path(reference)
    subject_directory_path = pathlib.Path(subject)

    if schema is None:
        schema = reference_directory_path/'smdx.xsd'
    else:
        schema = pathlib.Path(schema)

    paired_paths = epcpm.smdx.PairedPaths.from_directories(
        left_path=reference_directory_path,
        right_path=subject_directory_path,
        file_glob=smdx_glob,
    )

    schema = lxml.etree.fromstring(schema.read_bytes())
    schema = lxml.etree.XMLSchema(schema, attribute_defaults=True)

    spacing = '\n\n'
    present_spacing = ''

    diff_indent = '        '

    for reference_path, subject_path in sorted(paired_paths.pairs.items()):
        click.echo(present_spacing, nl=False)
        present_spacing = spacing

        click.echo(textwrap.dedent(f'''\
        Cross validating: {subject_path.name}
               reference: {reference_path}
                 subject: {subject_path}
        '''))

        reference = lxml.etree.fromstring(reference_path.read_bytes())
        subject = lxml.etree.fromstring(subject_path.read_bytes())

        result = epcpm.smdx.validate_against_reference(
            subject=subject,
            schema=schema,
            reference=reference,
        )

        if result.failed:
            failed = True

        for line in result.notes.splitlines():
            click.echo(diff_indent + line)

    for subject in sorted(paired_paths.only_right):
        click.echo(present_spacing, nl=False)
        present_spacing = spacing

        click.echo(textwrap.dedent(f'''\
        Validating: {subject.name}
           subject: {subject}
        '''))

        result = epcpm.smdx.validate_against_schema(
            subject=subject,
            schema=schema,
        )

        if result.failed:
            failed = True

        for line in result.notes.splitlines():
            click.echo(diff_indent + line)

    sys.exit(failed)


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
