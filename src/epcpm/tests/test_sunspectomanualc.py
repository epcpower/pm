import epcpm.sunspectomanualc


import functools

import pycparser.c_parser


def parse(c):
    parser = pycparser.c_parser.CParser()
    ast = parser.parse(c)
    return ast

c = """
void getSUNSPEC_MODEL1_DA (void) {
    sunspecInterface.model1.DA = modbusHandlerGetSlaveAddress();
}

void setSUNSPEC_MODEL1_DA (void) {
    modbusHandlerSetSlaveAddress(sunspecInterface.model1.DA);
}
"""

def Type(name, type):
    return pycparser.c_ast.TypeDecl(
        declname=name,
        quals=[],
        type=pycparser.c_ast.IdentifierType(
            names=(type,),
        ),
    )

Decl = functools.partial(
    pycparser.c_ast.Decl,
    name=None,
    quals=[],
    storage=[],
    funcspec=[],
    init=None,
    bitsize=None,
)

TypeDecl = functools.partial(
    pycparser.c_ast.TypeDecl,
    declname='',
    quals=[],
)


def function(name):
    type_decl = Type(
        name=name,
        type=['void'],
    )

    param_list = pycparser.c_ast.ParamList(
        params=[
            pycparser.c_ast.Typename(
                name=None,
                quals=[],
                type=pycparser.c_ast.IdentifierType(
                    names=['void'],
                ),
            ),
        ],
    )

    func_decl = pycparser.c_ast.FuncDecl(
        args=param_list,
        type=type_decl,
    )

    decl = Decl(
        name=name,
        type=func_decl,
    )

    compound = pycparser.c_ast.Compound(
        block_items=[],
    )

    function = pycparser.c_ast.FuncDef(
        decl=decl,
        param_decls=None,
        body=compound,
    )

    return function


def test_():
    ast = parse(c)
    ast.ext.append(function('myFunctionName'))
    ast.show()
