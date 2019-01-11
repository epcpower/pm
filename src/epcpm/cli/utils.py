import click


def project_option(required=False):
    return click.option(
        '--project',
        type=click.Path(exists=True, dir_okay=False),
        required=required,
        help='.pmp file to load',
    )


def target_path_option(required):
    return click.option(
        '--target-path',
        type=click.Path(exists=True, file_okay=False, resolve_path=True),
        required=required,
        help="Path to the embedded project to operate on",
    )
