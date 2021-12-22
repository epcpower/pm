import attr
import openpyxl
import typing

import epcpm

import epyqlib.utils.general


builders = epyqlib.utils.general.TypeMap()


@attr.s
class Fields:
    """The fields defined for a given row in the output XLS file."""

    modbus_address = attr.ib(default=None)
    name = attr.ib(default=None)
    label = attr.ib(default=None)
    size = attr.ib(default=None)
    type = attr.ib(default=None)
    units = attr.ib(default=None)
    read_write = attr.ib(default=None)
    description = attr.ib(default=None)
    field_type = attr.ib(default=None)

    def as_filtered_tuple(self, filter_):
        return tuple(
            value for value, f in zip(attr.astuple(self), attr.astuple(filter_)) if f
        )


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


def attr_fill(cls, value):
    return cls(**{field.name: value for field in attr.fields(cls) if field.init})


def export(
    path, staticmodbus_model, parameters_model, column_filter=None, skip_output=False
):
    if skip_output:
        return

    if column_filter is None:
        column_filter = attr_fill(Fields, True)

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
    wrapped = attr.ib()
    column_filter = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)
    parameter_model = attr.ib(default=None)

    def gen(self):
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
    wrapped = attr.ib(type=epcpm.staticmodbusmodel.FunctionData)
    parameter_uuid_finder = attr.ib(type=typing.Callable)

    def gen(self) -> typing.List[str]:
        type_node = self.parameter_uuid_finder(self.wrapped.type_uuid)
        row = Fields()
        row.field_type = FunctionData.__name__
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

        if type_node.name == "pad":
            row.name = "Pad"
            row.description = "Force even alignment"
            row.read_write = "R"

        return [row]


@builders(epcpm.staticmodbusmodel.FunctionDataBitfield)
@attr.s
class FunctionDataBitfield:
    wrapped = attr.ib(type=epcpm.staticmodbusmodel.FunctionDataBitfield)
    parameter_uuid_finder = attr.ib(type=typing.Callable)

    def gen(self) -> typing.List[str]:
        rows = []
        row = Fields()
        row.field_type = FunctionDataBitfield.__name__
        row.modbus_address = self.wrapped.address
        row.size = self.wrapped.size
        rows.append(row)

        for member in self.wrapped.children:
            builder = builders.wrap(
                wrapped=member,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )
            member_row = builder.gen()
            member_row.modbus_address = self.wrapped.address
            rows.append(member_row)

        return rows


@builders(epcpm.staticmodbusmodel.FunctionDataBitfieldMember)
@attr.s
class FunctionDataBitfieldMember:
    wrapped = attr.ib(type=epcpm.staticmodbusmodel.FunctionDataBitfield)
    parameter_uuid_finder = attr.ib(type=typing.Callable)

    def gen(self) -> typing.List[str]:
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
