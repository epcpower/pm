import os
import pathlib
import subprocess
import sys
import textwrap

import click
import epyqlib.pm.valueset
import epyqlib.pm.valuesetmodel
import lxml.etree

import mpm.__main__
import mpm.cli.exportdocx
import mpm.cli.sunspectostaticmodbus
import mpm.cli.utils
import mpm.importexport
import mpm.importexportdialog
import mpm.project
import mpm.smdx


@click.group()
def main():
    """Parameter manager"""


main.add_command(mpm.__main__._entry_point, name="gui")


@main.group(name="import")
def _import():
    """Import PM data from other formats"""
    pass


@_import.command()
@mpm.cli.utils.project_option(required=True)
@mpm.cli.utils.target_path_option(required=True)
def full(project, target_path):
    """Import PM data from embedded project directory"""
    project = pathlib.Path(project)

    paths = mpm.importexportdialog.paths_from_directory(target_path)

    imported_project = mpm.importexport.full_import(
        paths=paths,
    )

    project.parent.mkdir(exist_ok=True)
    imported_project.filename = project
    imported_project.save()


@main.group()
def export():
    """Export PM data to other formats"""
    pass


export.add_command(mpm.cli.exportdocx.cli, name="docx")


@export.command()
@mpm.cli.utils.project_option(required=True)
@click.option(
    "--bcu-project",
    type=click.Path(exists=True, dir_okay=False),
    required=False,
    help=".pmp file to load",
)
@mpm.cli.utils.target_path_option(required=True)
@click.option("--if-stale/--assume-stale", "only_if_stale")
@click.option("--skip-sunspec/--generate-sunspec", "skip_sunspec")
@click.option(
    "--include-uuid-in-item/--exclude-uuid-from-item",
    "include_uuid_in_item",
    default=False,
)
def build(
    project,
    bcu_project,
    target_path,
    only_if_stale,
    skip_sunspec,
    include_uuid_in_item,
):
    """Export PM data to embedded project directory"""
    project = pathlib.Path(project)
    target_path = pathlib.Path(target_path)

    paths = mpm.importexportdialog.paths_from_directory(target_path)

    if only_if_stale:
        if not mpm.importexport.is_stale(
            project=project,
            paths=paths,
            skip_sunspec=skip_sunspec,
        ):
            click.echo(
                "Generated files appear to be up to date, skipping export",
            )

            return

        click.echo("Generated files appear to be out of date, starting export")

    loaded_project = mpm.project.loadp(project)

    loaded_project2 = mpm.project.loadp(project)  # Project cannot be deep copied
    loaded_project2.models.can.droppable_from.add(loaded_project.models.parameters)

    loaded_bcu_project = mpm.project.loadp(bcu_project) if bcu_project else None

    mpm.importexport.can_hierarchy_export(
        project=loaded_project2,
        bcu_project=loaded_bcu_project,
        paths=paths,
    )

    mpm.importexport.interface_code_export(
        project=loaded_project,
        paths=paths,
        skip_output=skip_sunspec,
        include_uuid_in_item=include_uuid_in_item,
    )

    click.echo()
    click.echo("done")


@export.command()
@mpm.cli.utils.project_option(required=True)
@mpm.cli.utils.target_path_option(required=True)
@mpm.cli.utils.pmvs_overlay_recipes_path_option(required=True)
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
    Returns:

    """
    project = pathlib.Path(project)
    target_path = pathlib.Path(target_path)

    pmvs_base = pathlib.Path(pmvs_overlay_recipes_path) / "base.json"
    pmvs_configuration = epyqlib.pm.valueset.OverlayConfiguration.load(pmvs_base)
    pmvs_output_path = pmvs_configuration.reference_output_path()

    paths = mpm.importexportdialog.paths_from_directory(target_path)

    loaded_project = mpm.project.loadp(project)

    product_specific_defaults_list = []
    if product_specific_defaults:
        product_specific_defaults_list = product_specific_defaults.split(",")
        product_specific_defaults_list = [
            x.strip() for x in product_specific_defaults_list
        ]
    mpm.importexport.generate_docs(
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

    paired_paths = mpm.smdx.PairedPaths.from_directories(
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

        result = mpm.smdx.validate_against_reference(
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

        result = mpm.smdx.validate_against_schema(
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


utility.add_command(mpm.cli.sunspectostaticmodbus.cli, name="sunspec-to-staticmodbus")


@main.group()
def pmvs():
    pass


@pmvs.command()
@mpm.cli.utils.project_option(required=True)
@click.option("--input", type=click.File())
@click.option("--output", type=click.Path(dir_okay=False))
def filter(project, input, output):
    """Export PM data to embedded project directory"""
    project = pathlib.Path(project)
    project = mpm.project.loadp(project)

    value_set = epyqlib.pm.valuesetmodel.load(input)
    items = mpm.parameterstosil.collect_items(project.models.parameters.root)
    item_uuids = {item.uuid for item in items}

    values = list(value_set.model.root.children)

    for index, value in reversed(list(enumerate(values))):
        if value.parameter_uuid not in item_uuids:
            value_set.model.root.remove_child(row=index)

    value_set.save(path=output)
