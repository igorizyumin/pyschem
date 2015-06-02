from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QObject, QModelIndex
from PyQt5.QtWidgets import QMainWindow, QDockWidget, QMessageBox, QFileDialog, QWidget, QVBoxLayout
from sch.uic.ui_mainwindow import Ui_MainWindow
from sch.uic.ui_toolsdock import Ui_ToolsDock
from sch.uic.ui_projectdock import Ui_ProjectDock
from sch.view import SchView
from sch.controller import Controller, ToolType
from sch.document import MasterDocument, DocPage
from sch.forms.treeutils import AbstractTreeNode, AbstractTreeModel


class MainWindow(QMainWindow):
    tabUndo = pyqtSignal()
    tabRedo = pyqtSignal()
    docsChanged = pyqtSignal()

    def __init__(self):
        QMainWindow.__init__(self)
        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)
        self.ui.actionUndo.setEnabled(False)
        self.ui.actionRedo.setEnabled(False)
        self.ui.actionUndo.triggered.connect(self.tabUndo)
        self.ui.actionUndo.triggered.connect(self.tabRedo)
        self.docs = []
        self.toolsDock = ToolsDock()
        self.projDock = ProjectDock(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.toolsDock)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.projDock)
        self.docsChanged.connect(self.projDock.onDocsChanged)
        self.projDock.openPage.connect(self.on_pageOpen)
        self.activeTab = None
        # self.toolsDock.toolChanged.connect(self.ctrl.changeTool)

    def closeEvent(self, e):
        if self.saveAll():
            e.accept()
            super().closeEvent(e)
        else:
            e.ignore()

    def currentTab(self):
        return self.activeTab

    def currentDoc(self):
        return None

    def saveDoc(self, doc: MasterDocument):
        if doc is None:
            return False
        if doc.fileName is None:
            return self.saveAsDoc(doc)
        else:
            doc.saveToFile()
            self.ui.statusbar.showMessage("Document saved", 5000)
            return True

    def saveAsDoc(self, doc: MasterDocument):
        fn = QFileDialog.getSaveFileName(self)[0]
        if fn == "":
            return False
        doc.saveToFile(fn)
        self.ui.statusbar.showMessage("Document saved as {}".format(fn), 5000)
        return True

    def saveAll(self):
        for doc in self.docs:
            if doc.isModified():
                r = QMessageBox.warning(self,
                                        "pyschem",
                                        "The document {} has been modified\n"
                                        "Do you want to save your changes?".format(doc.name()),
                                        QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel)
                if r == QMessageBox.Save:
                    return self.saveDoc(doc)
                elif r == QMessageBox.Cancel:
                    return False
        return True

    @pyqtSlot('bool', 'bool')
    def onTabUndoChanged(self, enUndo, enRedo):
        self.ui.actionUndo.setEnabled(enUndo)
        self.ui.actionRedo.setEnabled(enRedo)

    @pyqtSlot()
    def on_actionNew_triggered(self):
        self.docs.append(MasterDocument())
        self.docsChanged.emit()

    @pyqtSlot()
    def on_actionOpen_triggered(self):
        fn = QFileDialog.getOpenFileName(self)[0]
        if fn != "":
            for d in self.docs:
                if d.fileName == fn:
                    self.ui.statusbar.showMessage("Document already open", 5000)
                    return
            try:
                d = MasterDocument()
                d.loadFromFile(fn)
                self.docs.append(d)
                self.docsChanged.emit()
                self.ui.statusbar.showMessage("Document loaded", 5000)
            except Exception as e:
                self.ui.statusbar.showMessage("Error loading document: {}: {}".format(str(type(e)), str(e)), 5000)

    @pyqtSlot()
    def on_actionSave_triggered(self):
        return self.saveDoc(self.currentDoc())

    @pyqtSlot()
    def on_actionSave_As_triggered(self):
        return self.saveAsDoc(self.currentDoc())

    def installTab(self, newTab):
        # disconnect signals from old tab
        if self.activeTab is not None:
            self.activeTab.undoChanged.disconnect(self.onTabUndoChanged)
            self.toolsDock.toolChanged.disconnect(self.activeTab.ctrl.changeTool)
        if newTab is not None:
            # restore active tool
            self.toolsDock.on_toolChanged(newTab.ctrl.toolType)
            # connect signals
            newTab.undoChanged.connect(self.onTabUndoChanged)
            self.toolsDock.toolChanged.connect(newTab.ctrl.changeTool)
            self.activeTab = newTab


    @pyqtSlot(DocPage)
    def on_pageOpen(self, page):
        tab = PageTab(page)
        self.installTab(tab)
        self.ui.tabWidget.addTab(tab, page.name)

    @pyqtSlot(int)
    def on_tabWidget_currentChanged(self, idx):
        tab = None
        if idx >= 0:
            tab = self.ui.tabWidget.widget(idx)
        self.installTab(tab)


class PageTab(QWidget):
    # args: can undo / can redo
    undoChanged = pyqtSignal(bool, bool)

    def __init__(self, doc: DocPage, parent=None):
        super().__init__(parent)
        self.view = SchView()
        self.doc = doc
        self.ctrl = Controller(doc=self.doc, view=self.view)
        self.view.setCtrl(self.ctrl)
        self.doc.undoStack.canUndoChanged.connect(self._onUndoChanged)
        self.doc.undoStack.canRedoChanged.connect(self._onUndoChanged)
        layout = QVBoxLayout()
        layout.addWidget(self.view)
        self.setLayout(layout)

    @pyqtSlot(bool)
    def _onUndoChanged(self):
        self.undoChanged.emit(self.canUndo(), self.canRedo())

    def canUndo(self):
        return self.doc.undoStack.canUndo()

    def canRedo(self):
        return self.doc.undoStack.canRedo()

    def undo(self):
        self.doc.undo()

    def redo(self):
        self.doc.redo()


class ToolsDock(QDockWidget):
    toolChanged = pyqtSignal(ToolType)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_ToolsDock()
        self.ui.setupUi(self)

    @pyqtSlot(ToolType)
    def on_toolChanged(self, tool):
        # print("tool changed: {}".format(tool))
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


class ProjectDock(QDockWidget):
    openPage = pyqtSignal('QObject')

    class PageElement(object):
        def __init__(self, page):
            self.name = page.name
            self.page = page
            self.subelements = []

    class DocElement(QObject):
        def __init__(self, doc: MasterDocument):
            self._doc = doc
            doc.sigChanged.connect(self.onDocChanged)
            self.name = None
            self.subelements = []
            self.onDocChanged()

        @pyqtSlot()
        def onDocChanged(self):
            self.name = self._doc.name()
            self.subelements = []
            for p in self._doc.pages:
                self.subelements.append(ProjectDock.PageElement(p))

    class Node(AbstractTreeNode):
        def __init__(self, ref, parent, row):
            self.ref = ref
            super().__init__(parent, row)

        def _getChildren(self):
            return [ProjectDock.Node(elem, self, index)
                    for index, elem in enumerate(self.ref.subelements)]

    class Model(AbstractTreeModel):
        def __init__(self, rootElements):
            self.rootElements = rootElements
            super().__init__()

        def _getRootNodes(self):
            return [ProjectDock.Node(elem, None, index)
                    for index, elem in enumerate(self.rootElements)]

        def columnCount(self, parent):
            return 1

        def data(self, index, role):
            if not index.isValid():
                return None
            node = index.internalPointer()
            if role == Qt.DisplayRole and index.column() == 0:
                return node.ref.name
            if role == Qt.UserRole and index.column() == 0:
                if type(node.ref) == ProjectDock.PageElement:
                    return node.ref.page
            return None

    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.ui = Ui_ProjectDock()
        self.ui.setupUi(self)
        self.onDocsChanged()

    @pyqtSlot()
    def onDocsChanged(self):
        self.ui.projectTree.setModel(ProjectDock.Model([ProjectDock.DocElement(d) for d in self.window.docs]))
        self.ui.projectTree.expandAll()

    @pyqtSlot(QModelIndex)
    def on_projectTree_doubleClicked(self, idx: QModelIndex):
        p = idx.data(Qt.UserRole)
        if p is not None:
            # print("Double click on {}".format(p.name))
            self.openPage.emit(p)
