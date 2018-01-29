import click
import graham
import pycparser.c_ast
import pycparser.c_generator

import epyqlib.attrsmodel
import epyqlib.pm.parametermodel

import epcpm.parameterstoc


@click.command()
@click.option('--parameters', type=click.File(), required=True)
@click.option('--declaration/--instantiation', default=True)
def cli(parameters, declaration):
    root_schema = graham.schema(epyqlib.pm.parametermodel.Root)
    root = root_schema.loads(parameters.read()).data

    model = epyqlib.attrsmodel.Model(
        root=root,
        columns=epyqlib.pm.parametermodel.columns,
    )

    builder = epcpm.parameterstoc.builders.wrap(model.root)

    generator = pycparser.c_generator.CGenerator()

    if declaration:
        items = builder.definition()
    else:
        items = builder.instantiation()

    ast = pycparser.c_ast.FileAST(items)
    s = generator.visit(ast)

    click.echo(s, nl=False)
