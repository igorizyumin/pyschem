from PyQt5.QtWidgets import QMainWindow
from sch.uic.ui_mainwindow import Ui_MainWindow
from sch.view import SchView
from sch.controller import Controller
from sch.document import Document


class MainWindow(QMainWindow):
    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.view = SchView()
        self.doc = Document()
        self.ctrl = Controller(doc=self.doc, view=self.view)
        self.view.setCtrl(self.ctrl)
        self.setCentralWidget(self.view)
