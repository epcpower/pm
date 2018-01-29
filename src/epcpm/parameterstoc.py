import itertools
import functools

import attr
import pycparser

import epyqlib.pm.parametermodel
import epyqlib.utils.general


builders = epyqlib.utils.general.TypeMap()


@builders(epyqlib.pm.parametermodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()

    def definition(self):
        definitions = []

        for member in self.wrapped.children:
            builder = builders.wrap(member)
            definitions.extend(builder.definition())

        return definitions

    def instantiation(self):
        decls = []

        for member in self.wrapped.children:
            builder = builders.wrap(member)

            decls.append(Decl(
                type=Type(
                    name=epyqlib.utils.general.spaced_to_lower_camel(
                        member.name,
                    ),
                    type=builder.type_name(),
                )
            ))

        return decls


@builders(epyqlib.pm.parametermodel.Parameter)
@attr.s
class Parameter:
    wrapped = attr.ib()

    def definition(self):
        return []

    def type_name(self):
        type_name = self.wrapped.type_name

        if type_name is None:
            return 'void'

        return type_name


@builders(epyqlib.pm.parametermodel.Group)
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
                    name=epyqlib.utils.general.spaced_to_lower_camel(
                        member.name,
                    ),
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
        return epyqlib.utils.general.spaced_to_upper_camel(name) + '_t'


@builders(epyqlib.pm.parametermodel.Array)
@attr.s
class Array:
    wrapped = attr.ib()

    def definition(self):
        builder = builders.wrap(self.wrapped.children[0])
        definitions = builder.definition()

        values = []
        if self.wrapped.named_enumerators:
            values.extend(enumerate(
                epyqlib.utils.general.spaced_to_upper_camel(child.name)
                for child in self.wrapped.children
            ))

        values.append((len(self.wrapped.children), 'Count'))

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
                for value, name in values
            ],
        )

        return [
            *definitions,
            *enum_definitions,
            array_typedef(
                target=builder.type_name(),
                name=self.type_name(),
                length=pycparser.c_ast.ID(
                    enum_definitions[0].type.values.enumerators[-1].name
                ),
            ),
        ]

    def base_type_name(self):
        return epyqlib.utils.general.spaced_to_upper_camel(self.wrapped.name)

    def type_name(self):
        return self.base_type_name() + '_t'


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


def typedef(target, name):
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


def array_typedef(target, name, length):
    return pycparser.c_ast.Typedef(
        name=name,
        quals=[],
        storage=['typedef'],
        type=ArrayDecl(
            dim=length,
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

    typedef_ = typedef(
        target=pycparser.c_ast.Enum(
            name=enum_name,
            values=None
        ),
        name=typedef_name,
    )

    return declaration, typedef_


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

    typedef_ = typedef(
        target=pycparser.c_ast.Struct(
            name=struct_name,
            decls=[],
        ),
        name=typedef_name,
    )

    return decl, typedef_


def array(type, name, length):
    return Decl(
        name=name,
        type=ArrayDecl(
            type=Type(name, type),
            dim=int_literal(length),
        )
    )
