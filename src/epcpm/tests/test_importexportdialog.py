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
        tables_c=None,
        bitfields_c=None,
        spreadsheet=None,
        spreadsheet_user=None,
        staticmodbus_spreadsheet=None,
        smdx=[],
        staticmodbus_c=None,
        sunspec_tables_c=None,
        sunspec_c=None,
        sil_c=None,
        interface_c=None,
        spreadsheet_can=None,
    )


def test_cancel(qtbot):
    dialog = epcpm.importexportdialog.Dialog()

    with qtbot.waitSignal(dialog.rejected):
        with qtbot.waitExposed(dialog):
            dialog.open()

        dialog.reject()

    assert dialog.paths_result is None
