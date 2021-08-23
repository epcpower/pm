import click
import csv
import distutils.util
import json
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


def create_function_data(
    input_sunspec_data, scale_factor_uuid_map, sunspec_types, staticmodbus_types
):
    function_data = dict()
    # TODO: This will likely be be split up into a separate method when bitfields and tables are implemented.
    if input_sunspec_data["class_name"] == "DataPoint":
        function_data["_type"] = "function_data"
    elif input_sunspec_data["class_name"] == "DataPointBitfield":
        function_data["_type"] = "function_data_bitfield"
    else:
        function_data[
            "_type"
        ] = f"Unsupported class_name '{input_sunspec_data['class_name']}' in create_function_data."
    if input_sunspec_data["scale_factor_uuid"]:
        function_data["factor_uuid"] = scale_factor_uuid_map[
            input_sunspec_data["scale_factor_uuid"]
        ]
    else:
        function_data["factor_uuid"] = None
    function_data["parameter_uuid"] = (
        input_sunspec_data["parameter_uuid"]
        if input_sunspec_data["parameter_uuid"]
        else None
    )
    function_data["not_implemented"] = bool(
        distutils.util.strtobool(input_sunspec_data["not_implemented"])
    )
    if input_sunspec_data["type_uuid"]:
        function_data["type_uuid"] = map_type_uuid(
            input_sunspec_data["type_uuid"], sunspec_types, staticmodbus_types
        )
    else:
        function_data["type_uuid"] = None
    function_data["size"] = int(input_sunspec_data["size"])
    function_data["enumeration_uuid"] = (
        input_sunspec_data["enumeration_uuid"]
        if input_sunspec_data["enumeration_uuid"]
        else None
    )
    function_data["units"] = (
        input_sunspec_data["units"] if input_sunspec_data["units"] else None
    )
    if input_sunspec_data["uuid"] in scale_factor_uuid_map:
        # This is a scale factor UUID, so set UUID to the newly generated UUID value.
        function_data["uuid"] = scale_factor_uuid_map[input_sunspec_data["uuid"]]
    else:
        function_data["uuid"] = generate_uuid()
    function_data["address"] = int(input_sunspec_data["modbus_address"])

    return function_data


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
    data = {
        "_type": "root",
        "name": "Static Modbus",
        "children": [],
        "uuid": generate_uuid(),
    }

    with open(input_sunspec_filename, "r", newline="") as csv_file:
        csv_reader = csv.reader(csv_file, quoting=csv.QUOTE_NONNUMERIC)
        keys = [
            "size",
            "name",
            "label",
            "type",
            "units",
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

        # Transform input data from sunspec to staticmodbus output.
        for data_row in input_sunspec_csv:
            root_child = create_function_data(
                data_row, scale_factor_uuid_map, sunspec_types, staticmodbus_types
            )
            data["children"].append(root_child)

        # Output staticmodbus JSON file.
        with open(
            output_staticmodbus_filename, "w", encoding="utf-8"
        ) as output_staticmodbus_fp:
            json.dump(data, output_staticmodbus_fp, ensure_ascii=False, indent=4)
