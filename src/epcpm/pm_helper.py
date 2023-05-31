"""The purpose of pm_helper is to consolidate refactored code used throughout pm."""
from __future__ import (
    annotations,
)  # See PEP 563, check to remove in future Python version higher than 3.7
import attr
import typing
import uuid
from abc import ABC
from enum import Enum
import epcpm.sunspecmodel
import epyqlib.treenode


class SunSpecSection(Enum):
    SUNSPEC_ONE = 1
    SUNSPEC_TWO = 2


# Define the size for 'SunS', which is the starting characters of a SunSpec address space.
SUNS_LENGTH = 2


# Define the start address for each SunSpec address space.
SUNSPEC_START_ADDRESS = {
    SunSpecSection.SUNSPEC_ONE: 0,
    SunSpecSection.SUNSPEC_TWO: 40000,
}


def convert_uuid_to_variable_name(input_uuid: uuid.UUID) -> str:
    """
    Replace the dashes in a given UUID with underscores. Return a string value.
    Replacement for CAMPid 9685439641536675431653179671436
    Replacement for CAMPid 07954360685417610543064316843160

    Args:
        input_uuid: input UUID

    Returns:
        str: UUID with dashes replaced by underscores
    """
    return str(input_uuid).replace("-", "_")


@attr.s
class FieldsInterface(ABC):
    def as_filtered_tuple(self, filter_: typing.Type[FieldsInterface]) -> typing.Tuple:
        """
        Returns a tuple of field attribute values specified by the filter.

        Args:
            filter_: a subset of a FieldsInterface object to be used as a filter

        Returns:
            tuple: a tuple of values that have been filtered specified by field values in filter_
        """
        return tuple(
            value for value, f in zip(attr.astuple(self), attr.astuple(filter_)) if f
        )


def attr_fill(cls: typing.Type[FieldsInterface], value: bool) -> FieldsInterface:
    """
    Takes as input a Fields class and outputs a Fields object
    with all attributes set to the value parameter
    which will then be used as a filter.

    Args:
        cls: attrs class of field names
        value: key on True or False values

    Returns:
        fields: Fields object to be used as a filter
    """
    return cls(**{field.name: value for field in attr.fields(cls) if field.init})


def add_padding_to_block(
    block: epyqlib.treenode.TreeNode,
    sunspec_id: SunSpecSection,
    model_id: int,
    block_type: str,
) -> bool:
    """
    Returns whether padding should be added to a given block.
    Contains specific rules for SunSpec1 vs. SunSpec2.

    Args:
        block: tree node block
        sunspec_id: SunSpec section internal identifier
        model_id: SunSpec model ID
        block_type: type of block

    Returns:
        add_padding: True/False if padding should be added to the given block
    """
    pre_pad_block_length = block.check_offsets_and_length()
    # Per SunSpec model specification, pad with a 16-bit pad to force even alignment to 32-bit boundaries.
    add_padding = (pre_pad_block_length % 2) == 1

    # Specifically for SunSpec1 and repeating blocks, do not add padding. This is actually a bug
    # in the original code for SunSpec1 that must continue being in place so that the registers
    # aren't shifted for customers using SunSpec statically by directly calling modbus registers
    # instead of using SunSpec properly.
    # Specifically for SunSpec2, only add padding for model 1. The 700 series models don't require padding.
    if (
        sunspec_id == SunSpecSection.SUNSPEC_ONE and block_type == "Repeating Block"
    ) or (sunspec_id == SunSpecSection.SUNSPEC_TWO and model_id != 1):
        add_padding = False

    return add_padding


def build_uuid_scale_factor_dict(
    points: typing.List[
        typing.Union[
            epcpm.staticmodbusmodel.FunctionData,
            epcpm.staticmodbusmodel.FunctionDataBitfield,
            epcpm.sunspecmodel.DataPoint,
            epcpm.sunspecmodel.DataPointBitfield,
        ]
    ],
    parameter_uuid_finder: typing.Callable,
) -> typing.Dict[
    uuid.UUID,
    typing.Union[
        epcpm.staticmodbusmodel.FunctionData,
        epcpm.staticmodbusmodel.FunctionDataBitfield,
        epcpm.sunspecmodel.DataPoint,
        epcpm.sunspecmodel.DataPointBitfield,
    ],
]:
    """
    Generates a dictionary of scale factor data.
    Replacement for CAMPid 45002738594281495565841631423784

    Args:
        points: list of FunctionData / FunctionDataBitfield objects from which to
        generate scale factor data parameter_uuid_finder: parameter UUID finder method

    Returns:
        dict: dictionary of scale factor data (UUID -> Union[FunctionData, FunctionDataBitfield])
    """
    scale_factor_from_uuid = {}
    for point in points:
        if point.type_uuid is None:
            continue

        type_node = parameter_uuid_finder(point.type_uuid)

        if type_node is None:
            continue

        if type_node.name == "sunssf" or type_node.name == "staticmodbussf":
            scale_factor_from_uuid[point.uuid] = point

    return scale_factor_from_uuid


def get_sunspec_starting_register_values(
    sunspec_id: SunSpecSection,
) -> typing.Tuple[str, str]:
    """
    For SunSpec discovery, start with SunSpec ID for SunSpec2 section only.
    SunSpec1 section starts with undefined so that it won't be discovered.

    Args:
        sunspec_id: SunSpec section internal identifier

    Returns:
        string, string: SunSpec starting register values in order high low
    """
    if sunspec_id == SunSpecSection.SUNSPEC_TWO:
        # High = 0x5375 ("Su"), Low = 0x6e53 ("nS") for combined "SunS"
        return "0x5375", "0x6e53"
    else:
        return "0xffff", "0xffff"


def calculate_start_address(sunspec_id: SunSpecSection) -> int:
    """
    Calculate the start address given the SunSpec section ID.

    Args:
        sunspec_id: SunSpec section internal identifier

    Returns:
        start address
    """
    # Calculate the start address
    start_address = SUNSPEC_START_ADDRESS[sunspec_id]
    # Account for 'SunS' length.
    start_address += SUNS_LENGTH

    return start_address
