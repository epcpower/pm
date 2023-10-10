import pandas as pd
import json

input_spreadsheet_path = "/home/annie/Documents/Parameter & Group Descriptions.xlsx"
parameter_description_df = pd.read_excel(
    input_spreadsheet_path, "Parameter Descriptions"
)
group_description_df = pd.read_excel(input_spreadsheet_path, "Group Descriptions")
group_description_map = dict(
    zip(group_description_df["Group"], group_description_df["Description"])
)

# Get all the group names (without separator) in a list
group_names = []
GROUP_SEPARATOR = " -> "
PARAMETER_SEPARATOR = ":"
for group in group_description_map.keys():
    group_names = group_names + group.split(GROUP_SEPARATOR)
group_names = list(set(group_names))

# Create parameter description map
parameters = parameter_description_df["Parameter"]
parameter_descriptions = parameter_description_df["Description"]
parameter_description_map = {}
for parameter, description in zip(parameters, parameter_descriptions):
    name = parameter.split(PARAMETER_SEPARATOR)[-1]
    parameter_description_map[name] = description

# Read in parameters.json file
json_file = open("/home/annie/Repos/grid-tied/interface/pm/parameters.json")
root_parameters = json.load(json_file)

groups = []
for child in root_parameters["children"]:
    if child["_type"] == "group":
        groups.append(child)

print(len(groups))
