import attr

import epcpm.c
import epcpm.sunspecmodel
import epcpm.sunspectoxlsx
import epyqlib.utils.general


builders = epyqlib.utils.general.TypeMap()


def export(path, sunspec_model):
    builder = builders.wrap(
        wrapped=sunspec_model.root,
        parameter_uuid_finder=sunspec_model.node_from_uuid,
        path=path,
    )

    path.mkdir(parents=True, exist_ok=True)
    builder.gen()


def gen(self, first=0):
    lines = []

    for member in self.wrapped.children[first:]:
        builder = builders.wrap(
            wrapped=member,
            parameter_uuid_finder=self.parameter_uuid_finder,
        )
        lines.extend(builder.gen())
        lines.append('')

    return lines


@builders(epcpm.sunspecmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()
    path = attr.ib()

    def gen(self):
        for member in self.wrapped.children:
            builder = builders.wrap(
                wrapped=member,
                parameter_uuid_finder=self.parameter_uuid_finder,
            )
            path = self.path/f'sunspecInterface{member.id:05}.c'
            lines = [
                '#include "faultHandler.h"',
                '#include "measurementd.h"',
                '#include "phaseControl.h"',
                '#include "referenceHandler.h"',
                # '#include "hardware.h"',
                # '#include "modbusHandler.h"',
                # '#include "uart.h"',
                '',
                '#include "sunspecInterfaceGen.h"',
                '#include "{}"'.format(path.with_suffix('.h').name),
                f'#include "sunspecModel{member.id}.h"',
                '',
                '',
            ]
            lines.extend(builder.gen())
            with path.open('w', newline='\n') as f:
                f.write(epcpm.c.format_nested_lists(lines).strip() + '\n')


@builders(epcpm.sunspecmodel.Model)
@attr.s
class SunSpecModel:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        return gen(self=self, first=1)


@builders(epcpm.sunspecmodel.HeaderBlock)
@builders(epcpm.sunspecmodel.FixedBlock)
@attr.s
class Block:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()

    gen = gen


@builders(epcpm.sunspecmodel.DataPoint)
@attr.s
class DataPoint:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        if self.wrapped.parameter_uuid is None:
            return []

        parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

        get_name = epcpm.sunspectoxlsx.getter_setter_name(
            get_set='get',
            point=self.wrapped,
            parameter=parameter,
        )

        set_name = epcpm.sunspectoxlsx.getter_setter_name(
            get_set='set',
            point=self.wrapped,
            parameter=parameter,
        )

        lines = []

        lines.extend([
            f'void {get_name}(void) {{',
            *(
                [self.wrapped.get.splitlines()]
                if self.wrapped.get is not None
                else []
            ),
            '}',
            '',
            f'void {set_name}(void) {{',
            *(
                [self.wrapped.set.splitlines()]
                if self.wrapped.set is not None
                else []
            ),
            '}',
        ])

        return lines
