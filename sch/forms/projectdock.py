from PySide6.QtCore import Signal, Slot, Qt, QObject, QModelIndex, QPoint
from PySide6.QtGui import QAction, QIcon
from PySide6.QtWidgets import QDockWidget, QMenu, QStyle
from sch.uic.ui_projectdock import Ui_ProjectDock
from sch.document import MasterDocument, DocPage
from sch.forms.treeutils import AbstractTreeNode, AbstractTreeModel
from sch.obj.sheetref import SheetRefObj


class ProjectDock(QDockWidget):
    openPage = Signal(object)

    class SymElement(object):
        def __init__(self, sym):
            self.name = "Symbol: " + sym.name
            self.page = sym
            self.subelements = []

        @property
        def doc(self):
            return self.page.parentDoc

    class SheetRefElement(object):
        """Element representing a sheet reference with its child page."""
        
        def __init__(self, sheet_ref: SheetRefObj, parent_element):
            self.sheet_ref = sheet_ref
            self._parent_element = parent_element
            
            # Resolve the target page
            doc, page = sheet_ref.resolve_target()
            self.resolved_page = page
            self.resolved_doc = doc
            
            # Display name shows the sheet reference label or page name
            if sheet_ref.page_name:
                self.name = f"└ {sheet_ref.page_name}"
            else:
                self.name = f"└ SheetRef (no name)"
            
            self.subelements = []
            if self.resolved_page is not None:
                # Add sheet references from the child page
                for child_sheet_ref in self.resolved_page.sheetReferences():
                    self.subelements.append(ProjectDock.SheetRefElement(child_sheet_ref, self))

        @property
        def doc(self):
            return self.resolved_doc if self.resolved_doc else self._parent_element.doc

        @property
        def page(self):
            return self.resolved_page

    class PageElement(object):
        """Element representing a page with its sheet references."""
        
        def __init__(self, page: DocPage):
            self.name = page.name
            self.page = page
            self.subelements = []
            
            # Add sheet references as children
            for sheet_ref in page.sheetReferences():
                self.subelements.append(ProjectDock.SheetRefElement(sheet_ref, self))

    class DocElement(QObject):
        """Element representing a document containing symbols and pages."""
        
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

        @Slot()
        def onDocChanged(self):
            """Update the document element when the document changes."""
            self.name = self._doc.name()
            self.subelements = []
            for s in self._doc.symbols:
                self.subelements.append(ProjectDock.SymElement(s))
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

    @Slot()
    def onDocsChanged(self):
        self.ui.projectTree.setModel(ProjectDock.Model([ProjectDock.DocElement(d) for d in self.window.docs]))
        self.ui.projectTree.expandAll()

    @Slot(QModelIndex)
    def on_projectTree_doubleClicked(self, idx: QModelIndex):
        p = idx.data(Qt.UserRole).page
        if p is not None:
            self.openPage.emit(p)

    @Slot(QPoint)
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

            def newSym():
                obj.doc.appendNewSymbol()
                self.onDocsChanged()

            addPageAction = QAction("Add page", None)
            addPageAction.triggered.connect(newPage)
            addSymAction = QAction("Add symbol", None)
            addSymAction.triggered.connect(newSym)
            rmPageAction = QAction("Delete page", None)
            menu.addAction(addPageAction)
            menu.addAction(addSymAction)
            menu.addSeparator()
            if obj.page is not None:
                menu.addAction(rmPageAction)
        menu.exec(self.ui.projectTree.mapToGlobal(pt))

