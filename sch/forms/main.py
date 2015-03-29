from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QMainWindow, QDockWidget
from sch.uic.ui_mainwindow import Ui_MainWindow
from sch.uic.ui_toolsdock import Ui_ToolsDock
from sch.view import SchView
from sch.controller import Controller, ToolType
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
        self.toolsDock = ToolsDock()
        self.addDockWidget(Qt.LeftDockWidgetArea, self.toolsDock)
        self.toolsDock.toolChanged.connect(self.ctrl.changeTool)

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


class ToolsDock(QDockWidget):
    toolChanged = pyqtSignal(ToolType)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_ToolsDock()
        self.ui.setupUi(self)

    @pyqtSlot(ToolType)
    def on_toolChanged(self, tool):
        self.blockSignals(True)
        if tool == ToolType.SelectTool:
            self.ui.selectBtn.setChecked(True)
        elif tool == ToolType.LineTool:
            self.ui.lineBtn.setChecked(True)
        self.blockSignals(False)

    @pyqtSlot()
    def on_selectBtn_clicked(self):
        self.toolChanged.emit(ToolType.SelectTool)

    @pyqtSlot()
    def on_lineBtn_clicked(self):
        self.toolChanged.emit(ToolType.LineTool)