import functools
import os
import textwrap

import click.testing
import pycparser.c_ast
import pycparser.c_generator
import pytest

import epcpm.parametermodel
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


@pytest.mark.skip
def test_exploration():
    path = os.path.join(os.path.dirname(__file__), 'example_parameters.json')

    with open(path) as f:
        epcpm.parameterstoc._cli(parameters=f)


def test_pycparser_exploration_parse():
    sample = '''
    typedef int int16_t;
    typedef int uint16_t;

    enum EnumName
    {
        one=1,
        two=2
    };
    typedef enum EnumName EnumTypedefName;

    struct StructName
    {
        int16_t a;
        uint16_t b;
    };
    typedef struct StructName StructTypedefName;
    
    int16_t array[5];
    '''

    parser = pycparser.CParser()
    ast = parser.parse(sample)

    generator = pycparser.c_generator.CGenerator()

    generator.visit(ast)

    return ast


def test_pycparser_exploration_wrapped():
    top_level = []

    top_level.extend(epcpm.parameterstoc.enum(
        name='EnumName',
        enumerators=(
            ('a', 1),
            ('b', 2),
        ),
    ))

    top_level.extend(epcpm.parameterstoc.struct(
        name='StructName',
        member_decls=(
            epcpm.parameterstoc.Decl(
                type=epcpm.parameterstoc.Type(
                    name=name,
                    type=type,
                )
            )
            for type, name in (
                ('int16_t', 'a'),
                ('uint16_t', 'b'),
            )
        )
    ))

    ast = pycparser.c_ast.FileAST(top_level)

    generator = pycparser.c_generator.CGenerator()

    s = generator.visit(ast)
    assert s == textwrap.dedent('''\
    enum EnumName_e {a = 1, b = 2};
    typedef enum EnumName_e EnumName_t;
    struct StructName_s
    {
      int16_t a;
      uint16_t b;
    };
    typedef enum StructName_s StructName_t;
    ''')


def test_single_layer_group_to_c():
    group = epcpm.parametermodel.Group(
        name='Group Name',
    )

    children = [
        epcpm.parametermodel.Parameter(
            name='Parameter A',
        ),
        epcpm.parametermodel.Parameter(
            name='Parameter B',
        ),
        epcpm.parametermodel.Parameter(
            name='Parameter C',
        ),
    ]

    for child in children:
        group.append_child(child)

    top_level = epcpm.parameterstoc.build_ast(group)
    ast = pycparser.c_ast.FileAST(top_level)
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
        struct GroupName_s
        {
          int16_t parameterA;
          int16_t parameterB;
          int16_t parameterC;
        };
        typedef enum GroupName_s GroupName_t;
        ''')


def test_nested_group_to_c():
    inner_inner_group = epcpm.parametermodel.Group(
        name='Inner Inner Group Name',
    )

    children = [
        epcpm.parametermodel.Parameter(
            name='Parameter F',
        ),
        epcpm.parametermodel.Parameter(
            name='Parameter G',
        ),
    ]

    for child in children:
        inner_inner_group.append_child(child)

    inner_group = epcpm.parametermodel.Group(
        name='Inner Group Name',
    )

    children = [
        epcpm.parametermodel.Parameter(
            name='Parameter D',
        ),
        inner_inner_group,
        epcpm.parametermodel.Parameter(
            name='Parameter E',
        ),
    ]

    for child in children:
        inner_group.append_child(child)

    outer_group = epcpm.parametermodel.Group(
        name='Outer Group Name',
    )

    children = [
        epcpm.parametermodel.Parameter(
            name='Parameter A',
        ),
        inner_group,
        epcpm.parametermodel.Parameter(
            name='Parameter B',
        ),
        epcpm.parametermodel.Parameter(
            name='Parameter C',
        ),
    ]

    for child in children:
        outer_group.append_child(child)

    ast = pycparser.c_ast.FileAST(epcpm.parameterstoc.build_ast(outer_group))
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
        struct InnerInnerGroupName_s
        {
          int16_t parameterF;
          int16_t parameterG;
        };
        typedef enum InnerInnerGroupName_s InnerInnerGroupName_t;
        struct InnerGroupName_s
        {
          int16_t parameterD;
          InnerInnerGroupName_t innerInnerGroupName;
          int16_t parameterE;
        };
        typedef enum InnerGroupName_s InnerGroupName_t;
        struct OuterGroupName_s
        {
          int16_t parameterA;
          InnerGroupName_t innerGroupName;
          int16_t parameterB;
          int16_t parameterC;
        };
        typedef enum OuterGroupName_s OuterGroupName_t;
        ''')


def test_array_group_to_c():
    array = epcpm.parametermodel.ArrayGroup(
        name='Array Group Name',
    )

    array.length = 5

    top_level = epcpm.parameterstoc.build_ast(array)
    ast = pycparser.c_ast.FileAST(top_level)
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
        int16_t arrayGroupName[5];
        ''')

    group = epcpm.parametermodel.Group(
        name='Group Name',
    )

    children = [
        epcpm.parametermodel.Parameter(
            name='Parameter A',
        ),
        array,
        epcpm.parametermodel.Parameter(
            name='Parameter B',
        ),
        epcpm.parametermodel.Parameter(
            name='Parameter C',
        ),
    ]

    for child in children:
        group.append_child(child)

    top_level = epcpm.parameterstoc.build_ast(group)
    ast = pycparser.c_ast.FileAST(top_level)
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
        struct GroupName_s
        {
          int16_t parameterA;
          int16_t arrayGroupName[5];
          int16_t parameterB;
          int16_t parameterC;
        };
        typedef enum GroupName_s GroupName_t;
        ''')
