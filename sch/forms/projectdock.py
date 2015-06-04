from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QObject, QModelIndex, QPoint
from PyQt5.QtWidgets import QDockWidget, QMenu, QAction
from sch.uic.ui_projectdock import Ui_ProjectDock
from sch.document import MasterDocument
from sch.forms.treeutils import AbstractTreeNode, AbstractTreeModel


class ProjectDock(QDockWidget):
    openPage = pyqtSignal('QObject')

    class PageElement(object):
        def __init__(self, page):
            self.name = page.name
            self.page = page
            self.subelements = []

        @property
        def doc(self):
            return self.page.parentDoc

    class DocElement(QObject):
        def __init__(self, doc: MasterDocument):
            super().__init__()
            self._doc = doc
            doc.sigChanged.connect(self.onDocChanged)
            self.name = None
            self.subelements = []
            self.onDocChanged()

        @property
        def doc(self):
            return self._doc

        @property
        def page(self):
            return None

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
            if role == Qt.DisplayRole:
                return node.ref.name
            if role == Qt.UserRole:
                return node.ref
            return None

    def __init__(self, window, parent=None):
        super().__init__(parent)
        self.window = window
        self.ui = Ui_ProjectDock()
        self.ui.setupUi(self)
        self.ui.projectTree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.ui.projectTree.customContextMenuRequested.connect(self.onContextMenu)
        self.onDocsChanged()

    @pyqtSlot()
    def onDocsChanged(self):
        self.ui.projectTree.setModel(ProjectDock.Model([ProjectDock.DocElement(d) for d in self.window.docs]))
        self.ui.projectTree.expandAll()

    @pyqtSlot(QModelIndex)
    def on_projectTree_doubleClicked(self, idx: QModelIndex):
        p = idx.data(Qt.UserRole).page
        if p is not None:
            self.openPage.emit(p)

    @pyqtSlot(QPoint)
    def onContextMenu(self, pt: QPoint):
        index = self.ui.projectTree.indexAt(pt)
        newDocAction = QAction("New document", None)
        newDocAction.triggered.connect(self.window.on_actionNew_triggered)
        menu = QMenu()
        menu.addAction(newDocAction)
        if index.isValid():
            obj = index.data(Qt.UserRole)

            def newPage():
                obj.doc.appendNewPage()
                self.onDocsChanged()

            addPageAction = QAction("Add page", None)
            addPageAction.triggered.connect(newPage)
            rmPageAction = QAction("Delete page", None)
            menu.addAction(addPageAction)
            if obj.page is not None:
                menu.addAction(rmPageAction)
        menu.exec(self.ui.projectTree.mapToGlobal(pt))

