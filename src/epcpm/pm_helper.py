"""The purpose of pm_helper is to consolidate refactored code used throughout pm."""
from __future__ import (
    annotations,
)  # See PEP 563, check to remove in future Python version higher than 3.7
import attr
import typing
import uuid
from abc import ABC
from enum import Enum


class SunSpecSection(Enum):
    SUNSPEC_ONE = 1
    SUNSPEC_TWO = 2


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
