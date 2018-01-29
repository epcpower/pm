import pathlib

import click.testing

import epyqlib.tests.common

import epcpm.cli.importsym
import epcpm.cli.exportsym


round_trip = pathlib.Path(__file__).parents[3] / 'roundtrip'


def test_import():
    runner = click.testing.CliRunner()

    result = runner.invoke(
        epcpm.cli.importsym.cli,
        [
            '--sym', epyqlib.tests.common.symbol_files['factory'],
            '--hierarchy', epyqlib.tests.common.hierarchy_files['factory'],
            '--project', round_trip / 'project.pmp',
            '--can', round_trip / 'can.json',
            '--parameters', round_trip / 'parameters.json',
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0


def test_export():
    runner = click.testing.CliRunner()

    result = runner.invoke(
        epcpm.cli.exportsym.cli,
        [
            '--project', round_trip / 'project.pmp',
            '--sym', round_trip / 'EPC_DG_ID247_FACTORY.sym',
            '--hierarchy', round_trip / 'EPC_DG_ID247_FACTORY.parameters.json',
        ],
        catch_exceptions=False,
    )

    assert result.exit_code == 0
