import attr
import pathlib
import typing
import epcpm.pm_helper
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
        # Add the initial two registers for the 'SunS' values, which form two 16-bit words.
        # These registers are reserved in static modbus because of their functionality in SunSpec.
        # It is possible they could be used by static modbus in the future.
        c_lines_interface = [
            "[0] = STATIC_MODBUS_REGISTER_DEFAULTS(),",
            "[1] = STATIC_MODBUS_REGISTER_DEFAULTS(),",
        ]

        for member in self.wrapped.children:
            builder = builders.wrap(
                wrapped=member,
                parameter_uuid_finder=self.parameter_uuid_finder,
                skip_output=self.skip_output,
            )
            more_c_lines = builder.gen()
            c_lines_interface.extend(more_c_lines)

        total_registers = len(c_lines_interface)
        c_lines = [
            '#include "staticmodbusInterfaceGen.h"',
            '#include "interfaceBitfieldsGen.h"',
            '#include "interfaceGen.h"',
            "",
            "",
            '#pragma DATA_SECTION(staticmodbusAddrRegMap, "ModbusInterfaceData")',
            f"StaticModbusReg staticmodbusAddrRegMap[{total_registers}] =",
            "{",
            c_lines_interface,
            "};",
        ]

        with self.c_path.open("w", newline="\n") as c_file:
            c_file.write(epcpm.c.format_nested_lists(c_lines).strip())
            c_file.write("\n")

        h_lines = [
            "#ifndef STATICMODBUS_INTERFACE_GEN_H",
            "#define STATICMODBUS_INTERFACE_GEN_H",
            "",
            '#include "interface.h"',
            "",
            "",
            "typedef enum InterfaceType {",
            "    INTERFACE_TYPE_UNASSIGNED   = 0,",
            "    INTERFACE_TYPE_NORMAL       = 1,",
            "    INTERFACE_TYPE_TABLE        = 2,",
            "    INTERFACE_TYPE_BITFIELD     = 3,",
            "} InterfaceType;",
            "",
            "typedef struct StaticModbusReg {",
            "    InterfaceType               interfaceType;",
            "    InterfaceItem_void         *interface;",
            "} StaticModbusReg;",
            "",
            "#define STATIC_MODBUS_REGISTER_DEFAULTS(...) {                  \\",
            "    .interfaceType              = INTERFACE_TYPE_UNASSIGNED,    \\",
            "    .interface                  = NULL,                         \\",
            "    __VA_ARGS__                                                 \\",
            "}",
            "",
            f"extern StaticModbusReg staticmodbusAddrRegMap[{total_registers}];",
            "",
            "#endif /* STATICMODBUS_INTERFACE_GEN_H */",
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
        ):
            parameter_uuid = epcpm.pm_helper.convert_uuid_to_variable_name(
                self.wrapped.parameter_uuid
            )
            uuid_interface_val = f"&interfaceItem_{parameter_uuid}"

            # Generate one or more ("size") lines with UUID interface.
            for addr_val in range(
                self.wrapped.address, self.wrapped.address + self.wrapped.size
            ):
                if is_table_item:
                    c_line = f"[{addr_val}] = STATIC_MODBUS_REGISTER_DEFAULTS(.interfaceType = INTERFACE_TYPE_TABLE, .interface = (InterfaceItem_void *){uuid_interface_val}),"
                else:
                    c_line = f"[{addr_val}] = STATIC_MODBUS_REGISTER_DEFAULTS(.interfaceType = INTERFACE_TYPE_NORMAL, .interface = (InterfaceItem_void *){uuid_interface_val}),"
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
        parameter_uuid = epcpm.pm_helper.convert_uuid_to_variable_name(
            self.wrapped.parameter_uuid
        )
        uuid_interface_val = f"&interfaceItem_{parameter_uuid}"
        c_lines = []
        # Generate one or more ("size") lines with NULL interface.
        for addr_val in range(
            self.wrapped.address, self.wrapped.address + self.wrapped.size
        ):
            if not self.skip_output:
                c_line = f"[{addr_val}] = STATIC_MODBUS_REGISTER_DEFAULTS(.interfaceType = INTERFACE_TYPE_BITFIELD, .interface = (InterfaceItem_void *){uuid_interface_val}),"
            else:
                c_line = f"[{addr_val}] = STATIC_MODBUS_REGISTER_DEFAULTS(),"
            c_lines.append(c_line)

        return c_lines
