import click
import json
import uuid

import epcpm.sunspecmodel
import epcpm.staticmodbusmodel


def generate_uuid():
    return str(uuid.uuid4())


def replace_data_point_with_function_data(input):
    return input.replace("data_point", "function_data")


def map_type_uuid(input, sunspec_types, staticmodbus_types):
    # Map the type UUID from sunspec type to static modbus type.
    for sunspec_type in sunspec_types.children:
        if input["type_uuid"] == str(sunspec_type.uuid):
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


def parse_sunspec_data_point(
    data_point,
    sunspec_types,
    staticmodbus_types,
    table_ref_uuid_map=None,
    scale_factor_uuid_map=None,
):
    print(f"data_point UUID: {data_point['uuid']}")
    data_point["_type"] = replace_data_point_with_function_data(data_point["_type"])
    data_point["type_uuid"] = map_type_uuid(
        data_point, sunspec_types, staticmodbus_types
    )

    if table_ref_uuid_map is not None:
        # UUID comes from table reference.
        data_point["uuid"] = table_ref_uuid_map[data_point["uuid"]]
    elif scale_factor_uuid_map is not None:
        if data_point["factor_uuid"] is not None:
            # Scale Factor UUID comes from scale factor map.
            data_point["factor_uuid"] = scale_factor_uuid_map[data_point["factor_uuid"]]
        if data_point["uuid"] in scale_factor_uuid_map:
            # UUID comes from scale factor map.
            data_point["uuid"] = scale_factor_uuid_map[data_point["uuid"]]
        else:
            # UUID generated normally.
            data_point["uuid"] = generate_uuid()
    else:
        # UUID generated normally.
        data_point["uuid"] = generate_uuid()

    del data_point["hand_coded_getter"]
    del data_point["hand_coded_setter"]
    del data_point["block_offset"]
    del data_point["get"]
    del data_point["set"]
    del data_point["mandatory"]

    return data_point


def parse_sunspec_data_point_bitfield(data_point_bitfield):
    found_data = []
    for child in data_point_bitfield["children"]:
        if child["_type"] == "data_point_bitfield_member":
            print(f"data_point_bitfield_member UUID: {child['uuid']}")
            child["_type"] = replace_data_point_with_function_data(child["_type"])
            child["uuid"] = generate_uuid()
            found_data.append(child)
        else:
            print(
                f"Encountered non data_point_bitfield_member in data_point_bitfield: {child['_type']}"
            )

    return found_data


def parse_sunspec_header_block(sunspec_header_block, sunspec_types, staticmodbus_types):
    found_data = []
    for child in sunspec_header_block["children"]:
        if child["_type"] == "data_point":
            found_data.append(
                parse_sunspec_data_point(child, sunspec_types, staticmodbus_types)
            )
        else:
            print(
                f"Encountered non data_point in sunspec_header_block: {child['_type']}"
            )

    return found_data


def parse_sunspec_fixed_block(
    sunspec_fixed_block, sunspec_types, staticmodbus_types, scale_factor_uuid_map
):
    found_data = []
    for child in sunspec_fixed_block["children"]:
        if child["_type"] == "data_point":
            found_data.append(
                parse_sunspec_data_point(
                    child,
                    sunspec_types,
                    staticmodbus_types,
                    scale_factor_uuid_map=scale_factor_uuid_map,
                )
            )
        elif child["_type"] == "data_point_bitfield":
            child["_type"] = replace_data_point_with_function_data(child["_type"])
            del child["block_offset"]
            child["children"] = parse_sunspec_data_point_bitfield(child)
            found_data.append(child)
        else:
            print(
                f"Encountered non data_point in sunspec_fixed_block: {child['_type']}"
            )

    return found_data


def parse_sunspec_table_repeating_block(
    sunspec_table_repeating_block, table_ref_uuid_map, scale_factor_uuid_map
):
    # Original UUID comes from table reference.
    replace_original = table_ref_uuid_map[sunspec_table_repeating_block["original"]]
    staticmodbus_trb = {
        "_type": "staticmodbus_table_repeating_block",
        "name": sunspec_table_repeating_block["name"],
        "children": [],
        "original": replace_original,
        "uuid": generate_uuid(),
    }
    for child in sunspec_table_repeating_block["children"]:
        if (
            child["_type"]
            == "sunspec_table_repeating_block_reference_data_point_reference"
        ):
            print(f"data_point (repeating block) UUID: {child['uuid']}")
            child[
                "_type"
            ] = "staticmodbus_table_repeating_block_reference_function_data_reference"

            if scale_factor_uuid_map is not None:
                if child["factor_uuid"] is not None:
                    # Scale Factor UUID comes from scale factor map.
                    child["factor_uuid"] = scale_factor_uuid_map[child["factor_uuid"]]
                if child["uuid"] in scale_factor_uuid_map:
                    # UUID comes from scale factor map.
                    child["uuid"] = scale_factor_uuid_map[child["uuid"]]
                else:
                    # UUID generated normally.
                    child["uuid"] = generate_uuid()
            else:
                # UUID generated normally.
                child["uuid"] = generate_uuid()

            child["original"] = table_ref_uuid_map[child["original"]]
            staticmodbus_trb["children"].append(child)
        else:
            print(
                f"Encountered non data_point in sunspec_table_repeating_block: {child['_type']}"
            )

    return [staticmodbus_trb]


def parse_sunspec_model(
    sunspec_model,
    sunspec_types,
    staticmodbus_types,
    table_ref_uuid_map,
    scale_factor_uuid_map,
):
    found_data = []
    for child in sunspec_model["children"]:
        if child["_type"] == "sunspec_header_block":
            found_child_data = parse_sunspec_header_block(
                child, sunspec_types, staticmodbus_types
            )
        elif child["_type"] == "sunspec_fixed_block":
            found_child_data = parse_sunspec_fixed_block(
                child, sunspec_types, staticmodbus_types, scale_factor_uuid_map
            )
        elif child["_type"] == "sunspec_table_repeating_block":
            found_child_data = parse_sunspec_table_repeating_block(
                child, table_ref_uuid_map, scale_factor_uuid_map
            )
        else:
            print(f"ERROR: unexpected sunspec_model child: {child['_type']}")
        found_data.extend(found_child_data)

    return found_data


def parse_table(table, sunspec_types, staticmodbus_types, table_ref_uuid_map):
    # Only replace data_point with function_data for all children.
    for child in table["children"]:
        if child["_type"] == "data_point":
            child = parse_sunspec_data_point(
                child,
                sunspec_types,
                staticmodbus_types,
                table_ref_uuid_map=table_ref_uuid_map,
            )
        elif child["_type"] == "table_model_reference":
            for ref_child in child["children"]:
                if ref_child["_type"] == "data_point":
                    ref_child = parse_sunspec_data_point(
                        ref_child, sunspec_types, staticmodbus_types
                    )
            child["uuid"] = table_ref_uuid_map[child["uuid"]]
            del child["abbreviation"]
    table["uuid"] = generate_uuid()


def generate_uuid_mapping_for_table_ref(table):
    uuid_map_for_table_ref = dict()
    for child in table["children"]:
        if child["_type"] == "data_point" or child["_type"] == "table_model_reference":
            uuid_map_for_table_ref.setdefault(child["uuid"], generate_uuid())

    return uuid_map_for_table_ref


def generate_uuid_mapping_for_scale_factor(input_json, sunspec_types):
    for sunspec_type in sunspec_types.children:
        if sunspec_type.name == "sunssf":
            sunssf_type_uuid = sunspec_type.uuid
    return _generate_uuid_mapping_for_scale_factor(input_json, str(sunssf_type_uuid))


def _generate_uuid_mapping_for_scale_factor(input_json, sunssf_type_uuid_str):
    uuid_map_for_sf = dict()
    for child in input_json:
        if (
            child["_type"] == "data_point"
            and child["type_uuid"] == sunssf_type_uuid_str
        ):
            uuid_map_for_sf.setdefault(child["uuid"], generate_uuid())
        elif "children" in child:
            uuid_map_for_sf_in = _generate_uuid_mapping_for_scale_factor(
                child["children"], sunssf_type_uuid_str
            )
            uuid_map_for_sf.update(uuid_map_for_sf_in)

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
    """SunSpec JSON file to static modbus JSON file"""
    sunspec_types = epcpm.sunspecmodel.build_sunspec_types_enumeration()
    staticmodbus_types = epcpm.staticmodbusmodel.build_staticmodbus_types_enumeration()
    data = {
        "_type": "root",
        "name": "Static Modbus",
        "children": [],
        "uuid": generate_uuid(),
    }
    with open(input_sunspec_filename, "r") as input_sunspec_fp:
        input_sunspec_json = json.load(input_sunspec_fp)
        if input_sunspec_json["_type"] == "root":
            # Generate new uuid's for table references, which are used in transformation below.
            table_ref_uuid_map = dict()
            for root_child in input_sunspec_json["children"]:
                if root_child["_type"] == "table":
                    uuid_map_for_table_ref = generate_uuid_mapping_for_table_ref(
                        root_child
                    )
                    table_ref_uuid_map.update(uuid_map_for_table_ref)

            # Generate new uuid's for scale factors, which are used in transformation below.
            scale_factor_uuid_map = generate_uuid_mapping_for_scale_factor(
                input_sunspec_json["children"], sunspec_types
            )

            # Transform from sunspec to staticmodbus.
            for root_child in input_sunspec_json["children"]:
                if root_child["_type"] == "sunspec_model":
                    found_data = parse_sunspec_model(
                        root_child,
                        sunspec_types,
                        staticmodbus_types,
                        table_ref_uuid_map,
                        scale_factor_uuid_map,
                    )
                    data["children"].extend(found_data)
                elif root_child["_type"] == "table":
                    parse_table(
                        root_child,
                        sunspec_types,
                        staticmodbus_types,
                        table_ref_uuid_map,
                    )
                    data["children"].append(root_child)
                else:
                    print(f"ERROR: unexpected root child: {root_child['_type']}")

    with open(
        output_staticmodbus_filename, "w", encoding="utf-8"
    ) as output_staticmodbus_fp:
        json.dump(data, output_staticmodbus_fp, ensure_ascii=False, indent=4)
