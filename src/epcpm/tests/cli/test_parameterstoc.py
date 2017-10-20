import pathlib
import textwrap

import click
import click.testing

import epcpm.cli.parameterstoc


parameters_path = (
    pathlib.Path(__file__).parents[0] / 'test_parameterstoc_parameters.json'
)


def test_declaration():
    runner = click.testing.CliRunner()
    result = runner.invoke(
        epcpm.cli.parameterstoc.cli,
        [
            '--parameters', parameters_path,
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
    struct GreenType_s
    {
      RedType red;
    };
    typedef struct GreenType_s GreenType_t;
    ''')


def test_instantiation():
    runner = click.testing.CliRunner()
    result = runner.invoke(
        epcpm.cli.parameterstoc.cli,
        [
            '--parameters', parameters_path,
            '--instantiation',
        ],
        catch_exceptions=False,
    )
    assert result.exit_code == 0
    assert result.output == textwrap.dedent('''\
    GreenType_t green;
    BlueType blue;
    ''')
