import click
import pycparser.c_ast
import pycparser.c_generator

import epyqlib.attrsmodel

import epcpm.parametermodel


@click.command()
@click.option('--parameters', type=click.File(), required=True)
@click.option('--declaration/--instantiation', default=True)
def cli(parameters, declaration):
    model = epyqlib.attrsmodel.Model.from_json_string(
        parameters.read(),
        columns=epcpm.parametermodel.columns,
        types=epcpm.parametermodel.types,
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
