from PyQt5.QtCore import pyqtSlot
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
        self.ui.actionUndo.setEnabled(False)
        self.ui.actionRedo.setEnabled(False)
        self.view = SchView()
        self.doc = Document()
        self.ctrl = Controller(doc=self.doc, view=self.view)
        self.doc.sigCanUndoChanged.connect(self.onCanUndoChanged)
        self.doc.sigCanRedoChanged.connect(self.onCanRedoChanged)
        self.view.setCtrl(self.ctrl)
        self.setCentralWidget(self.view)

    @pyqtSlot()
    def on_actionUndo_triggered(self):
        self.doc.undo()

    @pyqtSlot()
    def on_actionRedo_triggered(self):
        self.doc.redo()

    @pyqtSlot('bool')
    def onCanUndoChanged(self, en):
        self.ui.actionUndo.setEnabled(en)

    @pyqtSlot('bool')
    def onCanRedoChanged(self, en):
        self.ui.actionRedo.setEnabled(en)