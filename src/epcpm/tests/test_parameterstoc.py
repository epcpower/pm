import functools
import os
import textwrap

import click.testing
import pycparser.c_ast
import pycparser.c_generator

import epcpm.parameterstoc


def disabled_test_exploration():
    path = os.path.join(os.path.dirname(__file__), 'example_parameters.json')

    runner = click.testing.CliRunner()
    runner.isolated_filesystem()
    result = runner.invoke(
        epcpm.parameterstoc.cli,
        [
            '--parameters', path,
        ],
    )

    print(result.output)

    assert result.exit_code == 0


def test_exploration():
    path = os.path.join(os.path.dirname(__file__), 'example_parameters.json')

    with open(path) as f:
        epcpm.parameterstoc._cli(parameters=f)


def test_pycparser_exploration_parse():
    sample = '''
    typedef int int16_t;
    typedef int uint16_t;

    enum enumName
    {
        one=1,
        two=2
    };
    typedef enum enumName enumTypedefName;

    struct structName
    {
        int16_t a;
        uint16_t b;
    };
    typedef struct structName structTypedefName;
    '''

    parser = pycparser.CParser()
    ast = parser.parse(sample)

    generator = pycparser.c_generator.CGenerator()

    generator.visit(ast)


def test_pycparser_exploration_wrapped():
    top_level = []

    top_level.extend(epcpm.parameterstoc.enum(
        name='enumName',
        enumerators=(
            ('a', 1),
            ('b', 2),
        ),
    ))

    top_level.extend(epcpm.parameterstoc.struct(
        name='structName',
        members=(
            ('int16_t', 'a', None),
            ('uint16_t', 'b', None),
        )
    ))

    ast = pycparser.c_ast.FileAST(top_level)

    generator = pycparser.c_generator.CGenerator()

    s = generator.visit(ast)
    assert s == textwrap.dedent('''\
    enum enumName_e {a = 1, b = 2};
    typedef enum enumName_e enumName_t;
    struct structName_s
    {
      int16_t a;
      uint16_t b;
    };
    typedef enum structName_s structName_t;
    ''')
