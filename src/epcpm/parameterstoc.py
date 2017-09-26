import itertools
import functools

import click
import pycparser

import epcpm.parametermodel


@click.command()
@click.option('--parameters', type=click.File())
def cli(*args, **kwargs):
    _cli(*args, **kwargs)


def _cli(parameters):
    model = epcpm.attrsmodel.Model.from_json_string(
        parameters.read(),
        columns=epcpm.parametermodel.columns,
        types=epcpm.parametermodel.types,
    )

    ast = build_ast(model.root)

    print()


def build_ast(node):
    ast = []

    subgroups = tuple(
        child for child in node.children
        if isinstance(child, epcpm.parametermodel.Group)
    )

    subgroup_type = {}

    for child in subgroups:
        child_ast = build_ast(child)
        ast.extend(child_ast)

        subgroup_type[child] = ast[-1].type.declname

    if isinstance(node, epcpm.parametermodel.Group):
        member_decls = []

        for member in node.children:
            if isinstance(member, epcpm.parametermodel.Group):
                member_decls.append(Decl(
                    type=Type(
                        name=spaced_to_lower_camel(member.name),
                        type=subgroup_type[member],
                    )
                ))
            elif isinstance(member, epcpm.parametermodel.Parameter):
                member_decls.append(Decl(
                    type=Type(
                        name=spaced_to_lower_camel(member.name),
                        type='int16_t',
                    )
                ))
            elif isinstance(member, epcpm.parametermodel.ArrayGroup):
                member_decls.append(array(
                    type='int16_t',
                    name=spaced_to_lower_camel(member.name),
                    length=member.length,
                ))
            else:
                raise Exception('Unhandleable type: {}'.format(type(node)))

        ast.extend(struct(
            name=spaced_to_upper_camel(node.name),
            member_decls=member_decls,
        ))
    elif isinstance(node, epcpm.parametermodel.ArrayGroup):
        ast.append(
            array(
                type='int16_t',
                name=spaced_to_lower_camel(node.name),
                length=node.length,
            )
        )
    else:
        raise Exception('Unhandleable type: {}'.format(type(node)))

    return ast


# TODO: CAMPid 978597542154245264521645215421964521
def spaced_to_lower_camel(name):
    segments = name.split(' ')
    segments = itertools.chain(
        segments[0].lower(),
        *(''.join(itertools.chain(
            c[0].upper(), c[1:].lower(),
        )) for c in segments[1:]),
    )
    return ''.join(segments)


# TODO: CAMPid 978597542154245264521645215421964521
def spaced_to_upper_camel(name):
    segments = name.split(' ')
    segments = itertools.chain(
        *(''.join(itertools.chain(
            c[0].upper(), c[1:].lower(),
        )) for c in segments),
    )
    return ''.join(segments)


def int_literal(value):
    return pycparser.c_ast.Constant(type='int', value=str(value))


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


ArrayDecl = functools.partial(
    pycparser.c_ast.ArrayDecl,
    dim_quals=[],
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


def struct(name, member_decls=()):
    struct_name = f'{name}_s'
    typedef_name = f'{name}_t'

    struct = pycparser.c_ast.Struct(
        name=struct_name,
        decls=member_decls,
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


def array(type, name, length):
    return Decl(
        name=name,
        type=ArrayDecl(
            type=Type(name, type),
            dim=int_literal(length),
        )
    )
