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
import epyqlib.utils.general


builders = epyqlib.utils.general.TypeMap()


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
    field_type = attr.ib(default=None, type=typing.Union[str, bool])


field_names = Fields(
    modbus_address="Modbus Address",
    name="Name",
    label="Label",
    size="Size",
    type="Type",
    units="Units",
    read_write="R/W",
    description="Description",
    field_type="Field Type",
)


def export(
    path: pathlib.Path,
    staticmodbus_model: epyqlib.attrsmodel.Model,
    parameters_model: epyqlib.attrsmodel.Model,
    column_filter: typing.Type[epcpm.pm_helper.FieldsInterface] = None,
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


# TODO: Remove this method when static modbus start address is changed to zero.
def add_temporary_modbus_address_offset(input_modbus_address: int):
    """TEMPORARY offset addition, to be removed when static modbus start address becomes zero"""
    return input_modbus_address + 20000


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
        worksheet.append(field_names.as_filtered_tuple(self.column_filter))

        for member in self.wrapped.children:
            builder = builders.wrap(
                wrapped=member,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )
            rows = builder.gen()
            for row in rows:
                worksheet.append(row.as_filtered_tuple(self.column_filter))

        return workbook


@builders(epcpm.staticmodbusmodel.FunctionData)
@attr.s
class FunctionData:
    """Excel spreadsheet generator for the static modbus FunctionData class."""

    wrapped = attr.ib(type=epcpm.staticmodbusmodel.FunctionData)
    parameter_uuid_finder = attr.ib(type=typing.Callable)

    def gen(self) -> typing.List[Fields]:
        """
        Excel spreadsheet generator for the static modbus FunctionData class.

        Returns:
            list: single Fields row of FunctionData
        """
        type_node = self.parameter_uuid_finder(self.wrapped.type_uuid)
        row = Fields()
        row.field_type = FunctionData.__name__
        row.modbus_address = add_temporary_modbus_address_offset(self.wrapped.address)
        row.type = type_node.name
        row.size = self.wrapped.size
        row.units = self.wrapped.units
        if self.wrapped.parameter_uuid is not None:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)
            row.label = parameter.name
            row.name = parameter.abbreviation
            row.description = parameter.comment
            row.read_write = "R" if parameter.read_only else "RW"

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
        row.field_type = FunctionDataBitfield.__name__
        row.modbus_address = add_temporary_modbus_address_offset(self.wrapped.address)
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
            member_row.modbus_address = add_temporary_modbus_address_offset(
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
        row.field_type = FunctionDataBitfieldMember.__name__
        type_node = self.parameter_uuid_finder(self.wrapped.type_uuid)
        row.type = type_node.name
        row.size = self.wrapped.bit_length
        if self.wrapped.parameter_uuid is not None:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)
            row.label = parameter.name
            row.name = parameter.abbreviation
            row.description = parameter.comment
            row.read_write = "R" if parameter.read_only else "RW"

        return row
