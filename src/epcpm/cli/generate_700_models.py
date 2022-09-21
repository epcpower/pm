import json
import typing
import uuid
from pathlib import Path
from attrs import define, field, fields, has, Factory


PARAMETERS_OUTPUT_FILE = r"C:\Projects\pysunspec2\parameters_700.json"
SUNSPEC_OUTPUT_FILE = r"C:\Projects\pysunspec2\sunspec2_700.json"

INTERFACE_OUTPUT_DIR = r"C:\Projects\pysunspec2"

MODEL_JSON_701 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_701.json"
MODEL_JSON_702 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_702.json"
MODEL_JSON_703 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_703.json"
MODEL_JSON_704 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_704.json"
MODEL_JSON_705 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_705.json"
MODEL_JSON_706 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_706.json"
MODEL_JSON_707 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_707.json"
MODEL_JSON_708 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_708.json"
MODEL_JSON_709 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_709.json"
MODEL_JSON_710 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_710.json"
MODEL_JSON_711 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_711.json"
MODEL_JSON_712 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_712.json"
MODEL_JSON_713 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_713.json"
MODEL_JSON_714 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_714.json"
MODEL_JSON_715 = r"C:\Projects\pysunspec2\sunspec2\models\json\model_715.json"

MODEL_JSON_PATHS = [
    MODEL_JSON_701,
    MODEL_JSON_702,
    MODEL_JSON_703,
    MODEL_JSON_704,
    MODEL_JSON_705,
    MODEL_JSON_706,
    MODEL_JSON_707,
    MODEL_JSON_708,
    MODEL_JSON_709,
    MODEL_JSON_710,
    MODEL_JSON_711,
    MODEL_JSON_712,
    MODEL_JSON_713,
    MODEL_JSON_714,
    MODEL_JSON_715,
]

PARAMETERS_ROOT_UUID = "71895669-35d2-4445-a8f3-8a2c5585cfcf"
PARAMETERS_ENUMERATIONS_ROOT_UUID = "f7cb5703-967a-472d-a949-dabf51df7422"
ACCESS_LEVEL_SERVICE_TECH_UUID = "73ad7ac5-dcb4-4aef-9b44-5b12b10166d2"

MODEL_CURVE_INFO = {
    "705|NCrv": 1,
    "705|NPt": 5,
    "706|NCrv": 1,
    "706|NPt": 5,
    "707|NCrvSet": 1,
    "707|NPt": 5,
    "708|NCrvSet": 1,
    "708|NPt": 5,
    "709|NCrvSet": 1,
    "709|NPt": 5,
    "710|NCrvSet": 1,
    "710|NPt": 5,
    "711|NCtl": 1,
    "712|NCrv": 1,
    "712|NPt": 5,
    "714|NPrt": 1,
}

SUNSPEC_ROOT_UUID = "4210bf88-2079-480d-8b23-d9708f6eb836"

TYPE_DICT = {
    "int16": "2cf75e5a-ffc8-422a-bbc6-573d4206a7e1",
    "uint16": "4f856a7e-20f4-43e2-86b1-cc7ee772f919",
    "int32": "4fec39a5-b702-4dbf-8ad1-95f5e01201b6",
    "uint32": "eb8cdc87-05e2-4593-994e-ab3363236168",
    "uint64": "b361ca90-94bb-433b-a1a8-914472d4f411",
    "sunssf": "02e70616-4986-4f3e-8ac4-98ac153e66f9",
    "enum16": "209aebc8-652f-47bf-9952-4c112ced2781",
    "bitfield16": "5d30a559-13fe-42b1-89df-35c3edc237f0",
    "bitfield32": "fc0ad957-2785-4762-b2fc-4db2cf785ca2",
    "string": "5460c860-4aad-476a-908c-83a364b781c9",
    "acc16": "05830309-c61c-41d4-8c66-88ed25187575",
    "acc32": "f9d30fa6-33b2-48a2-8b64-72a4f47c0bd4",
    "acc64": "7ba30a78-a76d-4ce7-bb32-08e9410b14b9",
    "count": "d5d00207-d2c4-413f-88eb-e44946350007",
    "pad": "f8090bab-cf12-476c-b96a-1c8bb9848bb5",
}


def generate_uuid() -> str:
    """
    Generate a UUID in string format.

    Returns:
        str: UUID
    """
    return str(uuid.uuid4())


def to_json(item: typing.Any) -> dict:
    result = {}
    for fld in fields(type(item)):
        value = getattr(item, fld.name, None)
        if isinstance(value, (list, tuple)):
            result[fld.name] = [to_json(elem) for elem in value]
        elif isinstance(value, dict):
            result[fld.name] = {
                field_name: to_json(field_value)
                for (field_name, field_value) in value.values()
            }
        elif has(value):
            value = to_json(value)
            result[fld.name] = value
        else:
            result[fld.name] = value
    return result


@define
class ParametersChild:
    _type: str = field(init=False, default="parameter")
    name: str = field(init=False)
    abbreviation: str = field(init=False)
    type_name: str = field(init=False)
    default: str = field(init=False)
    minimum: int = field(init=False)
    maximum: int = field(init=False)
    units: str = field(init=False)
    enumeration_uuid: str = field(init=False)
    decimal_places: int = field(init=False)
    display_hexadecimal: bool = field(init=False, default=False)
    nv_format: str = field(init=False)
    nv_cast: bool = field(init=False, default=False)
    internal_variable: str = field(init=False)
    getter_function: str = field(init=False)
    setter_function: str = field(init=False)
    rejected_callback: str = field(init=False)
    internal_type: str = field(init=False)
    internal_scale_factor: int = field(init=False, default=0)
    reject_from_inactive_interfaces: bool = field(init=False, default=False)
    can_getter: str = field(init=False)
    can_setter: str = field(init=False)
    sunspec_getter: str = field(init=False)
    sunspec_setter: str = field(init=False)
    read_only: bool = field(init=False, default=False)
    access_level_uuid: str = field(init=False, default=ACCESS_LEVEL_SERVICE_TECH_UUID)
    parameter_uuid: str = field(init=False)
    comment: str = field(init=False)
    notes: str = field(init=False)
    original_frame_name: str = field(init=False)
    original_multiplexer_name: str = field(init=False)
    original_signal_name: str = field(init=False)
    visibility: str = field(init=False)
    uuid: str = field(init=False, default=Factory(generate_uuid))


@define
class ParametersGroup:
    _type: str = field(init=False, default="group")
    name: str = field(init=False)
    type_name: str = field(init=False, default="null")
    children: list = field(init=False)
    uuid: str = field(init=False, default=Factory(generate_uuid))


@define
class ParametersRoot:
    _type: str = field(init=False, default="root")
    name: str = field(init=False, default="Parameters")
    children: list = field(init=False)
    uuid: str = field(init=False, default=PARAMETERS_ROOT_UUID)


@define
class ParametersEnumerations:
    _type: str = field(init=False, default="enumerations")
    name: str = field(init=False, default="Enumerations")
    children: list = field(init=False)
    uuid: str = field(init=False, default=PARAMETERS_ENUMERATIONS_ROOT_UUID)


@define
class SunSpecEnumeration:
    _type: str = field(init=False, default="enumeration")
    name: str = field(init=False)
    children: list = field(init=False)
    uuid: str = field(init=False, default=Factory(generate_uuid))


@define
class SunSpecEnumerator:
    _type: str = field(init=False, default="sunspec_enumerator")
    name: str = field(init=False)
    abbreviation: str = field(init=False)
    label: str = field(init=False)
    description: str = field(init=False, default="")
    notes: str = field(init=False)
    value: int = field(init=False)
    type: str = field(init=False)
    uuid: str = field(init=False, default=Factory(generate_uuid))


@define
class SunSpecDataPoint:
    _type: str = field(init=False, default="data_point")
    factor_uuid: str = field(init=False, default=None)
    parameter_uuid: str = field(init=False)
    hand_coded_getter: str = field(init=False, default=True)
    hand_coded_setter: str = field(init=False, default=True)
    not_implemented: bool = field(init=False, default=False)
    type_uuid: str = field(init=False)
    block_offset: int = field(init=False)
    size: int = field(init=False)
    enumeration_uuid: str = field(init=False)
    units: str = field(init=False)
    get: str = field(init=False)
    set: str = field(init=False)
    mandatory: bool = field(init=False, default=False)
    uuid: str = field(init=False, default=Factory(generate_uuid))


@define
class SunSpecHeaderBlock:
    _type: str = field(init=False, default="sunspec_header_block")
    name: str = field(init=False, default="Header")
    children: list = field(init=False)
    uuid: str = field(init=False, default=Factory(generate_uuid))


@define
class SunSpecFixedBlock:
    _type: str = field(init=False, default="sunspec_fixed_block")
    name: str = field(init=False, default="Fixed Block")
    children: list = field(init=False)
    uuid: str = field(init=False, default=Factory(generate_uuid))


@define
class SunSpecModel:
    _type: str = field(init=False, default="sunspec_model")
    id: int = field(init=False)
    length: int = field(init=False)
    children: list = field(init=False)
    uuid: str = field(init=False, default=Factory(generate_uuid))


@define
class SunSpecRoot:
    _type: str = field(init=False, default="root")
    name: str = field(init=False, default="SunSpec2")
    children: list = field(init=False)
    uuid: str = field(init=False, default=SUNSPEC_ROOT_UUID)


class ModelConversion:
    def load_settings_json(
        self, model_filepath: str
    ) -> [ParametersGroup, SunSpecModel, typing.List[SunSpecEnumeration]]:
        """
        Load the model JSON and return data to be used for parameters and sunspec output.

        Args:
            model_filepath: file path of the model JSON

        Returns:
            ParametersGroup, SunSpecModel, list[SunSpecEnumeration]
        """
        settings_path = Path(model_filepath)
        parameters_model = ParametersGroup()
        sunspec_model = SunSpecModel()
        sunspec_header_block = SunSpecHeaderBlock()
        sunspec_fixed_block = SunSpecFixedBlock()
        with open(settings_path, encoding="utf-8") as settings_file:
            model_dict = json.load(settings_file)

            model_id = model_dict["id"]
            model_name = f"SunSpec Model {model_id}"
            parameters_model.name = model_name

            parameters_children = list()
            parameters_enumerations_children = list()
            points = model_dict["group"]["points"]
            if "groups" in model_dict["group"]:
                groups = model_dict["group"]["groups"]
            else:
                groups = dict()
            sunspec_model_children = list()
            sunspec_header_block_children = list()
            sunspec_fixed_block_children = list()
            scale_factor_dict = dict()

            total_length = 0
            header_block_offset = 0
            fixed_block_offset = 0

            for point in points:
                (
                    point_length,
                    sunspec_enumeration,
                    parameters_child,
                    sunspec_child,
                    is_scale_factor,
                ) = self._generate_point(point, model_id)

                # The ID and L are set to zero elsewhere.
                total_length += point_length

                point_name = point["name"]
                if point_name in ["ID", "L"]:
                    sunspec_child.block_offset = header_block_offset
                    sunspec_header_block_children.append(sunspec_child)
                    header_block_offset += point["size"]
                else:
                    sunspec_child.block_offset = fixed_block_offset
                    sunspec_fixed_block_children.append(sunspec_child)
                    fixed_block_offset += point["size"]

                if is_scale_factor:
                    # Save the scale factor (abbreviation -> UUID).
                    scale_factor_dict[point_name] = sunspec_child.uuid

                if parameters_child:
                    # Only add if parameters_child was created.
                    parameters_children.append(parameters_child)

                if sunspec_enumeration:
                    # Only append if sunspec_enumeration was created.
                    parameters_enumerations_children.append(sunspec_enumeration)

            total_length = self._generate_group_points(
                groups,
                model_id,
                total_length,
                fixed_block_offset,
                sunspec_fixed_block_children,
                scale_factor_dict,
                parameters_children,
                parameters_enumerations_children,
                "",
            )

            # Iterate back through the sunspec children list and complete the scale factor UUID.
            for sunspec_child in sunspec_fixed_block_children:
                if sunspec_child.factor_uuid is not None:
                    sunspec_child.factor_uuid = scale_factor_dict[
                        sunspec_child.factor_uuid
                    ]

            parameters_model.children = parameters_children

            sunspec_model.id = model_id
            sunspec_model.length = total_length

            # Apparently the 700 series models don't need padding???
            # if total_length % 2 == 0:
            #     sunspec_model.length = total_length
            # else:
            #     # Add one to account for the pad.
            #     sunspec_model.length = total_length + 1

            sunspec_header_block.children = sunspec_header_block_children
            sunspec_fixed_block.children = sunspec_fixed_block_children
            sunspec_model_children.append(sunspec_header_block)
            sunspec_model_children.append(sunspec_fixed_block)
            sunspec_model.children = sunspec_model_children

        return parameters_model, sunspec_model, parameters_enumerations_children

    @staticmethod
    def _generate_point(
        point: dict, model_id: int, prefix_for_group: typing.Optional[str] = None
    ) -> [
        int,
        typing.Optional[SunSpecEnumeration],
        ParametersChild,
        SunSpecDataPoint,
        bool,
    ]:
        """

        Args:
            point: dict of SunSpec point metadata
            model_id: model ID
            prefix_for_group: (optional) prefix to be used for the parameter / SunSpec name

        Returns:
            point_length: point length for use in calculating model size
            sunspec_enumeration: (optional) enumerator data for the point
            parameters_child: parameter metadata
            sunspec_child: sunspec point metadata
            is_scale_factor: is the parameter a scale factor
        """
        if prefix_for_group:
            point_name = f"{prefix_for_group}_{point['name']}"
        else:
            point_name = point["name"]

        if point_name in ["ID", "L"]:
            point_length = 0
        else:
            point_length = point["size"]

        sunspec_enumeration = None
        parameters_child = None
        sunspec_child = None
        is_scale_factor = False

        if "symbols" in point:
            enum_list = point["symbols"]
            sunspec_enumeration = SunSpecEnumeration()
            sunspec_enumeration.name = f"SunSpec{point_name}"
            sunspec_enumeration_children = list()
            for enum_item in enum_list:
                sunspec_enumerator = SunSpecEnumerator()
                if "name" in enum_item:
                    sunspec_enumerator.name = enum_item["name"]
                if "label" in enum_item:
                    sunspec_enumerator.label = enum_item["label"]
                sunspec_enumerator.value = enum_item["value"]
                if "desc" in enum_item:
                    sunspec_enumerator.description = enum_item["desc"]
                sunspec_enumerator.type = point["type"]
                sunspec_enumeration_children.append(sunspec_enumerator)
            sunspec_enumeration.children = sunspec_enumeration_children

        if point["type"] != "pad":
            # Skip the pad types, which are handled automatically by interface generation code.
            parameters_child = ParametersChild()
            point_label = point["label"]
            parameters_child.name = point_label
            parameters_child.abbreviation = point_name
            parameters_child.comment = point["desc"]
            if "static" in point and point["static"] == "S":
                parameters_child.read_only = True

            model_curve_info_key = f"{model_id}|{point_name}"
            if model_curve_info_key in MODEL_CURVE_INFO:
                parameters_child.sunspec_getter = (
                    f"{{interface}} = {MODEL_CURVE_INFO[model_curve_info_key]};"
                )

            sunspec_child = SunSpecDataPoint()
            if "sf" in point:
                # Temporarily put the name of the scale factor here.
                # Below will be replaced with factor UUID.
                sunspec_child.factor_uuid = point["sf"]
            sunspec_child.parameter_uuid = parameters_child.uuid
            sunspec_child.type_uuid = TYPE_DICT[point["type"]]
            if point["type"] == "sunssf":
                is_scale_factor = True
            sunspec_child.size = point["size"]

            if "mandatory" in point and point["mandatory"] == "M":
                sunspec_child.mandatory = True
            if "symbols" in point:
                sunspec_child.enumeration_uuid = sunspec_enumeration.uuid

        return (
            point_length,
            sunspec_enumeration,
            parameters_child,
            sunspec_child,
            is_scale_factor,
        )

    def _generate_group_points(
        self,
        groups: dict,
        model_id: int,
        total_length: int,
        fixed_block_offset: int,
        sunspec_fixed_block_children: list,
        scale_factor_dict: dict,
        parameters_children: list,
        parameters_enumerations_children: list,
        prefix: str,
    ) -> int:
        """
        Generate points for a group.

        Args:
            groups: list of the groups for a node
            model_id: model ID
            total_length: current total length, updated value is returned
            fixed_block_offset: current fixed block offset
            sunspec_fixed_block_children: container for SunSpec fixed block points
            scale_factor_dict: dictionary of scale factor UUID's
            parameters_children: list of parameters for the model
            parameters_enumerations_children: list of SunSpec enumerators
            prefix: prefix of the parameter / SunSpec point name

        Returns:
            total length of the group of points
        """
        for group in groups:
            points = group["points"]

            if "count" in group:
                count_name = group["count"]
                group_name = group["name"]
                total_points = MODEL_CURVE_INFO[f"{model_id}|{count_name}"]
                if prefix:
                    prefix_for_points = f"{prefix}_{group_name}"
                else:
                    prefix_for_points = group_name
            else:
                prefix_for_points = f"{prefix}"
                total_points = 1

            for point_num in range(total_points):
                if "count" in group:
                    prefix_for_group = f"{prefix_for_points}_{point_num:02}"
                else:
                    if prefix_for_points:
                        prefix_for_group = f"{prefix_for_points}_{group['name']}"
                    else:
                        prefix_for_group = f"{group['name']}"

                for point in points:
                    (
                        point_length,
                        sunspec_enumeration,
                        parameters_child,
                        sunspec_child,
                        is_scale_factor,
                    ) = self._generate_point(point, model_id, prefix_for_group)

                    # The ID and L are set to zero elsewhere.
                    total_length += point_length

                    point_name = point["name"]

                    sunspec_child.block_offset = fixed_block_offset
                    sunspec_fixed_block_children.append(sunspec_child)
                    fixed_block_offset += point["size"]

                    if is_scale_factor:
                        # Save the scale factor (abbreviation -> UUID).
                        scale_factor_dict[point_name] = sunspec_child.uuid

                    if parameters_child:
                        # Only add if parameters_child was created.
                        parameters_children.append(parameters_child)

                    if sunspec_enumeration:
                        # Only append if sunspec_enumeration was created.
                        parameters_enumerations_children.append(sunspec_enumeration)

                if "groups" in group:
                    total_length = self._generate_group_points(
                        group["groups"],
                        model_id,
                        total_length,
                        fixed_block_offset,
                        sunspec_fixed_block_children,
                        scale_factor_dict,
                        parameters_children,
                        parameters_enumerations_children,
                        prefix_for_group,
                    )

        return total_length

    @staticmethod
    def generate_interface_file(model_filepath: str, output_dir: str) -> None:
        """
        Generates interface files (.c / .h) for the SunSpec models.

        Args:
            model_filepath: SunSpec model JSON file path
            output_dir: output directory for interface file

        Returns:

        """
        settings_path = Path(model_filepath)
        with open(settings_path, encoding="utf-8") as settings_file:
            model_dict = json.load(settings_file)
            model_id = model_dict["id"]
            points = model_dict["group"]["points"]
            c_function_list = list()
            h_function_list = list()

            if "groups" in model_dict["group"]:
                groups = model_dict["group"]["groups"]
            else:
                groups = dict()

            for point in points:
                point_name = point["name"]

                if point["type"] != "pad":
                    h_function_list.append(
                        f"void getSunspec2Model{model_id}_{point_name}(void);"
                    )
                    h_function_list.append(
                        f"void setSunspec2Model{model_id}_{point_name}(void);"
                    )

                    c_function_list.append(
                        f"void getSunspec2Model{model_id}_{point_name}(void) {{\n}}"
                    )
                    c_function_list.append(
                        f"void setSunspec2Model{model_id}_{point_name}(void) {{\n}}\n"
                    )

            ModelConversion._generate_interface_for_point(
                groups, h_function_list, c_function_list, model_id, ""
            )

            c_output = [
                '#include "sunspec2InterfaceGen.h"',
                f'#include "sunspec2Interface{model_id:>05}.h"',
                f'#include "sunspec2Model{model_id}.h"',
                "",
            ]
            c_output.extend(c_function_list)

            include_guard = f"SUNSPEC2_INTERFACE{model_id:>05}_H"
            h_output = [
                f"#ifndef {include_guard}",
                f"#define {include_guard}",
                "",
            ]
            h_output.extend(h_function_list)
            h_output.append(f"\n#endif //{include_guard}\n")

            output_file_path = Path(output_dir)
            c_output_file_path = output_file_path / f"sunspec2Interface{model_id:>05}.c"
            h_output_file_path = output_file_path / f"sunspec2Interface{model_id:>05}.h"
            with open(c_output_file_path, "w") as out_file:
                for line in c_output:
                    out_file.write(f"{line}\n")
            with open(h_output_file_path, "w") as out_file:
                for line in h_output:
                    out_file.write(f"{line}\n")

    @staticmethod
    def _generate_interface_for_point(
        groups: dict,
        h_function_list: list,
        c_function_list: list,
        model_id: int,
        prefix: str,
    ) -> None:
        """

        Args:
            groups: SunSpec model groups
            h_function_list: list of .h functions to be output
            c_function_list: list of .c functions to be output
            model_id: model ID
            prefix: prefix for parameter / SunSpec point name

        Returns:

        """
        for group in groups:
            points = group["points"]

            if "count" in group:
                count_name = group["count"]
                group_name = group["name"]
                total_points = MODEL_CURVE_INFO[f"{model_id}|{count_name}"]
                if prefix:
                    prefix_for_points = f"{prefix}_{group_name}"
                else:
                    prefix_for_points = group_name
            else:
                prefix_for_points = f"{prefix}"
                total_points = 1

            for point_num in range(total_points):
                if "count" in group:
                    prefix_for_group = f"{prefix_for_points}_{point_num:02}"
                else:
                    if prefix_for_points:
                        prefix_for_group = f"{prefix_for_points}_{group['name']}"
                    else:
                        prefix_for_group = f"{group['name']}"

                for point in points:
                    point_name = point["name"]
                    full_name = f"{prefix_for_group}_{point_name}"

                    if point["type"] != "pad":
                        h_function_list.append(
                            f"void getSunspec2Model{model_id}_{full_name}(void);"
                        )
                        h_function_list.append(
                            f"void setSunspec2Model{model_id}_{full_name}(void);"
                        )
                        c_function_list.append(
                            f"void getSunspec2Model{model_id}_{full_name}(void) {{\n}}"
                        )
                        c_function_list.append(
                            f"void setSunspec2Model{model_id}_{full_name}(void) {{\n}}\n"
                        )

                if "groups" in group:
                    ModelConversion._generate_interface_for_point(
                        group["groups"],
                        h_function_list,
                        c_function_list,
                        model_id,
                        prefix_for_group,
                    )


def main() -> None:
    """
    Call point to output JSON formatted metadata for parameters.json and sunspec2.json.
    Also outputs SunSpec interface files (.c/.h).
    This method is meant to be executed from the pysunspec2 root directory. It could be modified to run elsewhere.

    Returns:

    """
    parameters_root = ParametersRoot()
    parameters_root_children = list()

    parameters_enumerations = ParametersEnumerations()
    parameters_enumerations_children = list()

    sunspec_root = SunSpecRoot()
    sunspec_root_children = list()

    config = ModelConversion()

    for model in MODEL_JSON_PATHS:
        (
            parameters_model,
            sunspec_model,
            parameters_enumerations_model_children,
        ) = config.load_settings_json(model)
        parameters_root_children.append(parameters_model)
        sunspec_root_children.append(sunspec_model)
        parameters_enumerations_children.extend(parameters_enumerations_model_children)

    if len(parameters_enumerations_children) > 0:
        parameters_enumerations.children = parameters_enumerations_children
        parameters_root_children.insert(0, parameters_enumerations)

    with open(PARAMETERS_OUTPUT_FILE, "w") as out_file:
        parameters_root.children = parameters_root_children
        json.dump(to_json(parameters_root), out_file, indent=4)

    with open(SUNSPEC_OUTPUT_FILE, "w") as out_file:
        sunspec_root.children = sunspec_root_children
        json.dump(to_json(sunspec_root), out_file, indent=4)

    for model in MODEL_JSON_PATHS:
        config.generate_interface_file(model, INTERFACE_OUTPUT_DIR)


if __name__ == "__main__":
    main()
