import click
import pycparser.c_ast
import pycparser.c_generator

import epyqlib.attrsmodel

import epcpm.parametermodel


@click.command()
@click.option('--parameters', type=click.File(), required=True)
@click.option('--include-definitions/--exclude-definitions', default=False)
def cli(parameters, include_definitions):
    model = epyqlib.attrsmodel.Model.from_json_string(
        parameters.read(),
        columns=epcpm.parametermodel.columns,
        types=epcpm.parametermodel.types,
    )

    builder = epcpm.parameterstoc.builders.wrap(model.root)

    generator = pycparser.c_generator.CGenerator()

    ast = pycparser.c_ast.FileAST(builder.definition())
    s = generator.visit(ast)

    if include_definitions:
        ast = pycparser.c_ast.FileAST(builder.instantiation())
        s = generator.visit(ast)

    click.echo(s, nl=False)
