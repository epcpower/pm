from pytestqt import qtbot

import pm.parameters
import pm.mainwindow

# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


def test_default_ranges():
    p = pm.parameters.Parameter(name='default_min_max')
    assert p.minimum is None
    assert p.maximum is None


# tests/test_parameters.py::test_gui_launch ERROR: InvocationError: '/epc/t/472/p/.tox/test/bin/python -m pytest -v'
# def test_gui_launch(qtbot):
#     window = pm.mainwindow.Window(ui_file='__main__.ui')
#     window.show()
#
#     qtbot.addWidget(window)
