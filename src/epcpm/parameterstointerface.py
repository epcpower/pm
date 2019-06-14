import decimal

import attr

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
        )

        return result


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
        meta_minimum = 0
    else:
        meta_minimum = parameter.minimum
    meta_minimum = create_literal(
        value=meta_minimum,
        type=parameter.internal_type,
    )
    if parameter.maximum is None:
        meta_maximum = 0
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

        return builders.wrap(
            wrapped=group,
            can_root=self.can_root,
            sunspec_root=self.sunspec_root,
            parameter_uuid_to_can_node=self.parameter_uuid_to_can_node,
            parameter_uuid_to_sunspec_node=(
                self.parameter_uuid_to_sunspec_node
            ),
            parameter_uuid_finder=self.parameter_uuid_finder,
        ).gen()


@builders(epyqlib.pm.parametermodel.TableGroupElement)
@attr.s
class TableGroupElement:
    wrapped = attr.ib()
    can_root = attr.ib()
    sunspec_root = attr.ib()
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
    layers = attr.ib()
    parameter_uuid_to_can_node = attr.ib()
    parameter_uuid_to_sunspec_node = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        # lineMonitorParams->fMonitorTables[{curve_type}           ].curves[{curve_index}].tbl[{point_index}].x
        # lineMonitorParams->fMonitorTables[IEEE1547_CURVE_TYPE_LRT].curves[0            ].tbl[0            ].x
        # lineMonitorParams->voltWatts.modes[{curve_index}].tbl[{point_index}].{axis};

        table_element = self.wrapped
        array_element = table_element.original

        if isinstance(array_element, epyqlib.pm.parametermodel.Parameter):
            parameter = array_element
        else:
            parameter = array_element.tree_parent.children[0]

        if parameter.setter_function is None:
            return [[], []]

        can_signal = self.parameter_uuid_to_can_node.get(parameter.uuid)
        sunspec_point = self.parameter_uuid_to_sunspec_node.get(parameter.uuid)

        access_level = get_access_level_string(
            parameter=parameter,
            parameter_uuid_finder=self.parameter_uuid_finder,
        )

        axis = table_element.tree_parent.axis

        # if parameter.setter_function is None:
        #     setter_function = 'NULL'
        # else:
        #     setter_function = parameter.setter_function.format(
        #         upper_axis=axis.upper(),
        #     )

        setter_function = parameter.setter_function.format(
            upper_axis=axis.upper(),
        )

        curve_type = get_curve_type(''.join(self.layers[:2]))

        curve_index = self.layers[-2]
        point_index = int(table_element.name.lstrip('_').lstrip('0')) - 1

        internal_variable = parameter.internal_variable.format(
            curve_type=curve_type,
            curve_index=curve_index,
            point_index=point_index,
        )

        variable_or_getter_setter = [
            f'.variable = &{internal_variable},',
            f'.setter = {setter_function},',
            f'.zone = {curve_type if curve_type is not None else "0"},',
            f'.curve = {curve_index},',
            f'.index = {point_index},',
        ]

        # var_or_func = 'variable'

        can_getter, can_setter, can_variable = can_getter_setter_variable(
            can_signal,
            parameter,
            var_or_func_or_table='table',
        )

        interface_item_type = (
            f'InterfaceItem_table_{parameter.internal_type}'
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

    item = [
        f'// {parameter.uuid}',
        f'{interface_item_type} const {item_name} = {{',
        [
            '.common = {',
            [
                f'.sunspecScaleFactor = {scale_factor_variable},',
                f'.canScaleFactor = NULL,',
                f'.scaleFactorUpdater = {scale_factor_updater},',
                # f'.handSunSpecGetterFunction = {hand_coded_getter_function},',
                # f'.handSunSpecSetterFunction = {hand_coded_setter_function},',
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
            ],
            '},',
            # f'.sunspecVariable = {sunspec_variable},',
            *variable_or_getter_setter,
            # f'.getter = {interface_item_type}_getter,',
            # f'.setter = {interface_item_type}_setter,',
            *meta_initializer,
        ],
        '};',
        '',
    ]

    return [
        item,
        [f'extern {interface_item_type} const {item_name};'],
    ]
