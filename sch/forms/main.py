from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt
from PyQt5.QtWidgets import QMainWindow, QDockWidget, QMessageBox, QFileDialog
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
        self.fileName = None
        self.ctrl = Controller(doc=self.doc, view=self.view)
        self.doc.sigCanUndoChanged.connect(self.onCanUndoChanged)
        self.doc.sigCanRedoChanged.connect(self.onCanRedoChanged)
        self.view.setCtrl(self.ctrl)
        self.setCentralWidget(self.view)
        self.toolsDock = ToolsDock()
        self.addDockWidget(Qt.LeftDockWidgetArea, self.toolsDock)
        self.toolsDock.toolChanged.connect(self.ctrl.changeTool)

    def newDoc(self):
        self.doc = Document()
        self.ctrl.doc = self.doc
        self.doc.sigCanUndoChanged.connect(self.onCanUndoChanged)
        self.doc.sigCanRedoChanged.connect(self.onCanRedoChanged)
        self.fileName = None

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

    @pyqtSlot()
    def on_actionNew_triggered(self):
        if self.maybeSave():
            self.newDoc()

    @pyqtSlot()
    def on_actionSave_triggered(self):
        if not self.fileName:
            return self.on_actionSave_As_triggered()
        else:
            self.saveFile(self.fileName)
            return True

    @pyqtSlot()
    def on_actionSave_As_triggered(self):
        fn = QFileDialog.getSaveFileName(self)[0]
        if fn == "":
            return False
        self.saveFile(fn)
        return True

    def maybeSave(self):
        if self.doc.isModified():
            r = QMessageBox.warning(self,
                                    "pyschem",
                                    "The document has been modified\n"
                                    "Do you want to save your changes?",
                                    QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
            if r == QMessageBox.Save:
                return self.on_actionSave_triggered()
            elif r == QMessageBox.Cancel:
                return False
        return True

    def saveFile(self, fileName):
        self.doc.saveToFile(fileName)
        self.fileName = fileName
        self.ui.statusbar.showMessage("File saved", 2000)


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