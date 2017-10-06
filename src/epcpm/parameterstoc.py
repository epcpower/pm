import itertools
import functools

import attr
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


@attr.s
class TypeMap:
    types = attr.ib(default=attr.Factory(dict), init=False)

    def __call__(self, wrapped):
        def inner(cls):
            self.types[wrapped] = cls

        return inner

    def __getitem__(self, item):
        return self.types[item]

    def wrap(self, wrapped):
        return self.types[type(wrapped)](wrapped=wrapped)


builders = TypeMap()


@builders(epcpm.parametermodel.Parameter)
@attr.s
class Parameter:
    wrapped = attr.ib()

    def definition(self):
        return []

    def type_name(self):
        return 'int16_t'


@builders(epcpm.parametermodel.Group)
@attr.s
class Group:
    wrapped = attr.ib()

    def definition(self):
        definitions = []
        member_decls = []

        for member in self.wrapped.children:
            builder = builders.wrap(member)

            member_decls.append(Decl(
                type=Type(
                    name=spaced_to_lower_camel(member.name),
                    type=builder.type_name(),
                )
            ))

            definitions.extend(builder.definition())

        return [
            *definitions,
            *struct(
                name=self.type_name()[:-2],
                member_decls=member_decls,
            ),
        ]

    def type_name(self):
        name = self.wrapped.type_name
        if name is None:
            name = self.wrapped.name
        return spaced_to_upper_camel(name) + '_t'


@builders(epcpm.parametermodel.Array)
@attr.s
class Array:
    wrapped = attr.ib()

    def definition(self):
        builder = builders.wrap(self.wrapped.children[0])
        definitions = builder.definition()

        enum_definitions = enum(
            name=self.base_type_name(),
            enumerators=[
                (
                    '{base}_{name}'.format(
                        base=self.base_type_name(),
                        name=name,
                    ),
                    value,
                )
                for value, name in enumerate(
                    [
                        spaced_to_upper_camel(child.name)
                        for child in self.wrapped.children
                    ]
                    + ['Count']
                )
            ],
        )

        return [
            *definitions,
            *enum_definitions,
            ArrayTypedef(
                target=builder.type_name(),
                name=self.type_name(),
                length=self.wrapped.length,
            ),
        ]

    def base_type_name(self):
        return spaced_to_upper_camel(self.wrapped.name)

    def type_name(self):
        return self.base_type_name() + '_t'


def build_ast(node):
    ast = []

    group_types = (
        epcpm.parametermodel.Group,
        epcpm.parametermodel.ArrayGroup,
    )

    subgroups = tuple(
        child for child in node.children
        if isinstance(child, group_types)
    )

    subgroup_type = {}

    for child in subgroups:
        child_ast = build_ast(child)
        ast.extend(child_ast)

        if isinstance(child, epcpm.parametermodel.ArrayGroup):
            ast.append(Typedef(
                target=array(ast[-1].type.declname, 'array_name', child.length),
                name=ast[-1].type.declname[:-1] + 'at',
            ))

        subgroup_type[child] = ast[-1].type.declname

    if isinstance(node, group_types):
        member_decls = []

        for member in node.children:
            if isinstance(member, group_types):
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
            else:
                raise Exception('Unhandleable type: {}'.format(type(member)))

        ast.extend(struct(
            name=spaced_to_upper_camel(node.name),
            member_decls=member_decls,
        ))
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


TypeDecl = functools.partial(
    pycparser.c_ast.TypeDecl,
    declname='',
    quals=[],
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


def ArrayTypedef(target, name, length):
    return pycparser.c_ast.Typedef(
        name=name,
        quals=[],
        storage=['typedef'],
        type=ArrayDecl(
            dim=int_literal(length),
            type=TypeDecl(
                declname=name,
                type=pycparser.c_ast.IdentifierType(
                    names=[target],
                ),
            ),
        ),
    )


def enum(name, enumerators=()):
    enum_name = '{name}_e'.format(name=name)
    typedef_name = '{name}_et'.format(name=name)

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
        target=pycparser.c_ast.Struct(
            name=struct_name,
            decls=[],
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
