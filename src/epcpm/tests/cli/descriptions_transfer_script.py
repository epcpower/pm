import numpy as np
import pandas as pd
import re
import openpyxl
from openpyxl.styles import Alignment

excel_path = "/home/annie/Documents/Appendix A Table.xlsx"
excel_path_epc_can_manual = "/home/annie/Documents/EPC-CAN_for_manual.xlsx"
exel_path_epc_can = "/home/annie/Documents/EPC-CAN.xlsx"
df = pd.read_excel(excel_path)
df_epc_can_manual = pd.read_excel(excel_path_epc_can_manual)
df_epc_can = pd.read_excel(exel_path_epc_can)[
    ["EPyQ CAN Parameter Name", "Enumerator List"]
]
df_epc_can.columns = ["Parameter", "Enumerators"]
df_epc_can = df_epc_can.set_index("Parameter")
df_epc_can_joined = df_epc_can_manual.join(df_epc_can, on="Parameter")


def get_longest_match(name: str) -> str:
    """
    Gets the longest matching name in `GROUP_NAMES` constant

    Args:
        name (str): The name to be matched

    Returns:
        str: The longest matching name in `GROUP_NAMES`
    """
    longest_matching_group_name = ""
    for group_name in GROUP_NAMES:
        if group_name in name:
            if len(group_name) > len(longest_matching_group_name):
                longest_matching_group_name = group_name
    return longest_matching_group_name


def create_parameter_name_description_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Creates a parameter name and description dataframe

    Args:
        df (pd.DataFrame): A dataframe read from an excel sheet

    Returns:
        pd.DataFrame: A dataframe filled with the parameter name and the description
    """
    # Selects columns from the original dataframe
    parameter_df = df[["Parameter Name", "Description", "Unnamed: 3"]]

    # Renames columns pulled from previous step
    parameter_df.columns = ["Parameter", "Description", "Overflow"]

    # Fills the NaN cells in `Description` column with values from the `Overflow` column
    parameter_df.Description.fillna(parameter_df.Overflow, inplace=True)
    del parameter_df["Overflow"]

    # Drops rows with NaN values in `Parameter` column
    parameter_df = parameter_df.dropna(subset=["Parameter"])

    return parameter_df


parameter_name_description_df = create_parameter_name_description_df(df)
parameter_name_description_4_5_0_df = df_epc_can_joined[
    ["Parameter", "Description", "Enumerators"]
].dropna(subset=["Parameter"])

GROUP_NAMES = [
    "1. AC -> B. Line Monitoring -> Enter service condition",
    "1. AC -> B. Line Monitoring -> Enter service condition -> Frequency limits",
    "1. AC -> B. Line Monitoring -> Enter service condition -> Voltage limits",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> High -> RideThrough -> X -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> High -> RideThrough -> X -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> High -> RideThrough -> X -> hertz",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> High -> RideThrough -> X -> seconds",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> High -> Trip -> X -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> High -> Trip -> X -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> High -> Trip -> X -> herzt",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> High -> Trip -> X -> seconds",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Low -> RideThrough -> X -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Low -> RideThrough -> X -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Low -> RideThrough -> X -> hertz",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Low -> RideThrough -> X -> seconds",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Low -> Trip -> X -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Low -> Trip -> X -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Low -> Trip -> X -> herzt",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Low -> Trip -> X -> seconds",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> EN 50549",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> EN 50549 -> Thresholds",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> EN 50549 -> Thresholds -> NS Overvoltage",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> EN 50549 -> Thresholds -> PS Undervoltage",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> EN 50549 -> Thresholds -> Stage1 Overvoltage",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> EN 50549 -> Thresholds -> Stage1 Undervoltage",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> EN 50549 -> Thresholds -> Stage2 Overvoltage",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> EN 50549 -> Thresholds -> Stage2 Undervoltage",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> High -> RideThrough -> X -> After",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> High -> RideThrough -> X -> Before",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> High -> RideThrough -> X -> percent",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> High -> RideThrough -> X -> seconds",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> High -> Trip -> X -> After",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> High -> Trip -> X -> Before",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> High -> Trip -> X -> percent",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> High -> Trip -> X -> seconds",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> Low -> RideThrough -> X -> After",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> Low -> RideThrough -> X -> Before",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> Low -> RideThrough -> X -> percent",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> Low -> RideThrough -> X -> seconds",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> Low -> Trip -> X -> After",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> Low -> Trip -> X -> Before",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> Low -> Trip -> X -> percent",
    "1. AC -> B. Line Monitoring ->Voltage Monitoring -> Tables -> Low -> Trip -> X -> seconds",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> X -> After",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> X -> Before",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> X -> hertz",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> X -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Synthetic Inertia -> Grid Forming",
    "1. AC -> C. Grid Support -> Synthetic Inertia -> Grid Forming -> Active Power control Coeffs",
    "1. AC -> C. Grid Support -> Synthetic Inertia -> Grid Forming -> Frequency Offset Limits",
    "1. AC -> C. Grid Support -> Synthetic Inertia -> Grid Forming -> Reactive Power control Coeffs",
    "1. AC -> C. Grid Support -> Synthetic Inertia -> Grid Forming -> Voltage Offset Limits",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> X -> After",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> X -> Before",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> X -> percent_nominal_var",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> X -> percent_nominal_volts",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> X -> After",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> X -> Before",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> X -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> X -> percent_nominal_volts",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> X -> After",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> X -> Before",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> X -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> X ->power_factor",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> X -> After",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> X -> Before",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> X -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> X -> percent_nominal_var",
    "1. AC -> 1. Harmonic Filter Observer -> 3. Current Offsets",
    "1. AC -> 1. Harmonic Filter Observer -> 3. Current Offsets -> Power Accuracy Tuning",
    "1. AC -> 1. Harmonic Filter Observer -> 3. Current Offsets -> Power Accuracy Tuning -> P Offsets",
    "1. AC -> 1. Harmonic Filter Observer -> 3. Current Offsets -> Power Accuracy Tuning -> Q Offsets",
    "1. AC -> 2. Phase-Locked Loop",
    "1. AC -> 2. Phase-Locked Loop -> 5. Measurement Adjustment",
    "1. AC -> 3. Forming Control -> 1. Island Detection Parameters",
    "1. AC -> 3. Forming Control -> 1. Island Detection Parameters -> 1. Voltage Destabilization Curve",
    "1. AC -> 3. Forming Control -> 1. Island Detection Parameters -> 2. Frequency Destabilization Curve",
    "1. AC -> 3. Forming Control -> 2. Frequency Regulator",
    "1. AC -> 3. Forming Control -> 3. Voltage Regulator",
    "1. AC -> 3. Forming Control -> 4. Voltage Droop Curve",
    "1. AC -> 3. Forming Control -> 5. Frequency Droop Curve",
    "1. AC -> 3. Forming Control -> 8. Fault Transient Response",
    "1. AC -> 3. Forming Control -> 9. Steady-state Fault Control",
    "1. AC -> 4. Current Control -> 1. Fundamental Current Regulator -> 1. Following",
    "1. AC -> 4. Current Control -> 1. Fundamental Current Regulator -> 2. Forming",
    "1. AC -> 4. Current Control -> 2. DC Offset Current Regulator",
    "1. AC -> 4. Current Control -> 3. Circulating Current Regulator",
    "1. AC -> 5. Harmonic Control -> 1. Current Harmonic Control",
    "1. AC -> 5. Harmonic Control -> 2. Voltage Harmonic Control",
    "1. AC -> 6. DC Voltage Control",
    "1. AC -> 7. Modulator -> 1. Basic Configuration",
    "1. AC -> 7. Modulator -> 2. Advanced Configuration -> 1. Modulation Schemes -> 1. Synchronous Modulation",
    "1. AC -> 7. Modulator -> 2. Advanced Configuration -> 1. Modulation Schemes -> 2. Spread-Spectrum Modulation",
    "1. AC -> 7. Modulator -> 2. Advanced Configuration -> 3. Constraints",
    "1. AC -> 8. References",
    "1. AC -> 8. References -> 1. Network References",
    "1. AC -> 8. References -> 2. Voltage Reference Characteristics",
    "1. AC -> 8. References -> 3. Frequency Reference Characteristics",
    "1. AC -> 8. References -> 4. Current Reference Characteristics",
    "1. AC -> 8. References -> 5. Power Reference Characteristics",
    "1. AC -> 8. References -> 5. Power Reference Characteristics -> Command",
    "1. AC -> 8. References -> 5. Power Reference Characteristics -> Connect",
    "1. AC -> 8. References -> 5. Power Reference Characteristics -> Reconnect",
    "1. AC -> 8. References -> 6. User Power and Current Limits",
    "1. AC -> 8. References -> 7. Battery Constraints",
    "1. AC -> 8. References -> 8. Pre-Shutdown Unload",
    "1. AC -> 8. References -> 9. Active Rectifier Reference -> 1. Voltage Reference Characteristics",
    "1. AC -> 8. References -> 9. Active Rectifier Reference -> 2. Limits",
    "1. AC -> 9. Flags",
    "1. AC -> A. Remote Network -> 1. Auxiliary Phase-Locked Loop -> 4. Measurement Adjustment",
    "1. AC -> A. Remote Network -> 2. Protected Bus Control -> 1. Behaviour Flags",
    "1. AC -> A. Remote Network -> 2. Protected Bus Control -> 2. Timings and Timeouts",
    "1. AC -> A. Remote Network -> 2. Protected Bus Control -> 3. Synchronization Control Settings",
    "1. AC -> B. Line Monitoring",
    "1. AC -> B. Line Monitoring -> Enter to service condition",
    "1. AC -> B. Line Monitoring -> Enter to service condition -> Frequency limits",
    "1. AC -> B. Line Monitoring -> Enter to service condition -> Voltage limits",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> EN 50549",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> EN 50549 -> Thresholds -> Stage1 Overfrequency",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> EN 50549 -> Thresholds -> Stage1 Underfrequency",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> EN 50549 -> Thresholds -> Stage2 Overfrequency",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> EN 50549 -> Thresholds -> Stage2 Underfrequency",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> RideThrough -> 1 -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> RideThrough -> 1 -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> RideThrough -> 1 -> hertz",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> RideThrough -> 1 -> seconds",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> RideThrough -> 2 -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> RideThrough -> 2 -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> RideThrough -> 2 -> hertz",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> RideThrough -> 2 -> seconds",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> Trip -> 1 -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> Trip -> 1 -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> Trip -> 1 -> hertz",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> Trip -> 1 -> seconds",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> Trip -> 2 -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> Trip -> 2 -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> Trip -> 2 -> hertz",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> High -> Trip -> 2 -> seconds",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> RideThrough -> 1 -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> RideThrough -> 1 -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> RideThrough -> 1 -> hertz",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> RideThrough -> 1 -> seconds",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> RideThrough -> 2 -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> RideThrough -> 2 -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> RideThrough -> 2 -> hertz",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> RideThrough -> 2 -> seconds",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> Trip -> 1 -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> Trip -> 1 -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> Trip -> 1 -> hertz",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> Trip -> 1 -> seconds",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> Trip -> 2 -> After",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> Trip -> 2 -> Before",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> Trip -> 2 -> hertz",
    "1. AC -> B. Line Monitoring -> Frequency Monitoring -> Tables -> Tree -> Low -> Trip -> 2 -> seconds",
    "1. AC -> B. Line Monitoring -> Return to service condition",
    "1. AC -> B. Line Monitoring -> Return to service condition -> Frequency limits",
    "1. AC -> B. Line Monitoring -> Return to service condition -> Voltage limits",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> EN 50549",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> EN 50549 -> Thresholds",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> EN 50549 -> Thresholds -> NS Overvoltage",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> EN 50549 -> Thresholds -> PS Undervoltage",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> EN 50549 -> Thresholds -> Stage1 Overvoltage",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> EN 50549 -> Thresholds -> Stage1 Undervoltage",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> EN 50549 -> Thresholds -> Stage2 Overvoltage",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> EN 50549 -> Thresholds -> Stage2 Undervoltage",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> After",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Before",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> RideThrough -> 1 -> After",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> RideThrough -> 1 -> Before",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> RideThrough -> 1 -> percent",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> RideThrough -> 1 -> seconds",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> RideThrough -> 2 -> After",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> RideThrough -> 2 -> Before",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> RideThrough -> 2 -> percent",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> RideThrough -> 2 -> seconds",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> Trip -> 1 -> After",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> Trip -> 1 -> Before",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> Trip -> 1 -> percent",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> Trip -> 1 -> seconds",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> Trip -> 2 -> After",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> Trip -> 2 -> Before",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> Trip -> 2 -> percent",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> High -> Trip -> 2 -> seconds",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> RideThrough -> 1 -> After",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> RideThrough -> 1 -> Before",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> RideThrough -> 1 -> percent",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> RideThrough -> 1 -> seconds",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> RideThrough -> 2 -> After",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> RideThrough -> 2 -> Before",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> RideThrough -> 2 -> percent",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> RideThrough -> 2 -> seconds",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> Trip -> 1 -> After",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> Trip -> 1 -> Before",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> Trip -> 1 -> percent",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> Trip -> 1 -> seconds",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> Trip -> 2 -> After",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> Trip -> 2 -> Before",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> Trip -> 2 -> percent",
    "1. AC -> B. Line Monitoring -> Voltage Monitoring -> Tables -> Tree -> Low -> Trip -> 2 -> seconds",
    "1. AC -> C. Grid Support",
    "1. AC -> C. Grid Support -> Fixed Power Factor",
    "1. AC -> C. Grid Support -> Hz-Watt",
    "1. AC -> C. Grid Support -> Hz-Watt -> AS4777",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> After",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> Before",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> Tree -> 1 -> After",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> Tree -> 1 -> Before",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> Tree -> 1 -> hertz",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> Tree -> 1 -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> Tree -> 2 -> After",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> Tree -> 2 -> Before",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> Tree -> 2 -> hertz",
    "1. AC -> C. Grid Support -> Hz-Watt -> Tables -> Tree -> 2 -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Hz-Watt Limit",
    "1. AC -> C. Grid Support -> Synthetic Inertia",
    "1. AC -> C. Grid Support -> Synthetic Inertia -> Grid Following",
    "1. AC -> C. Grid Support -> Synthetic Inertia -> Grid Forming ",
    "1. AC -> C. Grid Support -> Synthetic Inertia -> Grid Forming  -> Active Power control Coeffs",
    "1. AC -> C. Grid Support -> Synthetic Inertia -> Grid Forming  -> Frequency Offset Limits",
    "1. AC -> C. Grid Support -> Synthetic Inertia -> Grid Forming  -> Reactive Power control Coeffs",
    "1. AC -> C. Grid Support -> Synthetic Inertia -> Grid Forming  -> Voltage Offset Limits",
    "1. AC -> C. Grid Support -> Transient Reactive Current -> Configuration Flags",
    "1. AC -> C. Grid Support -> Transient Reactive Current -> Detection Parameters",
    "1. AC -> C. Grid Support -> Transient Reactive Current -> Filters",
    "1. AC -> C. Grid Support -> Transient Reactive Current -> Output Characteristics",
    "1. AC -> C. Grid Support -> Volt-Var",
    "1. AC -> C. Grid Support -> Volt-Var -> Reference Voltage",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> After",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> Before",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> Tree -> 1 -> After",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> Tree -> 1 -> Before",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> Tree -> 1 -> percent_nominal_var",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> Tree -> 1 -> percent_nominal_volts",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> Tree -> 2 -> After",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> Tree -> 2 -> Before",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> Tree -> 2 -> percent_nominal_var",
    "1. AC -> C. Grid Support -> Volt-Var -> Tables -> Tree -> 2 -> percent_nominal_volts",
    "1. AC -> C. Grid Support -> Volt-Watt",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> After",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> Before",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> Tree -> 1 -> After",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> Tree -> 1 -> Before",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> Tree -> 1 -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> Tree -> 1 -> percent_nominal_volts",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> Tree -> 2 -> After",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> Tree -> 2 -> Before",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> Tree -> 2 -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Volt-Watt -> Tables -> Tree -> 2 -> percent_nominal_volts",
    "1. AC -> C. Grid Support -> Volt-Watt Limit",
    "1. AC -> C. Grid Support -> Watt-Power Factor",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> After",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> Before",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> Tree -> 1 -> After",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> Tree -> 1 -> Before",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> Tree -> 1 -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> Tree -> 1 -> power_factor",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> Tree -> 2 -> After",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> Tree -> 2 -> Before",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> Tree -> 2 -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Watt-Power Factor -> Tables -> Tree -> 2 -> power_factor",
    "1. AC -> C. Grid Support -> Watt-Var",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> After",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> Before",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> Tree -> 1 -> After",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> Tree -> 1 -> Before",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> Tree -> 1 -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> Tree -> 1 -> percent_nominal_var",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> Tree -> 2 -> After",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> Tree -> 2 -> Before",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> Tree -> 2 -> percent_nominal_pwr",
    "1. AC -> C. Grid Support -> Watt-Var -> Tables -> Tree -> 2 -> percent_nominal_var",
    "1. AC -> E. Symmetrical Component Control",
    "1. AC -> F. Synchronous Harmonic Current Control -> 1. Harmonic Order Configuration",
    "1. AC -> F. Synchronous Harmonic Current Control -> 2. Harmonic Quadrature Signal Generator",
    "1. AC -> F. Synchronous Harmonic Current Control -> 3. Harmonic Current Regulator",
    "1. AC -> F. Synchronous Harmonic Current Control -> 4. Harmonic Current Ramp",
    "1. AC -> F. Synchronous Harmonic Current Control -> 5. Lag-Lead Configuration",
    "1. AC -> F. Synchronous Harmonic Current Control -> 6. Filters",
    "3. MPPT -> 1. Limits",
    "3. MPPT -> 2. Performance Parameters",
    "3. MPPT -> 3. AC MPPT State Parameters",
    "3. MPPT -> 4. Power Ramp Characteristics",
    "3. MPPT -> 5. Filters",
    "4. Hardware -> 3. Protections -> 2. Timed Trips -> 2. AC Grid Voltage Trip",
    "4. Hardware -> 3. Protections -> 5. Configurable Faults",
    "4. Hardware -> 3. Protections -> 7. External Inhibit",
    "4. Hardware -> 4. Measurement Channels -> 3. Measurement Assignments",
    "4. Hardware -> 6. Precharge",
    "4. Hardware -> 7. I/O Configuration",
    "4. Hardware -> 7. I/O Configuration -> Contactor Configuration -> Delays",
    "4. Hardware -> 7. I/O Configuration -> Contactor Configuration -> Force Closures",
    "4. Hardware -> 7. I/O Configuration -> Digital I/O Inversions",
    "4. Hardware -> 7. I/O Configuration -> Digital I/O Inversions -> Inputs",
    "4. Hardware -> 7. I/O Configuration -> Digital I/O Inversions -> Outputs",
    "4. Hardware -> 7. I/O Configuration -> Digital Output Control",
    "4. Hardware -> 8. Environmental Control",
    "4. Hardware -> 8. Environmental Control -> Cabinet Fan",
    "4. Hardware -> 8. Environmental Control -> Cabinet Fan -> Hardware Configuration",
    "4. Hardware -> 8. Environmental Control -> Coolant Fan",
    "4. Hardware -> 8. Environmental Control -> Coolant Fan -> Hardware Configuration",
    "4. Hardware -> 8. Environmental Control -> Humidity Control",
    "4. Hardware -> 8. Environmental Control -> Inductor Fan Control",
    "4. Hardware -> 8. Environmental Control -> Inductor Fan Control -> Hardware Configuration",
    "4. Hardware -> 8. Environmental Control -> Power Module Fans",
    "4. Hardware -> 8. Environmental Control -> Power Module Fans -> Hardware Configuration",
    "5. Communication -> CANbus",
    "5. Communication -> CANbus -> Transmit Frequency",
    "5. Communication -> Serial",
    "6. Status -> Control Board",
    "6. Status -> Environment",
    "6. Status -> Environment -> Aux Temps",
    "6. Status -> Environment -> Cabinet Fan",
    "6. Status -> Environment -> Coolant Fan",
    "6. Status -> Environment -> Inductor Fan",
    "6. Status -> Environment -> Power Module Fans",
    "6. Status -> Faults",
    "6. Status -> Grid support",
    "6. Status -> Harmonic Current",
    "6. Status -> Modulator",
    "6. Status -> Protections",
    "6. Status -> Voltages",
    "6. Status -> Warnings",
    "7. Identification",
    "8. Data Logger",
    "8. Data Logger -> Chunks",
    "8. Data Logger -> LogData",
    "8. Data Logger -> Trigger",
    "B. Other",
]
ACCESS_LEVELS = ["Service_Tech", "Service_Eng", "EPC_Eng", "EPC_Factory", "MAC_Auth"]

parameter_group_names = parameter_name_description_df["Parameter"].to_list()
descriptions = parameter_name_description_df["Description"].to_list()
parameter_group_names_4_5_0 = parameter_name_description_4_5_0_df["Parameter"].to_list()
descriptions_4_5_0 = (
    parameter_name_description_4_5_0_df["Description"].fillna("").to_list()
)
enumerators_4_5_0 = (
    parameter_name_description_4_5_0_df["Enumerators"].fillna("").to_list()
)

current_group_name = ""
GROUP_NAME_PATTERN = r"([A-Z0-9]\.)"

parameter_description_dict = {}
group_description_dict = {}
parameter_description_dict_4_5_0 = {}

for parameter_name, description in zip(parameter_group_names, descriptions):
    if not re.search(GROUP_NAME_PATTERN, parameter_name):
        parameter_description_dict[parameter_name] = description
    else:
        current_group_name = get_longest_match(parameter_name)
        description = parameter_name.replace(current_group_name, "")
        group_description_dict[current_group_name] = description.strip()


current_group_name = ""
for parameter_name, description_4_5_0, enumerators in zip(
    parameter_group_names_4_5_0, descriptions_4_5_0, enumerators_4_5_0
):
    if not re.search(GROUP_NAME_PATTERN, parameter_name):
        matched_description = ""
        if parameter_name in parameter_description_dict.keys():
            matched_description = parameter_description_dict[parameter_name]
            if matched_description is np.nan:
                matched_description = ""
        if description_4_5_0 in ACCESS_LEVELS:
            description_4_5_0 = ""

        difference = "N"
        matched_description = matched_description.rstrip()
        description_4_5_0 = description_4_5_0.rstrip()
        if matched_description != description_4_5_0:
            difference = "Y"
        parameter_description_dict_4_5_0[parameter_name] = (
            current_group_name,
            matched_description,
            description_4_5_0,
            enumerators,
            difference,
        )
    else:
        current_group_name = get_longest_match(parameter_name)
        if parameter_name not in group_description_dict.keys():
            group_description_dict[parameter_name] = description_4_5_0

output_workbook = openpyxl.Workbook()

output_parameters_worksheet = output_workbook.active
output_parameters_worksheet.title = "Parameter Descriptions"
output_group_worksheet = output_workbook.create_sheet("Group Descriptions")

output_parameters_worksheet["A1"] = "Group"
output_parameters_worksheet["B1"] = "Parameter"
output_parameters_worksheet["C1"] = "Manual Description"
output_parameters_worksheet["D1"] = "Short Description 4.5.0"
output_parameters_worksheet["E1"] = "Enumerator List"
output_parameters_worksheet["F1"] = "Difference (Y/N)"


output_group_worksheet["A1"] = "Group"
output_group_worksheet["B1"] = "Description"

row = 2
for parameter, description_group_tuple in parameter_description_dict_4_5_0.items():
    output_parameters_worksheet[f"A{row}"].value = description_group_tuple[0]
    output_parameters_worksheet[f"B{row}"].value = parameter
    output_parameters_worksheet[f"C{row}"].value = description_group_tuple[1]
    output_parameters_worksheet[f"D{row}"].value = description_group_tuple[2]
    output_parameters_worksheet[f"E{row}"].value = description_group_tuple[3]
    output_parameters_worksheet[f"F{row}"].value = description_group_tuple[4]

    row = row + 1

row = 2
for group, description_group_tuple in group_description_dict.items():
    output_group_worksheet[f"A{row}"].value = group
    output_group_worksheet[f"B{row}"].value = description_group_tuple
    row = row + 1

output_workbook.save("/home/annie/Documents/Parameter & Group Descriptions.xlsx")
