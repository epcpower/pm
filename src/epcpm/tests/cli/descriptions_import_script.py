import pandas as pd
import json

input_spreadsheet_path = "/home/annie/Documents/Parameter & Group Descriptions.xlsx"
df = pd.read_excel(input_spreadsheet_path)

json_file = open("/home/annie/Repos/grid-tied/interface/pm/parameters.json")
parameters = json.load(json_file)
