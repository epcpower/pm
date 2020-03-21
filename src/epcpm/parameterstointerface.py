import decimal
import itertools
import os
import string
import re
import uuid

import attr
import jinja2
import toolz

import epyqlib.pm.parametermodel
import epyqlib.utils.general

import epcpm.cantosym
import epcpm.sunspecmodel
import epcpm.sunspectoxlsx

builders = epyqlib.utils.general.TypeMap()


# TODO: move this somewhere common in python code...
sunspec_types = {
    'uint16': 'sunsU16',
    'enum16': 'sunsU16',
    'int16': 'sunsS16',
    'uint32': 'sunsU32',
    'int32': 'sunsS32',
}


class InvalidAccessLevelError(Exception):
    @classmethod
    def build(cls, value, parameter):
        message = (
            f'Invalid access level specified for'
            f' {parameter.name} ({parameter.uuid}): {value}'
        )

        return cls(message)


def export(
        c_path,
        h_path,
        parameters_model,
        can_model,
        sunspec_model,
        skip_sunspec=False,
        include_uuid_in_item=False,
):
    if skip_sunspec:
        sunspec_root = None
    else:
        sunspec_root = sunspec_model.root

    builder = builders.wrap(
        wrapped=parameters_model.root,
        can_root=can_model.root,
        sunspec_root=sunspec_root,
        include_uuid_in_item=include_uuid_in_item,
    )

    if skip_sunspec:
        model_ids = []
    else:
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
            *range(65000, 65010),
            65534,
        ]

    c_path.parent.mkdir(parents=True, exist_ok=True)

    built_c, built_h = builder.gen()

    template_context = {
        'sunspec_interface_gen_headers': (
            f'sunspecInterfaceGen{id}.h'
            for id in model_ids
        ),
        'sunspec_interface_headers': (
            f'sunspecInterface{id:05}.h'
            for id in model_ids
        ),
        'interface_items': epcpm.c.format_nested_lists(
            built_c,
        ).strip(),
        'declarations': epcpm.c.format_nested_lists(built_h).strip(),
    }

    epcpm.c.render(
        source=c_path.with_suffix(f'{c_path.suffix}_pm'),
        destination=c_path,
        context=template_context,
    )

    epcpm.c.render(
        source=h_path.with_suffix(f'{h_path.suffix}_pm'),
        destination=h_path,
        context=template_context,
    )


@builders(epyqlib.pm.parametermodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    can_root = attr.ib()
    sunspec_root = attr.ib()
    include_uuid_in_item = attr.ib()

    def gen(self):
        def can_node_wanted(node):
            if getattr(node, 'parameter_uuid', None) is None:
                return False

            uuids = [
                #CCP Response
                uuid.UUID('39315d58-1ddb-48b9-960c-96e724c89da1'),
                #CCP
                uuid.UUID('983bdc5d-8d4e-4107-a0a0-983f0ab101ce'),
            ]
            return not any(ancestor.uuid in uuids for ancestor in node.ancestors())

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

            wanted_types = (
                epcpm.sunspecmodel.DataPoint,
                epcpm.sunspecmodel.DataPointBitfieldMember,
            )
            if not isinstance(node, wanted_types):
                return False

            return True

        if self.sunspec_root is None:
            parameter_uuid_to_sunspec_node = {}
        else:
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
            uuids = [u.parameter_uuid for u in can_nodes_with_parameter_uuid]
            print('\n'.join(set(str(u) for u in uuids if uuids.count(u) > 1)))
            raise Exception()

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
                include_uuid_in_item=self.include_uuid_in_item,
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
    include_uuid_in_item = attr.ib()
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
                include_uuid_in_item=self.include_uuid_in_item,
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


@builders(epcpm.sunspecmodel.DataPoint)
@attr.s
class DataPoint:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()

    def interface_variable_name(self):
        parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

        maybe_model = self.wrapped.tree_parent

        while not isinstance(maybe_model, epcpm.sunspecmodel.Model):
            maybe_model = maybe_model.tree_parent

        model = maybe_model
        model_variable = f'sunspecInterface.model{model.id}'

        return f'&{model_variable}.{parameter.abbreviation}'


@builders(epcpm.sunspecmodel.DataPointBitfieldMember)
@attr.s
class DataPointBitfieldMember:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()

    def interface_variable_name(self):
        parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

        uuid_ = str(parameter.uuid).replace('-', '_')
        return f'&interfaceItem_variable_{uuid_}'


@builders(epyqlib.pm.parametermodel.Parameter)
@attr.s
class Parameter:
    wrapped = attr.ib()
    can_root = attr.ib()
    sunspec_root = attr.ib()
    include_uuid_in_item = attr.ib()
    parameter_uuid_to_can_node = attr.ib()
    parameter_uuid_to_sunspec_node = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        parameter = self.wrapped
        can_signal = self.parameter_uuid_to_can_node.get(parameter.uuid)
        sunspec_point = self.parameter_uuid_to_sunspec_node.get(parameter.uuid)

        interface_data = [
            can_signal,
            sunspec_point,
        ]

        uses_interface_item = (
            isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
            and parameter.uses_interface_item()
        )

        if not uses_interface_item or all(x is None for x in interface_data):
            return [[], []]

        scale_factor_variable = 'NULL'
        scale_factor_updater = 'NULL'

        if parameter.getter_function is None:
            getter_function = 'NULL'
        else:
            getter_function = parameter.getter_function

        if parameter.setter_function is None:
            setter_function = 'NULL'
        else:
            setter_function = parameter.setter_function

        if parameter.internal_variable is not None:
            var_or_func = 'variable'

            variable_or_getter_setter = [
                f'.variable = &{parameter.internal_variable},',
            ]
        else:
            var_or_func = 'functions'

            variable_or_getter_setter = [
                f'.getter = {getter_function},',
            ]

        variable_or_getter_setter.append(f'.setter = {setter_function},')

        if sunspec_point is None:
            sunspec_variable = 'NULL'
            sunspec_getter = 'NULL'
            sunspec_setter = 'NULL'
            hand_coded_sunspec_getter_function = 'NULL'
            hand_coded_sunspec_setter_function = 'NULL'
        else:
            maybe_model = sunspec_point.tree_parent

            while not isinstance(maybe_model, epcpm.sunspecmodel.Model):
                maybe_model = maybe_model.tree_parent

            model = maybe_model

            # TODO: move this somewhere common in python code...
            sunspec_type = sunspec_types[
                self.parameter_uuid_finder(sunspec_point.type_uuid).name
            ]

            # TODO: handle tables with repeating blocks and references

            hand_coded_getter_function_name = epcpm.sunspectoxlsx.getter_name(
                parameter=parameter,
                model_id=model.id,
                is_table=False,
            )

            hand_coded_setter_function_name = epcpm.sunspectoxlsx.setter_name(
                parameter=parameter,
                model_id=model.id,
                is_table=False,
            )

            if getattr(sunspec_point, 'hand_coded_getter', False):
                hand_coded_sunspec_getter_function = (
                    f'&{hand_coded_getter_function_name}'
                )
            else:
                hand_coded_sunspec_getter_function = 'NULL'

            if getattr(sunspec_point, 'hand_coded_setter', False):
                hand_coded_sunspec_setter_function = (
                    f'&{hand_coded_setter_function_name}'
                )
            else:
                hand_coded_sunspec_setter_function = 'NULL'

            # TODO: CAMPid 67549654267913467967436
            if getattr(sunspec_point, 'factor_uuid', False):
                factor_point = self.sunspec_root.model.node_from_uuid(
                    sunspec_point.factor_uuid,
                )
                sunspec_scale_factor = self.parameter_uuid_finder(
                    factor_point.parameter_uuid,
                ).abbreviation

                sunspec_factor_builder = builders.wrap(
                    wrapped=factor_point,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                )
                scale_factor_variable = sunspec_factor_builder.interface_variable_name()
                scale_factor_updater_name = (
                    f'getSUNSPEC_MODEL{model.id}_{sunspec_scale_factor}'
                )
                scale_factor_updater = f'&{scale_factor_updater_name}'

            sunspec_point_builder = builders.wrap(
                wrapped=sunspec_point,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )
            sunspec_variable = sunspec_point_builder.interface_variable_name()

            # TODO: CAMPid 9675436715674367943196954756419543975314
            getter_setter_list = [
                'InterfaceItem',
                var_or_func,
                types[parameter.internal_type].name,
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
            f'InterfaceItem_{var_or_func}_{types[parameter.internal_type].name}'
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

        if parameter.rejected_callback is None:
            rejected_callback = 'NULL'
        else:
            rejected_callback = f'&{parameter.rejected_callback}'

        result = create_item(
            item_uuid=parameter.uuid,
            include_uuid_in_item=self.include_uuid_in_item,
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
            rejected_callback=rejected_callback,
            can_scale_factor=getattr(can_signal, 'factor', None),
            reject_from_inactive_interfaces=parameter.reject_from_inactive_interfaces,
        )

        return result


@attr.s(frozen=True)
class FixedWidthType:
    name = attr.ib()
    type = attr.ib()
    bits = attr.ib()
    signed = attr.ib()
    minimum_code = attr.ib()
    maximum_code = attr.ib()

    @classmethod
    def build(cls, bits, signed):
        return cls(
            name=fixed_width_name(bits=bits, signed=signed),
            type=fixed_width_name(bits=bits, signed=signed),
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
    type = attr.ib()
    bits = attr.ib()
    minimum_code = attr.ib()
    maximum_code = attr.ib()

    @classmethod
    def build(cls, bits):
        return cls(
            name={32: 'float', 64: 'double'}[bits],
            type={32: 'float', 64: 'double'}[bits],
            bits=bits,
            minimum_code='(-INFINITY)',
            maximum_code='(INFINITY)',
        )


@attr.s(frozen=True)
class BooleanType:
    name = attr.ib(default='bool')
    type = attr.ib(default='bool')
    bits = attr.ib(default=2)
    minimum_code = attr.ib(default='(false)')
    maximum_code = attr.ib(default='(true)')


@attr.s(frozen=True)
class SizeType:
    name = attr.ib(default='size_t')
    type = attr.ib(default='size_t')
    bits = attr.ib(default=32)
    minimum_code = attr.ib(default='(0)')
    maximum_code = attr.ib(default='(SIZE_MAX)')


@attr.s(frozen=True)
class VoidPointerType:
    name = attr.ib(default='void_p')
    type = attr.ib(default='void*')
    minimum_code = attr.ib(default='(0)')
    maximum_code = attr.ib(default='(UINT32_C(0x240000))')


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
    type.type: type
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
        VoidPointerType(),
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
    access_level_uuid = parameter.access_level_uuid

    try:
        access_level = parameter_uuid_finder(access_level_uuid)
    except epyqlib.attrsmodel.NotFoundError as e:
        raise InvalidAccessLevelError.build(
            value=access_level_uuid,
            parameter=parameter,
        ) from e

    access_level = f'CAN_Enum_AccessLevel_{access_level.name}'

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
        types[parameter.internal_type].name,
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


# TODO: CAMPid 68945967541316743769675426795146379678431
def breakdown_nested_array(s):
    split = re.split(r'\[(.*?)\].', s)

    array_layers = list(toolz.partition(2, split))
    remainder, = split[2 * len(array_layers):]

    return array_layers, remainder


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

    # def sizeof(self, layers, remainder=False):
    #     indexed = self.index(indexes={layer: 0 for layer in layers})

    #     if remainder:
    #         if len(layers) != len(self.array_layers):
    #             raise Exception('Remainder requested without specifying all layers')

    #         indexed += f'.{self.remainder}'

    #     return f'sizeof({indexed})'


@attr.s
class TableBaseStructures:
    array_nests = attr.ib()
    parameter_uuid_to_can_node = attr.ib()
    parameter_uuid_to_sunspec_node = attr.ib()
    parameter_uuid_finder = attr.ib()
    include_uuid_in_item = attr.ib()
    common_structure_names = attr.ib(factory=dict)
    c_code = attr.ib(factory=list)
    h_code = attr.ib(factory=list)

    def ensure_common_structure(
            self,
            internal_type,
            internal_name,
            parameter_uuid,
            remainder,
            common_initializers,
            meta_initializer,
            setter,
    ):
        name = self.common_structure_names.get(parameter_uuid)

        if name is None:
            if len(self.h_code) > 0:
                self.h_code.append('')
            if len(self.c_code) > 0:
                self.c_code.append('')

            formatted_uuid = str(parameter_uuid).replace('-', '_')
            name = (
                f'InterfaceItem_table_common_{internal_type}_{formatted_uuid}'
            )

            if remainder is None:
                sizes = {}
                full_base_variable = 'NULL'
            else:
                nested_array = self.array_nests[remainder]

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

                sizes = {
                    layer: nested_array.sizeof(layers[:i + 1])
                    for i, layer in enumerate(layers)
                }

                full_base_variable = f'&{variable_base}.{remainder}'

            self.common_structure_names[parameter_uuid] = name
            self.h_code.append(
                f'extern InterfaceItem_table_common_{internal_name} {name};',
            )
            self.c_code.extend([
                f'#pragma DATA_SECTION({name}, "Interface")',
                f'// {parameter_uuid}',
                f'InterfaceItem_table_common_{internal_type} const {name} = {{',
                [
                    f'.common = {{',
                    common_initializers,
                    f'}},',
                    f'.variable_base = {full_base_variable},',
                    f'.setter = {"NULL" if setter is None else setter},',
                    f'.zone_size = {sizes.get("curve_type", 0)},',
                    f'.curve_size = {sizes.get("curve_index", 0)},',
                    f'.point_size = {sizes.get("point_index", 0)},',
                    f'.meta_values = {{',
                    meta_initializer,
                    f'}},',
                ],
                f'}};',
            ])

        return name

    def create_item(self, table_element, layers, sunspec_point):
        # TODO: CAMPid 9655426754319431461354643167
        array_element = table_element.original

        if isinstance(array_element, epyqlib.pm.parametermodel.Parameter):
            parameter = array_element
        else:
            parameter = array_element.tree_parent.children[0]

        uses_interface_item = (
            isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
            and parameter.uses_interface_item()
        )

        if not uses_interface_item:
            return [[], []]

        curve_type = get_curve_type(''.join(layers[:2]))

        curve_index = int(layers[-2])
        try:
            point_index = int(table_element.name.lstrip('_').lstrip('0')) - 1
        except ValueError:
            point_index = None

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

        if can_signal is None:
            can_factor = 1
        else:
            can_factor = can_signal.factor

        # TODO: CAMPid 954679654745154274579654265294624765247569765479
        sunspec_getter = 'NULL'
        sunspec_setter = 'NULL'
        sunspec_variable = 'NULL'
        scale_factor_variable = 'NULL'
        scale_factor_updater = 'NULL'

        if sunspec_point is not None:
            sunspec_type = sunspec_types[
                self.parameter_uuid_finder(sunspec_point.type_uuid).name
            ]

            # TODO: CAMPid 9675436715674367943196954756419543975314
            getter_setter_list = [
                'InterfaceItem',
                'table',
                types[parameter.internal_type].name,
                'sunspec',
                sunspec_type,
            ]

            node_in_model = get_sunspec_point_from_table_element(
                sunspec_point=sunspec_point,
                table_element=table_element,
            )

            if node_in_model is not None:
                model_id = node_in_model.tree_parent.tree_parent.id
                sunspec_model_variable = f'sunspecInterface.model{model_id}'
                abbreviation = table_element.abbreviation
                sunspec_variable = (
                    f'&{sunspec_model_variable}'
                    f'.Curve_{curve_index + 1:>02}_{abbreviation}'
                )

                sunspec_getter = '_'.join(
                    str(x)
                    for x in getter_setter_list + ['getter']
                )
                sunspec_setter = '_'.join(
                    str(x)
                    for x in getter_setter_list + ['setter']
                )

            # TODO: CAMPid 67549654267913467967436
            sunspec_scale_factor = None
            factor_uuid = None
            if node_in_model is not None:
                if node_in_model.factor_uuid is not None:
                    factor_uuid = node_in_model.factor_uuid

            if factor_uuid is not None:
                root = node_in_model.find_root()
                factor_point = root.model.node_from_uuid(
                    node_in_model.factor_uuid,
                )
                sunspec_scale_factor_node = self.parameter_uuid_finder(
                    factor_point.parameter_uuid,
                )
                sunspec_scale_factor = sunspec_scale_factor_node.abbreviation

            if sunspec_scale_factor is not None:
                scale_factor_variable = (
                    f'&{sunspec_model_variable}.{sunspec_scale_factor}'
                )
                scale_factor_updater_name = (
                    f'getSUNSPEC_MODEL{model_id}_{sunspec_scale_factor}'
                )
                scale_factor_updater = f'&{scale_factor_updater_name}'

        common_initializers = create_common_initializers(
            access_level=access_level,
            can_getter=can_getter,
            can_setter=can_setter,
            # not to be used so really hardcode NULL
            can_variable='NULL',
            hand_coded_sunspec_getter_function='NULL',
            hand_coded_sunspec_setter_function='NULL',
            internal_scale=parameter.internal_scale_factor,
            scale_factor_updater=scale_factor_updater,
            scale_factor_variable=scale_factor_variable,
            sunspec_getter=sunspec_getter,
            sunspec_setter=sunspec_setter,
            # not to be used so really hardcode NULL
            sunspec_variable='NULL',
            can_scale_factor=can_factor,
            reject_from_inactive_interfaces=(
                parameter.reject_from_inactive_interfaces
            ),
            uuid_=table_element.uuid,
            include_uuid_in_item=self.include_uuid_in_item,
        )

        meta_initializer = create_meta_initializer_values(parameter)

        if parameter.internal_variable is None:
            remainder = None
        else:
            remainder = NestedArrays.build(parameter.internal_variable).remainder

        common_structure_name = self.ensure_common_structure(
            internal_type=parameter.internal_type,
            internal_name=types[parameter.internal_type].name,
            parameter_uuid=parameter.uuid,
            remainder=remainder,
            common_initializers=common_initializers,
            meta_initializer=meta_initializer,
            setter=parameter.setter_function,
        )

        interface_item_type = (
            f'InterfaceItem_table_{types[parameter.internal_type].name}'
        )

        item_uuid_string = str(table_element.uuid).replace('-', '_')
        item_name = f'interfaceItem_{item_uuid_string}'

        maybe_uuid = []
        if self.include_uuid_in_item:
            maybe_uuid = [f'.uuid = {uuid_initializer(table_element.uuid)},']

        c = [
            f'#pragma DATA_SECTION({item_name}, "Interface")',
            f'// {table_element.uuid}',
            f'{interface_item_type} const {item_name} = {{',
            [
                f'.table_common = &{common_structure_name},',
                f'.can_variable = {can_variable},',
                f'.sunspec_variable = {sunspec_variable},',
                f'.zone = {curve_type if curve_type is not None else "0"},',
                f'.curve = {curve_index},',
                f'.point = {0 if point_index is None else point_index},',
                *maybe_uuid,
            ],
            '};',
            '',
        ]

        return [
            c,
            [f'extern {interface_item_type} const {item_name};'],
        ]


# TODO: CAMPid 3078980986754174316996743174316967431
def get_sunspec_point_from_table_element(sunspec_point, table_element):
    value = table_element.original

    if isinstance(value, epyqlib.pm.parametermodel.ArrayParameterElement):
        value = value.original

    value = value.uuid

    nodes_in_model = [
        node
        for node in sunspec_point.find_root().nodes_by_attribute(
            attribute_value=value,
            attribute_name='parameter_uuid',
            raise_=False,
        )
        if isinstance(
            node,
            epcpm.sunspecmodel.TableRepeatingBlockReferenceDataPointReference,
        )
    ]

    for node in nodes_in_model:
        for child in node.tree_parent.original.children:
            if child.parameter_uuid == sunspec_point.parameter_uuid:
                node_in_model = node
                break
        else:
            continue

        break
    else:
        node_in_model = None
    return node_in_model


# TODO: CAMPid 3078980986754174316996743174316967431
def get_sunspec_model_from_table_group_element(sunspec_point, table_element):
    nodes_in_model = [
        node
        for node in sunspec_point.find_root().nodes_by_attribute(
            attribute_value=table_element.uuid,
            attribute_name='parameter_uuid',
            raise_=False,
        )
        if isinstance(node, epcpm.sunspecmodel.DataPoint)
    ]

    for node in nodes_in_model:
        for child in node.tree_parent.children:
            if child.parameter_uuid == table_element.uuid:
                node_in_model = node
                break
        else:
            continue

        break
    else:
        return None

    model_repeating_block, = [
        node
        for node in sunspec_point.find_root().nodes_by_attribute(
            attribute_value=node_in_model.tree_parent,
            attribute_name='original',
            raise_=False,
        )
        if isinstance(node, epcpm.sunspecmodel.TableRepeatingBlockReference)
    ]

    return model_repeating_block.tree_parent


@builders(epyqlib.pm.parametermodel.Table)
@attr.s
class Table:
    wrapped = attr.ib()
    can_root = attr.ib()
    sunspec_root = attr.ib()
    include_uuid_in_item = attr.ib()
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

        groups = [
            child
            for child in self.wrapped.children
            if isinstance(child, epyqlib.pm.parametermodel.Group)
        ]

        non_arrays = list(itertools.chain.from_iterable(group.children for group in groups))

        # TODO: CAMPid 0795436754762451671643967431
        # TODO: get this from the ...  wherever we have it
        axes = ['x', 'y', 'z']

        array_nests = {
            name: NestedArrays.build(s=array.children[0].internal_variable)
            for name, array in zip(axes, arrays)
        }

        non_array_nests = [
            NestedArrays.build(s=non_array.internal_variable)
            for non_array in non_arrays
            if non_array.internal_variable is not None
        ]
        non_array_nests = {
            nest.remainder: nest
            for nest in non_array_nests
        }

        table_base_structures = TableBaseStructures(
            array_nests={**array_nests, **non_array_nests},
            parameter_uuid_to_can_node=self.parameter_uuid_to_can_node,
            parameter_uuid_to_sunspec_node=(
                self.parameter_uuid_to_sunspec_node
            ),
            parameter_uuid_finder=self.parameter_uuid_finder,
            include_uuid_in_item=self.include_uuid_in_item,
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
            include_uuid_in_item=self.include_uuid_in_item,
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
    include_uuid_in_item = attr.ib()
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
                include_uuid_in_item=self.include_uuid_in_item,
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
    include_uuid_in_item = attr.ib()
    parameter_uuid_to_can_node = attr.ib()
    parameter_uuid_to_sunspec_node = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        table_element = self.wrapped
        zone_node = table_element.tree_parent.tree_parent.tree_parent
        curve_node = zone_node.children[0]
        parameter = curve_node.descendent(
            self.wrapped.tree_parent.name,
            self.wrapped.name,
        )

        sunspec_point = self.parameter_uuid_to_sunspec_node.get(parameter.uuid)

        return self.table_base_structures.create_item(
            table_element=self.wrapped,
            layers=self.layers,
            sunspec_point=sunspec_point,
        )


def create_item(
        item_uuid,
        include_uuid_in_item,
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
        rejected_callback,
        can_scale_factor,
        reject_from_inactive_interfaces,
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
        reject_from_inactive_interfaces=reject_from_inactive_interfaces,
        uuid_=item_uuid,
        include_uuid_in_item=include_uuid_in_item,
    )

    item = [
        f'#pragma DATA_SECTION({item_name}, "Interface")',
        f'// {item_uuid}',
        f'{interface_item_type} const {item_name} = {{',
        [
            '.common = {',
            common_initializers,
            '},',
            *variable_or_getter_setter,
            f'.rejectedCallback = {rejected_callback},',
            *meta_initializer,
        ],
        '};',
        '',
    ]

    return [
        item,
        [f'extern {interface_item_type} const {item_name};'],
    ]


def uuid_initializer(uuid_):
    return '{{{}}}'.format(
        ', '.join(
            '0x{:02x}{:02x}'.format(high, low)
            for low, high in toolz.partition_all(2, uuid_.bytes)
        ),
    )


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
        reject_from_inactive_interfaces,
        uuid_,
        include_uuid_in_item,
):
    if can_scale_factor is None:
        # TODO: don't default here?
        can_scale_factor = 1

    maybe_uuid = []
    if include_uuid_in_item:
        maybe_uuid = [f'.uuid = {uuid_initializer(uuid_)},']

    reject_from_inactive_interfaces_literal = (
        'true'
        if reject_from_inactive_interfaces
        else 'false'
    )

    common_initializers = [
        f'.sunspecScaleFactor = {scale_factor_variable},',
        f'.canScaleFactor = {float(can_scale_factor)}f,',
        f'.scaleFactorUpdater = {scale_factor_updater},',
        f'.internalScaleFactor = {internal_scale},',
        f'.rejectFromInactiveInterface = {reject_from_inactive_interfaces_literal},',
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
        *maybe_uuid,
    ]
    return common_initializers
