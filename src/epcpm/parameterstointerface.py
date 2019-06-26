import decimal
import string
import re

import attr
import toolz

import epyqlib.pm.parametermodel
import epyqlib.utils.general

import epcpm.cantosym
import epcpm.sunspecmodel
import epcpm.sunspectoxlsx

builders = epyqlib.utils.general.TypeMap()


def export(c_path, h_path, parameters_model, can_model, sunspec_model):
    builder = builders.wrap(
        wrapped=parameters_model.root,
        can_root=can_model.root,
        sunspec_root=sunspec_model.root
    )

    model_ids = [
        1,
        17,
        103,
        120,
        121,
        122,
        123,
        126,
        129,
        130,
        132,
        134,
        135,
        136,
        137,
        138,
        141,
        142,
        145,
        160,
        *range(65000, 65011),
        65534,
    ]

    c_path.parent.mkdir(parents=True, exist_ok=True)
    c_gen = [
        '#include <stdint.h>',
        '',
        '#include "interface.h"',
        '#include "canInterfaceGen.h"',
        '#include "sunspecInterfaceGen.h"',
        '',
    ]
    # TODO: stop hardcoding this
    c_gen.extend(
        f'#include "sunspecInterfaceGen{id}.h"'
        for id in model_ids
    )
    c_gen.append('')
    c_gen.extend(
        f'#include "sunspecInterface{id:05}.h"'
        for id in model_ids
    )
    c_gen.extend(['', ''])

    h_gen = [
        f'#ifndef {h_path.stem.upper()}_H',
        f'#define {h_path.stem.upper()}_H',
        f'',
        f'#include "interface.h"',
        # f'',
        # *(
        #     f'#include "sunspecInterface{id:05}.h"'
        #     for id in model_ids
        # ),
        f'',
        f'',
    ]

    built_c, built_h = builder.gen()
    c_gen.extend(built_c)
    h_gen.extend(built_h)
    h_gen.extend([
        '',
        '#endif',
    ])

    with c_path.open('w', newline='\n') as f:
        f.write(epcpm.c.format_nested_lists(c_gen))

    with h_path.open('w', newline='\n') as f:
        f.write(epcpm.c.format_nested_lists(h_gen))


@builders(epyqlib.pm.parametermodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    can_root = attr.ib()
    sunspec_root = attr.ib()

    def gen(self):
        parameters = next(
            node
            for node in self.wrapped.children
            if node.name == 'Parameters'
        )

        def can_node_wanted(node):
            if getattr(node, 'parameter_uuid', None) is None:
                return False

            parameter_query_parent = node.tree_parent.tree_parent

            is_a_can_table = isinstance(
                node.tree_parent.tree_parent,
                epcpm.canmodel.CanTable,
            )
            if is_a_can_table:
                parameter_query_parent = parameter_query_parent.tree_parent

            is_a_query = (
                getattr(parameter_query_parent, 'name', '')
                == 'ParameterQuery'
            )
            if not is_a_query:
                return False

            return True

        can_nodes_with_parameter_uuid = self.can_root.nodes_by_filter(
            filter=can_node_wanted,
        )

        parameter_uuid_to_can_node = {
            node.parameter_uuid: node
            for node in can_nodes_with_parameter_uuid
        }

        def sunspec_node_wanted(node):
            if getattr(node, 'parameter_uuid', None) is None:
                return False

            if not isinstance(node, epcpm.sunspecmodel.DataPoint):
                return False

            return True

        sunspec_nodes_with_parameter_uuid = self.sunspec_root.nodes_by_filter(
            filter=sunspec_node_wanted,
        )

        parameter_uuid_to_sunspec_node = {
            node.parameter_uuid: node
            for node in sunspec_nodes_with_parameter_uuid
        }

        lengths_equal = (
            len(can_nodes_with_parameter_uuid)
            == len(parameter_uuid_to_can_node)
        )
        if not lengths_equal:
            raise Exception()

        c = []
        h = []

        for child in parameters.children:
            if not isinstance(
                    child,
                    (
                        epyqlib.pm.parametermodel.Group,
                        epyqlib.pm.parametermodel.Parameter,
                        # epcpm.parametermodel.EnumeratedParameter,
                    ),
            ):
                continue

            c_built, h_built = builders.wrap(
                wrapped=child,
                can_root=self.can_root,
                sunspec_root=self.sunspec_root,
                parameter_uuid_to_can_node=parameter_uuid_to_can_node,
                parameter_uuid_to_sunspec_node=(
                    parameter_uuid_to_sunspec_node
                ),
                parameter_uuid_finder=self.wrapped.model.node_from_uuid,
            ).gen()

            c.extend(c_built)
            h.extend(h_built)

        return c, h

        # return itertools.chain.from_iterable(
        #     builders.wrap(
        #         wrapped=child,
        #         can_root=self.can_root,
        #         sunspec_root=self.sunspec_root,
        #         parameter_uuid_to_can_node=parameter_uuid_to_can_node,
        #         parameter_uuid_to_sunspec_node=(
        #             parameter_uuid_to_sunspec_node
        #         ),
        #         parameter_uuid_finder=self.wrapped.model.node_from_uuid,
        #     ).gen()
        #     for child in parameters.children
        #     if isinstance(
        #         child,
        #         (
        #             epyqlib.pm.parametermodel.Group,
        #             epyqlib.pm.parametermodel.Parameter,
        #             # epcpm.parametermodel.EnumeratedParameter,
        #         ),
        #     )
        # )


@builders(epyqlib.pm.parametermodel.Group)
@attr.s
class Group:
    wrapped = attr.ib()
    can_root = attr.ib()
    sunspec_root = attr.ib()
    parameter_uuid_to_can_node = attr.ib()
    parameter_uuid_to_sunspec_node = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        c = []
        h = []
        for child in self.wrapped.children:
            if not isinstance(
                    child,
                    (
                        epyqlib.pm.parametermodel.Group,
                        epyqlib.pm.parametermodel.Parameter,
                        epyqlib.pm.parametermodel.Table,
                        # epcpm.parametermodel.EnumeratedParameter,
                    ),
            ):
                continue

            c_built, h_built = builders.wrap(
                wrapped=child,
                can_root=self.can_root,
                sunspec_root=self.sunspec_root,
                parameter_uuid_to_can_node=(
                    self.parameter_uuid_to_can_node
                ),
                parameter_uuid_to_sunspec_node=(
                    self.parameter_uuid_to_sunspec_node
                ),
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()

            c.extend(c_built)
            h.extend(h_built)

        return c, h
        # return itertools.chain.from_iterable(
        #     result
        #     for result in (
        #         builders.wrap(
        #             wrapped=child,
        #             can_root=self.can_root,
        #             sunspec_root=self.sunspec_root,
        #             parameter_uuid_to_can_node=(
        #                 self.parameter_uuid_to_can_node
        #             ),
        #             parameter_uuid_to_sunspec_node=(
        #                 self.parameter_uuid_to_sunspec_node
        #             ),
        #             parameter_uuid_finder=self.parameter_uuid_finder,
        #         ).gen()
        #         for child in self.wrapped.children
        #         if isinstance(
        #             child,
        #             (
        #                 epyqlib.pm.parametermodel.Group,
        #                 epyqlib.pm.parametermodel.Parameter,
        #                 # epcpm.parametermodel.EnumeratedParameter,
        #             ),
        #         )
        #     )
        # )


@builders(epyqlib.pm.parametermodel.Parameter)
@attr.s
class Parameter:
    wrapped = attr.ib()
    can_root = attr.ib()
    sunspec_root = attr.ib()
    parameter_uuid_to_can_node = attr.ib()
    parameter_uuid_to_sunspec_node = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        parameter = self.wrapped
        can_signal = self.parameter_uuid_to_can_node.get(parameter.uuid)
        sunspec_point = self.parameter_uuid_to_sunspec_node.get(parameter.uuid)

        uses_interface_item = (
            isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
            and parameter.uses_interface_item()
        )

        if not uses_interface_item:
            return [[], []]

        scale_factor_variable = 'NULL'
        scale_factor_updater = 'NULL'

        if parameter.internal_variable is not None:
            var_or_func = 'variable'
            if parameter.setter_function is None:
                setter_function = 'NULL'
            else:
                setter_function = parameter.setter_function

            variable_or_getter_setter = [
                f'.variable = &{parameter.internal_variable},',
                f'.setter = {setter_function},',
            ]
        else:
            var_or_func = 'functions'
            variable_or_getter_setter = [
                f'.getter = {parameter.getter_function},',
                f'.setter = {parameter.setter_function},',
            ]

        if sunspec_point is None:
            sunspec_variable = 'NULL'
            sunspec_getter = 'NULL'
            sunspec_setter = 'NULL'
            hand_coded_sunspec_getter_function = 'NULL'
            hand_coded_sunspec_setter_function = 'NULL'
        else:
            model_id = sunspec_point.tree_parent.tree_parent.id
            # TODO: move this somewhere common in python code...
            sunspec_type = {
                'uint16': 'sunsU16',
                'enum16': 'sunsU16',
                'int16': 'sunsS16',
                'uint32': 'sunsU32',
                'int32': 'sunsS32',
            }[self.parameter_uuid_finder(sunspec_point.type_uuid).name]

            # TODO: handle tables with repeating blocks and references

            sunspec_scale_factor = None
            if sunspec_point.factor_uuid is not None:
                factor_point = self.sunspec_root.model.node_from_uuid(sunspec_point.factor_uuid)
                sunspec_scale_factor = self.parameter_uuid_finder(factor_point.parameter_uuid).abbreviation

            hand_coded_getter_function_name = epcpm.sunspectoxlsx.getter_name(
                parameter=parameter,
                model_id=model_id,
                is_table=False,
            )

            hand_coded_setter_function_name = epcpm.sunspectoxlsx.setter_name(
                parameter=parameter,
                model_id=model_id,
                is_table=False,
            )

            if sunspec_point.hand_coded_getter:
                hand_coded_sunspec_getter_function = (
                    f'&{hand_coded_getter_function_name}'
                )
            else:
                hand_coded_sunspec_getter_function = 'NULL'

            if sunspec_point.hand_coded_setter:
                hand_coded_sunspec_setter_function = (
                    f'&{hand_coded_setter_function_name}'
                )
            else:
                hand_coded_sunspec_setter_function = 'NULL'

            sunspec_model_variable = f'sunspecInterface.model{model_id}'

            if sunspec_scale_factor is not None:
                scale_factor_variable = (
                    f'&{sunspec_model_variable}.{sunspec_scale_factor}'
                )
                scale_factor_updater_name = (
                    f'getSUNSPEC_MODEL{model_id}_{sunspec_scale_factor}'
                )
                scale_factor_updater = f'&{scale_factor_updater_name}'

            sunspec_variable = (
                f'&{sunspec_model_variable}.{parameter.abbreviation}'
            )

            getter_setter_list = [
                'InterfaceItem',
                var_or_func,
                parameter.internal_type,
                sunspec_type,
            ]

            sunspec_getter = '_'.join(
                str(x)
                for x in getter_setter_list + ['getter']
            )
            sunspec_setter = '_'.join(
                str(x)
                for x in getter_setter_list + ['setter']
            )

        interface_item_type = (
            f'InterfaceItem_{var_or_func}_{parameter.internal_type}'
        )

        can_getter, can_setter, can_variable = can_getter_setter_variable(
            can_signal=can_signal,
            parameter=parameter,
            var_or_func_or_table=var_or_func,
        )

        access_level = get_access_level_string(
            parameter=parameter,
            parameter_uuid_finder=self.parameter_uuid_finder,
        )

        result = create_item(
            item_uuid=parameter.uuid,
            access_level=access_level, 
            can_getter=can_getter, 
            can_setter=can_setter,
            can_variable=can_variable,
            hand_coded_sunspec_getter_function=hand_coded_sunspec_getter_function,
            hand_coded_sunspec_setter_function=hand_coded_sunspec_setter_function,
            interface_item_type=interface_item_type,
            internal_scale=parameter.internal_scale_factor,
            meta_initializer_values=create_meta_initializer_values(parameter),
            parameter=parameter,
            scale_factor_updater=scale_factor_updater, 
            scale_factor_variable=scale_factor_variable,
            sunspec_getter=sunspec_getter, 
            sunspec_setter=sunspec_setter,
            sunspec_variable=sunspec_variable, 
            variable_or_getter_setter=variable_or_getter_setter,
            can_scale_factor=getattr(can_signal, 'factor', None),
        )

        return result


@attr.s(frozen=True)
class FixedWidthType:
    name = attr.ib()
    bits = attr.ib()
    signed = attr.ib()
    minimum_code = attr.ib()
    maximum_code = attr.ib()

    @classmethod
    def build(cls, bits, signed):
        return cls(
            name=fixed_width_name(bits=bits, signed=signed),
            bits=bits,
            signed=signed,
            minimum_code=fixed_width_limit_text(
                bits=bits,
                signed=signed,
                limit='min',
            ),
            maximum_code=fixed_width_limit_text(
                bits=bits,
                signed=signed,
                limit='max',
            ),
        )


@attr.s(frozen=True)
class FloatingType:
    name = attr.ib()
    bits = attr.ib()
    minimum_code = attr.ib()
    maximum_code = attr.ib()

    @classmethod
    def build(cls, bits):
        return cls(
            name={32: 'float', 64: 'double'}[bits],
            bits=bits,
            minimum_code='(-INFINITY)',
            maximum_code='(INFINITY)',
        )


@attr.s(frozen=True)
class BooleanType:
    name = attr.ib(default='bool')
    bits = attr.ib(default=2)
    minimum_code = attr.ib(default='(false)')
    maximum_code = attr.ib(default='(true)')


@attr.s(frozen=True)
class SizeType:
    name = attr.ib(default='size_t')
    bits = attr.ib(default=32)
    minimum_code = attr.ib(default='(0)')
    maximum_code = attr.ib(default='(SIZE_MAX)')


def fixed_width_name(bits, signed):
    if signed:
        u = ''
    else:
        u = 'u'

    return f'{u}int{bits}_t'


def fixed_width_limit_text(bits, signed, limit):
    limits = ('min', 'max')

    if limit not in limits:
        raise Exception(f'Requested limit not found in {list(limits)}: {limit:!r}')

    if not signed and limit == 'min':
        return '(0U)'

    u = '' if signed else 'U'

    return f'({u}INT{bits}_{limit.upper()})'


types = {
    type.name: type
    for type in (
        *(
            FixedWidthType.build(
                bits=bits,
                signed=signed,
            )
            for bits in (8, 16, 32, 64)
            for signed in (False, True)
        ),
        *(
            FloatingType.build(bits=bits)
            for bits in (32, 64)
        ),
        BooleanType(),
        SizeType(),
    )
}


def create_meta_initializer_values(parameter):
    def create_literal(value, type):
        value *= decimal.Decimal(10) ** parameter.internal_scale_factor

        suffix = ''

        if type == 'float':
            suffix = 'f'
            value = float(value)
        elif type == 'bool':
            value = str(bool(value)).lower()
        elif type.startswith('uint'):
            suffix = 'U'
            value = int(round(value))
        else:
            value = int(round(value))

        return str(value) + suffix

    if parameter.default is None:
        meta_default = 0
    else:
        meta_default = parameter.default
    meta_default = create_literal(
        value=meta_default,
        type=parameter.internal_type,
    )

    if parameter.minimum is None:
        meta_minimum = types[parameter.internal_type].minimum_code
    else:
        meta_minimum = parameter.minimum
        meta_minimum = create_literal(
            value=meta_minimum,
            type=parameter.internal_type,
        )

    if parameter.maximum is None:
        meta_maximum = types[parameter.internal_type].maximum_code
    else:
        meta_maximum = parameter.maximum
        meta_maximum = create_literal(
            value=meta_maximum,
            type=parameter.internal_type,
        )

    meta_initializer_values = [
        f'[Meta_UserDefault - 1] = {meta_default},',
        f'[Meta_FactoryDefault - 1] = {meta_default},',
        f'[Meta_Min - 1] = {meta_minimum},',
        f'[Meta_Max - 1] = {meta_maximum}',
    ]
    return meta_initializer_values


def get_access_level_string(parameter, parameter_uuid_finder):
    if parameter.access_level_uuid is not None:
        access_level_name = (
            parameter_uuid_finder(parameter.access_level_uuid).name
        )
    else:
        # TODO: stop defaulting here
        access_level_name = 'User'
    access_level = f'CAN_Enum_AccessLevel_{access_level_name}'
    return access_level


def can_getter_setter_variable(can_signal, parameter, var_or_func_or_table):
    if can_signal is None:
        can_variable = 'NULL'
        can_getter = 'NULL'
        can_setter = 'NULL'

        return can_getter, can_setter, can_variable

    in_table = isinstance(
        can_signal.tree_parent.tree_parent,
        epcpm.canmodel.CanTable,
    )
    if in_table:
        can_variable = (
            f'&{can_signal.tree_parent.tree_parent.tree_parent.name}'
            f'.{can_signal.tree_parent.tree_parent.name}'
            f'{can_signal.tree_parent.name}'
            f'.{can_signal.name}'
        )
    else:
        can_variable = (
            f'&{can_signal.tree_parent.tree_parent.name}'
            f'.{can_signal.tree_parent.name}'
            f'.{can_signal.name}'
        )

    if can_signal.signed:
        can_type = ''
    else:
        can_type = 'u'

    can_type += 'int'

    if can_signal.bits <= 16:
        can_type += '16'
    elif can_signal.bits <= 32:
        can_type += '32'
    else:
        raise Exception('ack')

    can_type += '_t'

    getter_setter_list = [
        'InterfaceItem',
        var_or_func_or_table,
        parameter.internal_type,
        'can',
        can_type,
    ]

    can_getter = '_'.join(
        str(x)
        for x in getter_setter_list + ['getter']
    )
    can_setter = '_'.join(
        str(x)
        for x in getter_setter_list + ['setter']
    )

    return can_getter, can_setter, can_variable


def breakdown_nested_array(s):
    split = re.split(r'\[(.*?)\].', s)

    array_layers = list(toolz.partition(2, split))
    remainder, = split[2 * len(array_layers):]

    return array_layers, remainder


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

    # def sizeof(self, layers, remainder=False):
    #     indexed = self.index(indexes={layer: 0 for layer in layers})

    #     if remainder:
    #         if len(layers) != len(self.array_layers):
    #             raise Exception('Remainder requested without specifying all layers')

    #         indexed += f'.{self.remainder}'

    #     return f'sizeof({indexed})'


@attr.s
class TableBaseStructures:
    uuid = attr.ib()
    array_nests = attr.ib()
    parameter_uuid_to_can_node = attr.ib()
    parameter_uuid_to_sunspec_node = attr.ib()
    parameter_uuid_finder = attr.ib()
    common_structure_names = attr.ib(factory=dict)
    c_code = attr.ib(factory=list)
    h_code = attr.ib(factory=list)

    def ensure_common_structure(
            self,
            internal_type,
            common_initializers,
            meta_initializer,
    ):
        name = self.common_structure_names.get(internal_type)

        if name is None:
            if len(self.h_code) > 0:
                self.h_code.append('')
            if len(self.c_code) > 0:
                self.c_code.append('')

            formatted_uuid = str(self.uuid).replace('-', '_')
            name = (
                f'InterfaceItem_table_common_{internal_type}_{formatted_uuid}'
            )

            nested_array = self.array_nests['x']

            layers = []
            for layer in nested_array.array_layers:
                layer_format_name, = [
                    list(field)[0][1]
                    for field in [string.Formatter().parse(layer[1])]
                ]
                layers.append(layer_format_name)

            variable_base = nested_array.index(
                indexes={
                    layer: 0
                    for layer in layers
                },
            )

            sizes = [
                self.array_nests['x'].sizeof(layers[:i + 1])
                for i in range(len(layers))
            ]

            if len(sizes) == 3:
                zone_size, curve_size, point_size = sizes
            else:
                zone_size = 0
                curve_size, point_size = sizes

            axis_offsets = [
                f'[{index}] = &{variable_base}.{nested_array.remainder} - &{variable_base},'
                for index, nested_array in enumerate(self.array_nests.values())
            ]

            self.common_structure_names[internal_type] = name
            self.h_code.append(
                f'extern InterfaceItem_table_common_{internal_type} {name};',
            )
            self.c_code.extend([
                f'InterfaceItem_table_common_{internal_type} {name} = {{',
                [
                    f'.common = {{',
                    common_initializers,
                    f'}},',
                    f'.variable_base = ({internal_type} *) &{variable_base},',
                    f'.zone_size = {zone_size},',
                    f'.curve_size = {curve_size},',
                    f'.point_size = {point_size},',
                    f'.axis_offsets = {{',
                    axis_offsets,
                    f'}},',
                    f'.meta_values = {{',
                    meta_initializer,
                    f'}},',
                ],
                f'}};',
            ])

        return name

    def create_item(self, table_element, layers):
        # TODO: CAMPid 9655426754319431461354643167
        array_element = table_element.original

        if isinstance(array_element, epyqlib.pm.parametermodel.Parameter):
            parameter = array_element
        else:
            parameter = array_element.tree_parent.children[0]

        if parameter.internal_variable is None:
            return [[], []]

        curve_type = get_curve_type(''.join(layers[:2]))

        curve_index = layers[-2]
        point_index = int(table_element.name.lstrip('_').lstrip('0')) - 1

        access_level = get_access_level_string(
            parameter=parameter,
            parameter_uuid_finder=self.parameter_uuid_finder,
        )

        can_signal = self.parameter_uuid_to_can_node.get(table_element.uuid)

        can_getter, can_setter, can_variable = can_getter_setter_variable(
            can_signal,
            parameter,
            var_or_func_or_table='table',
        )

        common_initializers = create_common_initializers(
            access_level=access_level,
            can_getter=can_getter,
            can_setter=can_setter,
            # not to be used so really hardcode NULL
            can_variable='NULL',
            hand_coded_sunspec_getter_function='NULL',
            hand_coded_sunspec_setter_function='NULL',
            internal_scale=parameter.internal_scale_factor,
            scale_factor_updater='NULL',
            scale_factor_variable='NULL',
            sunspec_getter='NULL',
            sunspec_setter='NULL',
            # not to be used so really hardcode NULL
            sunspec_variable='NULL',
            can_scale_factor=can_signal.factor,
        )

        meta_initializer = create_meta_initializer_values(parameter)

        common_structure_name = self.ensure_common_structure(
            internal_type=parameter.internal_type,
            common_initializers=common_initializers,
            meta_initializer=meta_initializer,
        )

        interface_item_type = (
            f'InterfaceItem_table_{parameter.internal_type}'
        )

        item_uuid_string = str(table_element.uuid).replace('-', '_')
        item_name = f'interfaceItem_{item_uuid_string}'

        remainder = NestedArrays.build(parameter.internal_variable).remainder

        axis_index, = (
            index
            for index, name in enumerate(self.array_nests)
            if name == remainder
        )

        c = [
            f'// {table_element.uuid}',
            f'{interface_item_type} const {item_name} = {{',
            [
                f'.table_common = &{common_structure_name},',
                f'.can_variable = {can_variable},',
                f'.sunspec_variable = NULL,',
                f'.zone = {curve_type if curve_type is not None else "0"},',
                f'.curve = {curve_index},',
                f'.point = {point_index},',
                f'.axis = {axis_index},',
            ],
            '};',
            '',
        ]

        return [
            c,
            [f'extern {interface_item_type} const {item_name};'],
        ]


@builders(epyqlib.pm.parametermodel.Table)
@attr.s
class Table:
    wrapped = attr.ib()
    can_root = attr.ib()
    sunspec_root = attr.ib()
    parameter_uuid_to_can_node = attr.ib()
    parameter_uuid_to_sunspec_node = attr.ib()
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

        # TODO: CAMPid 0795436754762451671643967431
        # TODO: get this from the ...  wherever we have it
        axes = ['x', 'y', 'z']

        array_nests = {
            name: NestedArrays.build(s=array.children[0].internal_variable)
            for name, array in zip(axes, arrays)
        }

        table_base_structures = TableBaseStructures(
            uuid=self.wrapped.uuid,
            array_nests=array_nests,
            parameter_uuid_to_can_node=self.parameter_uuid_to_can_node,
            parameter_uuid_to_sunspec_node=(
                self.parameter_uuid_to_sunspec_node
            ),
            parameter_uuid_finder=self.parameter_uuid_finder,
        )

        item_code = builders.wrap(
            wrapped=group,
            can_root=self.can_root,
            sunspec_root=self.sunspec_root,
            table_base_structures=table_base_structures,
            parameter_uuid_to_can_node=self.parameter_uuid_to_can_node,
            parameter_uuid_to_sunspec_node=(
                self.parameter_uuid_to_sunspec_node
            ),
            parameter_uuid_finder=self.parameter_uuid_finder,
        ).gen()

        return [
            [
                *table_base_structures.c_code,
                '',
                *item_code[0],
            ],
            [
                *table_base_structures.h_code,
                '',
                *item_code[1],
            ],
        ]


@builders(epyqlib.pm.parametermodel.TableGroupElement)
@attr.s
class TableGroupElement:
    wrapped = attr.ib()
    can_root = attr.ib()
    sunspec_root = attr.ib()
    table_base_structures = attr.ib()
    parameter_uuid_to_can_node = attr.ib()
    parameter_uuid_to_sunspec_node = attr.ib()
    parameter_uuid_finder = attr.ib()
    layers = attr.ib(default=[])

    def gen(self):
        c = []
        h = []

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
                can_root=self.can_root,
                sunspec_root=self.sunspec_root,
                table_base_structures=self.table_base_structures,
                parameter_uuid_to_can_node=self.parameter_uuid_to_can_node,
                parameter_uuid_to_sunspec_node=(
                    self.parameter_uuid_to_sunspec_node
                ),
                parameter_uuid_finder=self.parameter_uuid_finder,
                layers=layers,
            ).gen()

            c_built, h_built = result
            c.extend(c_built)
            h.extend(h_built)

        return c, h


# TODO: CAMPid 079549750417808543178043180
def get_curve_type(combination_string):
    # TODO: backmatching
    return {
        'LowRideThrough': 'IEEE1547_CURVE_TYPE_LRT',
        'HighRideThrough': 'IEEE1547_CURVE_TYPE_HRT',
        'LowTrip': 'IEEE1547_CURVE_TYPE_LTRIP',
        'HighTrip': 'IEEE1547_CURVE_TYPE_HTRIP',
    }.get(combination_string)


@builders(epyqlib.pm.parametermodel.TableArrayElement)
@attr.s
class TableArrayElement:
    wrapped = attr.ib()
    can_root = attr.ib()
    sunspec_root = attr.ib()
    table_base_structures = attr.ib()
    layers = attr.ib()
    parameter_uuid_to_can_node = attr.ib()
    parameter_uuid_to_sunspec_node = attr.ib()
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
        return self.table_base_structures.create_item(
            table_element=self.wrapped,
            layers=self.layers,
        )

    def handle_group(self):
        # raise Exception('...')

        table_element = self.wrapped

        curve_index = self.layers[-2]

        parameter = table_element.original

        if parameter.internal_variable is None:
            return [[], []]

        can_signal = self.parameter_uuid_to_can_node.get(table_element.uuid)
        sunspec_point = self.parameter_uuid_to_sunspec_node.get(table_element.uuid)

        access_level = get_access_level_string(
            parameter=table_element,
            parameter_uuid_finder=self.parameter_uuid_finder,
        )

        # axis = table_element.tree_parent.axis

        # if parameter.setter_function is None:
        #     setter_function = 'NULL'
        # else:
        #     setter_function = parameter.setter_function.format(
        #         upper_axis=axis.upper(),
        #     )

        if parameter.setter_function is None:
            setter_function = 'NULL'
        else:
            setter_function = '&' + parameter.setter_function

        curve_type = get_curve_type(''.join(self.layers[:2]))

        internal_variable = parameter.internal_variable.format(
            curve_type=curve_type,
            curve_index=curve_index,
        )

        meta_initializer = create_meta_initializer_values(parameter)

        variable_or_getter_setter = [
            f'.variable = &{internal_variable},',
            f'.setter = {setter_function},',
            f'.meta_values = {{',
            meta_initializer,
            f'}},',
        ]

        # var_or_func = 'variable'

        can_getter, can_setter, can_variable = can_getter_setter_variable(
            can_signal,
            parameter,
            var_or_func_or_table='variable',
        )

        interface_item_type = (
            f'InterfaceItem_variable_{parameter.internal_type}'
        )

        # signal = self.parameter_uuid_to_can_node.get(self.wrapped.uuid)
        #
        # if signal is None:
        #     return None
        #
        # message = signal.tree_parent
        #
        # can_table = message.tree_parent

        # can_getter_setter_base = '_'.join(
        #     'InterfaceItem',
        #     'table',
        #     parameter.internal_type,
        #     'can',
        #     signal.can_interface_type,
        # )

        # can_getter, can_setter, can_variable = can_getter_setter_variable(
        #     can_signal,
        #     parameter,
        #     var_or_func_or_table=var_or_func,
        # )

        result = create_item(
            item_uuid=table_element.uuid,
            access_level=access_level,
            can_getter=can_getter,
            can_setter=can_setter,
            can_variable=can_variable,
            hand_coded_sunspec_getter_function='NULL',
            hand_coded_sunspec_setter_function='NULL',
            interface_item_type=interface_item_type,
            internal_scale=parameter.internal_scale_factor,
            meta_initializer_values=create_meta_initializer_values(parameter),
            parameter=parameter,
            scale_factor_updater='NULL',
            scale_factor_variable='NULL',
            sunspec_getter='NULL',
            sunspec_setter='NULL',
            sunspec_variable='NULL',
            variable_or_getter_setter=variable_or_getter_setter,
            can_scale_factor=getattr(can_signal, 'factor', None),
        )

        return result


def create_item(
        item_uuid,
        access_level,
        can_getter,
        can_setter,
        can_variable,
        hand_coded_sunspec_getter_function,
        hand_coded_sunspec_setter_function,
        interface_item_type,
        internal_scale,
        meta_initializer_values,
        parameter,
        scale_factor_updater,
        scale_factor_variable,
        sunspec_getter,
        sunspec_setter,
        sunspec_variable,
        variable_or_getter_setter,
        can_scale_factor,
):
    item_uuid_string = str(item_uuid).replace('-', '_')
    item_name = f'interfaceItem_{item_uuid_string}'

    if meta_initializer_values is None:
        meta_initializer = []
    else:
        meta_initializer = [
            '.meta_values = {',
            meta_initializer_values,
            '}',
        ]

    common_initializers = create_common_initializers(
        access_level=access_level, 
        can_getter=can_getter, 
        can_setter=can_setter,
        can_variable=can_variable,
        hand_coded_sunspec_getter_function=hand_coded_sunspec_getter_function,
        hand_coded_sunspec_setter_function=hand_coded_sunspec_setter_function,
        internal_scale=internal_scale, 
        scale_factor_updater=scale_factor_updater,
        scale_factor_variable=scale_factor_variable, 
        sunspec_getter=sunspec_getter,
        sunspec_setter=sunspec_setter,
        sunspec_variable=sunspec_variable,
        can_scale_factor=can_scale_factor,
    )

    item = [
        f'// {item_uuid}',
        f'{interface_item_type} const {item_name} = {{',
        [
            '.common = {',
            common_initializers,
            '},',
            *variable_or_getter_setter,
            *meta_initializer,
        ],
        '};',
        '',
    ]

    return [
        item,
        [f'extern {interface_item_type} const {item_name};'],
    ]


def create_common_initializers(
        access_level, 
        can_getter, 
        can_setter, 
        can_variable,
        hand_coded_sunspec_getter_function,
        hand_coded_sunspec_setter_function,
        internal_scale,
        scale_factor_updater, 
        scale_factor_variable, 
        sunspec_getter,
        sunspec_setter, 
        sunspec_variable,
        can_scale_factor,
):
    if can_scale_factor is None:
        # TODO: don't default here?
        can_scale_factor = 1

    common_initializers = [
        f'.sunspecScaleFactor = {scale_factor_variable},',
        f'.canScaleFactor = {float(can_scale_factor)}f,',
        f'.scaleFactorUpdater = {scale_factor_updater},',
        f'.internalScaleFactor = {internal_scale},',
        f'.sunspec = {{',
        [
            f'.variable = {sunspec_variable},',
            f'.getter = {sunspec_getter},',
            f'.setter = {sunspec_setter},',
            f'.handGetter = {hand_coded_sunspec_getter_function},',
            f'.handSetter = {hand_coded_sunspec_setter_function},',
        ],
        f'}},',
        f'.can = {{',
        [
            f'.variable = {can_variable},',
            f'.getter = {can_getter},',
            f'.setter = {can_setter},',
            f'.handGetter = NULL,',
            f'.handSetter = NULL,',
        ],
        f'}},',
        f'.access_level = {access_level},',
    ]
    return common_initializers
