import click
import csv
import distutils.util
import graham
import typing
import uuid

import epcpm.sunspecmodel
import epcpm.staticmodbusmodel
import epyqlib.pm.parametermodel


def generate_uuid() -> str:
    """
    Generate a UUID in string format.

    Returns:
        str: UUID
    """
    return str(uuid.uuid4())


def map_type_uuid(
    input_type_uuid: str,
    sunspec_types: epyqlib.pm.parametermodel.Enumeration,
    staticmodbus_types: epyqlib.pm.parametermodel.Enumeration,
) -> str:
    """
    Map the type UUID from SunSpec type to static modbus type.

    Args:
        input_type_uuid: input SunSpec type UUID
        sunspec_types: enum of SunSpec types
        staticmodbus_types: enum of static modbus types

    Returns:
        str: UUID of the static modbus type
    """
    for sunspec_type in sunspec_types.children:
        if input_type_uuid == str(sunspec_type.uuid):
            for staticmodbus_type in staticmodbus_types.children:
                if sunspec_type.name == staticmodbus_type.name:
                    return str(staticmodbus_type.uuid)
                elif (
                    sunspec_type.name == "sunssf"
                    and staticmodbus_type.name == "staticmodbussf"
                ):
                    # Special case for scale factor, which isn't the same name.
                    return str(staticmodbus_type.uuid)
    raise ValueError("Error: failure to map type")


def create_data_objects(
    input_sunspec_csv: typing.List[typing.Dict[str, str]],
    scale_factor_uuid_map: typing.Dict[str, str],
    sunspec_types: epyqlib.pm.parametermodel.Enumeration,
    staticmodbus_types: epyqlib.pm.parametermodel.Enumeration,
) -> epcpm.staticmodbusmodel.Root:
    """
    Given the input SunSpec CSV data, transform and generate data objects for the output static modbus root.

    Args:
        input_sunspec_csv: input SunSpec CSV data structure
        scale_factor_uuid_map: map of SunSpec to static modbus scale factor UUID's
        sunspec_types: enum of SunSpec types
        staticmodbus_types: enum of static modbus types

    Returns:
        Root: root object to store the static modbus model
    """
    root = epcpm.staticmodbusmodel.Root()

    # Transform input data from sunspec to staticmodbus output.
    last_bitfield_parent = None
    for data_row in input_sunspec_csv:
        # Determine the type of data object to create and then create the object and return it.
        if data_row["class_name"] == epcpm.sunspecmodel.DataPoint.__name__:
            root_child = create_function_data(
                data_row, scale_factor_uuid_map, sunspec_types, staticmodbus_types
            )
            root.children.append(root_child)
        elif data_row["class_name"] == epcpm.sunspecmodel.DataPointBitfield.__name__:
            last_bitfield_parent = create_function_data_bitfield(
                data_row, sunspec_types, staticmodbus_types
            )
            root.children.append(last_bitfield_parent)
        elif (
            data_row["class_name"]
            == epcpm.sunspecmodel.DataPointBitfieldMember.__name__
        ):
            root_child = create_function_data_bitfield_member(
                data_row, sunspec_types, staticmodbus_types
            )
            assert (
                last_bitfield_parent is not None
            ), "There is no parent bitfield for connection to child bitfield member"
            last_bitfield_parent.children.append(root_child)
        elif (
            data_row["class_name"]
            == epcpm.sunspecmodel.TableRepeatingBlockReferenceDataPointReference.__name__
        ):
            root_child = create_function_data(
                data_row, scale_factor_uuid_map, sunspec_types, staticmodbus_types
            )
            root.children.append(root_child)
        else:
            raise ValueError(
                f"Unsupported class_name '{data_row['class_name']}' in create_data"
            )

    return root


def set_common_staticmodbus_node_data(
    staticmodbus_node: typing.Union[
        epcpm.staticmodbusmodel.FunctionData,
        epcpm.staticmodbusmodel.FunctionDataBitfield,
        epcpm.staticmodbusmodel.FunctionDataBitfieldMember,
    ],
    input_sunspec_data: typing.List[typing.Dict[str, str]],
    sunspec_types: epyqlib.pm.parametermodel.Enumeration,
    staticmodbus_types: epyqlib.pm.parametermodel.Enumeration,
):
    """
    Given the input SunSpec CSV data, sets common values to the given static modbus node.

    Args:
        staticmodbus_node: static modbus node on which to set common values
        input_sunspec_data: input SunSpec CSV data structure
        sunspec_types: enum of SunSpec types
        staticmodbus_types: enum of static modbus types

    Returns:

    """
    staticmodbus_node.parameter_uuid = (
        input_sunspec_data["parameter_uuid"]
        if input_sunspec_data["parameter_uuid"]
        else None
    )
    if input_sunspec_data["type_uuid"]:
        staticmodbus_node.type_uuid = map_type_uuid(
            input_sunspec_data["type_uuid"], sunspec_types, staticmodbus_types
        )
    else:
        staticmodbus_node.type_uuid = None


def create_function_data(
    input_sunspec_data: typing.List[typing.Dict[str, str]],
    scale_factor_uuid_map: typing.Dict[str, str],
    sunspec_types: epyqlib.pm.parametermodel.Enumeration,
    staticmodbus_types: epyqlib.pm.parametermodel.Enumeration,
) -> epcpm.staticmodbusmodel.FunctionData:
    """
    Given the input SunSpec CSV data, transform and generate FunctionData objects for the output static modbus.

    Args:
        input_sunspec_data: input SunSpec CSV data structure
        scale_factor_uuid_map: map of SunSpec to static modbus scale factor UUID's
        sunspec_types: enum of SunSpec types
        staticmodbus_types: enum of static modbus types

    Returns:
        FunctionData: object to store in the static modbus model
    """
    function_data = epcpm.staticmodbusmodel.FunctionData()
    set_common_staticmodbus_node_data(
        function_data, input_sunspec_data, sunspec_types, staticmodbus_types
    )
    if input_sunspec_data["scale_factor_uuid"]:
        function_data.factor_uuid = scale_factor_uuid_map[
            input_sunspec_data["scale_factor_uuid"]
        ]
    else:
        function_data.factor_uuid = None
    function_data.not_implemented = bool(
        distutils.util.strtobool(input_sunspec_data["not_implemented"])
    )
    function_data.size = int(input_sunspec_data["size"])
    function_data.enumeration_uuid = (
        input_sunspec_data["enumeration_uuid"]
        if input_sunspec_data["enumeration_uuid"]
        else None
    )
    function_data.units = (
        input_sunspec_data["units"] if input_sunspec_data["units"] else None
    )
    if input_sunspec_data["uuid"] in scale_factor_uuid_map:
        # This is a scale factor UUID, so set UUID to the newly generated UUID value.
        function_data.uuid = scale_factor_uuid_map[input_sunspec_data["uuid"]]
    else:
        function_data.uuid = generate_uuid()
    function_data.address = int(input_sunspec_data["modbus_address"])

    return function_data


def create_function_data_bitfield(
    input_sunspec_data: typing.List[typing.Dict[str, str]],
    sunspec_types: epyqlib.pm.parametermodel.Enumeration,
    staticmodbus_types: epyqlib.pm.parametermodel.Enumeration,
) -> epcpm.staticmodbusmodel.FunctionDataBitfield:
    """
    Given the input SunSpec CSV data, transform and generate FunctionDataBitfield objects for the output static modbus.

    Args:
        input_sunspec_data: input SunSpec CSV data structure
        sunspec_types: enum of SunSpec types
        staticmodbus_types: enum of static modbus types

    Returns:
        FunctionDataBitfield: object to store in the static modbus model
    """
    function_data_bitfield = epcpm.staticmodbusmodel.FunctionDataBitfield()
    set_common_staticmodbus_node_data(
        function_data_bitfield, input_sunspec_data, sunspec_types, staticmodbus_types
    )
    function_data_bitfield.uuid = generate_uuid()
    function_data_bitfield.size = int(input_sunspec_data["size"])
    function_data_bitfield.address = int(input_sunspec_data["modbus_address"])

    return function_data_bitfield


def create_function_data_bitfield_member(
    input_sunspec_data: typing.List[typing.Dict[str, str]],
    sunspec_types: epcpm.staticmodbusmodel.FunctionDataBitfield,
    staticmodbus_types: epcpm.staticmodbusmodel.FunctionDataBitfield,
) -> epcpm.staticmodbusmodel.FunctionDataBitfieldMember:
    """
    Given the input SunSpec CSV data, transform and generate FunctionDataBitfieldMember objects for the output static modbus.

    Args:
        input_sunspec_data: input SunSpec CSV data structure
        sunspec_types: enum of SunSpec types
        staticmodbus_types: enum of static modbus types

    Returns:
        FunctionDataBitfieldMember: object to store in the static modbus model
    """
    function_data_bitfield_member = epcpm.staticmodbusmodel.FunctionDataBitfieldMember()
    set_common_staticmodbus_node_data(
        function_data_bitfield_member,
        input_sunspec_data,
        sunspec_types,
        staticmodbus_types,
    )
    function_data_bitfield_member.uuid = generate_uuid()
    function_data_bitfield_member.bit_offset = int(input_sunspec_data["bit_offset"])
    function_data_bitfield_member.bit_length = int(input_sunspec_data["bit_length"])

    return function_data_bitfield_member


def generate_uuid_mapping_for_scale_factor(
    input_sunspec_data: typing.List[typing.Dict[str, str]]
) -> typing.Dict[str, str]:
    """
    Generates map of SunSpec to static modbus scale factor UUID's.

    Args:
        input_sunspec_data: input SunSpec CSV data structure

    Returns:
        dict: map of SunSpec to static modbus scale factor UUID's
    """
    uuid_map_for_sf = dict()
    for data_row in input_sunspec_data:
        if data_row["type"] == "sunssf":
            uuid_map_for_sf.setdefault(data_row["uuid"], generate_uuid())
    return uuid_map_for_sf


@click.command()
@click.option(
    "--input-sunspec-filename",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
    required=True,
)
@click.option(
    "--output-staticmodbus-filename",
    type=click.Path(dir_okay=False, resolve_path=True),
    required=True,
)
def cli(input_sunspec_filename: str, output_staticmodbus_filename: str) -> None:
    """
    Transforms input SunSpec CSV file to a static modbus JSON file.

    Args:
        input_sunspec_filename: input SunSpec CSV path and file name
        output_staticmodbus_filename: output static modbus JSON path and file name

    Returns:

    """
    sunspec_types = epcpm.sunspecmodel.build_sunspec_types_enumeration()
    staticmodbus_types = epcpm.staticmodbusmodel.build_staticmodbus_types_enumeration()

    with open(input_sunspec_filename, "r", newline="") as csv_file:
        csv_reader = csv.reader(csv_file, quoting=csv.QUOTE_NONNUMERIC)
        # These keys should match the fields defined in the sunspectocsv export located in importexport.py.
        keys = [
            "size",
            "name",
            "label",
            "type",
            "units",
            "bit_offset",
            "bit_length",
            "modbus_address",
            "parameter_uuid",
            "parameter_uses_interface_item",
            "scale_factor_uuid",
            "enumeration_uuid",
            "type_uuid",
            "not_implemented",
            "uuid",
            "class_name",
        ]
        # Convert list of lists to list of dictionaries, using the keys above.
        input_sunspec_csv = [dict(zip(keys, l)) for l in csv_reader]

        # Generate new uuid's for scale factors, which are used in transformation below.
        scale_factor_uuid_map = generate_uuid_mapping_for_scale_factor(
            input_sunspec_csv
        )

        # Create root object to store the static modbus model.
        # Transform input data from sunspec into staticmodbus output.
        root = create_data_objects(
            input_sunspec_csv, scale_factor_uuid_map, sunspec_types, staticmodbus_types
        )

        # Output staticmodbus JSON file using graham.
        with open(output_staticmodbus_filename, "w", newline="\n") as f:
            # JSON file indents are 4 spaces.
            staticmodbus_out = graham.dumps(root, indent=4).data
            f.write(staticmodbus_out)

            if not staticmodbus_out.endswith("\n"):
                f.write("\n")
