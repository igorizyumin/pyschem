from PyQt5.QtWidgets import QMainWindow
from sch.uic.ui_mainwindow import Ui_MainWindow
from sch.view import SchView


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.schView = SchView()
        self.setCentralWidget(self.ui.schView)
