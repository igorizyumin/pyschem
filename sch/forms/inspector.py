from PySide6.QtCore import Signal, Slot, Qt, QObject, QModelIndex, QPoint
from PySide6.QtGui import QAction
from PySide6.QtWidgets import QDockWidget, QMenu, QWidget
from sch.uic.ui_inspectordock import Ui_InspectorDock


class InspectorDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_InspectorDock()
        self.ui.setupUi(self)
        self._child = None

    @Slot(QWidget)
    def setChild(self, child):
        self._clearChild()
        if child is not None:
            self._newChild(child)

    def _clearChild(self):
        if self._child is not None:
            self.ui.contents.layout().removeWidget(self._child)
            self._child.setParent(None)
        self._child = None

    def _newChild(self, child):
        self._child = child
        self.ui.contents.layout().addWidget(self._child)