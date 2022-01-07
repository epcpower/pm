"""The purpose of pm_helper is to consolidate refactored code used throughout pm."""
from __future__ import (
    annotations,
)  # See PEP 563, check to remove in future Python version higher than 3.7
import attr
import typing
import uuid
from abc import ABC


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


def attr_fill(
    cls: typing.Type[FieldsInterface], value: bool
) -> FieldsInterface:
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
