import epcpm.importexportdialog


def test_blank(qtbot):
    dialog = epcpm.importexportdialog.Dialog()

    with qtbot.waitSignal(dialog.accepted):
        with qtbot.waitExposed(dialog):
            dialog.open()

        dialog.accept()

    assert dialog.paths_result == epcpm.importexportdialog.ImportPaths(
        can=None,
        hierarchy=None,
        spreadsheet=None,
        smdx=[],
        sunspec_c=None,
    )


def test_cancel(qtbot):
    dialog = epcpm.importexportdialog.Dialog()

    with qtbot.waitSignal(dialog.rejected):
        with qtbot.waitExposed(dialog):
            dialog.open()

        dialog.reject()

    assert dialog.paths_result is None
