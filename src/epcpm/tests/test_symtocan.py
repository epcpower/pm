import decimal
import io
import json
import textwrap

import pytest

import epyqlib.pm.parametermodel
import epyqlib.tests.common

import epcpm.canmodel
import epcpm.symtoproject


@pytest.fixture
def sym_file():
    return io.BytesIO(textwrap.dedent('''\
    FormatVersion=5.0 // Do not edit this line!
    Title="canmatrix-Export"
    
    {ENUMS}
    enum AccessLevel(0="User", 1="Engineering", 2="Factory")
    enum CmmControlsVariant(0="None", 1="MG3", 2="MG4", 3="DG", 4="HY", 5="DC")
    
    {SEND}
    
    [ParameterQuery]
    ID=1DEFF741h
    Type=Extended
    DLC=8
    Mux=TestMux 0,14 0 
    Var=TestParam unsigned 14,2 /f:0.01  /min:0.01  /max:0.2 /p:2 /d:0.02
    Var=FactoryParam unsigned 14,2 /f:0.01  /min:0.01  /max:0.2 /p:2 /d:0.02  // before <factory> after
    
    {SENDRECEIVE}
    
    [ParameterResponse]
    ID=1DEF41F7h
    Type=Extended
    DLC=8
    Mux=TestMux 0,14 0 
    Var=TestParam unsigned 14,2 /f:0.01  /min:0.01  /max:0.2 /p:2 /d:0.02
    Var=FactoryParam unsigned 14,2 /f:0.01  /min:0.01  /max:0.2 /p:2 /d:0.02  // before <factory> after
    ''').encode('utf-8'))


other_group_name = 'Uncategorized Stuff'


@pytest.fixture
def hierarchy_file():
    return io.StringIO(json.dumps({
        'children': [
            {
                'name': 'Test Group',
                'children': [
                    [
                        "TestMux",
                        "TestParam"
                    ],
                    [
                        "TestMux",
                        "FactoryParam"
                    ]
                ]
            },
            {
                'name': other_group_name,
                'unreferenced': True,
            },
        ]
    }))


@pytest.fixture
def empty_hierarchy_file():
    return io.StringIO('{"children": []}')


def test_other_group_name(hierarchy_file):
    hierarchy = json.load(hierarchy_file)
    assert epcpm.symtoproject.get_other_name(hierarchy) == other_group_name


def test_load_can_file():
    parameter_root, can_root, sunspec_root = epcpm.symtoproject.load_can_path(
        epyqlib.tests.common.symbol_files['customer'],
        epyqlib.tests.common.hierarchy_files['customer'],
    )

    assert isinstance(parameter_root, epyqlib.pm.parametermodel.Root)
    assert isinstance(can_root, epcpm.canmodel.Root)
    assert isinstance(sunspec_root, epcpm.sunspecmodel.Root)


def test_only_one_parameter_per_query_response_pair(
        sym_file,
        empty_hierarchy_file,
):
    parameter_root, *_ = epcpm.symtoproject.load_can_file(
        can_file=sym_file,
        file_type='sym',
        parameter_hierarchy_file=empty_hierarchy_file,
    )

    parameters = next(
        node
        for node in parameter_root.children
        if node.name == 'Parameters'
    )

    assert len(parameters.children[0].children) == 2


def test_access_level(sym_file, hierarchy_file):
    parameter_root, *_ = epcpm.symtoproject.load_can_file(
        can_file=sym_file,
        file_type='sym',
        parameter_hierarchy_file=hierarchy_file,
    )

    access_levels, = parameter_root.nodes_by_attribute(
        attribute_name='name',
        attribute_value='AccessLevel',
    )

    regular_parameter, = parameter_root.nodes_by_attribute(
        attribute_name='name',
        attribute_value='TestParam',
    )

    assert regular_parameter.access_level_uuid == access_levels.default().uuid

    factory_parameter, = parameter_root.nodes_by_attribute(
        attribute_name='name',
        attribute_value='FactoryParam',
    )

    assert (
        factory_parameter.access_level_uuid
        == access_levels.by_name('factory').uuid
    )
    assert 'before  after' == factory_parameter.comment


def test_accurate_decimal(sym_file, hierarchy_file):
    parameter_root, *_ = epcpm.symtoproject.load_can_file(
        can_file=sym_file,
        file_type='sym',
        parameter_hierarchy_file=hierarchy_file,
    )

    parameters = next(
        node
        for node in parameter_root.children
        if node.name == 'Parameters'
    )

    test_group = next(
        node
        for node in parameters.children
        if node.name == 'Test Group'
    )

    test_parameter = next(
        node
        for node in test_group.children
        if node.name.endswith('TestParam')
    )

    # TODO: default is probably in wrong scaling
    # assert isinstance(test_parameter.default, decimal.Decimal)
    # assert test_parameter.default == decimal.Decimal('0.02')

    assert isinstance(test_parameter.minimum, decimal.Decimal)
    assert test_parameter.minimum == decimal.Decimal('0.01')
