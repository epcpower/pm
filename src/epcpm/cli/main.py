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
import epcpm.project
import epcpm.smdx


@click.group()
def main():
    """Parameter manager"""


main.add_command(epcpm.__main__._entry_point, name='gui')


@main.group(name='import')
def _import():
    """Import PM data from other formats"""
    pass


@_import.command()
@epcpm.cli.utils.project_option(required=True)
@epcpm.cli.utils.target_path_option(required=True)
def full(project, target_path):
    """Import PM data from embedded project directory"""
    project = pathlib.Path(project)

    paths = epcpm.importexportdialog.paths_from_directory(target_path)

    imported_project = epcpm.importexport.full_import(
        paths=paths,
    )

    project.parent.mkdir(exist_ok=True)
    imported_project.filename = project
    imported_project.save()


@main.group()
def export():
    """Export PM data to other formats"""
    pass


export.add_command(epcpm.cli.exportdocx.cli, name='docx')


@export.command()
@epcpm.cli.utils.project_option(required=True)
@epcpm.cli.utils.target_path_option(required=True)
@click.option('--if-stale/--assume-stale', 'only_if_stale')
def build(project, target_path, only_if_stale):
    """Export PM data to embedded project directory"""
    project = pathlib.Path(project)
    target_path = pathlib.Path(target_path)

    paths = epcpm.importexportdialog.paths_from_directory(target_path)

    if only_if_stale:
        if not epcpm.importexport.is_stale(project=project, paths=paths):
            click.echo(
                'Generated files appear to be up to date, skipping export',
            )

            return

        click.echo(
            'Generated files appear to be out of date, starting export'
        )

    loaded_project = epcpm.project.loadp(project)

    epcpm.importexport.full_export(
        project=loaded_project,
        target_directory=target_path,
        paths=paths,
        first_time=False,
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

    c_project = target_path/'.cproject'

    library_path = target_path / 'embedded-library'

    original_spreadsheet = library_path/'MODBUS_SunSpec-EPC.xls'
    new_spreadsheet = original_spreadsheet.with_suffix('.xlsx')

    tables_py = library_path/'python'/'embeddedlibrary'/'tables.py'
    sunspecparser_py = (
        library_path/'python'/'embeddedlibrary'/'sunspecparser.py'
    )

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
        ['git', 'rm', os.fspath(tables_py)],
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
        [target_path/'venv'/'bin'/'sunspecparser', os.fspath(new_spreadsheet)],
        check=True,
        cwd=library_path, # it expects to be in _some_ subdirectory and then ..
    )
    subprocess.run(
        ['sed', '-i', r's/\.xls/\.xlsx/g', os.fspath(c_project)],
        check=True,
        cwd=target_path,
    )
    subprocess.run(
        ['git', 'add', os.fspath(c_project)],
        check=True,
        cwd=target_path,
    )

    content = sunspecparser_py.read_text()
    with sunspecparser_py.open('w', newline='\n') as f:
        for line in content.splitlines():
            f.write(line + '\n')
            if r"""'#include "faultHandler.h"\n'""" in line:
                f.write(r"""            c_file.write('#include "sunspecInterface{:>05}.h"\n'.format(model))""" '\n')
                f.write(r"""            c_file.write('#include "math.h"\n')""" '\n')

    subprocess.run(
        ['git', 'add', os.fspath(sunspecparser_py)],
        check=True,
        cwd=library_path,
    )

    paths = epcpm.importexportdialog.paths_from_directory(target_path)
    print(paths)

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
