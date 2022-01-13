from __future__ import (
    annotations,
)  # See PEP 563, check to remove in future Python version higher than 3.7
import attr
import csv
import math
import pathlib
import typing
import uuid
import epcpm.c
import epyqlib.attrsmodel
import epcpm.pm_helper
import epcpm.sunspecmodel
import epyqlib.pm.parametermodel
import epyqlib.utils.general


builders = epyqlib.utils.general.TypeMap()

data_point_fields = attr.fields(epcpm.sunspecmodel.DataPoint)
bitfield_fields = attr.fields(epcpm.sunspecmodel.DataPointBitfield)
bitfield_member_fields = attr.fields(epcpm.sunspecmodel.DataPointBitfieldMember)

sunspec_types = epcpm.sunspecmodel.build_sunspec_types_enumeration()


@attr.s
class Fields(epcpm.pm_helper.FieldsInterface):
    """The fields defined for a given row in the output CSV file."""

    model_id = attr.ib(default=None, type=typing.Union[str, bool])
    address_offset = attr.ib(default=None, type=typing.Union[str, bool])
    block_offset = attr.ib(default=None, type=typing.Union[str, bool])
    size = attr.ib(default=None, type=typing.Union[str, bool])
    name = attr.ib(default=None, type=typing.Union[str, bool])
    label = attr.ib(default=None, type=typing.Union[str, bool])
    value = attr.ib(default=None, type=typing.Union[str, bool])
    type = attr.ib(default=None, type=typing.Union[str, bool])
    units = attr.ib(default=None, type=typing.Union[str, bool])
    scale_factor = attr.ib(default=None, type=typing.Union[str, bool])
    read_write = attr.ib(default=None, type=typing.Union[str, bool])
    mandatory = attr.ib(default=None, type=typing.Union[str, bool])
    description = attr.ib(default=None, type=typing.Union[str, bool])
    bit_offset = attr.ib(default=None, type=typing.Union[str, bool])
    bit_length = attr.ib(default=None, type=typing.Union[str, bool])
    modbus_address = attr.ib(default=None, type=typing.Union[str, bool])
    parameter_uuid = attr.ib(default=None, type=typing.Union[str, bool])
    parameter_uses_interface_item = attr.ib(default=None, type=typing.Union[str, bool])
    scale_factor_uuid = attr.ib(default=None, type=typing.Union[str, bool])
    enumeration_uuid = attr.ib(default=None, type=typing.Union[str, bool])
    type_uuid = attr.ib(default=None, type=typing.Union[str, bool])
    not_implemented = attr.ib(default=None, type=typing.Union[str, bool])
    uuid = attr.ib(default=None, type=typing.Union[str, bool])
    class_name = attr.ib(default=None, type=typing.Union[str, bool])


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

bitfield_member_fields = Fields(
    type=bitfield_member_fields.type_uuid,
)


def export(
    path: pathlib.Path,
    sunspec_model: epyqlib.attrsmodel.Model,
    parameters_model: epyqlib.attrsmodel.Model,
    column_filter: epcpm.pm_helper.FieldsInterface = None,
    skip_output: bool = False,
) -> None:
    """
    Generate the SunSpec model data .csv file.

    Args:
        path: path and filename for .csv file
        sunspec_model: SunSpec model
        parameters_model: parameters model
        column_filter: columns to be output to .csv file
        skip_output: skip output of the generated files, previously used for skip_sunspec

    Returns:

    """
    if skip_output:
        return

    if column_filter is None:
        column_filter = epcpm.pm_helper.attr_fill(Fields, True)

    builder = epcpm.sunspectocsv.builders.wrap(
        wrapped=sunspec_model.root,
        parameter_uuid_finder=sunspec_model.node_from_uuid,
        parameter_model=parameters_model,
        column_filter=column_filter,
    )

    csv_data = builder.gen()

    with open(path.with_suffix(".csv"), "w", newline="") as csv_file:
        csv_writer = csv.writer(csv_file, quoting=csv.QUOTE_ALL)
        for data_row in csv_data:
            csv_writer.writerow(data_row)


@builders(epcpm.sunspecmodel.Root)
@attr.s
class Root:
    """CSV generator for the SunSpec Root class."""

    wrapped = attr.ib(type=epcpm.sunspecmodel.Root)
    column_filter = attr.ib(type=Fields)
    parameter_uuid_finder = attr.ib(default=None, type=typing.Callable)
    parameter_model = attr.ib(default=None, type=epyqlib.attrsmodel.Model)
    sort_models = attr.ib(default=False, type=bool)

    def gen(self) -> typing.List[str]:
        """
        CSV generator for the SunSpec Root class.

        Returns:
            list: the rows of CSV data to be output
        """
        csv_data = []

        if self.sort_models:
            children = sorted(
                self.wrapped.children,
                key=lambda child: (
                    0 if isinstance(child, epcpm.sunspecmodel.Model) else 1,
                    getattr(child, "id", math.inf),
                ),
            )
        else:
            children = list(self.wrapped.children)

        model_offset = 2  # account for starting 'SunS'
        for model in children:
            if isinstance(model, epcpm.sunspecmodel.Table):
                # TODO: for now, implement it soon...
                continue

            model_offset += builders.wrap(
                wrapped=model,
                csv_data=csv_data,
                column_filter=self.column_filter,
                padding_type=self.parameter_model.list_selection_roots[
                    "sunspec types"
                ].child_by_name("pad"),
                parameter_uuid_finder=self.parameter_uuid_finder,
                model_offset=model_offset,
            ).gen()

        return csv_data


@builders(epcpm.sunspecmodel.Model)
@attr.s
class Model:
    """CSV generator for the SunSpec Model class."""

    wrapped = attr.ib(type=epcpm.sunspecmodel.Model)
    csv_data = attr.ib(type=typing.List[str])
    column_filter = attr.ib(type=Fields)
    padding_type = attr.ib(type=epyqlib.pm.parametermodel.Enumerator)
    model_offset = attr.ib(type=int)  # starting Modbus address for the model
    parameter_uuid_finder = attr.ib(default=None, type=typing.Callable)

    def gen(self) -> int:
        """
        CSV generator for the SunSpec Model class.

        Returns:
            int: total register length of SunSpec model, including header, fixed, padding, repeating
        """
        self.wrapped.children[0].check_offsets_and_length()

        non_header_block_length = sum(
            child.check_offsets_and_length() for child in self.wrapped.children[1:]
        )

        # Per SunSpec model specification, pad with a 16-bit pad to force even alignment to 32-bit boundaries.
        add_padding = (non_header_block_length % 2) == 1
        if add_padding:
            non_header_block_length += 1

        # Track the total accumulated length of the model's registers.
        accumulated_length = 0

        rows = []

        model_types = ["Header", "Fixed Block", "Repeating Block"]

        zipped = zip(enumerate(self.wrapped.children), model_types)
        for (model_type_index, child), model_type in zipped:
            # TODO: Check if this is one of the spots where "add_padding" is incorrect for tables.
            builder = builders.wrap(
                wrapped=child,
                add_padding=add_padding and model_type_index == 1,
                padding_type=self.padding_type,
                model_type=model_type,
                model_id=self.wrapped.id,
                model_offset=self.model_offset,
                parameter_uuid_finder=self.parameter_uuid_finder,
                address_offset=accumulated_length,
            )

            built_rows, block_length = builder.gen()
            accumulated_length += block_length
            if len(built_rows) > 0:
                rows.extend(built_rows)

        for i, row in enumerate(rows):
            row.model_id = self.wrapped.id
            if i == 0:
                # Set ID value with model ID.
                row.value = self.wrapped.id
            elif i == 1:
                # Set L value with length of fixed block plus repeating block.
                row.value = non_header_block_length

            self.csv_data.append(row.as_filtered_tuple(self.column_filter))

        return accumulated_length


@builders(epcpm.sunspecmodel.Table)
@attr.s
class Table:
    """CSV generator for the SunSpec Table class."""

    wrapped = attr.ib(type=epcpm.sunspecmodel.Model)
    padding_type = attr.ib(type=epyqlib.pm.parametermodel.Enumerator)
    parameter_uuid_finder = attr.ib(default=None, type=typing.Callable)

    def gen(self) -> typing.List:
        """
        CSV generator for the SunSpec Table class.

        Returns:
            list: empty list
        """
        return []


def build_uuid_scale_factor_dict(
    points: typing.List[
        typing.Union[epcpm.sunspecmodel.DataPoint, epcpm.sunspecmodel.DataPointBitfield]
    ],
    parameter_uuid_finder: typing.Callable,
) -> typing.Dict[uuid.UUID, epcpm.sunspecmodel.DataPoint]:
    """
    Generates a dictionary of scale factor data.

    Args:
        points: list of DataPoint / DataPointBitfield objects from which to generate scale factor data
        parameter_uuid_finder: parameter UUID finder method

    Returns:
        dict: dictionary of scale factor data (UUID -> DataPoint)
    """
    # TODO: CAMPid 45002738594281495565841631423784
    scale_factor_from_uuid = {}
    for point in points:
        if point.type_uuid is None:
            continue

        type_node = parameter_uuid_finder(point.type_uuid)

        if type_node is None:
            continue

        if type_node.name == "sunssf":
            scale_factor_from_uuid[point.uuid] = point

    return scale_factor_from_uuid


@builders(epcpm.sunspecmodel.HeaderBlock)
@builders(epcpm.sunspecmodel.FixedBlock)
@attr.s
class Block:
    """CSV generator for the SunSpec HeaderBlock and FixedBlock classes."""

    wrapped = attr.ib(
        type=typing.Union[epcpm.sunspecmodel.HeaderBlock, epcpm.sunspecmodel.FixedBlock]
    )
    add_padding = attr.ib(type=bool)
    padding_type = attr.ib(type=epyqlib.pm.parametermodel.Enumerator)
    model_type = attr.ib(type=str)
    model_id = attr.ib(type=int)
    model_offset = attr.ib(type=int)
    address_offset = attr.ib(type=int)
    repeating_block_reference = attr.ib(
        default=None, type=epcpm.sunspecmodel.TableRepeatingBlockReference
    )
    parameter_uuid_finder = attr.ib(default=None, type=typing.Callable)
    is_table = attr.ib(default=False, type=bool)

    def gen(self) -> typing.Tuple[list, int]:
        """
        CSV generator for the SunSpec HeaderBlock and FixedBlock classes.

        Returns:
            list, int: list of point data, total register size of block
        """
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
            rows.extend(built_rows)

        return rows, summed_increments


@builders(epcpm.sunspecmodel.DataPointBitfield)
@attr.s
class DataPointBitfield:
    """CSV generator for the SunSpec DataPointBitfield class."""

    wrapped = attr.ib(type=epcpm.sunspecmodel.DataPointBitfield)
    model_type = attr.ib(type=str)
    scale_factor_from_uuid = attr.ib(
        type=typing.Dict[uuid.UUID, epcpm.sunspecmodel.DataPoint]
    )
    parameter_uuid_finder = attr.ib(type=typing.Callable)
    model_id = attr.ib(type=int)
    model_offset = attr.ib(type=int)
    is_table = attr.ib(type=bool)
    repeating_block_reference = attr.ib(
        type=epcpm.sunspecmodel.TableRepeatingBlockReference
    )
    address_offset = attr.ib(type=int)

    def gen(self) -> typing.Tuple[typing.List[Fields], int]:
        """
        CSV generator for the SunSpec DataPointBitfield class.
        Call to generate the DataPointBitfieldMember children.

        Returns:
            list, int: row data for bitfield, bitfield size
        """
        row = Fields()
        for name, field in attr.asdict(bitfield_fields).items():
            if field is None:
                continue

            setattr(row, name, getattr(self.wrapped, field.name))

        row.address_offset = self.address_offset
        row.modbus_address = self.model_offset + self.address_offset

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
            if row.units is None:
                row.units = parameter.units
            row.description = parameter.comment
            row.read_write = "R" if parameter.read_only else "RW"
            row.parameter_uuid = parameter.uuid
            row.parameter_uses_interface_item = False
            row.type_uuid = self.wrapped.type_uuid
            row.not_implemented = False
            row.uuid = self.wrapped.uuid
            row.class_name = "DataPointBitfield"

        # The parent DataPointBitfield row slots in before the DataPointBitfieldMember rows.
        rows = [row]
        points = list(self.wrapped.children)
        for child in points:
            builder = builders.wrap(
                wrapped=child,
                model_type=self.model_type,
                parameter_uuid_finder=self.parameter_uuid_finder,
                model_id=self.model_id,
                model_offset=self.model_offset,
                address_offset=self.address_offset,
            )
            child_row = builder.gen()
            rows.append(child_row)

        return rows, row.size


@builders(epcpm.sunspecmodel.DataPointBitfieldMember)
@attr.s
class DataPointBitfieldMember:
    """CSV generator for the SunSpec DataPointBitfieldMember class."""

    wrapped = attr.ib(type=epcpm.sunspecmodel.DataPointBitfieldMember)
    model_type = attr.ib(type=str)
    parameter_uuid_finder = attr.ib(type=typing.Callable)
    model_id = attr.ib(type=int)
    model_offset = attr.ib(type=int)
    address_offset = attr.ib(type=int)

    def gen(self) -> Fields:
        """
        CSV generator for the SunSpec DataPointBitfieldMember class.

        Returns:
            row: row data for bitfield member
        """
        row = Fields()
        row.address_offset = self.address_offset
        row.modbus_address = self.model_offset + self.address_offset

        for name, field in attr.asdict(bitfield_member_fields).items():
            if field is None:
                continue

            setattr(row, name, getattr(self.wrapped, field.name))

        if row.type is not None:
            row.type = self.parameter_uuid_finder(row.type).name

        if self.wrapped.parameter_uuid is not None:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

            uses_interface_item = (
                isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
                and parameter.uses_interface_item()
            )

            row.label = parameter.name
            row.name = parameter.abbreviation
            if row.units is None:
                row.units = parameter.units
            row.description = parameter.comment
            row.read_write = "R" if parameter.read_only else "RW"
            row.parameter_uuid = parameter.uuid
            row.parameter_uses_interface_item = uses_interface_item
            row.type_uuid = self.wrapped.type_uuid
            row.not_implemented = False
            row.size = 0
            row.bit_offset = self.wrapped.bit_offset
            row.bit_length = self.wrapped.bit_length
            row.uuid = self.wrapped.uuid
            row.class_name = "DataPointBitfieldMember"

        return row


@builders(epcpm.sunspecmodel.TableRepeatingBlockReference)
@attr.s
class TableRepeatingBlockReference:
    """CSV generator for the SunSpec TableRepeatingBlockReference class."""

    wrapped = attr.ib(type=epcpm.sunspecmodel.TableRepeatingBlockReference)
    add_padding = attr.ib(type=bool)
    padding_type = attr.ib(type=epyqlib.pm.parametermodel.Enumerator)
    model_type = attr.ib(type=str)
    model_id = attr.ib(type=int)
    model_offset = attr.ib(type=int)
    address_offset = attr.ib(type=int)
    parameter_uuid_finder = attr.ib(default=None, type=typing.Callable)

    def gen(self) -> typing.Tuple[typing.List[Fields], int]:
        """
        CSV generator for the SunSpec TableRepeatingBlockReference class.

        Returns:
            list, int: list of point data, total register size of block
        """
        table_repeating_block = self.wrapped.original

        rows = []
        block_size = 0
        # For each curve (# curves = repeats) in the table, add the table's tree children.
        for curve_index in range(table_repeating_block.repeats):
            curve_points = 0
            for point in table_repeating_block.children:
                table_element1 = self.parameter_uuid_finder(point.parameter_uuid)
                curve_parent = table_element1.tree_parent.tree_parent.tree_parent
                table_element2 = curve_parent.descendent(
                    str(curve_index + 1),
                    table_element1.tree_parent.name,
                    table_element1.name,
                )

                row = Fields()

                for name, field in attr.asdict(point_fields).items():
                    if field is None:
                        continue

                    setattr(row, name, getattr(point, field.name))

                row.address_offset = self.address_offset
                row.name = table_element2.name
                row.label = table_element2.abbreviation
                row.type_uuid = row.type
                row.type = self.parameter_uuid_finder(row.type).name
                row.units = table_element2.units
                row.modbus_address = (
                    block_size + self.model_offset + self.address_offset
                )
                row.parameter_uuid = table_element2.uuid
                parameter = self.parameter_uuid_finder(table_element2.uuid)
                uses_interface_item = (
                    isinstance(parameter, epyqlib.pm.parametermodel.TableArrayElement)
                    and parameter.uses_interface_item()
                )
                row.parameter_uses_interface_item = uses_interface_item

                # TODO: the scale factor is on the TableRepeatingBlockReference children, so something special will need to be done.
                # if row.scale_factor is not None:
                #     row.scale_factor_uuid = row.scale_factor
                #     row.scale_factor = self.parameter_uuid_finder(
                #         self.scale_factor_from_uuid[row.scale_factor].parameter_uuid
                #     ).abbreviation

                row.enumeration_uuid = table_element2.enumeration_uuid
                row.not_implemented = point.not_implemented
                row.uuid = point.uuid
                row.class_name = "TableRepeatingBlockReferenceDataPointReference"

                rows.append(row)

                # Increase the address offset by the size of the data type.
                block_size += point.size
                curve_points += 1

        return rows, block_size


@builders(epcpm.sunspecmodel.TableRepeatingBlock)
@attr.s
class TableRepeatingBlock:
    """CSV generator for the SunSpec TableRepeatingBlock class."""

    wrapped = attr.ib(type=epcpm.sunspecmodel.TableRepeatingBlock)
    add_padding = attr.ib(type=bool)
    padding_type = attr.ib(type=epyqlib.pm.parametermodel.Enumerator)
    model_type = attr.ib(type=str)
    model_id = attr.ib(type=int)
    model_offset = attr.ib(type=int)
    address_offset = attr.ib(type=int)
    repeating_block_reference = attr.ib(
        default=None, type=epcpm.sunspecmodel.TableRepeatingBlockReference
    )
    parameter_uuid_finder = attr.ib(default=None, type=typing.Callable)
    is_table = attr.ib(default=False, type=bool)

    def gen(self) -> typing.Tuple[typing.List[Fields], int]:
        """
        CSV generator for the SunSpec TableRepeatingBlock class.

        Returns:
            list, int: empty list, zero size
        """
        return [], 0


@builders(epcpm.sunspecmodel.DataPoint)
@attr.s
class Point:
    """CSV generator for the SunSpec DataPoint class."""

    wrapped = attr.ib(type=epcpm.sunspecmodel.DataPoint)
    scale_factor_from_uuid = attr.ib(
        type=typing.Dict[uuid.UUID, epcpm.sunspecmodel.DataPoint]
    )
    model_type = attr.ib(type=str)
    model_id = attr.ib(type=int)
    model_offset = attr.ib(type=int)
    is_table = attr.ib(type=bool)
    address_offset = attr.ib(type=int)
    repeating_block_reference = attr.ib(
        type=epcpm.sunspecmodel.TableRepeatingBlockReference
    )
    parameter_uuid_finder = attr.ib(default=None, type=typing.Callable)

    # TODO: CAMPid 07397546759269756456100183066795496952476951653
    def gen(self) -> typing.Tuple[typing.List[Fields], int]:
        """
        CSV generator for the SunSpec DataPoint class.

        Returns:
            list, int: row data for data point, data point size
        """
        row = Fields()
        row.address_offset = self.address_offset
        row.modbus_address = self.model_offset + self.address_offset

        for name, field in attr.asdict(point_fields).items():
            if field is None:
                continue

            setattr(row, name, getattr(self.wrapped, field.name))

        row_scale_factor_uuid = ""
        if self.repeating_block_reference is not None:
            target = self.parameter_uuid_finder(self.wrapped.parameter_uuid).original
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
                (reference,) = references

                if reference.factor_uuid is not None:
                    row.scale_factor = self.parameter_uuid_finder(
                        self.parameter_uuid_finder(reference.factor_uuid).parameter_uuid
                    ).abbreviation
        else:
            if row.scale_factor is not None:
                row_scale_factor_uuid = row.scale_factor
                row.scale_factor = self.parameter_uuid_finder(
                    self.scale_factor_from_uuid[row.scale_factor].parameter_uuid
                ).abbreviation

        if row.type is not None:
            row.type = self.parameter_uuid_finder(row.type).name

        row.mandatory = "M" if self.wrapped.mandatory else "O"

        if self.wrapped.parameter_uuid is not None:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

            uses_interface_item = (
                isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
                and parameter.uses_interface_item()
            )
            row.label = parameter.name
            row.name = parameter.abbreviation

            if row.units is None:
                row.units = parameter.units
            row.read_write = "R" if parameter.read_only else "RW"
            row.parameter_uuid = parameter.uuid
            row.parameter_uses_interface_item = uses_interface_item
            row.scale_factor_uuid = row_scale_factor_uuid
            row.enumeration_uuid = parameter.enumeration_uuid
            row.type_uuid = self.wrapped.type_uuid
            row.not_implemented = self.wrapped.not_implemented
            row.uuid = self.wrapped.uuid
            row.class_name = "DataPoint"

        if self.parameter_uuid_finder(self.wrapped.type_uuid).name == "pad":
            row.name = "Pad"
            row.description = "Force even alignment"
            row.read_write = "R"
            row.mandatory = "O"
            row.parameter_uses_interface_item = False
            pad_uuid = ""
            # TODO: This pad UUID discovery code should probably be a separate method.
            # Discover the pad UUID.
            for sunspec_type in sunspec_types.children:
                if sunspec_type.name == "pad":
                    pad_uuid = sunspec_type.uuid
                    break
            row.type_uuid = pad_uuid
            row.not_implemented = False
            row.class_name = "DataPoint"

        return [row], row.size
