from __future__ import (
    annotations,
)  # See PEP 563, check to remove in future Python version higher than 3.7
import attr
import openpyxl
import pathlib
import typing

import epcpm
import epcpm.pm_helper
import epcpm.staticmodbusmodel
import epyqlib.attrsmodel
import epyqlib.pm.parametermodel
import epyqlib.utils.general


builders = epyqlib.utils.general.TypeMap()
enumeration_builders = epyqlib.utils.general.TypeMap()
enumerator_builders = epyqlib.utils.general.TypeMap()

# epc_enumerator_fields = attr.fields(epyqlib.pm.parametermodel.Enumerator)
epc_enumerator_fields = attr.fields(epyqlib.pm.parametermodel.SunSpecEnumerator)

@attr.s
class Fields(epcpm.pm_helper.FieldsInterface):
    """The fields defined for a given row in the output XLS file."""

    modbus_address = attr.ib(default=None, type=typing.Union[str, bool, int])
    name = attr.ib(default=None, type=typing.Union[str, bool])
    label = attr.ib(default=None, type=typing.Union[str, bool])
    size = attr.ib(default=None, type=typing.Union[str, bool, int])
    type = attr.ib(default=None, type=typing.Union[str, bool])
    units = attr.ib(default=None, type=typing.Union[str, bool])
    read_write = attr.ib(default=None, type=typing.Union[str, bool])
    description = attr.ib(default=None, type=typing.Union[str, bool])
    parameter_uses_interface_item = attr.ib(default=False, type=typing.Union[str, bool])
    access_level = attr.ib(default=None, type=typing.Union[str, bool, int])
    min = attr.ib(default=None, type=typing.Union[str, bool, int])
    max = attr.ib(default=None, type=typing.Union[str, bool, int])
    bit_offset = attr.ib(default=None, type=typing.Union[str, bool, int])
    scale_factor = attr.ib(default=None, type=typing.Union[str, bool])


field_names = Fields(
    modbus_address="Modbus Address",
    name="Name",
    label="Label",
    size="Size",
    type="Type",
    units="Units",
    read_write="R/W",
    description="Description",
    parameter_uses_interface_item="Implemented",
    access_level="Access Level",
    min="Min",
    max="Max",
    bit_offset="Bit Offset",
    scale_factor="SF",
)

enumerator_fields = Fields(
    name=epc_enumerator_fields.name,
    # description=epc_enumerator_fields.description,
    # value=epc_enumerator_fields.value
)

def build_uuid_scale_factor_dict(points, parameter_uuid_finder):
    factor_uuid_list = []
    for point in points:
        if type(point) is not epcpm.staticmodbusmodel.FunctionData:
            continue

        if point.factor_uuid is None:
            continue

        factor_uuid_list.append(point.factor_uuid)

    factor_uuid_list = list(set(factor_uuid_list))

    scale_factor_from_uuid = {}
    for point in points:
        type_node = None
        if point.uuid in factor_uuid_list:
            if point.parameter_uuid is not None:
                type_node = parameter_uuid_finder(point.parameter_uuid)

        if type_node is None:
            continue

        scale_factor_from_uuid[point.uuid] = type_node.abbreviation

    return scale_factor_from_uuid

def export(
    path: pathlib.Path,
    staticmodbus_model: epyqlib.attrsmodel.Model,
    parameters_model: epyqlib.attrsmodel.Model,
    column_filter: epcpm.pm_helper.FieldsInterface = None,
    skip_output: bool = False,
) -> None:
    """
    Generate the static modbus model data Excel .xls file.
    Args:
        path: path and filename for .xls file
        staticmodbus_model: static modbus model
        parameters_model: parameters model
        column_filter: columns to be output to .xls file
        skip_output: skip output of the generated files
    Returns:
    """
    if skip_output:
        return

    if column_filter is None:
        column_filter = epcpm.pm_helper.attr_fill(Fields, True)

    builder = epcpm.staticmodbustoxls.builders.wrap(
        wrapped=staticmodbus_model.root,
        parameter_uuid_finder=staticmodbus_model.node_from_uuid,
        parameter_model=parameters_model,
        column_filter=column_filter,
    )

    workbook = builder.gen()

    path.parent.mkdir(parents=True, exist_ok=True)
    workbook.save(path)


@builders(epcpm.staticmodbusmodel.Root)
@attr.s
class Root:
    """Excel spreadsheet generator for the static modbus Root class."""

    wrapped = attr.ib(type=epcpm.staticmodbusmodel.Root)
    column_filter = attr.ib(type=Fields)
    parameter_uuid_finder = attr.ib(default=None, type=typing.Callable)
    parameter_model = attr.ib(default=None, type=epyqlib.attrsmodel.Model)

    def gen(self) -> openpyxl.workbook.workbook.Workbook:
        """
        Excel spreadsheet generator for the static modbus root class.
        Returns:
            workbook: generated Excel workbook
        """
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)
        worksheet = workbook.create_sheet()
        enumeration_worksheet = workbook.create_sheet()
        worksheet.append(field_names.as_filtered_tuple(self.column_filter))
        scale_factor_from_uuid = build_uuid_scale_factor_dict(
            points=self.wrapped.children,
            parameter_uuid_finder=self.parameter_uuid_finder
        )
        for member in self.wrapped.children:
            builder = builders.wrap(
                wrapped=member,
                parameter_uuid_finder=self.parameter_uuid_finder,
                scale_factor_from_uuid=scale_factor_from_uuid
            )
            rows = builder.gen()
            for row in rows:
                worksheet.append(row.as_filtered_tuple(self.column_filter))

        for member in self.wrapped.children:
            builder = enumeration_builders.wrap(
                wrapped=member,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )
            rows = builder.gen()
            for row in rows:
                enumeration_worksheet.append(row.as_filtered_tuple(self.column_filter))

        return workbook

@builders(epcpm.staticmodbusmodel.FunctionData)
@attr.s
class FunctionData:
    """Excel spreadsheet generator for the static modbus FunctionData class."""

    wrapped = attr.ib(type=epcpm.staticmodbusmodel.FunctionData)
    parameter_uuid_finder = attr.ib(type=typing.Callable)
    scale_factor_from_uuid = attr.ib(type=typing.Callable)

    def gen(self) -> typing.List[Fields]:
        """
        Excel spreadsheet generator for the static modbus FunctionData class.
        Returns:
            list: single Fields row of FunctionData
        """
        type_node = self.parameter_uuid_finder(self.wrapped.type_uuid)
        row = Fields()
        row.modbus_address = self.wrapped.address
        row.type = type_node.name
        row.size = self.wrapped.size
        row.units = self.wrapped.units
        if self.wrapped.parameter_uuid is not None:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)
            row.label = parameter.name
            row.name = parameter.abbreviation
            row.description = parameter.comment
            row.read_write = "R" if parameter.read_only else "RW"
            row.min = parameter.minimum
            row.max = parameter.maximum
            uses_interface_item = (
                isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
                and parameter.uses_interface_item()
            )
            row.parameter_uses_interface_item = uses_interface_item
            if parameter.access_level_uuid is not None:
                access_level = self.parameter_uuid_finder(parameter.access_level_uuid)
                row.access_level = access_level.value

            if self.wrapped.uuid in self.scale_factor_from_uuid.keys():
                row.scale_factor = self.scale_factor_from_uuid[self.wrapped.uuid]

        if type_node.name == "pad":
            row.name = "Pad"
            row.description = "Force even alignment"
            row.read_write = "R"

        return [row]


@builders(epcpm.staticmodbusmodel.FunctionDataBitfield)
@attr.s
class FunctionDataBitfield:
    """Excel spreadsheet generator for the static modbus FunctionDataBitfield class."""

    wrapped = attr.ib(type=epcpm.staticmodbusmodel.FunctionDataBitfield)
    parameter_uuid_finder = attr.ib(type=typing.Callable)
    scale_factor_from_uuid = attr.ib(type=typing.Callable)

    def gen(self) -> typing.List[Fields]:
        """
        Excel spreadsheet generator for the static modbus FunctionDataBitfield class.
        Call to generate the FunctionDataBitfieldMember children.
        Returns:
            list: list of Fields rows for FunctionDataBitfield and FunctionDataBitfieldMember
        """
        rows = []
        row = Fields()
        parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)
        row.modbus_address = self.wrapped.address
        row.size = self.wrapped.size
        row.label = parameter.name
        row.name = parameter.abbreviation
        row.description = parameter.comment
        row.read_write = "R" if parameter.read_only else "RW"
        rows.append(row)

        for member in self.wrapped.children:
            builder = builders.wrap(
                wrapped=member,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )
            member_row = builder.gen()
            member_row.modbus_address = (
                self.wrapped.address
            )
            rows.append(member_row)

        return rows


@builders(epcpm.staticmodbusmodel.FunctionDataBitfieldMember)
@attr.s
class FunctionDataBitfieldMember:
    """Excel spreadsheet generator for the static modbus FunctionDataBitfieldMember class."""

    wrapped = attr.ib(type=epcpm.staticmodbusmodel.FunctionDataBitfield)
    parameter_uuid_finder = attr.ib(type=typing.Callable)

    def gen(self) -> Fields:
        """
        Excel spreadsheet generator for the static modbus FunctionDataBitfieldMember class.
        Returns:
            row: Fields row for a FunctionDataBitfieldMember
        """
        row = Fields()
        type_node = self.parameter_uuid_finder(self.wrapped.type_uuid)
        row.type = type_node.name
        row.size = self.wrapped.bit_length
        row.bit_offset = self.wrapped.bit_offset
        if self.wrapped.parameter_uuid is not None:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)
            row.label = parameter.name
            row.name = parameter.abbreviation
            row.description = parameter.comment
            row.read_write = "R" if parameter.read_only else "RW"
            uses_interface_item = (
                isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
                and parameter.uses_interface_item()
            )
            row.parameter_uses_interface_item = uses_interface_item
            if parameter.access_level_uuid is not None:
                access_level = self.parameter_uuid_finder(parameter.access_level_uuid)
                row.access_level = access_level.value

        return row


@enumeration_builders(epcpm.staticmodbusmodel.FunctionData)
@attr.s
class FunctionDataOutput:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        rows = []
        enumeration_uuid = getattr(self.wrapped, "enumeration_uuid", None)
        if enumeration_uuid is None:
            return rows

        enumeration = self.parameter_uuid_finder(enumeration_uuid)
        enumerators_by_bit = {
            enumerator.value: enumerator for enumerator in enumeration.children
        }

        # 16 bits per register
        total_bit_count = self.wrapped.size * 16
        decimal_digits = len(str(total_bit_count - 1))
        for bit in range(total_bit_count):
            enumerator = enumerators_by_bit.get(bit)

            if enumerator is None:
                padded_bit_string = f"{bit:0{decimal_digits}}"
                enumerator = epyqlib.pm.parametermodel.SunSpecEnumerator(
                    label=f"Reserved - {padded_bit_string}",
                    name=f"Rsvd{padded_bit_string}",
                    value=bit,
                )

            builder = enumerator_builders.wrap(
                wrapped=enumerator,
            )
            rows.append(builder.gen())

        return rows


@enumerator_builders(epyqlib.pm.parametermodel.SunSpecEnumerator)
@attr.s
class Enumerator:
    wrapped = attr.ib()

    def gen(self):
        row = Fields()
        for name, field in attr.asdict(enumerator_fields).items():
            if field is None:
                continue

            setattr(row, name, getattr(self.wrapped, field.name) if type(field) is not bool else field)

        if row.name is None:
            row.name = self.wrapped.name

        return row


@enumeration_builders(epcpm.staticmodbusmodel.FunctionDataBitfield)
@attr.s
class DataPointBitfield:
    wrapped = attr.ib()
    point = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        rows = []

        # 16 bits per register
        total_bit_count = self.wrapped.size * 16
        decimal_digits = len(str(total_bit_count - 1))

        enumerators_by_bit = {
            enumerator.bit_offset
            + i: [enumerator, i if enumerator.bit_length > 1 else None]
            for enumerator in self.wrapped.children
            for i in range(enumerator.bit_length)
        }

        for bit in range(total_bit_count):
            enumerator, index = enumerators_by_bit.get(bit, [None, None])

            if enumerator is None:
                padded_bit_string = f"{bit:0{decimal_digits}}"
                row = Fields(
                    field_type=f"bitfield{total_bit_count}",
                    value=bit,
                    name=f"Rsvd{padded_bit_string}",
                    label=f"Reserved - {padded_bit_string}",
                )
            else:
                builder = enumerator_builders.wrap(
                    wrapped=enumerator,
                )
                row = builder.gen()

                if index is not None:
                    padded_index_string = f"{index:0{decimal_digits}}"

                    row = attr.evolve(
                        row,
                        name=f"{row.name}{padded_index_string}",
                        label=f"{row.label} - {padded_index_string}",
                        value=row.value + index,
                    )

            rows.append(row)

        return rows


@enumerator_builders(epcpm.staticmodbusmodel.FunctionDataBitfieldMember)
@attr.s
class DataPointBitfieldMember:
    wrapped = attr.ib()
    point = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        member_parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

        length = self.point.size * 16

        row = Fields(
            field_type=f"bitfield{length}",
            value=self.wrapped.bit_offset,
            name=member_parameter.abbreviation,
            label=member_parameter.name,
            description=member_parameter.comment,
            notes=member_parameter.notes,
        )

        return row


@enumeration_builders(epcpm.staticmodbusmodel.TableRepeatingBlockReference)
@attr.s
class GenericEnumeratorBuilder:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        rows = []

        for child in self.wrapped.children:
            builder = enumeration_builders.wrap(
                wrapped=child,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )

            new_rows = builder.gen()

            if len(new_rows) > 0:
                rows.extend(new_rows)
                rows.append(Fields())

        return rows


@enumeration_builders(
    epcpm.staticmodbusmodel.TableRepeatingBlockReferenceFunctionDataReference,
)
@attr.s
class TableRepeatingBlockReferenceDataPointReferenceEnumerationBuilder:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        builder = enumeration_builders.wrap(
            wrapped=self.wrapped.original,
            parameter_uuid_finder=self.parameter_uuid_finder,
        )

        return builder.gen()


@builders(epcpm.staticmodbusmodel.TableRepeatingBlockReference)
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