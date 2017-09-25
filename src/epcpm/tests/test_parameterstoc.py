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


def int_literal(value):
    return pycparser.c_ast.Constant(type='int', value=str(value))


Decl = functools.partial(
    pycparser.c_ast.Decl,
    name=None,
    quals=[],
    storage=[],
    funcspec=[],
    init=None,
    bitsize=None,
)


def Typedef(target, name):
    return pycparser.c_ast.Typedef(
        name='',
        quals=[],
        storage=['typedef'],
        type=pycparser.c_ast.TypeDecl(
            declname=name,
            quals=[],
            type=target,
        ),
    )


def enum(name, enumerators=()):
    enum_name = '{name}_e'.format(name=name)
    typedef_name = '{name}_t'.format(name=name)

    enumerators = pycparser.c_ast.EnumeratorList(enumerators=tuple(
        pycparser.c_ast.Enumerator(name=name, value=int_literal(value))
        for name, value in enumerators
    ))

    enumeration = pycparser.c_ast.Enum(
        name=enum_name,
        values=enumerators
    )

    declaration = Decl(type=enumeration)

    typedef = Typedef(
        target=pycparser.c_ast.Enum(
            name=enum_name,
            values=[],
        ),
        name=typedef_name,
    )

    return declaration, typedef


def struct(name, members=()):
    struct_name = f'{name}_s'
    typedef_name = f'{name}_t'

    struct = pycparser.c_ast.Struct(
        name=name,
        decls=tuple(
            pycparser.c_ast.Decl(
                name=None,
                quals=[],
                storage=[],
                funcspec=[],
                type=pycparser.c_ast.TypeDecl(
                    declname=name,
                    quals=[],
                    type=pycparser.c_ast.IdentifierType(
                        names=(type,),
                    ),
                ),
                init=None,
                bitsize=bits,
            )
            for type, name, bits in members
        ),
    )

    decl = pycparser.c_ast.Decl(
        name=None,
        quals=[],
        storage=[],
        funcspec=[],
        type=struct,
        init=None,
        bitsize=None,
    )

    typedef = Typedef(
        target=pycparser.c_ast.Enum(
            name=struct_name,
            values=[],
        ),
        name=typedef_name,
    )

    return decl, typedef


def test_pycparser_exploration_wrapped():
    top_level = []

    top_level.extend(enum(
        name='enumName',
        enumerators=(
            ('a', 1),
            ('b', 2),
        ),
    ))

    top_level.extend(struct(
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
    struct structName
    {
      int16_t a;
      uint16_t b;
    };
    typedef enum structName_s structName_t;
    ''')
