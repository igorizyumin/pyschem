from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from sch.forms.main import MainWindow

if __name__ == '__main__':
    import sys

    app = QApplication(sys.argv)

    app.setApplicationName('pyschem')
    app.setOrganizationName('xpcb.org')
    app.setOrganizationDomain('xpcb.org')

    w = MainWindow()
    w.show()

    sys.exit(app.exec_())