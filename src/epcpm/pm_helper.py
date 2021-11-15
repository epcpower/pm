"""The purpose of pm_helper is to consolidate refactored code used throughout pm."""
import uuid


def convert_uuid_to_variable_name(uuid: uuid.UUID) -> str:
    """
    Replace the dashes in a given UUID with underscores. Return a string value.
    Replacement for CAMPid 9685439641536675431653179671436
    Replacement for CAMPid 07954360685417610543064316843160

    Args:
        uuid: input UUID

    Returns:
        str: UUID with dashes replaced by underscores
    """
    return str(uuid).replace("-", "_")
