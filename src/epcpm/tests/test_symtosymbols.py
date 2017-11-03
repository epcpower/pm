import io
import json
import textwrap

import epyqlib.tests.common

import epcpm.symbolmodel
import epcpm.symtoproject


def test_load_can_file():
    parameter_root, symbol_root = epcpm.symtoproject.load_can_path(
        epyqlib.tests.common.symbol_files['customer'],
        epyqlib.tests.common.hierarchy_files['customer'],
    )

    assert isinstance(parameter_root, epcpm.parametermodel.Root)
    assert isinstance(symbol_root, epcpm.symbolmodel.Root)


def test_only_one_parameter_per_query_response_pair():
    sym_file = io.BytesIO(textwrap.dedent('''\
    FormatVersion=5.0 // Do not edit this line!
    Title="canmatrix-Export"

    {SEND}
    
    [ParameterQuery]
    ID=1DEFF741h
    Type=Extended
    DLC=8
    Mux=TestMux 0,14 0 
    Var=TestParam unsigned 14,2

    {SENDRECEIVE}
    
    [ParameterResponse]
    ID=1DEF41F7h
    Type=Extended
    DLC=8
    Mux=TestMux 0,14 0 
    Var=TestParam unsigned 14,2
    ''').encode('utf-8'))

    hierarchy_file = io.StringIO(json.dumps({
        'children': [
            {
                'name': 'Test Group',
                'children': [
                    [
                        "TestMux",
                        "TestParam"
                    ]
                ]
            }
        ]
    }))
    hierarchy_file = io.StringIO('{"children": []}')

    parameter_root, symbol_root = epcpm.symtoproject.load_can_file(
        can_file=sym_file,
        file_type='sym',
        parameter_hierarchy_file=hierarchy_file,
    )

    parameters = next(
        node
        for node in parameter_root.children
        if node.name == 'Parameters'
    )

    assert len(parameters.children[0].children) == 1
