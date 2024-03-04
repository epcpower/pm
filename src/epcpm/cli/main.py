import os
import pathlib
import subprocess
import sys
import textwrap

import click
import epyqlib.pm.valueset
import epyqlib.pm.valuesetmodel
import lxml.etree

import epcpm.__main__
import epcpm.cli.exportdocx
import epcpm.cli.sunspectostaticmodbus
import epcpm.cli.utils
import epcpm.importexport
import epcpm.importexportdialog
import epcpm.project
import epcpm.smdx


@click.group()
def main():
    """Parameter manager"""


main.add_command(epcpm.__main__._entry_point, name="gui")


@main.group(name="import")
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


export.add_command(epcpm.cli.exportdocx.cli, name="docx")


@export.command()
@epcpm.cli.utils.project_option(required=True)
@epcpm.cli.utils.target_path_option(required=True)
@click.option("--if-stale/--assume-stale", "only_if_stale")
@click.option("--skip-sunspec/--generate-sunspec", "skip_sunspec")
@click.option(
    "--include-uuid-in-item/--exclude-uuid-from-item",
    "include_uuid_in_item",
    default=False,
)
def build(
    project,
    target_path,
    only_if_stale,
    skip_sunspec,
    include_uuid_in_item,
):
    """Export PM data to embedded project directory"""
    project = pathlib.Path(project)
    target_path = pathlib.Path(target_path)

    paths = epcpm.importexportdialog.paths_from_directory(target_path)

    if only_if_stale:
        if not epcpm.importexport.is_stale(
            project=project,
            paths=paths,
            skip_sunspec=skip_sunspec,
        ):
            click.echo(
                "Generated files appear to be up to date, skipping export",
            )

            return

        click.echo("Generated files appear to be out of date, starting export")

    loaded_project = epcpm.project.loadp(project)

    epcpm.importexport.full_export(
        project=loaded_project,
        target_directory=target_path,
        paths=paths,
        first_time=False,
        skip_output=skip_sunspec,
        include_uuid_in_item=include_uuid_in_item,
    )

    click.echo()
    click.echo("done")


@export.command()
@epcpm.cli.utils.project_option(required=True)
@epcpm.cli.utils.target_path_option(required=True)
@epcpm.cli.utils.pmvs_overlay_recipes_path_option(required=True)
@click.option("--generate-formatted-output", "generate_formatted_output", is_flag=True)
@click.option(
    "--product-specific-defaults",
    help="Comma separated list of defaults to be included in the output",
)
def docs(
    project: str,
    target_path: str,
    pmvs_overlay_recipes_path: str,
    generate_formatted_output: bool,
    product_specific_defaults: str,
) -> None:
    """
    Export PM documentation to embedded project directory

    Args:
        project: path to PM project file
        target_path: path to root target directory
        pmvs_overlay_recipes_path: path to PMVS overlay recipes directory (contains base.json)
        generate_formatted_output: generate formatted output of the documentation (takes a long time)
        product_specific_defaults: optional argument to specify which defaults are included in the output
    Returns:

    """
    project = pathlib.Path(project)
    target_path = pathlib.Path(target_path)

    pmvs_base = pathlib.Path(pmvs_overlay_recipes_path) / "base.json"
    pmvs_configuration = epyqlib.pm.valueset.OverlayConfiguration.load(pmvs_base)
    pmvs_output_path = pmvs_configuration.reference_output_path()

    paths = epcpm.importexportdialog.paths_from_directory(target_path)

    loaded_project = epcpm.project.loadp(project)
    product_specific_defaults_list = []
    if product_specific_defaults:
        product_specific_defaults_list = product_specific_defaults.split(",")
        product_specific_defaults_list = [
            x.strip() for x in product_specific_defaults_list
        ]
    epcpm.importexport.generate_docs(
        project=loaded_project,
        pmvs_path=pmvs_output_path,
        paths=paths,
        generate_formatted_output=generate_formatted_output,
        product_specific_defaults=product_specific_defaults_list,
    )

    click.echo()
    click.echo("Export documentation complete.")


@main.group()
def validate():
    pass


@validate.command()
@click.option(
    "--reference",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    "--subject",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    "--schema",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
)
@click.option("--smdx-glob", default="smdx_*.xml")
def batch(reference, schema, subject, smdx_glob):
    failed = False

    reference_directory_path = pathlib.Path(reference)
    subject_directory_path = pathlib.Path(subject)

    if schema is None:
        schema = reference_directory_path / "smdx.xsd"
    else:
        schema = pathlib.Path(schema)

    paired_paths = epcpm.smdx.PairedPaths.from_directories(
        left_path=reference_directory_path,
        right_path=subject_directory_path,
        file_glob=smdx_glob,
    )

    schema = lxml.etree.fromstring(schema.read_bytes())
    schema = lxml.etree.XMLSchema(schema, attribute_defaults=True)

    spacing = "\n\n"
    present_spacing = ""

    diff_indent = "        "

    for reference_path, subject_path in sorted(paired_paths.pairs.items()):
        click.echo(present_spacing, nl=False)
        present_spacing = spacing

        click.echo(
            textwrap.dedent(
                f"""\
        Cross validating: {subject_path.name}
               reference: {reference_path}
                 subject: {subject_path}
        """
            )
        )

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

        click.echo(
            textwrap.dedent(
                f"""\
        Validating: {subject.name}
           subject: {subject}
        """
            )
        )

        result = epcpm.smdx.validate_against_schema(
            subject=subject,
            schema=schema,
        )

        if result.failed:
            failed = True

        for line in result.notes.splitlines():
            click.echo(diff_indent + line)

    sys.exit(failed)


@main.group()
def utility():
    """Utilities for administrative purposes"""
    pass


utility.add_command(epcpm.cli.sunspectostaticmodbus.cli, name="sunspec-to-staticmodbus")


@utility.command()
@epcpm.cli.utils.target_path_option(required=True)
def transition(target_path):
    """Don't use this unless you know"""
    target_path = pathlib.Path(target_path)

    click.echo("Working in: {}".format(target_path))
    value = click.prompt(
        "This will wipe out changes in the above project path, continue? ",
        prompt_suffix="",
    )

    if value != "yep":
        click.echo("Sorry, that response is not acceptable to continue.")
        return

    c_project = target_path / ".cproject"

    library_path = target_path / "embedded-library"

    original_spreadsheet = library_path / "MODBUS_SunSpec-EPC.xls"
    new_spreadsheet = original_spreadsheet.with_suffix(".xlsx")

    tables_py = library_path / "python" / "embeddedlibrary" / "tables.py"
    sunspecparser_py = library_path / "python" / "embeddedlibrary" / "sunspecparser.py"

    subprocess.run(["git", "reset", "."], check=True, cwd=library_path)
    subprocess.run(["git", "checkout", "--", "."], check=True, cwd=library_path)
    subprocess.run(["git", "clean", "-fdx"], check=True, cwd=library_path)
    subprocess.run(
        [
            "libreoffice",
            "--convert-to",
            "xlsx",
            "--outdir",
            os.fspath(library_path),
            os.fspath(original_spreadsheet),
        ],
        check=True,
        cwd=library_path,
    )
    subprocess.run(
        ["git", "rm", os.fspath(tables_py)],
        check=True,
        cwd=library_path,
    )
    subprocess.run(
        ["git", "rm", os.fspath(original_spreadsheet)],
        check=True,
        cwd=library_path,
    )
    subprocess.run(
        ["git", "add", os.fspath(new_spreadsheet)],
        check=True,
        cwd=library_path,
    )

    subprocess.run(["git", "reset", "."], check=True, cwd=target_path)
    subprocess.run(["git", "checkout", "--", "."], check=True, cwd=target_path)
    subprocess.run(
        ["git", "clean", "-fdx", "--exclude", ".venv"],
        check=True,
        cwd=target_path,
    )
    subprocess.run(
        ["python", os.fspath(target_path / "create_venv.py"), "ensure"],
        check=True,
        cwd=target_path,
    )
    subprocess.run(
        [target_path / ".venv" / "bin" / "sunspecparser", os.fspath(new_spreadsheet)],
        check=True,
        cwd=library_path,  # it expects to be in _some_ subdirectory and then ..
    )
    subprocess.run(
        ["sed", "-i", r"s/\.xls/\.xlsx/g", os.fspath(c_project)],
        check=True,
        cwd=target_path,
    )
    subprocess.run(
        ["git", "add", os.fspath(c_project)],
        check=True,
        cwd=target_path,
    )

    content = sunspecparser_py.read_text()
    with sunspecparser_py.open("w", newline="\n") as f:
        for line in content.splitlines():
            f.write(line + "\n")
            if r"""'#include "faultHandler.h"\n'""" in line:
                f.write(
                    r"""            c_file.write('#include "sunspecInterface{:>05}.h"\n'.format(model))"""
                    "\n"
                )
                f.write(r"""            c_file.write('#include "math.h"\n')""" "\n")

    subprocess.run(
        ["git", "add", os.fspath(sunspecparser_py)],
        check=True,
        cwd=library_path,
    )

    paths = epcpm.importexportdialog.paths_from_directory(target_path)
    print(paths)

    project = epcpm.importexport.full_import(
        paths=paths,
    )

    pm_directory = target_path / "interface" / "pm"
    pm_directory.mkdir(exist_ok=True)
    project.filename = pm_directory / "project.pmp"
    project.save()

    subprocess.run(
        ["git", "add", os.fspath(pm_directory)],
        check=True,
        cwd=target_path,
    )

    epcpm.importexport.full_export(
        project=project,
        paths=paths,
        first_time=True,
    )

    click.echo()
    click.echo("done")


@main.group()
def pmvs():
    pass


@pmvs.command()
@epcpm.cli.utils.project_option(required=True)
@click.option("--input", type=click.File())
@click.option("--output", type=click.Path(dir_okay=False))
def filter(project, input, output):
    """Export PM data to embedded project directory"""
    project = pathlib.Path(project)
    project = epcpm.project.loadp(project)

    value_set = epyqlib.pm.valuesetmodel.load(input)
    items = epcpm.parameterstosil.collect_items(project.models.parameters.root)
    item_uuids = {item.uuid for item in items}

    values = list(value_set.model.root.children)

    for index, value in reversed(list(enumerate(values))):
        if value.parameter_uuid not in item_uuids:
            value_set.model.root.remove_child(row=index)

    value_set.save(path=output)
