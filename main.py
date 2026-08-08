from PySide6.QtCore import *
from PySide6.QtWidgets import *
from sch.forms.main import MainWindow

import faulthandler
import os

if os.environ.get("PYSCHEM_NET_TRACE", "0") not in ("", "0", "false", "False"):
    faulthandler.enable(all_threads=True)

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)

    app.setApplicationName('pyschem')
    app.setOrganizationName('xpcb.org')
    app.setOrganizationDomain('xpcb.org')

    w = MainWindow()
    w.show()

    sys.exit(app.exec())
