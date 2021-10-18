import attr
import pathlib
import typing
import epcpm.staticmodbusmodel
import epyqlib.attrsmodel
import epyqlib.utils.general


builders = epyqlib.utils.general.TypeMap()


def export(
    c_path: pathlib.Path,
    h_path: pathlib.Path,
    staticmodbus_model: epyqlib.attrsmodel.Model,
    skip_output: bool,
) -> None:
    """
    Generate the static modbus interface .c and .h files.

    Args:
        c_path: path and filename to generated .c file
        h_path: path and filename to generated .h file
        staticmodbus_model: static modbus model
        skip_output: skip output of the generated files, previously used for skip_sunspec

    Returns:

    """
    builder = builders.wrap(
        wrapped=staticmodbus_model.root,
        parameter_uuid_finder=staticmodbus_model.node_from_uuid,
        c_path=c_path,
        h_path=h_path,
        skip_output=skip_output,
    )

    c_path.parent.mkdir(parents=True, exist_ok=True)
    builder.gen()


@builders(epcpm.staticmodbusmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib(type=epcpm.staticmodbusmodel.Root)
    parameter_uuid_finder = attr.ib(type=typing.Callable)
    c_path = attr.ib(type=pathlib.Path)
    h_path = attr.ib(type=pathlib.Path)
    skip_output = attr.ib(default=False, type=bool)

    def gen(self) -> None:
        """
        Interface generator for the static modbus Root class.
        Writes the .c and .h files.
        Calls generators for Root children.

        Returns:

        """
        c_lines_interface = []

        for member in self.wrapped.children:
            builder = builders.wrap(
                wrapped=member,
                parameter_uuid_finder=self.parameter_uuid_finder,
                skip_output=self.skip_output,
            )
            more_c_lines = builder.gen()
            c_lines_interface.extend(more_c_lines)

        # Add the +2 for the 'SunS' values.
        total_registers = len(c_lines_interface) + 2
        c_lines = [
            '#include "staticmodbusInterfaceGen.h"',
            '#include "interfaceGen.h"',
            "",
            "",
            "// TODO: Create a StaticModbusInterfaceData data section",
            '#pragma DATA_SECTION(staticmodbusAddrRegMap, "SunSpecInterfaceData")',
            f"StaticModbusReg staticmodbusAddrRegMap[{total_registers}] =",
            "{",
            c_lines_interface,
            "};",
        ]

        with self.c_path.open("w", newline="\n") as c_file:
            c_file.write(epcpm.c.format_nested_lists(c_lines).strip())
            c_file.write("\n")

        h_lines = [
            "#ifndef __STATICMODBUS_INTERFACE_GEN_H__",
            "#define __STATICMODBUS_INTERFACE_GEN_H__",
            "",
            '#include "interface.h"',
            "",
            "",
            "typedef enum InterfaceType {",
            "    INTERFACE_TYPE_UNASSIGNED = 0,",
            "    INTERFACE_TYPE_NORMAL = 1,",
            "    INTERFACE_TYPE_TABLE = 2,",
            "} InterfaceType;",
            "",
            "typedef struct StaticModbusReg StaticModbusReg;",
            "struct StaticModbusReg",
            "{",
            "    InterfaceType interfaceType;",
            "    InterfaceItem_void * interface;",
            "};",
            "",
            "#define STATIC_MODBUS_REGISTER_DEFAULTS(...) \\",
            "{ \\",
            "    .interfaceType = INTERFACE_TYPE_UNASSIGNED, \\",
            "    .interface = NULL, \\",
            "    __VA_ARGS__ \\",
            "}",
            "",
            f"extern StaticModbusReg staticmodbusAddrRegMap[{total_registers}];",
            "",
            "#endif //__STATICMODBUS_INTERFACE_GEN_H__",
        ]

        with self.h_path.open("w", newline="\n") as h_file:
            h_file.write(epcpm.c.format_nested_lists(h_lines).strip())
            h_file.write("\n")


@builders(epcpm.staticmodbusmodel.FunctionData)
@attr.s
class FunctionData:
    wrapped = attr.ib(type=epcpm.staticmodbusmodel.FunctionData)
    parameter_uuid_finder = attr.ib(type=typing.Callable)
    skip_output = attr.ib(default=False, type=bool)

    def gen(self) -> typing.List[str]:
        """
        Interface generator for the static modbus FunctionData class.
        Generates the interface items for FunctionData, including tables.

        Returns:
            list: staticmodbusAddrRegMap rows for the generated .c file output
        """
        uses_interface_item = False
        is_table_item = False
        if self.wrapped.parameter_uuid is not None:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)
            uses_interface_item = (
                isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
                and parameter.uses_interface_item()
            )

            # Special handling for TableArrayElement, which ultimately generates a FunctionData object.
            if isinstance(parameter, epyqlib.pm.parametermodel.TableArrayElement):
                is_table_item = True

                # TODO: CAMPid 9655426754319431461354643167
                array_element = parameter.original

                if isinstance(array_element, epyqlib.pm.parametermodel.Parameter):
                    parameter = array_element
                else:
                    parameter = array_element.tree_parent.children[0]

                uses_interface_item = (
                    isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
                    and parameter.uses_interface_item()
                )

        type_node = self.parameter_uuid_finder(self.wrapped.type_uuid)

        # Generate the defined register that returns interfaceItem_<UUID> (or NULL for many cases).
        c_lines = []
        if (
            not self.skip_output
            and uses_interface_item
            and not self.wrapped.not_implemented
            and type_node is not None
            and type_node.name != "staticmodbussf"
        ):
            # TODO: CAMPid 9685439641536675431653179671436
            parameter_uuid = str(self.wrapped.parameter_uuid).replace("-", "_")
            uuid_interface_val = f"&interfaceItem_{parameter_uuid}"

            # Generate one or more ("size") lines with UUID interface.
            for addr_val in range(
                self.wrapped.address, self.wrapped.address + self.wrapped.size
            ):
                if is_table_item:
                    c_line = f"[{addr_val}] = STATIC_MODBUS_REGISTER_DEFAULTS(.interfaceType = INTERFACE_TYPE_TABLE, .interface = {uuid_interface_val}),"
                else:
                    c_line = f"[{addr_val}] = STATIC_MODBUS_REGISTER_DEFAULTS(.interfaceType = INTERFACE_TYPE_NORMAL, .interface = {uuid_interface_val}),"
                c_lines.append(c_line)
        else:
            # Generate one or more ("size") lines with default NULL interface.
            for addr_val in range(
                self.wrapped.address, self.wrapped.address + self.wrapped.size
            ):
                c_line = f"[{addr_val}] = STATIC_MODBUS_REGISTER_DEFAULTS(),"
                c_lines.append(c_line)

        return c_lines


@builders(epcpm.staticmodbusmodel.FunctionDataBitfield)
@attr.s
class FunctionDataBitfield:
    wrapped = attr.ib(type=epcpm.staticmodbusmodel.FunctionDataBitfield)
    parameter_uuid_finder = attr.ib(type=typing.Callable)
    skip_output = attr.ib(default=False, type=bool)

    def gen(self) -> typing.List[str]:
        """
        Interface generator for the static modbus FunctionDataBitfield class.
        Generates the interface items for FunctionDataBitfield.

        Returns:
            list: staticmodbusAddrRegMap rows for the generated .c file output
        """
        # TODO: to be implemented, for now NULL for all FunctionDataBitfield objects
        c_lines = []
        # Generate one or more ("size") lines with NULL interface.
        for addr_val in range(
            self.wrapped.address, self.wrapped.address + self.wrapped.size
        ):
            c_line = f"[{addr_val}] = STATIC_MODBUS_REGISTER_DEFAULTS(),"
            c_lines.append(c_line)

        return c_lines
