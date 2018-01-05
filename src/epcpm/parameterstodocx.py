import itertools

import attr
import docx
import docx.enum.section
import docx.enum.text

import epyqlib.cangenmanual
import epyqlib.pm.parametermodel
import epyqlib.treenode
import epyqlib.utils.general

builders = epyqlib.utils.general.TypeMap()


@attr.s
class Row:
    name = attr.ib()
    indent = attr.ib(default=0)
    fill = attr.ib(default='')
    factor = attr.ib(default='')
    units = attr.ib(default='')
    enumeration = attr.ib(default='')
    comment = attr.ib(default='')

    def to_tuple(self, max_indent=5):
        return (
            *((self.fill,) * self.indent),
            self.name,
            *((self.fill,) * (max_indent - self.indent - 1)),
            self.factor,
            self.units,
            self.enumeration,
            self.comment,
        )


@builders(epyqlib.pm.parametermodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    can_root = attr.ib()

    def gen(self):
        headings = Row(
            name='Name',
            factor='Factor',
            units='Units',
            enumeration='Enumeration',
            comment='Comment',
        )
        max_indent = 5
        fill_width = 0.25
        name_width = 2
        widths = Row(
            name=name_width - (fill_width * (max_indent - 1)),
            indent=max_indent,
            fill=fill_width,
            factor=0.625,
            units=0.625,
            enumeration=1.5,
            comment=None,
        )

        table = epyqlib.cangenmanual.Table(
            title=None,
            headings=headings.to_tuple(),
            widths=widths.to_tuple(),
        )

        import time
        start = time.monotonic()

        for child in self.wrapped.children:
            try:
                builder = builders.wrap(
                    wrapped=child,
                    parameter_root=self.wrapped,
                    can_root=self.can_root,
                )
            except KeyError:
                continue

            table.rows.extend(builder.gen(indent=0))

        now = time.monotonic()
        delta = now - start
        start = now
        print('rows built', int(delta))

        raw_rows = table.rows

        table.rows = tuple(
            row.to_tuple(max_indent=max_indent)
            for row in table.rows[:100]
        )

        now = time.monotonic()
        delta = now - start
        start = now
        print('rows converted', int(delta))

        doc = docx.Document()

        for section in doc.sections:
            section.orientation = docx.enum.section.WD_ORIENT.LANDSCAPE

        doc_table = doc.add_table(rows=0, cols=len(table.headings))

        table.fill_docx(doc_table)

        epyqlib.cangenmanual.set_repeat_table_header(doc_table.rows[0])
        epyqlib.cangenmanual.prevent_row_breaks(doc_table)

        for row, doc_row in zip(itertools.chain((headings,), raw_rows), doc_table.rows):
            base_cell = doc_row.cells[row.indent]
            base_cell.merge(doc_row.cells[max_indent - 1])

        for row in doc_table.rows:
            for cell in row.cells:
                cell.text = cell.text.strip()
                cell.paragraphs[0].paragraph_format.line_spacing_rule = (
                    docx.enum.text.WD_LINE_SPACING.SINGLE
                )

        now = time.monotonic()
        delta = now - start
        start = now
        print('table filled', int(delta))

        return doc


@builders(epyqlib.pm.parametermodel.Group)
@attr.s
class Group:
    wrapped = attr.ib()
    parameter_root = attr.ib()
    can_root = attr.ib()

    def gen(self, indent):
        rows = [
            Row(
                name=self.wrapped.name,
                indent=indent,
            ),
        ]

        for child in self.wrapped.children:
            builder = builders.wrap(
                wrapped=child,
                parameter_root=self.parameter_root,
                can_root=self.can_root,
            )
            rows.extend(builder.gen(indent=indent + 1))

        return rows


@builders(epyqlib.pm.parametermodel.Parameter)
@attr.s
class Parameter:
    wrapped = attr.ib()
    parameter_root = attr.ib()
    can_root = attr.ib()

    def gen(self, indent):
        signal = self.can_root.nodes_by_attribute(
            attribute_value=self.wrapped.uuid,
            attribute_name='parameter_uuid',
        ).pop()

        factor = signal.factor
        if factor is None or factor == 1:
            factor = ''

        units = self.wrapped.units
        if units is None:
            units = ''

        try:
            enumeration = self.parameter_root.nodes_by_attribute(
                attribute_value=self.wrapped.enumeration_uuid,
                attribute_name='uuid',
            ).pop().name
        except epyqlib.treenode.NotFoundError:
            enumeration = ''

        comment = self.wrapped.comment
        if comment is None:
            comment = ''

        return [
            Row(
                name=self.wrapped.name,
                indent=indent,
                factor=factor,
                units=units,
                enumeration=enumeration,
                comment=comment,
            ),
        ]
