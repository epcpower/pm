# import collections
import pathlib

import pytest
import sunspec.core.client

import epcpm.smdxtosunspec


this = pathlib.Path(__file__).resolve()
here = this.parent


smdx_path = here/'sunspec'


@pytest.fixture
def fresh_pathlist():
    original_pathlist = sunspec.core.device.file_pathlist
    sunspec.core.device.file_pathlist = sunspec.core.util.PathList()

    yield sunspec.core.device.file_pathlist

    sunspec.core.device.file_pathlist = original_pathlist


def test_load():
    requested_models = [1, 17, 103, 65534]

    models = epcpm.smdxtosunspec.import_models(
        *requested_models,
        paths=[smdx_path],
    )

    assert [model.id for model in models] == requested_models
