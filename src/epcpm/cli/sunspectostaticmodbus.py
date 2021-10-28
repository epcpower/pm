import click
import csv
import distutils.util
import graham
import uuid

import epcpm.sunspecmodel
import epcpm.staticmodbusmodel


def generate_uuid():
    return str(uuid.uuid4())


def map_type_uuid(input, sunspec_types, staticmodbus_types):
    # Map the type UUID from sunspec type to static modbus type.
    for sunspec_type in sunspec_types.children:
        if input == str(sunspec_type.uuid):
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
    input_sunspec_csv, scale_factor_uuid_map, sunspec_types, staticmodbus_types
):
    # Create root object to store the static modbus model.
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


def create_function_data(
    input_sunspec_data, scale_factor_uuid_map, sunspec_types, staticmodbus_types
):
    function_data = epcpm.staticmodbusmodel.FunctionData()

    if input_sunspec_data["scale_factor_uuid"]:
        function_data.factor_uuid = scale_factor_uuid_map[
            input_sunspec_data["scale_factor_uuid"]
        ]
    else:
        function_data.factor_uuid = None
    function_data.parameter_uuid = (
        input_sunspec_data["parameter_uuid"]
        if input_sunspec_data["parameter_uuid"]
        else None
    )
    function_data.not_implemented = bool(
        distutils.util.strtobool(input_sunspec_data["not_implemented"])
    )
    if input_sunspec_data["type_uuid"]:
        function_data.type_uuid = map_type_uuid(
            input_sunspec_data["type_uuid"], sunspec_types, staticmodbus_types
        )
    else:
        function_data.type_uuid = None
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
    input_sunspec_data, sunspec_types, staticmodbus_types
):
    function_data_bitfield = epcpm.staticmodbusmodel.FunctionDataBitfield()

    function_data_bitfield.parameter_uuid = (
        input_sunspec_data["parameter_uuid"]
        if input_sunspec_data["parameter_uuid"]
        else None
    )
    if input_sunspec_data["type_uuid"]:
        function_data_bitfield.type_uuid = map_type_uuid(
            input_sunspec_data["type_uuid"], sunspec_types, staticmodbus_types
        )
    else:
        function_data_bitfield.type_uuid = None
    function_data_bitfield.size = int(input_sunspec_data["size"])
    # A bitfield is never a scale factor, so no need to check for uuid in scale_factor_uuid_map.
    function_data_bitfield.uuid = generate_uuid()
    function_data_bitfield.address = int(input_sunspec_data["modbus_address"])

    return function_data_bitfield


def create_function_data_bitfield_member(
    input_sunspec_data, sunspec_types, staticmodbus_types
):
    function_data_bitfield_member = epcpm.staticmodbusmodel.FunctionDataBitfieldMember()

    function_data_bitfield_member.parameter_uuid = (
        input_sunspec_data["parameter_uuid"]
        if input_sunspec_data["parameter_uuid"]
        else None
    )
    if input_sunspec_data["type_uuid"]:
        function_data_bitfield_member.type_uuid = map_type_uuid(
            input_sunspec_data["type_uuid"], sunspec_types, staticmodbus_types
        )
    else:
        function_data_bitfield_member.type_uuid = None
    # A bitfield member is never a scale factor, so no need to check for uuid in scale_factor_uuid_map.
    function_data_bitfield_member.uuid = generate_uuid()
    function_data_bitfield_member.bit_offset = int(input_sunspec_data["bit_offset"])
    function_data_bitfield_member.bit_length = int(input_sunspec_data["bit_length"])

    return function_data_bitfield_member


def generate_uuid_mapping_for_scale_factor(input_sunspec_data):
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
def cli(input_sunspec_filename, output_staticmodbus_filename):
    """SunSpec CSV file to static modbus JSON file"""
    sunspec_types = epcpm.sunspecmodel.build_sunspec_types_enumeration()
    staticmodbus_types = epcpm.staticmodbusmodel.build_staticmodbus_types_enumeration()

    with open(input_sunspec_filename, "r", newline="") as csv_file:
        csv_reader = csv.reader(csv_file, quoting=csv.QUOTE_NONNUMERIC)
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
