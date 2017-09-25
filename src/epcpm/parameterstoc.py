import click

import epcpm.parametermodel


@click.command()
@click.option('--parameters', type=click.File())
def cli(*args, **kwargs):
    _cli(*args, **kwargs)


def _cli(parameters):
    model = epcpm.attrsmodel.Model.from_json_string(
        parameters.read(),
        columns=epcpm.parametermodel.columns,
        types=epcpm.parametermodel.types,
    )
    print()
