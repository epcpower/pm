import click

import epyqlib.pm.parametermodel
import epcpm.parameterstodocx
import epcpm.project


@click.command()
@click.option('--project', 'project_file', type=click.File(), required=True)
@click.option('--docx', 'docx_file', type=click.File('wb'), required=True)
@click.option('--template', type=click.File('rb'))
@click.option('--access-level', default='user')
def cli(project_file, docx_file, template, access_level):
    project = epcpm.project.load(project_file)

    access_levels, = project.models.parameters.root.nodes_by_filter(
        filter=(
            lambda node: isinstance(
                node,
                epyqlib.pm.parametermodel.AccessLevels
            )
        ),
    )

    access_level = access_levels.by_name(access_level)

    docx_builder = epcpm.parameterstodocx.builders.wrap(
        wrapped=project.models.parameters.root,
        can_root=project.models.can.root,
        template=template,
        access_level=access_level,
    )

    doc = docx_builder.gen()

    doc.save(docx_file)
