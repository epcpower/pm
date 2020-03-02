import itertools
import math

import attr
import openpyxl

import epyqlib.pm.parametermodel
import epyqlib.utils.general

import epcpm.c
import epcpm.sunspecmodel


builders = epyqlib.utils.general.TypeMap()
enumeration_builders = epyqlib.utils.general.TypeMap()
enumerator_builders = epyqlib.utils.general.TypeMap()


data_point_fields = attr.fields(epcpm.sunspecmodel.DataPoint)
epc_enumerator_fields = attr.fields(
    epyqlib.pm.parametermodel.SunSpecEnumerator,
)
bitfield_fields = attr.fields(epcpm.sunspecmodel.DataPointBitfield)


def attr_fill(cls, value):
    return cls(**{field.name: value for field in attr.fields(cls) if field.init})


@attr.s
class Fields:
    field_type = attr.ib(default=None)
    applicable_point = attr.ib(default=None)
    address_offset = attr.ib(default=None)
    block_offset = attr.ib(default=None)
    size = attr.ib(default=None)
    name = attr.ib(default=None)
    label = attr.ib(default=None)
    value = attr.ib(default=None)
    type = attr.ib(default=None)
    units = attr.ib(default=None)
    scale_factor = attr.ib(default=None)
    read_write = attr.ib(default=None)
    mandatory = attr.ib(default=None)
    description = attr.ib(default=None)
    notes = attr.ib(default=None)
    modbus_address = attr.ib(default=None)
    get = attr.ib(default=None)
    set = attr.ib(default=None)
    item = attr.ib(default=None)

    def as_filtered_tuple(self, filter_):
        return tuple(
            value
            for value, f in zip(attr.astuple(self), attr.astuple(filter_))
            if f
        )


field_names = Fields(
    field_type='Field Type',
    applicable_point='Applicable Point',
    address_offset='Address Offset',
    block_offset='Block Offset',
    size='Size',
    name='Name',
    label='Label',
    value='Value',
    type='Type',
    units='Units',
    scale_factor='SF',
    read_write='R/W',
    mandatory='Mandatory M/O',
    description='Description',
    notes='Notes',
    modbus_address='Modbus Address',
    get='get',
    set='set',
    item='item',
)


point_fields = Fields(
    block_offset=data_point_fields.block_offset,
    size=data_point_fields.size,
    type=data_point_fields.type_uuid,
    scale_factor=data_point_fields.factor_uuid,
    units=data_point_fields.units,
)

bitfield_fields = Fields(
    block_offset=bitfield_fields.block_offset,
    size=bitfield_fields.size,
    type=bitfield_fields.type_uuid,
)

enumerator_fields = Fields(
    name=epc_enumerator_fields.name,
    label=epc_enumerator_fields.label,
    description=epc_enumerator_fields.description,
    notes=epc_enumerator_fields.notes,
    value=epc_enumerator_fields.value,
    field_type=epc_enumerator_fields.type,
)


def export(
        path,
        sunspec_model,
        parameters_model,
        column_filter=None,
        skip_sunspec=False
    ):
    if column_filter is None:
        column_filter = attr_fill(Fields, True)

    builder = epcpm.sunspectoxlsx.builders.wrap(
        wrapped=sunspec_model.root,
        parameter_uuid_finder=sunspec_model.node_from_uuid,
        parameter_model=parameters_model,
        skip_sunspec=skip_sunspec,
        column_filter=column_filter,
    )

    workbook = builder.gen()

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


@builders(epcpm.sunspecmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    column_filter = attr.ib()
    skip_sunspec = attr.ib(default=False)
    parameter_uuid_finder = attr.ib(default=None)
    parameter_model = attr.ib(default=None)

    def gen(self):
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)

        workbook.create_sheet('License Agreement')
        workbook.create_sheet('Summary')
        workbook.create_sheet('Index')

        if not self.skip_sunspec:
            children = sorted(
                self.wrapped.children,
                key=lambda child: (
                    0 if isinstance(child, epcpm.sunspecmodel.Model) else 1,
                    getattr(child, 'id', math.inf),
                )
            )

            model_offset = 2 #account for starting 'SunS'
            for model in children:
                if isinstance(model, epcpm.sunspecmodel.Table):
                    # TODO: for now, implement it soon...
                    continue

                worksheet = workbook.create_sheet()

                model_offset += builders.wrap(
                    wrapped=model,
                    worksheet=worksheet,
                    padding_type=self.parameter_model.list_selection_roots['sunspec types'].child_by_name('pad'),
                    parameter_uuid_finder=self.parameter_uuid_finder,
                    column_filter=self.column_filter,
                    model_offset=model_offset,
                ).gen()

        return workbook


@builders(epcpm.sunspecmodel.Model)
@attr.s
class Model:
    wrapped = attr.ib()
    worksheet = attr.ib()
    padding_type = attr.ib()
    column_filter = attr.ib()
    model_offset = attr.ib() #starting Modbus address for the model
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        self.worksheet.title = str(self.wrapped.id)
        self.worksheet.append(field_names.as_filtered_tuple(self.column_filter))

        self.wrapped.children[0].check_offsets_and_length()

        overall_length = sum(
            child.check_offsets_and_length()
            for child in self.wrapped.children[1:]
        )

        add_padding = (overall_length % 2) == 1
        if add_padding:
            overall_length += 1

        accumulated_length = 0

        rows = []

        model_types = ['Header', 'Fixed Block', 'Repeating Block']

        zipped = zip(enumerate(self.wrapped.children), model_types)
        for (i, child), model_type in zipped:
            builder = builders.wrap(
                wrapped=child,
                add_padding=add_padding and i == 1,
                padding_type=self.padding_type,
                model_type=model_type,
                model_id=self.wrapped.id,
                model_offset=self.model_offset,
                parameter_uuid_finder=self.parameter_uuid_finder,
                address_offset=accumulated_length,
            )

            built_rows, block_length = builder.gen()
            accumulated_length += block_length
            rows.extend(built_rows)

            rows.append(Fields())

        for i, row in enumerate(rows):
            if i == 0:
                row.value = self.wrapped.id
            elif i == 1:
                row.value = overall_length

            self.worksheet.append(row.as_filtered_tuple(self.column_filter))

        for block in self.wrapped.children:
            to_be_handled = isinstance(
                block,
                (
                    epcpm.sunspecmodel.HeaderBlock,
                    epcpm.sunspecmodel.FixedBlock,
                ),
            )
            if not to_be_handled:
                continue

            for point in block.children:
                builder = enumeration_builders.wrap(
                    wrapped=point,
                    point=point,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                )

                rows = builder.gen()

                if len(rows) > 0:
                    for row in rows:
                        self.worksheet.append(
                            row.as_filtered_tuple(self.column_filter)
                        )

                    self.worksheet.append(
                        Fields().as_filtered_tuple(self.column_filter)
                    )

        return overall_length + 2 #add header length


@builders(epcpm.sunspecmodel.Table)
@attr.s
class Table:
    wrapped = attr.ib()
    worksheet = attr.ib()
    padding_type = attr.ib()
    column_filter = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        return []


@enumeration_builders(epcpm.sunspecmodel.DataPoint)
@attr.s
class Enumeration:
    wrapped = attr.ib()
    point = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        rows = []

        enumeration_uuid = getattr(self.wrapped, 'enumeration_uuid', None)
        if enumeration_uuid is None:
            return rows

        enumeration = self.parameter_uuid_finder(enumeration_uuid)

        for enumerator in enumeration.children:
            builder = enumerator_builders.wrap(
                wrapped=enumerator,
                point=self.point,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )
            rows.append(builder.gen())

        return rows


@enumerator_builders(epyqlib.pm.parametermodel.SunSpecEnumerator)
@attr.s
class Enumerator:
    wrapped = attr.ib()
    point = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    # TODO: CAMPid 07397546759269756456100183066795496952476951653
    def gen(self):
        row = Fields()

        for name, field in attr.asdict(enumerator_fields).items():
            if field is None:
                continue

            setattr(row, name, getattr(self.wrapped, field.name))

        parameter = self.parameter_uuid_finder(self.point.parameter_uuid)
        row.applicable_point = parameter.abbreviation

        return row


def build_uuid_scale_factor_dict(points, parameter_uuid_finder):
    scale_factor_from_uuid = {}
    for point in points:
        if point.type_uuid is None:
            continue

        type_node = parameter_uuid_finder(point.type_uuid)

        if type_node is None:
            continue

        if type_node.name == 'sunssf':
            scale_factor_from_uuid[point.uuid] = point

    return scale_factor_from_uuid


@builders(epcpm.sunspecmodel.TableRepeatingBlock)
@builders(epcpm.sunspecmodel.HeaderBlock)
@builders(epcpm.sunspecmodel.FixedBlock)
@attr.s
class Block:
    wrapped = attr.ib()
    add_padding = attr.ib()
    padding_type = attr.ib()
    model_type = attr.ib()
    model_id = attr.ib()
    model_offset = attr.ib()
    address_offset = attr.ib()
    repeating_block_reference = attr.ib(default=None)
    parameter_uuid_finder = attr.ib(default=None)
    is_table = attr.ib(default=False)

    def gen(self):
        # TODO: CAMPid 07548795421667967542697543743987

        scale_factor_from_uuid = build_uuid_scale_factor_dict(
            points=self.wrapped.children,
            parameter_uuid_finder=self.parameter_uuid_finder,
        )

        rows = []

        points = list(self.wrapped.children)

        if self.add_padding:
            point = epcpm.sunspecmodel.DataPoint(
                type_uuid=self.padding_type.uuid,
                block_offset=(
                    self.wrapped.children[-1].block_offset
                    + self.wrapped.children[-1].size
                ),
                size=self.padding_type.value,
            )
            # TODO: ack!  just to get the address offset calculated but
            #       not calling append_child() because i don't want to shove
            #       this into the model.  :[
            point.tree_parent = self.wrapped
            points.append(point)

        summed_increments = 0

        for child in points:
            builder = builders.wrap(
                wrapped=child,
                model_type=self.model_type,
                scale_factor_from_uuid=scale_factor_from_uuid,
                parameter_uuid_finder=self.parameter_uuid_finder,
                model_id=self.model_id,
                model_offset=self.model_offset,
                is_table=self.is_table,
                repeating_block_reference=self.repeating_block_reference,
                address_offset=self.address_offset + summed_increments,
            )
            built_rows, address_offset_increment = builder.gen()
            summed_increments += address_offset_increment
            rows.append(built_rows)

        return rows, summed_increments


@builders(epcpm.sunspecmodel.DataPointBitfield)
@attr.s
class DataPointBitfield:
    wrapped = attr.ib()
    model_type = attr.ib()
    scale_factor_from_uuid = attr.ib()
    parameter_uuid_finder = attr.ib()
    model_id = attr.ib()
    model_offset = attr.ib()
    is_table = attr.ib()
    repeating_block_reference = attr.ib()
    address_offset = attr.ib()

    def gen(self):
        row = Fields()
        row.address_offset = self.address_offset
        row.modbus_address = self.model_offset + self.address_offset
        row.field_type = self.model_type

        for name, field in attr.asdict(bitfield_fields).items():
            if field is None:
                continue

            setattr(row, name, getattr(self.wrapped, field.name))

        if row.type is not None:
            row.type = self.parameter_uuid_finder(row.type).name

        if self.wrapped.parameter_uuid is not None:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

            row.label = parameter.name
            row.name = parameter.abbreviation
            row.notes = '' if parameter.notes is None else parameter.notes
            row.notes = f'{row.notes}  <uuid:{parameter.uuid}>'.strip()

            if row.units is None:
                row.units = parameter.units
            row.description = parameter.comment
            row.read_write = 'R' if parameter.read_only else 'RW'

        uses_interface_item = (
                isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
                and parameter.uses_interface_item()
        )

        getter = []
        setter = []

        # TODO: should we just require that it does and assume etc?
        if uses_interface_item:
            # TODO: CAMPid 9685439641536675431653179671436
            parameter_uuid = str(parameter.uuid).replace('-', '_')
            item_name = f'interfaceItem_{parameter_uuid}'

            getter.extend([
                f'{item_name}.common.sunspec.getter(',
                [
                    f'(InterfaceItem_void *) &{item_name},',
                    f'Meta_Value',
                ],
                f');',
            ])
            setter.extend([
                f'{item_name}.common.sunspec.setter(',
                [
                    f'(InterfaceItem_void *) &{item_name},',
                    f'true,',
                    f'Meta_Value',
                ],
                f');',
            ])

        if len(getter) > 0:
            # TODO: what if write-only?
            row.get = epcpm.c.format_nested_lists(getter)

        if not parameter.read_only:
            row.set = epcpm.c.format_nested_lists(setter)
        else:
            row.set = None

        return row, row.size


@enumeration_builders(epcpm.sunspecmodel.DataPointBitfield)
@attr.s
class DataPointBitfield:
    wrapped = attr.ib()
    point = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        rows = []

        for enumerator in self.wrapped.children:
            builder = enumerator_builders.wrap(
                wrapped=enumerator,
                point=self.point,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )
            rows.append(builder.gen())

        return rows


@enumerator_builders(epcpm.sunspecmodel.DataPointBitfieldMember)
@attr.s
class DataPointBitfieldMember:
    wrapped = attr.ib()
    point = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    # TODO: CAMPid 07397546759269756456100183066795496952476951653
    def gen(self):
        field_parameter = self.parameter_uuid_finder(self.point.parameter_uuid)
        member_parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

        length = self.point.size * 16

        row = Fields(
            field_type=f'bitfield{length}',
            value=self.wrapped.bit_offset,
            applicable_point=field_parameter.abbreviation,
            name=member_parameter.abbreviation,
            label=member_parameter.name,
            description=member_parameter.comment,
            notes=member_parameter.notes,
        )

        return row


@builders(epcpm.sunspecmodel.TableRepeatingBlockReference)
@attr.s
class TableRepeatingBlockReference:
    wrapped = attr.ib()
    add_padding = attr.ib()
    padding_type = attr.ib()
    model_type = attr.ib()
    model_id = attr.ib()
    model_offset = attr.ib()
    address_offset = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        builder = builders.wrap(
            wrapped=self.wrapped.original,
            model_type=self.model_type,
            parameter_uuid_finder=self.parameter_uuid_finder,
            add_padding=self.add_padding,
            padding_type=self.padding_type,
            model_id=self.model_id,
            model_offset=self.model_offset,
            is_table=True,
            repeating_block_reference=self.wrapped,
            address_offset=self.address_offset,
        )

        return builder.gen()


@builders(epcpm.sunspecmodel.DataPoint)
@attr.s
class Point:
    wrapped = attr.ib()
    scale_factor_from_uuid = attr.ib()
    model_type = attr.ib()
    model_id = attr.ib()
    model_offset = attr.ib()
    is_table = attr.ib()
    address_offset = attr.ib()
    repeating_block_reference = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    # TODO: CAMPid 07397546759269756456100183066795496952476951653
    def gen(self):
        row = Fields()
        row.address_offset = self.address_offset
        row.modbus_address = self.model_offset + self.address_offset

        for name, field in attr.asdict(point_fields).items():
            if field is None:
                continue

            setattr(row, name, getattr(self.wrapped, field.name))

        if self.repeating_block_reference is not None:
            target = (
                self.parameter_uuid_finder(self.wrapped.parameter_uuid)
                .original
            )
            is_array_element = isinstance(
                target,
                epyqlib.pm.parametermodel.ArrayParameterElement,
            )
            if is_array_element:
                target = target.tree_parent.children[0]

            references = [
                child
                for child in self.repeating_block_reference.children
                if target.uuid == child.parameter_uuid
            ]
            if len(references) > 0:
                reference, = references

                if reference.factor_uuid is not None:
                    row.scale_factor = self.parameter_uuid_finder(self.parameter_uuid_finder(reference.factor_uuid).parameter_uuid).abbreviation
        else:
            if row.scale_factor is not None:
                row.scale_factor = (
                    self.parameter_uuid_finder(
                        self.scale_factor_from_uuid[row.scale_factor].parameter_uuid).abbreviation
                )

        if row.type is not None:
            row.type = self.parameter_uuid_finder(row.type).name

        row.mandatory = 'M' if self.wrapped.mandatory else 'O'

        if self.wrapped.parameter_uuid is not None:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

            row.label = parameter.name
            row.name = parameter.abbreviation
            row.notes = '' if parameter.notes is None else parameter.notes
            row.notes = f'{row.notes}  <uuid:{parameter.uuid}>'.strip()

            if row.units is None:
                row.units = parameter.units
            row.description = parameter.comment
            row.read_write = 'R' if parameter.read_only else 'RW'

            meta = '[Meta_Value]'

            getter = []
            setter = []

            uses_interface_item = (
                isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
                and parameter.uses_interface_item()
            )

            hand_coded_getter_function_name = getter_name(
                parameter=parameter,
                model_id=self.model_id,
                is_table=self.is_table,
            )

            hand_coded_setter_function_name = setter_name(
                parameter=parameter,
                model_id=self.model_id,
                is_table=self.is_table,
            )

            if not uses_interface_item and not self.wrapped.not_implemented:
                if row.scale_factor is not None:
                    scale_factor_updater_name = (
                        f'getSUNSPEC_MODEL{self.model_id}_{row.scale_factor}'
                    )

                    f = f'{scale_factor_updater_name}();'
                    get_scale_factor = f.format(
                        model_id=self.model_id,
                        abbreviation=row.scale_factor,
                    )
                    getter.append(get_scale_factor)
                    setter.append(get_scale_factor)

                getter.append(f'{hand_coded_getter_function_name}();')

            sunspec_model_variable = f'sunspecInterface.model{self.model_id}'

            sunspec_variable = (
                f'{sunspec_model_variable}.{parameter.abbreviation}'
            )

            if row.type == 'pad':
                getter.append(
                    f'{sunspec_variable} = 0x8000;'
                )
            elif self.wrapped.not_implemented:
                value = {
                    'int16': 'INT16_C(0x8000)',
                    'uint16': 'UINT16_C(0xffff)',
                    'acc16': 'UINT16_C(0x0000)',
                    'enum16': 'UINT16_C(0xffff)',
                    'bitfield16': 'UINT16_C(0xffff)',
                    'int32': 'sunspecInt32ToSS32_returns(INT32_C(0x80000000))',
                    'uint32': 'sunspecUint32ToSSU32_returns(UINT32_C(0xffffffff))',
                    'acc32': 'sunspecUint32ToSSU32_returns(UINT32_C(0x00000000))',
                    'enum32': 'sunspecUint32ToSSU32_returns(UINT32_C(0xffffffff))',
                    'bitfield32': 'sunspecUint32ToSSU32_returns(UINT32_C(0xffffffff))',
                    'ipaddr': 'sunspecUint32ToSSU32_returns(UINT32_C(0x00000000))',
                    'int64': 'sunspecInt64ToSS64_returns(INT64_C(0x8000000000000000))',
                    # yes, acc64 seems to be an int64, not a uint64
                    'acc64': 'sunspecInt64ToSS64_returns(INT64_C(0x0000000000000000))',
                    # 'ipv6addr': 'INT128_C(0x00000000000000000000000000000000)',
                    # 'float32': 'NAN',
                    'sunssf': 'INT16_C(0x8000)',
                    'string': 'UINT16_C(0x0000)',
                }[row.type]
                if row.type == 'string':
                    getter.extend([
                        f'for (size_t i = 0; i < LENGTHOF({sunspec_variable}); i++) {{',
                        [
                            f'{sunspec_variable}[i] = {value};'
                        ],
                        '}',
                    ])
                elif row.type.startswith('bitfield'):
                    getter.append(
                        f'{sunspec_variable}.raw = {value};'
                    )
                    # # below because parsesunspec only detects bitfields
                    # # if they have values
                    # if self.wrapped.enumeration_uuid is not None:
                    #     getter.append(
                    #         f'{sunspec_variable}.raw = {value};'
                    #     )
                    # else:
                    #     getter.append(
                    #         f'*((uint{row.type[-2:]}_t*) &{sunspec_variable})'
                    #         f' = {value};'
                    #     )
                else:
                    getter.append(
                        f'{sunspec_variable} = {value};'
                    )

                setter.append('// point not implemented, do nothing')
            elif parameter.nv_format is not None:
                internal_variable = parameter.nv_format.format(meta)

                # TODO: CAMPid 075780541068182645821856068542023499
                converter = {
                    'uint32': {
                        'get': 'sunspecUint32ToSSU32',
                        'set': 'sunspecSSU32ToUint32',
                    },
                    'int32': {
                        # TODO: add this to embedded?
                        # 'get': 'sunspecInt32ToSSS32',
                        'set': 'sunspecSSS32ToInt32',
                    },
                }.get(row.type)

                if converter is not None:
                    get_converter = converter['get']
                    set_converter = converter['set']

                    get_cast = ''
                    set_cast = ''
                    if parameter.nv_cast:
                        set_cast = f'(__typeof__({internal_variable})) '
                        get_type = {
                            'uint32': 'uint32_t',
                        }[row.type]
                        get_cast = f'({get_type})'

                    getter.extend([
                        f'{get_converter}(',
                        [
                            f'&{sunspec_variable},',
                            f'{get_cast}{internal_variable}',
                        ],
                        ');',
                    ])
                    setter.extend([
                        f'{internal_variable} = {set_cast}{set_converter}(',
                        [
                            f'&{sunspec_variable}',
                        ],
                        ');',
                    ])
                else:
                    getter.append(adjust_assignment(
                        left_hand_side=sunspec_variable,
                        right_hand_side=internal_variable,
                        sunspec_model_variable=sunspec_model_variable,
                        scale_factor=row.scale_factor,
                        internal_scale=parameter.internal_scale_factor,
                        parameter=parameter,
                        factor_operator='*',
                    ))

                    setter.append(adjust_assignment(
                        left_hand_side=internal_variable,
                        right_hand_side=sunspec_variable,
                        sunspec_model_variable=sunspec_model_variable,
                        scale_factor=row.scale_factor,
                        internal_scale=parameter.internal_scale_factor,
                        parameter=parameter,
                        factor_operator='/',
                    ))

                # minimum_variable = parameter.nv_format.format('[Meta_Min]')
                # maximum_variable = parameter.nv_format.format('[Meta_Max]')
            elif uses_interface_item:
                # TODO: CAMPid 9685439641536675431653179671436
                parameter_uuid = str(parameter.uuid).replace('-', '_')
                item_name = f'interfaceItem_{parameter_uuid}'

                getter.extend([
                    f'{item_name}.common.sunspec.getter(',
                    [
                        f'(InterfaceItem_void *) &{item_name},',
                        f'Meta_Value',
                    ],
                    f');',
                ])
                setter.extend([
                    f'{item_name}.common.sunspec.setter(',
                    [
                        f'(InterfaceItem_void *) &{item_name},',
                        f'true,',
                        f'Meta_Value',
                    ],
                    f');',
                ])
            else:
                if getattr(parameter, 'sunspec_getter', None) is not None:
                    getter.append(
                        parameter.sunspec_getter.format(
                            interface=sunspec_variable,
                        )
                    )

                if getattr(parameter, 'sunspec_setter', None) is not None:
                    setter.append(
                        parameter.sunspec_setter.format(
                            interface=sunspec_variable,
                        )
                    )

            row.get = epcpm.c.format_nested_lists(getter)

            if not uses_interface_item and not self.wrapped.not_implemented:
                setter.append(f'{hand_coded_setter_function_name}();')

            if not parameter.read_only:
                row.set = epcpm.c.format_nested_lists(setter)
            else:
                row.set = None

        row.field_type = self.model_type

        if self.parameter_uuid_finder(self.wrapped.type_uuid).name == 'pad':
            row.name = 'Pad'
            row.description = 'Force even alignment'
            row.read_write = 'R'
            row.mandatory = 'O'

        return row, row.size


def adjust_assignment(
        left_hand_side,
        right_hand_side,
        sunspec_model_variable,
        scale_factor,
        internal_scale,
        parameter,
        factor_operator,
):
    if scale_factor is not None:
        scale_factor_variable = f'{sunspec_model_variable}.{scale_factor}'
        # TODO: what about positive scalings?
        # factor = f'(P99_IPOW(-{scale_factor_variable}, 10))'
        # TODO: we really don't want doubles here, do we?
        # factor = f'(pow(10, -{scale_factor_variable}))'

        opposite = '' if factor_operator == '*' else '-'

        right_hand_side = (
            f'(sunspecScale({right_hand_side},'
            f' {opposite}({scale_factor_variable} + {internal_scale})))'
        )

    if parameter.nv_cast:
        right_hand_side = f'((__typeof__({left_hand_side})) {right_hand_side})'

    result = f'{left_hand_side} = {right_hand_side};'

    return result


def getter_setter_name(get_set, parameter, model_id, is_table):
    if is_table:
        table_option = '_{table_option}'
    else:
        table_option = ''

    format_string = (
        '{get_set}SunspecModel{model_id}{table_option}_{abbreviation}'
    )

    return format_string.format(
        get_set=get_set,
        model_id=model_id,
        abbreviation=parameter.abbreviation,
        table_option=table_option,
    )


def getter_name(parameter, model_id, is_table):
    return getter_setter_name(
        get_set='get',
        parameter=parameter,
        model_id=model_id,
        is_table=is_table,
    )


def setter_name(parameter, model_id, is_table):
    return getter_setter_name(
        get_set='set',
        parameter=parameter,
        model_id=model_id,
        is_table=is_table,
    )
