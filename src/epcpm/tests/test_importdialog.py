import epcpm.importdialog


def test_blank(qtbot):
    dialog = epcpm.importdialog.Dialog()

    with qtbot.waitSignal(dialog.accepted):
        with qtbot.waitExposed(dialog):
            dialog.open()

        dialog.accept()

    assert dialog.paths_result == epcpm.importdialog.ImportPaths(
        can=None,
        hierarchy=None,
        spreadsheet=None,
        smdx=[],
    )


def test_cancel(qtbot):
    dialog = epcpm.importdialog.Dialog()

    with qtbot.waitSignal(dialog.rejected):
        with qtbot.waitExposed(dialog):
            dialog.open()

        dialog.reject()

    assert dialog.paths_result is None
