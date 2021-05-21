import click
import json


def replace_data_point_with_function_data(input):
    return input.replace('data_point', 'function_data')

def parse_data_point_bitfield(data_point_bitfield):
    found_data = []
    for child in data_point_bitfield['children']:
        if child['_type'] == 'data_point_bitfield_member':
            print(f"data_point_bitfield_member UUID: {child['uuid']}")
            child['_type'] = replace_data_point_with_function_data(child['_type'])
            found_data.append(child)
        else:
            print(f"Encountered non data_point_bitfield_member in data_point_bitfield: {child['_type']}")

    return found_data


def parse_sunspec_header_block(sunspec_header_block):
    found_data = []
    for child in sunspec_header_block['children']:
        if child['_type'] == 'data_point':
            print(f"data_point UUID: {child['uuid']}")
            child['_type'] = replace_data_point_with_function_data(child['_type'])
            found_data.append(child)
        else:
            print(f"Encountered non data_point in sunspec_header_block: {child['_type']}")

    return found_data


def parse_sunspec_fixed_block(sunspec_fixed_block):
    found_data = []
    for child in sunspec_fixed_block['children']:
        if child['_type'] == 'data_point':
            print(f"data_point UUID: {child['uuid']}")
            child['_type'] = replace_data_point_with_function_data(child['_type'])
            found_data.append(child)
        elif child['_type'] == 'data_point_bitfield':
            found_child_data = parse_data_point_bitfield(child)
            # Chop out children key-value pair.
            stripped_child = {key: val for key, val in child.items() if key != 'children'}
            stripped_child['_type'] = replace_data_point_with_function_data(stripped_child['_type'])
            found_data.append(stripped_child)
            found_data.extend(found_child_data)
        else:
            print(f"Encountered non data_point in sunspec_fixed_block: {child['_type']}")

    return found_data


def parse_sunspec_table_repeating_block(sunspec_table_repeating_block):
    found_data = []
    for child in sunspec_table_repeating_block['children']:
        if child['_type'] == 'sunspec_table_repeating_block_reference_data_point_reference':
            print(f"data_point (repeating block) UUID: {child['uuid']}")
            # child['_type'] = replace_data_point_with_function_data(child['_type'])
            child['_type'] = 'staticmodbus_table_repeating_block_reference_function_data_reference'
            found_data.append(child)
        else:
            print(f"Encountered non data_point in sunspec_table_repeating_block: {child['_type']}")

    return found_data


def parse_sunspec_model(sunspec_model):
    found_data = []
    for child in sunspec_model['children']:
        if child['_type'] == 'sunspec_header_block':
            found_child_data = parse_sunspec_header_block(child)
        elif child['_type'] == 'sunspec_fixed_block':
            found_child_data = parse_sunspec_fixed_block(child)
        elif child['_type'] == 'sunspec_table_repeating_block':
            found_child_data = parse_sunspec_table_repeating_block(child)
        else:
            print(f"ERROR: unexpected sunspec_model child: {child['_type']}")
        found_data.extend(found_child_data)

    return found_data


def parse_table(table):
    # Only replace data_point with function_data for all children.
    for child in table['children']:
        if child['_type'] == 'data_point':
            child['_type'] = replace_data_point_with_function_data(child['_type'])
        elif child['_type'] == 'table_model_reference':
            for ref_child in child['children']:
                if ref_child['_type'] == 'data_point':
                    ref_child['_type'] = replace_data_point_with_function_data(ref_child['_type'])


@click.command()
@click.option('--input_sunspec_filename')
@click.option('--output_staticmodbus_filename')
def sunspec_to_staticmodbus_generator(input_sunspec_filename, output_staticmodbus_filename):
    # The purpose of this script is to take as input the sunspec JSON file and
    # output a comparable static modbus JSON file.
    # It is most likely one time use code.
    data = {
        "_type": "root",
        "name": "Static Modbus",
        "children": [],
        "uuid": "7cb2d0b2-acd9-4e7f-b785-23f667d4a4df",
    }
    with open(input_sunspec_filename, "r") as input_sunspec_fp:
        input_sunspec_json = json.load(input_sunspec_fp)
        if input_sunspec_json['_type'] == 'root':
            for root_child in input_sunspec_json['children']:
                if root_child['_type'] == 'sunspec_model':
                    found_data = parse_sunspec_model(root_child)
                    data["children"].extend(found_data)
                elif root_child['_type'] == 'table':
                    parse_table(root_child)
                    data["children"].append(root_child)
                else:
                    print(f"ERROR: unexpected root child: {root_child['_type']}")

    with open(output_staticmodbus_filename, 'w', encoding='utf-8') as output_staticmodbus_fp:
        json.dump(data, output_staticmodbus_fp, ensure_ascii=False, indent=4)


if __name__ == '__main__':
    sunspec_to_staticmodbus_generator()
