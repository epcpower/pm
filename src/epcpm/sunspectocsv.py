import attr
import csv
import itertools
import math
import openpyxl
import epcpm.c
import epcpm.sunspecmodel
import epyqlib.pm.parametermodel
import epyqlib.utils.general


builders = epyqlib.utils.general.TypeMap()

data_point_fields = attr.fields(epcpm.sunspecmodel.DataPoint)
bitfield_fields = attr.fields(epcpm.sunspecmodel.DataPointBitfield)

sunspec_types = epcpm.sunspecmodel.build_sunspec_types_enumeration()


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
    modbus_address = attr.ib(default=None)
    item = attr.ib(default=None)
    parameter_uuid = attr.ib(default=None)
    parameter_uses_interface_item = attr.ib(default=None)
    scale_factor_uuid = attr.ib(default=None)
    enumeration_uuid = attr.ib(default=None)
    type_uuid = attr.ib(default=None)
    not_implemented = attr.ib(default=None)
    uuid = attr.ib(default=None)
    class_name = attr.ib(default=None)

    def as_filtered_tuple(self, filter_):
        return tuple(
            value for value, f in zip(attr.astuple(self), attr.astuple(filter_)) if f
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


def export(
    path,
    sunspec_model,
    parameters_model,
    column_filter=None,
    skip_output=False,
):
    if skip_output:
        return

    if column_filter is None:
        column_filter = attr_fill(Fields, True)

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
    wrapped = attr.ib()
    column_filter = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)
    parameter_model = attr.ib(default=None)
    sort_models = attr.ib(default=False)

    def gen(self):
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
    wrapped = attr.ib()
    csv_data = attr.ib()
    column_filter = attr.ib()
    padding_type = attr.ib()
    model_offset = attr.ib()  # starting Modbus address for the model
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        self.wrapped.children[0].check_offsets_and_length()

        overall_length = sum(
            child.check_offsets_and_length() for child in self.wrapped.children[1:]
        )

        add_padding = (overall_length % 2) == 1
        if add_padding:
            overall_length += 1

        accumulated_length = 0

        rows = []

        model_types = ["Header", "Fixed Block", "Repeating Block"]

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
            if len(built_rows) > 0:
                rows.extend(built_rows)

        for i, row in enumerate(rows):
            if i == 0:
                row.value = self.wrapped.id
            elif i == 1:
                row.value = overall_length

            self.csv_data.append(row.as_filtered_tuple(self.column_filter))

        return overall_length + 2  # add header length


@builders(epcpm.sunspecmodel.Table)
@attr.s
class Table:
    wrapped = attr.ib()
    padding_type = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        return []


def build_uuid_scale_factor_dict(points, parameter_uuid_finder):
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

        uses_interface_item = (
            isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
            and parameter.uses_interface_item()
        )

        return row, row.size


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
        table_repeating_block = self.wrapped.original

        rows = []
        block_size = 0
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
        return [], 0


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

        return row, row.size
