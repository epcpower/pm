import numpy as np
import pandas as pd
import json

GROUP_SEPARATOR = " -> "
PARAMETER_SEPARATOR = ":"
GROUP_MAP = {
    "1. AC -> B. Line Monitoring -> Enter service condition": "1. AC -> B. Line Monitoring -> Enter to service condition",
    "1. AC -> B. Line Monitoring -> Enter service condition -> Frequency limits": "1. AC -> B. Line Monitoring -> Enter to service condition -> Frequency limits",
    "1. AC -> B. Line Monitoring -> Enter service condition -> Voltage limits": "1. AC -> B. Line Monitoring -> Enter to service condition -> Voltage limits",
}
old_group_names = list(GROUP_MAP.keys())
new_group_names = list(GROUP_MAP.values())

input_spreadsheet_path = "/home/annie/Documents/Parameter & Group Descriptions.xlsx"
parameter_description_df = pd.read_excel(
    input_spreadsheet_path, "Parameter Descriptions"
)
parameter_description_df = parameter_description_df.replace({np.nan: None})
group_description_df = pd.read_excel(input_spreadsheet_path, "Group Descriptions")
group_description_df = group_description_df.replace({np.nan: None})

# Create group description map
groups = group_description_df["Group"]
groups = groups.replace(old_group_names, new_group_names)
group_descriptions = group_description_df["Description"]
group_description_map = {}
for group, description in zip(groups, group_descriptions):
    name = group.split(GROUP_SEPARATOR)[-1]
    if name not in group_description_map.keys():
        group_description_map[name] = description
    else:
        if not group_description_map[name] and description is not None:
            group_description_map[name] = description

# Get all the group names (without separator) in a list
group_names = []
for group in groups:
    group_names = group_names + group.split(GROUP_SEPARATOR)
group_names = list(set(group_names))

# Create parameter description map
parameters = parameter_description_df["Parameter"]
parameter_descriptions = parameter_description_df["Short Description 4.5.0"]
parameter_description_map = {}
for parameter, description in zip(parameters, parameter_descriptions):
    name = parameter.split(PARAMETER_SEPARATOR)[-1]
    parameter_description_map[name] = description

# Read in parameters.json file
GRID_TIED_PARAMETERS_PATH = "/home/annie/Repos/grid-tied/interface/pm/parameters.json"
json_file = open(GRID_TIED_PARAMETERS_PATH)
root_parameters = json.load(json_file)


def populate_description(current_json: dict) -> None:
    """
    Function that is intended to recursively populate the parameters.json with
    relevant parameter and group descriptions

    Args:
        current_json (dict): A dictionary (most likely nested) in parameters.json
    """
    if current_json["_type"] == "group":
        if (
            current_json["name"] in group_description_map.keys()
            and group_description_map[current_json["name"]] is not None
        ):
            current_json["comment"] = group_description_map[current_json["name"]]
    elif current_json["_type"] == "parameter":
        if "comment" in current_json.keys() and current_json["comment"] is None:
            if current_json["name"] in parameter_description_map.keys():
                current_json["comment"] = parameter_description_map[
                    current_json["name"]
                ]
        elif "comment" in current_json.keys():
            if (
                current_json["name"] in parameter_description_map.keys()
                and parameter_description_map[current_json["name"]] is not None
            ):
                current_json["comment"] = parameter_description_map[
                    current_json["name"]
                ]
        elif current_json["name"] in parameter_description_map.keys():
            current_json["comment"] = parameter_description_map[current_json["name"]]

    if "children" in current_json.keys():
        for child in current_json["children"]:
            populate_description(child)


populate_description(root_parameters)
with open(GRID_TIED_PARAMETERS_PATH, "w", encoding="utf-8") as f:
    json.dump(root_parameters, f, ensure_ascii=True, indent=4)
