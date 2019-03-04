import os
import pathlib

import attr
import epyqlib.utils.qt
import PyQt5.uic
from PyQt5 import QtWidgets


Ui, UiBase = PyQt5.uic.loadUiType(
    pathlib.Path(__file__).with_suffix('.ui'),
)


all_files_filter = ('All Files', ['*'])


def path_or_none(s):
    if isinstance(s, pathlib.Path):
        return s

    if s is None or len(s) == 0:
        return None

    return pathlib.Path(s)


def paths_or_none(x):
    return [
        pathlib.Path(path)
        for path in x
        if len(x) > 0
    ]


def import_dialog():
    dialog = Dialog()

    dialog.ui.sunspec_c_label.hide()
    dialog.ui.sunspec_c.hide()
    dialog.ui.pick_sunspec_c.hide()

    dialog.ui.tables_c_label.hide()
    dialog.ui.tables_c.hide()
    dialog.ui.pick_tables_c.hide()

    dialog.ui.sunspec_tables_c_label.hide()
    dialog.ui.sunspec_tables_c.hide()
    dialog.ui.pick_sunspec_tables_c.hide()

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
    sunspec_tables_c = attr.ib(converter=path_or_none)
    spreadsheet = attr.ib(converter=path_or_none)
    smdx = attr.ib(converter=paths_or_none)
    sunspec_c = attr.ib(converter=path_or_none)


def paths_from_directory(directory):
    path = pathlib.Path(directory)
    interface = path / 'interface'
    embedded = path / 'embedded-library'
    sunspec = embedded / 'system' / 'sunspec'

    return ImportPaths(
        can=interface / 'EPC_DG_ID247_FACTORY.sym',
        hierarchy=interface / 'EPC_DG_ID247_FACTORY.parameters.json',
        tables_c=interface / 'canInterfaceGenTables.c',
        sunspec_tables_c=sunspec / 'sunspecInterfaceGenTables.c',
        spreadsheet=embedded / 'MODBUS_SunSpec-EPC.xlsx',
        smdx=sorted(sunspec.glob('smdx_*.xml')),
        sunspec_c=sunspec,
    )


@attr.s
class Dialog(UiBase):
    ui = attr.ib(factory=Ui)
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
        self.ui.pick_sunspec_tables_c.clicked.connect(
            self.pick_sunspec_tables_c,
        )
        self.ui.pick_spreadsheet.clicked.connect(self.pick_spreadsheet)
        self.ui.pick_sunspec_c.clicked.connect(self.pick_sunspec_c)
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
            sunspec_tables_c=self.ui.sunspec_tables_c.text(),
            spreadsheet=self.ui.spreadsheet.text(),
            smdx=smdx,
            sunspec_c=self.ui.sunspec_c.text(),
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
        self.ui.sunspec_tables_c.setText(os.fspath(paths.sunspec_tables_c))
        self.ui.spreadsheet.setText(os.fspath(paths.spreadsheet))
        self.ui.sunspec_c.setText(os.fspath(paths.sunspec_c))

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
            ('PEAK PCAN Symbol File', ['sym']),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.can,
            filters=filters,
            multiple=False,
        )

    def pick_hierarchy(self):
        filters = (
            ('Parameter Hierarchy', ['json']),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.hierarchy,
            filters=filters,
            multiple=False,
        )

    def pick_tables_c(self):
        filters = (
            ('Tables C', ['c']),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.tables_c,
            filters=filters,
            multiple=False,
        )

    def pick_sunspec_tables_c(self):
        filters = (
            ('Tables C', ['c']),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.sunspec_tables_c,
            filters=filters,
            multiple=False,
        )

    def pick_spreadsheet(self):
        filters = (
            ('SunSpec Spreadsheet', ['xls']),
            all_files_filter,
        )

        self.file_dialog(
            target=self.ui.spreadsheet,
            filters=filters,
            multiple=False,
        )

    def pick_sunspec_c(self):
        directory = QtWidgets.QFileDialog.getExistingDirectory(parent=self)

        if len(directory) == 0:
            return

        self.ui.sunspec_c.setText(directory)

    def pick_smdx(self):
        filters = (
            ('SunSpec SMDX', ['xml']),
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


if __name__ == '__main__':
    main()
