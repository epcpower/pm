import itertools

import attr
import openpyxl

import epyqlib.utils.general

import epcpm.sunspecmodel


builders = epyqlib.utils.general.TypeMap()


data_point_fields = attr.fields(epcpm.sunspecmodel.DataPoint)
epc_enumerator_fields = attr.fields(
    epyqlib.pm.parametermodel.SunSpecEnumerator,
)


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
)


point_fields = Fields(
    address_offset=data_point_fields.offset,
    block_offset=data_point_fields.block_offset,
    size=data_point_fields.size,
    type=data_point_fields.type_uuid,
    scale_factor=data_point_fields.factor_uuid,
)


enumerator_fields = Fields(
    name=epc_enumerator_fields.name,
    label=epc_enumerator_fields.label,
    description=epc_enumerator_fields.description,
    notes=epc_enumerator_fields.notes,
    value=epc_enumerator_fields.value,
    field_type=epc_enumerator_fields.type,
)


@builders(epcpm.sunspecmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)
    parameter_model = attr.ib(default=None)

    def gen(self):
        workbook = openpyxl.Workbook()
        workbook.remove(workbook.active)

        for model in self.wrapped.children:
            worksheet = workbook.create_sheet()

            builders.wrap(
                wrapped=model,
                worksheet=worksheet,
                padding_type=self.parameter_model.list_selection_roots['sunspec types'].child_by_name('pad'),
                parameter_uuid_finder=self.parameter_uuid_finder,
            ).gen()

        return workbook


@builders(epcpm.sunspecmodel.Model)
@attr.s
class Model:
    wrapped = attr.ib()
    worksheet = attr.ib()
    padding_type = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        self.worksheet.title = str(self.wrapped.id)
        self.worksheet.append(attr.astuple(field_names))

        self.wrapped.children[0].check_offsets_and_length()

        length = sum(
            child.check_offsets_and_length()
            for child in self.wrapped.children[1:]
        )

        add_padding = (length % 2) == 1
        if add_padding:
            length += 1

        rows = []

        model_types = ['Header', 'Fixed Block']

        for (i, child), model_type in itertools.zip_longest(enumerate(self.wrapped.children), model_types):
            builder = builders.wrap(
                wrapped=child,
                add_padding=add_padding and i == 1,
                padding_type=self.padding_type,
                model_type=model_type,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )

            for row in builder.gen():
                rows.append(row)

            rows.append(Fields())

        for i, row in enumerate(rows):
            if i == 0:
                row.value = self.wrapped.id
            elif i == 1:
                row.value = length

            self.worksheet.append(attr.astuple(row))

        for block in self.wrapped.children:
            for point in block.children:
                parameter = self.parameter_uuid_finder(point.parameter_uuid)
                enumeration_uuid = parameter.enumeration_uuid
                if enumeration_uuid is None:
                    continue

                enumeration = self.parameter_uuid_finder(enumeration_uuid)
                builder = builders.wrap(
                    wrapped=enumeration,
                    point=point,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                )

                rows = builder.gen()

                for row in rows:
                    self.worksheet.append(attr.astuple(row))

                self.worksheet.append(attr.astuple(Fields()))


@builders(epyqlib.pm.parametermodel.Enumeration)
@attr.s
class Enumeration:
    wrapped = attr.ib()
    point = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        rows = []

        for enumerator in self.wrapped.children:
            builder = builders.wrap(
                wrapped=enumerator,
                point=self.point,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )
            rows.append(builder.gen())

        return rows


@builders(epyqlib.pm.parametermodel.SunSpecEnumerator)
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

        row.applicable_point = (
            self.parameter_uuid_finder(self.point.parameter_uuid).abbreviation
        )

        return row


@builders(epcpm.sunspecmodel.HeaderBlock)
@builders(epcpm.sunspecmodel.FixedBlock)
@attr.s
class Block:
    wrapped = attr.ib()
    add_padding = attr.ib()
    padding_type = attr.ib()
    model_type = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    def gen(self):
        scale_factor_from_uuid = {}
        for point in self.wrapped.children:
            if point.type_uuid is None:
                continue

            type_node = self.parameter_uuid_finder(point.type_uuid)

            if type_node is None:
                continue

            if type_node.name == 'sunssf':
                scale_factor_from_uuid[point.uuid] = point

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

        for child in points:
            builder = builders.wrap(
                wrapped=child,
                model_type=self.model_type,
                scale_factor_from_uuid=scale_factor_from_uuid,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )
            rows.append(builder.gen())

        return rows


@builders(epcpm.sunspecmodel.DataPoint)
@attr.s
class Point:
    wrapped = attr.ib()
    scale_factor_from_uuid = attr.ib()
    model_type = attr.ib()
    parameter_uuid_finder = attr.ib(default=None)

    # TODO: CAMPid 07397546759269756456100183066795496952476951653
    def gen(self):
        row = Fields()

        for name, field in attr.asdict(point_fields).items():
            if field is None:
                continue

            setattr(row, name, getattr(self.wrapped, field.name))

        if row.scale_factor is not None:
            row.scale_factor = (
                self.parameter_uuid_finder(
                    self.scale_factor_from_uuid[row.scale_factor].parameter_uuid).abbreviation
            )
        if row.type is not None:
            row.type = self.parameter_uuid_finder(row.type).name

        if self.wrapped.parameter_uuid is not None:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

            row.label = parameter.name
            row.name = parameter.abbreviation
            row.notes = parameter.notes
            row.units = parameter.units
            row.description = parameter.comment
            row.read_write = 'R' if parameter.read_only else 'RW'

        row.field_type = self.model_type

        if self.parameter_uuid_finder(self.wrapped.type_uuid).name == 'pad':
            row.name = 'Pad'
            row.description = 'Force even alignment'
            row.read_write = 'R'

        return row
