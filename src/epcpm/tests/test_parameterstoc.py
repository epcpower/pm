import functools
import os
import textwrap

import click.testing
import pycparser.c_ast
import pycparser.c_generator
import pytest

import epyqlib.attrsmodel
import epyqlib.pm.parametermodel

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
    enum EnumName_e
    {
      a = 1,
      b = 2
    };
    typedef enum EnumName_e EnumName_et;
    struct StructName_s
    {
      int16_t a;
      uint16_t b;
    };
    typedef struct StructName_s StructName_t;
    ''')


def test_single_layer_group_to_c():
    group = epyqlib.pm.parametermodel.Group(
        name='Group Name',
    )

    children = [
        epyqlib.pm.parametermodel.Parameter(
            name='Parameter A',
            type_name='int16_t',
        ),
        epyqlib.pm.parametermodel.Parameter(
            name='Parameter B',
            type_name='int16_t',
        ),
        epyqlib.pm.parametermodel.Parameter(
            name='Parameter C',
            type_name='int16_t',
        ),
    ]

    for child in children:
        group.append_child(child)

    builder = epcpm.parameterstoc.builders.wrap(group)

    ast = pycparser.c_ast.FileAST(builder.definition())
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
        struct GroupName_s
        {
          int16_t parameterA;
          int16_t parameterB;
          int16_t parameterC;
        };
        typedef struct GroupName_s GroupName_t;
        ''')


def test_nested_group_to_c():
    inner_inner_group = epyqlib.pm.parametermodel.Group(
        name='Inner Inner Group Name',
    )

    children = [
        epyqlib.pm.parametermodel.Parameter(
            name='Parameter F',
            type_name='int16_t',
        ),
        epyqlib.pm.parametermodel.Parameter(
            name='Parameter G',
            type_name='int16_t',
        ),
    ]

    for child in children:
        inner_inner_group.append_child(child)

    inner_group = epyqlib.pm.parametermodel.Group(
        name='Inner Group Name',
    )

    children = [
        epyqlib.pm.parametermodel.Parameter(
            name='Parameter D',
            type_name='int16_t',
        ),
        inner_inner_group,
        epyqlib.pm.parametermodel.Parameter(
            name='Parameter E',
            type_name='int16_t',
        ),
    ]

    for child in children:
        inner_group.append_child(child)

    outer_group = epyqlib.pm.parametermodel.Group(
        name='Outer Group Name',
    )

    children = [
        epyqlib.pm.parametermodel.Parameter(
            name='Parameter A',
            type_name='int16_t',
        ),
        inner_group,
        epyqlib.pm.parametermodel.Parameter(
            name='Parameter B',
            type_name='int16_t',
        ),
        epyqlib.pm.parametermodel.Parameter(
            name='Parameter C',
            type_name='int16_t',
        ),
    ]

    for child in children:
        outer_group.append_child(child)

    builder = epcpm.parameterstoc.builders.wrap(outer_group)

    ast = pycparser.c_ast.FileAST(builder.definition())
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
        struct InnerInnerGroupName_s
        {
          int16_t parameterF;
          int16_t parameterG;
        };
        typedef struct InnerInnerGroupName_s InnerInnerGroupName_t;
        struct InnerGroupName_s
        {
          int16_t parameterD;
          InnerInnerGroupName_t innerInnerGroupName;
          int16_t parameterE;
        };
        typedef struct InnerGroupName_s InnerGroupName_t;
        struct OuterGroupName_s
        {
          int16_t parameterA;
          InnerGroupName_t innerGroupName;
          int16_t parameterB;
          int16_t parameterC;
        };
        typedef struct OuterGroupName_s OuterGroupName_t;
        ''')


def test_datalogger_a():
    data_logger = epyqlib.pm.parametermodel.Group(name='Data Logger')

    chunks_array = epyqlib.pm.parametermodel.Array(name='Chunks')
    data_logger.append_child(chunks_array)

    chunk = epyqlib.pm.parametermodel.Group(type_name='Chunk')
    chunks_array.append_child(chunk)
    chunks_array.length = 4
    chunks_array.children[0].name = 'First'
    chunks_array.children[1].name = 'Second'
    chunks_array.children[2].name = 'Third'
    chunks_array.children[3].name = 'Fourth'

    address = epyqlib.pm.parametermodel.Parameter(
        name='Address',
        default=0,
        type_name='int16_t',
    )
    chunk.append_child(address)
    bytes_ = epyqlib.pm.parametermodel.Parameter(
        name='Bytes',
        default=0,
        type_name='int16_t',
    )
    chunk.append_child(bytes_)

    post_trigger_duration = epyqlib.pm.parametermodel.Parameter(
        name='Post Trigger Duration',
        default=500,
        type_name='int16_t',
    )
    data_logger.append_child(post_trigger_duration)

    group = epyqlib.pm.parametermodel.Group(name='Group')
    data_logger.append_child(group)

    param = epyqlib.pm.parametermodel.Parameter(
        name='Param',
        type_name='int16_t',
    )
    group.append_child(param)

    builder = epcpm.parameterstoc.builders.wrap(data_logger)

    ast = pycparser.c_ast.FileAST(builder.definition())
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
    struct Chunk_s
    {
      int16_t address;
      int16_t bytes;
    };
    typedef struct Chunk_s Chunk_t;
    enum Chunks_e
    {
      Chunks_First = 0,
      Chunks_Second = 1,
      Chunks_Third = 2,
      Chunks_Fourth = 3,
      Chunks_Count = 4
    };
    typedef enum Chunks_e Chunks_et;
    typedef Chunk_t Chunks_t[Chunks_Count];
    struct Group_s
    {
      int16_t param;
    };
    typedef struct Group_s Group_t;
    struct DataLogger_s
    {
      Chunks_t chunks;
      int16_t postTriggerDuration;
      Group_t group;
    };
    typedef struct DataLogger_s DataLogger_t;
    ''')

data_logger_structures = '''\
typedef struct
{
    void*	address;
    size_t	bytes;
} DataLogger_Chunk;

#define DATALOGGER_CHUNK_DEFAULTS(...) \
{ \
    .address = 0, \
    .bytes = 0, \
    __VA_ARGS__ \
}

typedef DataLogger_Chunk DataLogger_Chunks[dataLoggerChunkCount];

typedef struct
{
    DataLogger_Chunks chunks;
    uint16_t postTriggerDuration_ms;
} DataLogger_Params;

#define DATALOGGER_PARAMS_DEFAULTS(...) \
{ \
    .chunks = {[0 ... dataLoggerChunkCount-1] = DATALOGGER_CHUNK_DEFAULTS()}, \
    .postTriggerDuration_ms = 500, \
    __VA_ARGS__ \
}
'''


def test_basic_parameter_array():
    array = epyqlib.pm.parametermodel.Array(name='Array Name')
    parameter = epyqlib.pm.parametermodel.Parameter(
        name='Parameter Name',
        type_name='int16_t',
    )

    array.append_child(parameter)

    n = 5

    array.length = n

    builder = epcpm.parameterstoc.builders.wrap(array)

    ast = pycparser.c_ast.FileAST(builder.definition())
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
    enum ArrayName_e
    {
      ArrayName_ParameterName = 0,
      ArrayName_NewArrayParameterElement = 1,
      ArrayName_NewArrayParameterElement = 2,
      ArrayName_NewArrayParameterElement = 3,
      ArrayName_NewArrayParameterElement = 4,
      ArrayName_Count = 5
    };
    typedef enum ArrayName_e ArrayName_et;
    typedef int16_t ArrayName_t[ArrayName_Count];
    ''')


def test_grouped_parameter_array():
    group = epyqlib.pm.parametermodel.Group(name='Group Name')
    array = epyqlib.pm.parametermodel.Array(name='Array Name')
    parameter = epyqlib.pm.parametermodel.Parameter(
        name='Parameter Name',
        type_name='int16_t',
    )

    group.append_child(array)
    array.append_child(parameter)

    n = 5

    array.length = n

    builder = epcpm.parameterstoc.builders.wrap(group)

    ast = pycparser.c_ast.FileAST(builder.definition())
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
    enum ArrayName_e
    {
      ArrayName_ParameterName = 0,
      ArrayName_NewArrayParameterElement = 1,
      ArrayName_NewArrayParameterElement = 2,
      ArrayName_NewArrayParameterElement = 3,
      ArrayName_NewArrayParameterElement = 4,
      ArrayName_Count = 5
    };
    typedef enum ArrayName_e ArrayName_et;
    typedef int16_t ArrayName_t[ArrayName_Count];
    struct GroupName_s
    {
      ArrayName_t arrayName;
    };
    typedef struct GroupName_s GroupName_t;
    ''')


def test_grouped_parameter_array_no_enum():
    array = epyqlib.pm.parametermodel.Array(name='Array Name')
    array.named_enumerators = False
    parameter = epyqlib.pm.parametermodel.Parameter(
        name='Parameter Name',
        type_name='int16_t',
    )

    array.append_child(parameter)

    n = 5

    array.length = n

    builder = epcpm.parameterstoc.builders.wrap(array)

    ast = pycparser.c_ast.FileAST(builder.definition())
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
    enum ArrayName_e
    {
      ArrayName_Count = 5
    };
    typedef enum ArrayName_e ArrayName_et;
    typedef int16_t ArrayName_t[ArrayName_Count];
    ''')


def test_line_monitor_params():
    line_monitoring = epyqlib.pm.parametermodel.Group(
        name='Line Monitoring',
    )

    frequency_limits = epyqlib.pm.parametermodel.Array(
        name='Frequency Limits',
    )
    line_monitoring.append_child(frequency_limits)

    frequency_limit = epyqlib.pm.parametermodel.Group(
        name='First',
        type_name='Frequency Limit',
    )
    frequency_limits.append_child(frequency_limit)

    frequency = epyqlib.pm.parametermodel.Parameter(
        name='Frequency',
        type_name='_iq',
    )
    frequency_limit.append_child(frequency)

    clearing_time = epyqlib.pm.parametermodel.Parameter(
        name='Clearing Time',
        type_name='_iq',
    )
    frequency_limit.append_child(clearing_time)

    frequency_limits.length = 4
    frequency_limits.children[1].name = 'Second'
    frequency_limits.children[2].name = 'Third'
    frequency_limits.children[3].name = 'Fourth'

    builder = epcpm.parameterstoc.builders.wrap(line_monitoring)

    ast = pycparser.c_ast.FileAST(builder.definition())
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
    struct FrequencyLimit_s
    {
      _iq frequency;
      _iq clearingTime;
    };
    typedef struct FrequencyLimit_s FrequencyLimit_t;
    enum FrequencyLimits_e
    {
      FrequencyLimits_First = 0,
      FrequencyLimits_Second = 1,
      FrequencyLimits_Third = 2,
      FrequencyLimits_Fourth = 3,
      FrequencyLimits_Count = 4
    };
    typedef enum FrequencyLimits_e FrequencyLimits_et;
    typedef FrequencyLimit_t FrequencyLimits_t[FrequencyLimits_Count];
    struct LineMonitoring_s
    {
      FrequencyLimits_t frequencyLimits;
    };
    typedef struct LineMonitoring_s LineMonitoring_t;
    ''')


def test_root():
    root = epyqlib.pm.parametermodel.Root()
    group = epyqlib.pm.parametermodel.Group(name='Group')
    p1 = epyqlib.pm.parametermodel.Parameter(name='red', type_name='RedType')
    p2 = epyqlib.pm.parametermodel.Parameter(name='blue', type_name='BlueType')

    root.append_child(group)
    group.append_child(p1)
    root.append_child(p2)

    builder = epcpm.parameterstoc.builders.wrap(root)

    ast = pycparser.c_ast.FileAST(builder.definition())
    generator = pycparser.c_generator.CGenerator()
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
    struct Group_s
    {
      RedType red;
    };
    typedef struct Group_s Group_t;
    ''')

    ast = pycparser.c_ast.FileAST(builder.instantiation())
    s = generator.visit(ast)

    assert s == textwrap.dedent('''\
    Group_t group;
    BlueType blue;
    ''')
