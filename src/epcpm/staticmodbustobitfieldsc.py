import attr

import epcpm.c
import epcpm.parameterstointerface
import epcpm.staticmodbusmodel
import epcpm.sunspectoxlsx
import epyqlib.utils.general


builders = epyqlib.utils.general.TypeMap()


def export(c_path, h_path, staticmodbus_model, include_uuid_in_item):
    builder = builders.wrap(
        wrapped=staticmodbus_model.root,
        parameter_uuid_finder=staticmodbus_model.node_from_uuid,
        c_path=c_path,
        h_path=h_path,
        include_uuid_in_item=include_uuid_in_item,
    )

    c_path.parent.mkdir(parents=True, exist_ok=True)
    builder.gen()


def gen(self, first=0):
    lines = [[], []]

    for member in self.wrapped.children[first:]:
        try:
            builder = builders.wrap(
                wrapped=member,
                parameter_uuid_finder=self.parameter_uuid_finder,
                include_uuid_in_item=self.include_uuid_in_item,
            )
        except KeyError:
            continue
        new_lines = builder.gen()
        for ch_lines, ch_new_lines in zip(lines, new_lines):
            if len(ch_new_lines) > 0:
                ch_lines.extend(ch_new_lines)
                ch_lines.append("")

    return lines


@builders(epcpm.staticmodbusmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()
    c_path = attr.ib()
    h_path = attr.ib()
    include_uuid_in_item = attr.ib()

    def gen(self):
        c_lines = [
            '#include "interface.h"',
            '#include "interfaceGen.h"',
            '#include "interfaceStructures_generated.h"',
            '#include "staticmodbusInterfaceGen.h"',
            '#include "staticmodbusInterfaceFunctions_generated.h"',
            "",
            "",
        ]

        include_guard = self.h_path.name.replace(".", "_").upper()

        h_lines = [
            f"#ifndef {include_guard}",
            f"#define {include_guard}",
            f"",
            f'#include "interface.h"',
            f"",
            f"",
        ]

        for member in self.wrapped.children:
            try:
                builder = builders.wrap(
                    wrapped=member,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                    include_uuid_in_item=self.include_uuid_in_item,
                )
            except KeyError:
                continue
            more_c_lines, more_h_lines = builder.gen()
            c_lines.extend(more_c_lines)
            h_lines.extend(more_h_lines)

        h_lines.append("#endif")

        with self.c_path.open("w", newline="\n") as f:
            f.write(epcpm.c.format_nested_lists(c_lines).strip() + "\n")

        with self.h_path.open("w", newline="\n") as f:
            f.write(epcpm.c.format_nested_lists(h_lines).strip() + "\n")


@builders(epcpm.staticmodbusmodel.FunctionDataBitfield)
@attr.s
class FunctionDataBitfield:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()
    include_uuid_in_item = attr.ib()

    def gen(self):
        # TODO: CAMPid 07954360685417610543064316843160

        bits_per_modbus_register = 16
        bit_length = bits_per_modbus_register * self.wrapped.size

        name_uuid = str(self.wrapped.parameter_uuid).replace("-", "_")

        members = self.wrapped.children

        array_name = f"staticmodbusBitfieldItems_{name_uuid}"
        # model = self.wrapped.tree_parent.tree_parent.id

        parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

        c_lines = []
        h_lines = []

        for member in members:
            member_name_uuid = str(member.parameter_uuid).replace("-", "_")
            variable_name = f"interfaceItem_variable_{member_name_uuid}"
            variable_type = epcpm.parameterstointerface.staticmodbus_types[
                self.parameter_uuid_finder(member.type_uuid).name
            ]

            h_lines.append(
                f"// extern {variable_type} {variable_name};",
            )

            # TODO: initializer that doesn't assume int16_t
            c_lines.append(
                f"// {variable_type} {variable_name} = 0;",
            )

        c_lines.append("")
        h_lines.append("")

        c_lines.extend(
            [
                f"InterfaceItem_BitfieldMember {array_name}[{len(members)}] = {{",
                [
                    [
                        f"[{i}] = {{",
                        [
                            f".offset = {member.bit_offset},",
                            f".length = {member.bit_length},",
                            f'.item = &interfaceItem_{str(member.parameter_uuid).replace("-", "_")},',
                        ],
                        f"}},",
                    ]
                    for i, member in enumerate(members)
                ],
                f"}};",
                f"",
                f"InterfaceItem_Bitfield interfaceItem_staticmodbus_{name_uuid} = {{",
                [
                    f".common = {{",
                    [  # TODO: generate a real complete common initializer
                        f".staticmodbus = {{",
                        [
                            f".getter = InterfaceItem_bitfield_{bit_length}_staticmodbus_getter,",
                            f".setter = InterfaceItem_bitfield_{bit_length}_staticmodbus_setter,",
                            ".variable = NULL,",
                            # f".variable = &staticmodbusInterface.model{model:05}.{parameter.abbreviation},",
                        ],
                        f"}},",
                    ],
                    f"}},",
                    f".members = {array_name},",
                    f".membersCount = {len(members)},",
                ],
                f"}};",
            ]
        )

        h_lines.extend(
            [
                f"extern InterfaceItem_BitfieldMember {array_name}[{len(members)}];",
                f"extern InterfaceItem_Bitfield interfaceItem_staticmodbus_{name_uuid};",
            ]
        )

        return c_lines, h_lines
