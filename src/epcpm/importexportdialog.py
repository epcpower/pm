import os
import pathlib

import attr
import epyqlib.utils.qt
from PyQt5 import QtWidgets
from functools import partial

import epcpm.importexportdialog_ui


all_files_filter = ("All Files", ["*"])


def path_or_none(s):
    if isinstance(s, pathlib.Path):
        return s

    if s is None or len(s) == 0:
        return None

    return pathlib.Path(s)


def paths_or_none(x):
    return [pathlib.Path(path) for path in x if len(x) > 0]


def import_dialog():
    dialog = Dialog()

    dialog.ui.sunspec_c_label.hide()
    dialog.ui.sunspec_c.hide()
    dialog.ui.pick_sunspec_c.hide()

    dialog.ui.tables_c_label.hide()
    dialog.ui.tables_c.hide()
    dialog.ui.pick_tables_c.hide()

    dialog.ui.staticmodbus_c_label.hide()
    dialog.ui.staticmodbus_c.hide()
    dialog.ui.pick_staticmodbus_c.hide()

    dialog.ui.bitfields_c_label.hide()
    dialog.ui.bitfields_c.hide()
    dialog.ui.pick_bitfields_c.hide()

    dialog.ui.sunspec1_tables_c_label.hide()
    dialog.ui.sunspec1_tables_c.hide()
    dialog.ui.pick_sunspec1_tables_c.hide()

    dialog.ui.sunspec2_tables_c_label.hide()
    dialog.ui.sunspec2_tables_c.hide()
    dialog.ui.pick_sunspec2_tables_c.hide()

    dialog.ui.sil_tables_c_label.hide()
    dialog.ui.sil_tables_c.hide()
    dialog.ui.pick_sil_tables_c.hide()

    dialog.ui.interface_c_label.hide()
    dialog.ui.interface_c.hide()
    dialog.ui.pick_interface_c.hide()

    dialog.ui.rejected_callback_c_label.hide()
    dialog.ui.rejected_callback_c.hide()
    dialog.ui.pick_rejected_callback_c.hide()

    return dialog


def export_dialog():
    dialog = Dialog(for_save=True)

    dialog.ui.smdx_label.hide()
    dialog.ui.smdx_list.hide()
    dialog.ui.pick_smdx.hide()
    dialog.ui.remove_smdx.hide()
    dialog.setMaximumHeight(0)

    return dialog


@attr.s
class ImportPaths:
    can = attr.ib(converter=path_or_none)
    hierarchy = attr.ib(converter=path_or_none)
    tables_c = attr.ib(converter=path_or_none)
    bitfields_c = attr.ib(converter=path_or_none)
    staticmodbus_c = attr.ib(converter=path_or_none)
    sunspec1_tables_c = attr.ib(converter=path_or_none)
    sunspec2_tables_c = attr.ib(converter=path_or_none)
    sunspec1_spreadsheet = attr.ib(converter=path_or_none)
    sunspec2_spreadsheet = attr.ib(converter=path_or_none)
    sunspec1_spreadsheet_user = attr.ib(converter=path_or_none)
    sunspec2_spreadsheet_user = attr.ib(converter=path_or_none)
    staticmodbus_spreadsheet = attr.ib(converter=path_or_none)
    smdx = attr.ib(converter=paths_or_none)
    sunspec_c = attr.ib(converter=path_or_none)
    sil_c = attr.ib(converter=path_or_none)
    interface_c = attr.ib(converter=path_or_none)
    rejected_callback_c = attr.ib(converter=path_or_none)
    # No UI handling for spreadsheet_can since it is not part of normal import/export
    spreadsheet_can = attr.ib(converter=path_or_none)


def paths_from_directory(directory):
    path = pathlib.Path(directory)
    interface = path / "interface"
    embedded = path / "embedded-library"
    sunspec = embedded / "system" / "sunspec"

    return ImportPaths(
        can=interface / "EPC_DG_ID247_FACTORY.sym",
        hierarchy=interface / "EPC_DG_ID247_FACTORY.parameters.json",
        tables_c=interface / "canInterfaceGenTables.c",
        bitfields_c=interface / "interfaceBitfieldsGen.c",
        staticmodbus_c=interface / "staticmodbusInterfaceGen.c",
        sunspec1_tables_c=sunspec / "sunspec1InterfaceGenTables.c",
        sunspec2_tables_c=sunspec / "sunspec2InterfaceGenTables.c",
        sunspec1_spreadsheet=embedded / "MODBUS_SunSpec1-EPC.xlsx",
        sunspec2_spreadsheet=embedded / "MODBUS_SunSpec2-EPC.xlsx",
        sunspec1_spreadsheet_user=embedded / "EPCSunspec1.xlsx",
        sunspec2_spreadsheet_user=embedded / "EPCSunspec2.xlsx",
        staticmodbus_spreadsheet=embedded / "MODBUS-EPC.xlsx",
        smdx=sorted(sunspec.glob("smdx_*.xml")),
        sunspec_c=sunspec,
        sil_c=path / "sil" / "libEpcControlInterfaceGen.c",
        interface_c=interface / "interfaceGen.c",
        rejected_callback_c=interface / "rejectedCallbackHandler.c",
        spreadsheet_can=embedded / "EPC-CAN.xlsx",
    )


@attr.s
class Dialog(QtWidgets.QDialog):
    ui = attr.ib(factory=epcpm.importexportdialog_ui.Ui_Dialog)
    paths_result = attr.ib(default=None)
    for_save = attr.ib(default=False)
    _parent = attr.ib(default=None)
    directory = attr.ib(default=None)

    def __attrs_post_init__(self):
        super().__init__(self._parent)

        self.ui.setupUi(self)

        self.ui.buttons.accepted.connect(self.accept)
        self.ui.buttons.rejected.connect(self.reject)

        self.ui.pick_can.clicked.connect(self.pick_can)
        self.ui.pick_hierarchy.clicked.connect(self.pick_hierarchy)
        self.ui.pick_tables_c.clicked.connect(self.pick_tables_c)
        self.ui.pick_bitfields_c.clicked.connect(self.pick_bitfields_c)
        self.ui.pick_staticmodbus_c.clicked.connect(self.pick_staticmodbus_c)
        self.ui.pick_sunspec1_tables_c.clicked.connect(
            partial(self.pick_sunspec_tables_c, self.ui.sunspec1_tables_c)
        )
        self.ui.pick_sunspec2_tables_c.clicked.connect(
            partial(self.pick_sunspec_tables_c, self.ui.sunspec2_tables_c)
        )
        self.ui.pick_sunspec1_spreadsheet.clicked.connect(
            partial(self.pick_sunspec_spreadsheet, self.ui.sunspec1_spreadsheet)
        )
        self.ui.pick_sunspec2_spreadsheet.clicked.connect(
            partial(self.pick_sunspec_spreadsheet, self.ui.sunspec2_spreadsheet)
        )
        self.ui.pick_sunspec1_spreadsheet_user.clicked.connect(
            partial(
                self.pick_sunspec_spreadsheet_user, self.ui.sunspec1_spreadsheet_user
            )
        )
        self.ui.pick_sunspec2_spreadsheet_user.clicked.connect(
            partial(
                self.pick_sunspec_spreadsheet_user, self.ui.sunspec2_spreadsheet_user
            )
        )
        self.ui.pick_staticmodbus_spreadsheet.clicked.connect(
            self.pick_staticmodbus_spreadsheet
        )
        self.ui.pick_sunspec_c.clicked.connect(self.pick_sunspec_c)
        self.ui.pick_sil_c.clicked.connect(self.pick_sil_c)
        self.ui.pick_interface_c.clicked.connect(self.pick_interface_c)
        self.ui.pick_rejected_callback_c.clicked.connect(self.pick_rejected_callback_c)
        self.ui.pick_smdx.clicked.connect(self.pick_smdx)
        self.ui.remove_smdx.clicked.connect(self.remove_smdx)
        self.ui.from_directory.clicked.connect(self.from_directory)

    def accept(self):
        if self.for_save:
            smdx = []
        else:
            smdx = self.smdx_paths()

        self.paths_result = ImportPaths(
            can=self.ui.can.text(),
            hierarchy=self.ui.hierarchy.text(),
            tables_c=self.ui.tables_c.text(),
            bitfields_c=self.ui.bitfields_c.text(),
            sunspec1_tables_c=self.ui.sunspec1_tables_c.text(),
            sunspec2_tables_c=self.ui.sunspec2_tables_c.text(),
            sunspec1_spreadsheet=self.ui.sunspec1_spreadsheet.text(),
            sunspec2_spreadsheet=self.ui.sunspec2_spreadsheet.text(),
            sunspec1_spreadsheet_user=self.ui.sunspec1_spreadsheet_user.text(),
            sunspec2_spreadsheet_user=self.ui.sunspec2_spreadsheet_user.text(),
            staticmodbus_spreadsheet=self.ui.staticmodbus_spreadsheet.text(),
            smdx=smdx,
            staticmodbus_c=self.ui.staticmodbus_c.text(),
            sunspec_c=self.ui.sunspec_c.text(),
            sil_c=self.ui.sil_c.text(),
            interface_c=self.ui.interface_c.text(),
            rejected_callback_c=self.ui.rejected_callback_c.text(),
            spreadsheet_can=None,
        )
        super().accept()

    def from_directory(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(parent=self)
        if len(directory) == 0:
            return

        self.directory = pathlib.Path(directory)

        paths = paths_from_directory(directory=self.directory)

        self.ui.can.setText(os.fspath(paths.can))
        self.ui.hierarchy.setText(os.fspath(paths.hierarchy))
        self.ui.tables_c.setText(os.fspath(paths.tables_c))
        self.ui.bitfields_c.setText(os.fspath(paths.bitfields_c))
        self.ui.staticmodbus_c.setText(os.fspath(paths.staticmodbus_c))
        self.ui.sunspec1_tables_c.setText(os.fspath(paths.sunspec1_tables_c))
        self.ui.sunspec2_tables_c.setText(os.fspath(paths.sunspec2_tables_c))
        self.ui.sunspec1_spreadsheet.setText(os.fspath(paths.sunspec1_spreadsheet))
        self.ui.sunspec2_spreadsheet.setText(os.fspath(paths.sunspec2_spreadsheet))
        self.ui.sunspec1_spreadsheet_user.setText(
            os.fspath(paths.sunspec1_spreadsheet_user)
        )
        self.ui.sunspec2_spreadsheet_user.setText(
            os.fspath(paths.sunspec2_spreadsheet_user)
        )
        self.ui.staticmodbus_spreadsheet.setText(
            os.fspath(paths.staticmodbus_spreadsheet)
        )
        self.ui.sunspec_c.setText(os.fspath(paths.sunspec_c))
        self.ui.sil_c.setText(os.fspath(paths.sil_c))
        self.ui.interface_c.setText(os.fspath(paths.interface_c))
        self.ui.rejected_callback_c.setText(os.fspath(paths.rejected_callback_c))

        self.clear_smdx_list()
        if not self.for_save:
            for path in paths.smdx:
                self.ui.smdx_list.addItem(os.fspath(path))

    def clear_smdx_list(self):
        for i in range(self.ui.smdx_list.count()):
            self.ui.smdx_list.takeAt(i)

    def smdx_paths(self):
        return [
            self.ui.smdx_list.item(index).text()
            for index in range(self.ui.smdx_list.count())
        ]

    def remove_smdx(self):
        selected_items = self.ui.smdx_list.selectedItems()

        for item in reversed(selected_items):
            self.ui.smdx_list.takeItem(self.ui.smdx_list.row(item))

    def pick_can(self):
        filters = (
            ("PEAK PCAN Symbol File", ["sym"]),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.can,
            filters=filters,
            multiple=False,
        )

    def pick_hierarchy(self):
        filters = (
            ("Parameter Hierarchy", ["json"]),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.hierarchy,
            filters=filters,
            multiple=False,
        )

    def pick_tables_c(self):
        filters = (
            ("Tables C", ["c"]),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.tables_c,
            filters=filters,
            multiple=False,
        )

    def pick_bitfields_c(self):
        filters = (
            ("Bitfields C", ["c"]),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.bitfields_c,
            filters=filters,
            multiple=False,
        )

    def pick_staticmodbus_c(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(parent=self)

        if len(directory) == 0:
            return

        self.ui.staticmodbus_c.setText(directory)

    def pick_sunspec_tables_c(self, sunspec_tables_c: QtWidgets.QLineEdit) -> None:
        filters = (
            ("SunSpec Tables C", ["c"]),
            all_files_filter,
        )

        self.file_dialog(
            target=sunspec_tables_c,
            filters=filters,
            multiple=False,
        )

    def pick_sunspec_spreadsheet(
        self, sunspec_spreadsheet: QtWidgets.QLineEdit
    ) -> None:
        print(f"{type(sunspec_spreadsheet)}")
        filters = (
            ("SunSpec Spreadsheet", ["xlsx"]),
            all_files_filter,
        )

        self.file_dialog(
            target=sunspec_spreadsheet,
            filters=filters,
            multiple=False,
        )

    def pick_sunspec_spreadsheet_user(
        self, sunspec_spreadsheet_user: QtWidgets.QLineEdit
    ) -> None:
        filters = (
            ("SunSpec Spreadsheet", ["xlsx"]),
            all_files_filter,
        )

        self.file_dialog(
            target=sunspec_spreadsheet_user,
            filters=filters,
            multiple=False,
        )

    def pick_staticmodbus_spreadsheet(self):
        filters = (
            ("Static Modbus Spreadsheet", ["xls"]),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.staticmodbus_spreadsheet,
            filters=filters,
            multiple=False,
        )

    def pick_sunspec_c(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(parent=self)

        if len(directory) == 0:
            return

        self.ui.sunspec_c.setText(directory)

    def pick_sil_c(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(parent=self)

        if len(directory) == 0:
            return

        self.ui.sil_c.setText(directory)

    def pick_interface_c(self):
        filters = (
            ("Tables C", ["c"]),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.sunspec_tables_c,
            filters=filters,
            multiple=False,
        )

    def pick_rejected_callback_c(self):
        filters = (
            ("Rejected Callback C", ["c"]),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.rejected_callback_c,
            filters=filters,
            multiple=False,
        )

    def pick_smdx(self):
        filters = (
            ("SunSpec SMDX", ["xml"]),
            all_files_filter,
        )

        paths = self.file_dialog(
            target=None,
            filters=filters,
            multiple=True,
        )

        existing_items = set(self.smdx_paths())

        for path in paths:
            path = os.fspath(path)

            if path not in existing_items:
                self.ui.smdx_list.addItem(path)

    def file_dialog(self, target, filters, multiple):
        path = epyqlib.utils.qt.file_dialog(
            filters=filters,
            parent=self,
            save=self.for_save,
            path_factory=pathlib.Path,
            multiple=multiple,
        )

        if path is None:
            return

        if target is not None:
            target.setText(os.fspath(path))

        return path


@attr.s
class Main:
    application = attr.ib()
    dialog = attr.ib(factory=Dialog)

    def show_dialog(self):
        self.dialog.accepted.connect(self.dialog_accepted)
        self.dialog.open()

    def dialog_accepted(self):
        print(self.dialog.paths_result)
        self.application.quit()

    def one_call(self):
        if self.dialog.exec():
            print(self.dialog.paths_result)
        self.application.quit()


def main():
    from PyQt5 import QtCore
    from PyQt5 import QtWidgets

    app = QtWidgets.QApplication([])

    main = Main(application=app)
    QtCore.QTimer.singleShot(0, main.one_call)
    app.exec()


if __name__ == "__main__":
    main()
