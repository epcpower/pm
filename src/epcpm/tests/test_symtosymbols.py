import epyqlib.tests.common

import epcpm.symbolmodel
import epcpm.symtoproject


def test_load_can_file():
    root = epcpm.symtoproject.load_can_path(
        epyqlib.tests.common.symbol_files['customer']
    )

    assert isinstance(root, epcpm.symbolmodel.Root)
