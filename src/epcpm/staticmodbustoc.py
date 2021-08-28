import attr

import epcpm.staticmodbusmodel
import epyqlib.utils.general


builders = epyqlib.utils.general.TypeMap()


def export(c_path, h_path, staticmodbus_model):
    builder = builders.wrap(
        wrapped=staticmodbus_model.root,
        parameter_uuid_finder=staticmodbus_model.node_from_uuid,
        c_path=c_path,
        h_path=h_path,
    )

    c_path.parent.mkdir(parents=True, exist_ok=True)
    builder.gen()


def gen(self, first=0):
    lines = []

    for member in self.wrapped.children[first:]:
        builder = builders.wrap(
            wrapped=member,
            parameter_uuid_finder=self.parameter_uuid_finder,
            c_path=self.c_path,
            h_path=self.h_path,
        )
        lines.extend(builder.gen())
        lines.append("")

    return lines


@builders(epcpm.staticmodbusmodel.Root)
@attr.s
class Root:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()
    c_path = attr.ib()
    h_path = attr.ib()

    def gen(self):
        with self.h_path.open("w", newline="\n") as h_file:
            h_file.write("#ifndef __STATICMODBUS_INTERFACE_GEN_H__\n")
            h_file.write("#define __STATICMODBUS_INTERFACE_GEN_H__\n\n")
            h_file.write('#include "interface.h"\n\n')
            h_file.write(
                "extern InterfaceItem_void * const staticmodbusAddrRegMap[];\n"
            )
            h_file.write("\n#endif //__STATICMODBUS_INTERFACE_GEN_H__\n")

        with self.c_path.open("w", newline="\n") as c_file:
            c_file.write('#include "staticmodbusInterfaceGen.h"\n')
            c_file.write('#include "interfaceGen.h"\n\n')
            c_file.write("InterfaceItem_void * const staticmodbusAddrRegMap[] = \n{\n")

            current_addr = 0
            for member in self.wrapped.children:
                builder = builders.wrap(
                    wrapped=member,
                    parameter_uuid_finder=self.parameter_uuid_finder,
                )

                addr_val, c_line = builder.gen()

                # Fill the undefined registers to return NULL.
                while current_addr < addr_val:
                    null_line = f"    [{current_addr}] = NULL,\n"
                    c_file.write(null_line)
                    current_addr += 1
                # Write the defined register that returns interfaceItem_<UUID>.
                c_file.write(c_line)
                # Update the current address for the next undefined register fill.
                current_addr = addr_val + 1

            c_file.write("};\n\n")


@builders(epcpm.staticmodbusmodel.FunctionData)
@attr.s
class FunctionData:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        uses_interface_item = False
        if self.wrapped.parameter_uuid is not None:
            parameter = self.parameter_uuid_finder(self.wrapped.parameter_uuid)
            uses_interface_item = (
                isinstance(parameter, epyqlib.pm.parametermodel.Parameter)
                and parameter.uses_interface_item()
            )

        type_node = self.parameter_uuid_finder(self.wrapped.type_uuid)

        # Generate the defined register that returns interfaceItem_<UUID> (or NULL for some cases).
        if (
            uses_interface_item
            and not self.wrapped.not_implemented
            and type_node is not None
            and type_node.name != "staticmodbussf"
        ):
            # TODO: CAMPid 9685439641536675431653179671436
            parameter_uuid = str(self.wrapped.parameter_uuid).replace("-", "_")
            uuid_interface_val = f"&interfaceItem_{parameter_uuid}"
        else:
            uuid_interface_val = "NULL"
        addr_val = self.wrapped.address
        c_line = f"    [{addr_val}] = {uuid_interface_val},\n"

        return addr_val, c_line


@builders(epcpm.staticmodbusmodel.FunctionDataBitfield)
@attr.s
class FunctionDataBitfield:
    wrapped = attr.ib()
    parameter_uuid_finder = attr.ib()

    def gen(self):
        # NULL for all FunctionDataBitfield objects.
        addr_val = self.wrapped.address
        c_line = f"    [{addr_val}] = NULL,\n"

        return addr_val, c_line
