import attr

import epyqlib.pm.parametermodel
import epyqlib.utils.general

import epcpm.c


builders = epyqlib.utils.general.TypeMap()


# TODO: get rid of this or get it somewhere else (pm exclude-from-SIL bool?)
def ignore_item(item):
    if 'sunspec' in item.variable.casefold():
        return True

    return False


@attr.s
class CHContents:
    c = attr.ib(factory=list)
    h = attr.ib(factory=list)

    def extend(self, other):
        self.c.extend(other.c)
        self.h.extend(other.h)

    def append(self, other):
        self.c.append(other.c)
        self.h.append(other.h)


def export(c_path, h_path, parameters_model):
    builder = builders.wrap(
        wrapped=parameters_model.root,
        parameters_root=parameters_model.root,
    )

    contents = CHContents()

    c_path.parent.mkdir(parents=True, exist_ok=True)
    contents.c.extend([
        '#include "libEpcControlInterfaceGen.h"',
        '',
        *[
            f'#include "{name}"'
            for name in [
                'islandControlI.h',
            ]
        ],
        '',
        '',
    ])

    contents.h.extend([
        f'#ifndef libEpcControlInterfaceGen_h_guard',
        f'#define libEpcControlInterfaceGen_h_guard',
        f'',
        f'#include "libEpcControlInterface.h"',
        f'',
    ])

    built = builder.gen()
    contents.extend(built)

    contents.h.extend([
        '',
        '#endif',
    ])

    with c_path.open('w', newline='\n') as f:
        f.write(epcpm.c.format_nested_lists(contents.c))

    with h_path.open('w', newline='\n') as f:
        f.write(epcpm.c.format_nested_lists(contents.h))


@builders(epyqlib.pm.parametermodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    parameters_root = attr.ib()

    def gen(self):
        parameters = next(
            node
            for node in self.wrapped.children
            if node.name == 'Parameters'
        )

        contents = CHContents()
        item_count = 0
        types = set()

        for child in parameters.children:
            if not isinstance(
                    child,
                    (
                        epyqlib.pm.parametermodel.Group,
                        epyqlib.pm.parametermodel.Parameter,
                    ),
            ):
                continue

            items = builders.wrap(
                wrapped=child,
                parameters_root=self.parameters_root,
                parameter_uuid_finder=self.wrapped.model.node_from_uuid,
            ).gen()
            
            for item in items:
                types.add(item.type)
                item_lines = item.create_initializer(index=item_count)
                contents.c.extend(item_lines)
                item_count += 1

        everything = CHContents()

        everything.c.extend([
                f'Item SIL_interfaceItems[{item_count}] = {{',
                contents.c,
                '};',
        ])

        everything.h.extend([
            # 'typedef enum SetterTypes {',
            # [
            #     f'setter_{type},'
            #     for type in types
            # ],
            # '} SetterTypes;',
            # '',
            # *[
            #     f'typedef void (*SetterPointer_{type})({type});'
            #     for type in types
            # ],
            # '',
            # 'typedef union Setter {',
            # [
            #     f'SetterPointer_{type} {type}_;'
            #     for type in types
            # ],
            # '} Setter;',
            # '',
            f'extern Item SIL_interfaceItems[{item_count}];',
        ])

        return everything


@builders(epyqlib.pm.parametermodel.Group)
@attr.s
class Group:
    wrapped = attr.ib()
    parameters_root = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        items = []

        for child in self.wrapped.children:
            if not isinstance(
                    child,
                    (
                        epyqlib.pm.parametermodel.Group,
                        epyqlib.pm.parametermodel.Parameter,
                    ),
            ):
                continue

            built = builders.wrap(
                wrapped=child,
                parameters_root=self.parameters_root,
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()

            items.extend(built)

        return items


@attr.s
class Item:
    item_uuid = attr.ib()
    variable = attr.ib()
    type = attr.ib()
    on_write = attr.ib()
    internal_scale = attr.ib()

    def create_initializer(self, index=None):
        initializers = self.create_subinitializers()

        if index is not None:
            index_text = f'[{index}] = '
        else:
            index_text = ''

        item_initializer = [
            f'{index_text}{{',
            initializers,
            '},',
        ]

        return item_initializer

    def create_subinitializers(self):
        initializers = [
            f'.uuid = "{self.item_uuid}",',
            f'.setterType = setter_{self.type},',
            f'.setter = {{ .{self.type}_ = {self.on_write} }},',
            f'.variable = {{ .{self.type}_ = {self.variable} }},',
            f'.internalScale = {self.internal_scale},',
        ]

        return initializers


@builders(epyqlib.pm.parametermodel.Parameter)
@attr.s
class Parameter:
    wrapped = attr.ib()
    parameters_root = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        parameter = self.wrapped

        supported_item_type = (
            parameter.uses_interface_item()
            and parameter.internal_variable is not None
        )

        if not supported_item_type:
            return []

        if parameter.setter_function is None:
            on_write = 'NULL'
        else:
            on_write = f'&{parameter.setter_function}'

        item = Item(
            item_uuid=parameter.uuid,
            variable=f'&{parameter.internal_variable}',
            type=parameter.internal_type,
            on_write=on_write,
            internal_scale=parameter.internal_scale_factor,
        )

        if ignore_item(item):
            return []

        return [item]
