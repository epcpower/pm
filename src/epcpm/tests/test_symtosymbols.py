import epyqlib.tests.common

import epcpm.symbolmodel
import epcpm.symtoproject


def test_load_can_file():
    parameter_root, symbol_root = epcpm.symtoproject.load_can_path(
        epyqlib.tests.common.symbol_files['customer'],
        epyqlib.tests.common.hierarchy_files['customer'],
    )

    assert isinstance(parameter_root, epcpm.parametermodel.Root)
    assert isinstance(symbol_root, epcpm.symbolmodel.Root)
