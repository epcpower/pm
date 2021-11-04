import attr
import pathlib
import typing
from typing import Any

import epcpm.c
import epcpm.parameterstointerface
import epcpm.staticmodbusmodel
import epcpm.sunspecmodel
import epyqlib.attrsmodel
import epyqlib.utils.general


builders = epyqlib.utils.general.TypeMap()


def export(
    c_path: pathlib.Path,
    h_path: pathlib.Path,
    parameters_model: epyqlib.attrsmodel.Model,
    sunspec_model: epyqlib.attrsmodel.Model,
    staticmodbus_model: epyqlib.attrsmodel.Model,
    skip_output: bool = False,
):
    """
    Generate the SunSpec and static modbus bitfield interfaces (.c/.h).

    Args:
        c_path: path and filename for .c file
        h_path: path and filename for .h file
        parameters_model: parameters model
        sunspec_model: SunSpec model
        staticmodbus_model: static modbus model
        skip_output: skip output of the interface in the generated files (files are still output)

    Returns:

    """
    sunspec_root = sunspec_model.root
    staticmodbus_root = staticmodbus_model.root

    builder = builders.wrap(
        wrapped=parameters_model.root,
        c_path=c_path,
        h_path=h_path,
        sunspec_root=sunspec_root,
        sunspec_model=sunspec_model,
        staticmodbus_root=staticmodbus_root,
        staticmodbus_model=staticmodbus_model,
        skip_output=skip_output,
    )

    builder.gen()


@builders(epyqlib.pm.parametermodel.Root)
@attr.s
class Root:
    wrapped = attr.ib(type=epyqlib.pm.parametermodel.Root)
    c_path = attr.ib(type=pathlib.Path)
    h_path = attr.ib(type=pathlib.Path)
    sunspec_root = attr.ib(type=epyqlib.attrsmodel.Root)
    sunspec_model = attr.ib(type=epyqlib.attrsmodel.Model)
    staticmodbus_root = attr.ib(type=epyqlib.attrsmodel.Root)
    staticmodbus_model = attr.ib(type=epyqlib.attrsmodel.Model)
    skip_output = attr.ib(type=bool)

    def gen(self) -> None:
        """
        From the root of the parameter model, generate the bitfield interfaces for SunSpec and static modbus.

        Returns:

        """

        def sunspec_node_wanted(node: Any) -> bool:
            # Filter for SunSpec DataPointBitfield types
            if getattr(node, "parameter_uuid", None) is None:
                return False

            wanted_types = (epcpm.sunspecmodel.DataPointBitfield,)
            if not isinstance(node, wanted_types):
                return False

            return True

        if self.sunspec_root is None:
            parameter_uuid_to_sunspec_node = {}
        else:
            sunspec_nodes_with_parameter_uuid = self.sunspec_root.nodes_by_filter(
                filter=sunspec_node_wanted,
            )

            parameter_uuid_to_sunspec_node = {
                node.parameter_uuid: node for node in sunspec_nodes_with_parameter_uuid
            }

        def staticmodbus_node_wanted(node: Any) -> bool:
            # Filter for static modbus FunctionDataBitfield types
            if getattr(node, "parameter_uuid", None) is None:
                return False

            wanted_types = (epcpm.staticmodbusmodel.FunctionDataBitfield,)
            if not isinstance(node, wanted_types):
                return False

            return True

        if self.staticmodbus_root is None:
            parameter_uuid_to_staticmodbus_node = {}
        else:
            staticmodbus_nodes_with_parameter_uuid = (
                self.staticmodbus_root.nodes_by_filter(
                    filter=staticmodbus_node_wanted,
                )
            )

            parameter_uuid_to_staticmodbus_node = {
                node.parameter_uuid: node
                for node in staticmodbus_nodes_with_parameter_uuid
            }

        # Combine the SunSpec and static modbus nodes
        parameter_uuid_to_modbus_node = {}
        for key, value in parameter_uuid_to_sunspec_node.items():
            parameter_uuid_to_modbus_node[key] = {"sunspec": value}
        for key, value in parameter_uuid_to_staticmodbus_node.items():
            if key not in parameter_uuid_to_modbus_node:
                parameter_uuid_to_modbus_node[key] = {"staticmodbus", value}
            else:
                parameter_uuid_to_modbus_node[key]["staticmodbus"] = value

        c_lines = [
            '#include "interface.h"',
            '#include "interfaceGen.h"',
            '#include "interfaceStructures_generated.h"',
            '#include "staticmodbusInterfaceGen.h"',
            '#include "staticmodbusInterfaceFunctions_generated.h"',
            '#include "sunspecInterfaceFunctions_generated.h"',
            '#include "sunspecInterfaceGen.h"',
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

        if not self.skip_output:
            for parameter_uuid, modbus_nodes in parameter_uuid_to_modbus_node.items():
                members_interface_c_lines = []
                members_info_c_lines = []

                name_uuid = str(parameter_uuid).replace("-", "_")

                # Generate the SunSpec related .c/.h rows.
                builder = builders.wrap(
                    wrapped=modbus_nodes["sunspec"],
                    parameter_uuid_finder=self.sunspec_model.node_from_uuid,
                )
                more_c_lines, more_h_lines = builder.gen()
                c_lines.extend(more_c_lines)
                h_lines.extend(more_h_lines)

                common_c_lines = []
                # Generate C lines for SunSpec node
                if "sunspec" in modbus_nodes:
                    builder = builders.wrap(
                        wrapped=modbus_nodes["sunspec"],
                        parameter_uuid_finder=self.sunspec_model.node_from_uuid,
                    )
                    common_c_lines.extend(builder.gen_common_interface())
                    members_interface_c_lines.extend(
                        builder.gen_bitfield_members_interface()
                    )
                    members_info_c_lines.extend(builder.gen_members_interface())
                else:
                    common_c_lines.extend(builder.gen_default_common_interface())

                # Generate C lines for static modbus node
                if "staticmodbus" in modbus_nodes:
                    builder = builders.wrap(
                        wrapped=modbus_nodes["staticmodbus"],
                        parameter_uuid_finder=self.staticmodbus_model.node_from_uuid,
                    )
                    common_c_lines.extend(builder.gen_common_interface())
                    members_interface_c_lines.extend(
                        builder.gen_bitfield_members_interface()
                    )
                    members_info_c_lines.extend(builder.gen_members_interface())
                else:
                    common_c_lines.extend(builder.gen_default_common_interface())

                c_lines.extend(members_interface_c_lines)

                # Generate the combined interface item code
                c_lines.extend(
                    [
                        f"InterfaceItem_Bitfield interfaceItem_{name_uuid} = {{",
                        [
                            f".common = {{",
                            [ccl for ccl in common_c_lines],
                            f"}},",
                        ],
                        [micl for micl in members_info_c_lines],
                        f"}};",
                        "",
                    ]
                )

                # Generate the static modbus related .h rows.
                builder = builders.wrap(
                    wrapped=modbus_nodes["staticmodbus"],
                    parameter_uuid_finder=self.staticmodbus_model.node_from_uuid,
                )
                more_h_lines = builder.gen()
                h_lines.extend(more_h_lines)

                # Add the interfaceItem_<UUID>, which defines both SunSpec and static modbus interfaces.
                h_lines.extend(
                    [
                        f"extern InterfaceItem_Bitfield interfaceItem_{name_uuid};",
                        "",
                    ]
                )

        h_lines.append("#endif")

        # Output the .c & .h files
        with self.c_path.open("w", newline="\n") as f:
            f.write(epcpm.c.format_nested_lists(c_lines).strip() + "\n")

        with self.h_path.open("w", newline="\n") as f:
            f.write(epcpm.c.format_nested_lists(h_lines).strip() + "\n")


@builders(epcpm.staticmodbusmodel.FunctionDataBitfield)
@attr.s
class FunctionDataBitfield:
    wrapped = attr.ib(type=epcpm.staticmodbusmodel.FunctionDataBitfield)
    parameter_uuid_finder = attr.ib(type=typing.Callable)

    def gen(self) -> typing.List[str]:
        """
        Generate a static modbus bitfield member extern definition.

        Returns:
            list: bitfield member definition row
        """
        # TODO: CAMPid 07954360685417610543064316843160

        bits_per_modbus_register = 16
        bit_length = bits_per_modbus_register * self.wrapped.size

        name_uuid = str(self.wrapped.parameter_uuid).replace("-", "_")
        members = self.wrapped.children
        array_name = f"staticmodbusBitfieldItems_{name_uuid}"

        h_lines = [
            f"extern InterfaceItem_BitfieldMember {array_name}[{len(members)}];",
        ]

        return h_lines

    def gen_common_interface(self) -> typing.List[str]:
        """
        Generate a static modbus bitfield common definitions for the interface item.

        Returns:
            list: bitfield common definitions
        """
        bits_per_modbus_register = 16
        bit_length = bits_per_modbus_register * self.wrapped.size

        c_lines = [
            f".staticmodbus = {{",
            [
                f".getter = InterfaceItem_bitfield_{bit_length}_staticmodbus_getter,",
                f".setter = InterfaceItem_bitfield_{bit_length}_staticmodbus_setter,",
                ".variable = NULL,",
            ],
            f"}},",
        ]

        return c_lines

    @staticmethod
    def gen_default_common_interface() -> typing.List[str]:
        """
        Generate a default (empty) static modbus bitfield common definitions for the interface item.

        Returns:
            list: default bitfield common definitions
        """
        return [
            f".staticmodbus = {{",
            [
                f".getter = NULL,",
                f".setter = NULL,",
                f".variable = NULL,",
            ],
            f"}},",
        ]

    def gen_bitfield_members_interface(self) -> typing.List[str]:
        """
        Generate a static modbus bitfield member definition.

        Returns:
            list: bitfield member definition
        """
        name_uuid = str(self.wrapped.parameter_uuid).replace("-", "_")
        members = self.wrapped.children
        array_name = f"staticmodbusBitfieldItems_{name_uuid}"

        return [
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
            "",
        ]

    def gen_members_interface(self) -> typing.List[str]:
        """
        Generate the static modbus bitfield member additional definitions.

        Returns:
            list: bitfield member additional definitions
        """
        name_uuid = str(self.wrapped.parameter_uuid).replace("-", "_")
        members = self.wrapped.children
        array_name = f"staticmodbusBitfieldItems_{name_uuid}"

        return [
            f".staticmodbusMembers = {array_name},",
            f".staticmodbusMembersCount = {len(members)},",
        ]


@builders(epcpm.sunspecmodel.DataPointBitfield)
@attr.s
class DataPointBitfield:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self) -> typing.List:
        """
        Generate a SunSpec bitfield variable and bitfield member extern definitions.
        Returns:
            list: bitfield variable and bitfield member extern definitions (.c)
            list: bitfield variable and bitfield member extern definitions (.h)
        """
        name_uuid = str(self.wrapped.parameter_uuid).replace("-", "_")
        members = self.wrapped.children
        array_name = f"sunspecBitfieldItems_{name_uuid}"

        c_lines = []
        h_lines = []

        for member in members:
            member_name_uuid = str(member.parameter_uuid).replace("-", "_")
            variable_name = f"interfaceItem_variable_{member_name_uuid}"
            variable_type = epcpm.parameterstointerface.sunspec_types[
                self.parameter_uuid_finder(member.type_uuid).name
            ]

            h_lines.append(
                f"extern {variable_type} {variable_name};",
            )

            # TODO: initializer that doesn't assume int16_t
            c_lines.append(
                f"{variable_type} {variable_name} = 0;",
            )

        c_lines.append("")
        h_lines.append("")

        h_lines.extend(
            [
                f"extern InterfaceItem_BitfieldMember {array_name}[{len(members)}];",
            ]
        )

        return c_lines, h_lines

    def gen_common_interface(self) -> typing.List[str]:
        """
        Generate a SunSpec bitfield common definitions for the interface item.

        Returns:
            list: bitfield common definitions
        """
        bits_per_modbus_register = 16
        bit_length = bits_per_modbus_register * self.wrapped.size
        model = self.wrapped.tree_parent.tree_parent.id
        parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)

        c_lines = [
            f".sunspec = {{",
            [
                f".getter = InterfaceItem_bitfield_{bit_length}_sunspec_getter,",
                f".setter = InterfaceItem_bitfield_{bit_length}_sunspec_setter,",
                f".variable = &sunspecInterface.model{model:05}.{parameter.abbreviation},",
            ],
            f"}},",
        ]

        return c_lines

    @staticmethod
    def gen_default_common_interface() -> typing.List[str]:
        """
        Generate a default (empty) SunSpec bitfield common definitions for the interface item.

        Returns:
            list: default bitfield common definitions
        """
        return [
            f".sunspec = {{",
            [
                f".getter = NULL,",
                f".setter = NULL,",
                f".variable = NULL,",
            ],
            f"}},",
        ]

    def gen_bitfield_members_interface(self) -> typing.List[str]:
        """
        Generate a SunSpec bitfield member definition.

        Returns:
            list: bitfield member definition
        """
        name_uuid = str(self.wrapped.parameter_uuid).replace("-", "_")
        members = self.wrapped.children
        array_name = f"sunspecBitfieldItems_{name_uuid}"

        return [
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
            "",
        ]

    def gen_members_interface(self) -> typing.List[str]:
        """
        Generate the SunSpec bitfield member additional definitions.

        Returns:
            list: bitfield member additional definitions
        """
        name_uuid = str(self.wrapped.parameter_uuid).replace("-", "_")
        members = self.wrapped.children
        array_name = f"sunspecBitfieldItems_{name_uuid}"

        return [
            f".sunspecMembers = {array_name},",
            f".sunspecMembersCount = {len(members)},",
        ]
