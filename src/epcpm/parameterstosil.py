import re

import attr
import toolz

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
        f'#include "interfaceAccessors.h"',
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
                        epyqlib.pm.parametermodel.Table,
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
                        epyqlib.pm.parametermodel.Table,
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
    is_table = attr.ib(default=False)
    table_info = attr.ib(default=None)
    #     factory=lambda: TableInfo(zone=0, curve=0, index=0, setter=0, type=''),
    # )

    # TODO: index -> designator
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
        if self.table_info is None:
            table_info_initializer = []
        else:
            table_info_initializer = self.table_info.create_initializer(
                designator='.tableInfo',
            )

        is_table = 'true' if self.is_table else 'false'

        initializers = [
            f'.uuid = "{self.item_uuid}",',
            f'.setterType = setter_{self.type},',
            f'.setter = {{ .{self.type}_ = {self.on_write} }},',
            f'.variable = {{ .{self.type}_ = {self.variable} }},',
            f'.internalScale = {self.internal_scale},',
            f'.isTable = {is_table},',
            *table_info_initializer,
        ]

        return initializers


@attr.s
class TableInfo:
    zone = attr.ib()
    curve = attr.ib()
    index = attr.ib()
    setter = attr.ib()
    type = attr.ib()

    # TODO: index -> designator
    def create_initializer(self, designator=None):
        initializers = self.create_subinitializers()

        if designator is not None:
            designator_text = f'{designator} = '
        else:
            designator_text = ''

        item_initializer = [
            f'{designator_text}{{',
            initializers,
            '},',
        ]

        return item_initializer

    def create_subinitializers(self):
        initializers = []

        if self.zone is not None:
            initializers.append(f'.zone = {self.zone},')

        initializers.extend([
            f'.curve = {self.curve},',
            f'.index = {self.index},',
            # TODO: ugh, again with tables being all the same type internally
            f'.setter = {{ .int16_t_ = {self.setter} }},',
        ])

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


# TODO: CAMPid 68945967541316743769675426795146379678431
def breakdown_nested_array(s):
    split = re.split(r'\[(.*?)\].', s)

    array_layers = list(toolz.partition(2, split))
    remainder, = split[2 * len(array_layers):]

    return array_layers, remainder


# TODO: CAMPid 079549750417808543178043180
def get_curve_type(combination_string):
    # TODO: backmatching
    return {
        'LowRideThrough': 'IEEE1547_CURVE_TYPE_LRT',
        'HighRideThrough': 'IEEE1547_CURVE_TYPE_HRT',
        'LowTrip': 'IEEE1547_CURVE_TYPE_LTRIP',
        'HighTrip': 'IEEE1547_CURVE_TYPE_HTRIP',
    }.get(combination_string)


# TODO: CAMPid 0974567213671436714671907842679364
@attr.s
class NestedArrays:
    array_layers = attr.ib()
    remainder = attr.ib()

    @classmethod
    def build(cls, s):
        array_layers, remainder = breakdown_nested_array(s)

        return cls(
            array_layers=array_layers,
            remainder=remainder,
        )

    def index(self, indexes):
        try:
            return '.'.join(
                '{layer}[{index}]'.format(
                    layer=layer,
                    index=index_format.format(**indexes),
                )
                for (layer, index_format), index in zip(self.array_layers, indexes)
            )
        except KeyError as e:
            raise

    def sizeof(self, layers):
        indexed = self.index(indexes={layer: 0 for layer in layers})

        return f'sizeof({indexed})'

    def full(self, indexes):
        variable_base = self.index(indexes)
        variable = f'{variable_base}.{self.remainder}'

        return variable


# TODO: CAMPid 0795436754762451671643967431
# TODO: get this from the ...  wherever we have it
axes = ['x', 'y', 'z']


@builders(epyqlib.pm.parametermodel.Table)
@attr.s
class Table:
    wrapped = attr.ib()
    parameters_root = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        group, = (
            child
            for child in self.wrapped.children
            if isinstance(child, epyqlib.pm.parametermodel.TableGroupElement)
        )

        arrays = [
            child
            for child in self.wrapped.children
            if isinstance(child, epyqlib.pm.parametermodel.Array)
        ]

        array_nests = {
            name: NestedArrays.build(s=array.children[0].internal_variable)
            for name, array in zip(axes, arrays)
        }

        items = builders.wrap(
            wrapped=group,
            table=self.wrapped,
            array_nests=array_nests,
            parameter_uuid_finder=self.parameter_uuid_finder,
        ).gen()

        return items


@builders(epyqlib.pm.parametermodel.TableGroupElement)
@attr.s
class TableGroupElement:
    wrapped = attr.ib()
    table = attr.ib()
    array_nests = attr.ib()
    parameter_uuid_finder = attr.ib()
    layers = attr.ib(default=[])

    def gen(self):
        items = []

        table_tree_root = not isinstance(
            self.wrapped.tree_parent,
            epyqlib.pm.parametermodel.TableGroupElement,
        )

        layers = list(self.layers)
        if not table_tree_root:
            layers.append(self.wrapped.name)

        for child in self.wrapped.children:
            result = builders.wrap(
                wrapped=child,
                table=self.table,
                layers=layers,
                array_nests=self.array_nests,
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()

            items.extend(result)

        return items


@builders(epyqlib.pm.parametermodel.TableArrayElement)
@attr.s
class TableArrayElement:
    wrapped = attr.ib()
    table = attr.ib()
    layers = attr.ib()
    array_nests = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        table_element = self.wrapped

        # TODO: CAMPid 9655426754319431461354643167
        array_element = table_element.original

        if isinstance(array_element, epyqlib.pm.parametermodel.Parameter):
            parameter = array_element
        else:
            parameter = array_element.tree_parent.children[0]

        is_group = isinstance(
            parameter.tree_parent,
            epyqlib.pm.parametermodel.Group,
        )

        if is_group:
            return self.handle_group()

        return self.handle_array()

    def handle_array(self):
        table_element = self.wrapped

        # TODO: CAMPid 9655426754319431461354643167
        array_element = table_element.original

        if isinstance(array_element, epyqlib.pm.parametermodel.Parameter):
            parameter = array_element
        else:
            parameter = array_element.tree_parent.children[0]

        indexes = {
            'curve_type': get_curve_type(''.join(self.layers[:2])),
            'curve_index': int(self.layers[-2]),
            'point_index': int(table_element.name.lstrip('_').lstrip('0')) - 1,
        }

        axis = axes[self.table.arrays.index(parameter.tree_parent)]
        variable = self.array_nests[axis].full(indexes)
        # This cast covers the fact that all table points are internally
        # int16_t despite some being used as uint16_t.
        # TODO: verify compatible size at least?
        variable = f'({parameter.internal_type} *) &{variable}'

        if parameter.setter_function is None:
            # TODO: should Item do this?
            table_on_write = 'NULL'
        else:
            table_on_write = parameter.setter_function.format(upper_axis=axis.upper())

        table_info = TableInfo(
            zone=indexes['curve_type'],
            curve=indexes['curve_index'],
            index=indexes['point_index'],
            setter=table_on_write,
            type=parameter.internal_type,
        )

        return [
            Item(
                item_uuid=table_element.uuid,
                variable=variable,
                type=parameter.internal_type,
                on_write='NULL',
                internal_scale=parameter.internal_scale_factor,
                is_table=True,
                table_info=table_info,
            )
        ]

    def handle_group(self):
        table_element = self.wrapped

        curve_index = int(self.layers[-2])

        parameter = table_element.original

        if parameter.internal_variable is None:
            return []

        if parameter.setter_function is None:
            # TODO: i think it's reasonable for Item to handle this?
            setter_function = 'NULL'
        else:
            setter_function = '&' + parameter.setter_function

        curve_type = get_curve_type(''.join(self.layers[:2]))

        internal_variable = parameter.internal_variable.format(
            curve_type=curve_type,
            curve_index=curve_index,
        )

        item = Item(
            item_uuid=table_element.uuid,
            variable=f'&{internal_variable}',
            type=parameter.internal_type,
            on_write=setter_function,
            internal_scale=parameter.internal_scale_factor,
        )

        return [item]
