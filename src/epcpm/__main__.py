import logging
import os.path
import sys

import click
from PyQt5 import QtCore, QtGui, QtWidgets

import epyqlib.utils.qt
import epcpm.mainwindow

import epcpm.cli.utils


# See file COPYING in this source tree
__copyright__ = 'Copyright 2017, EPC Power Corp.'
__license__ = 'GPLv2+'


def main(project, verbosity, logger):
    app = QtWidgets.QApplication(sys.argv)

    epyqlib.utils.qt.exception_message_box_register_versions(
        version_tag=epcpm.__version_tag__,
        build_tag=epcpm.__build_tag__,
    )

    sys.excepthook = epyqlib.utils.qt.exception_message_box

    os_signal_timer = epyqlib.utils.qt.setup_sigint()

    QtCore.qInstallMessageHandler(epyqlib.utils.qt.message_handler)

    app.setStyleSheet('QMessageBox {{ messagebox-text-interaction-flags: {}; }}'
                      .format(QtCore.Qt.TextBrowserInteraction))

    app.setOrganizationName('EPC Power Corp.')
    app.setApplicationName('EPC Parameter Management')

    if verbosity >= 1:
        logger.setLevel(logging.DEBUG)

        if verbosity >= 2:
            # twisted.internet.defer.setDebugging(True)
            pass

            if verbosity >= 3:
                logging.getLogger().setLevel(logging.DEBUG)

    window = epcpm.mainwindow.Window(
        title='EPC Parameter Manager',
        ui_file='__main__.ui',
        icon_path='icon.ico',
    )

    epyqlib.utils.qt.exception_message_box_register_parent(parent=window.ui)

    if project is not None:
        filename = os.path.abspath(project)
        window.open_project(filename=filename)

    window.ui.show()

    return app.exec()


@click.command()
@epcpm.cli.utils.project_option()
@click.option(
    '-v',
    '--verbose',
    'verbosity',
    count=True,
    help='Increase verbosity of output (up to three times)',
)
def _entry_point(project, verbosity):
    """Parameter Manager GUI"""

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    stream_handler = logging.StreamHandler()
    file_handler = logging.FileHandler('epcpm.log')

    for handler in (stream_handler, file_handler):
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s')

    sys.excepthook = epyqlib.utils.general.exception_logger

    return main(project=project, verbosity=verbosity, logger=logger)


# for PyInstaller
if __name__ == '__main__':
    sys.exit(_entry_point())
