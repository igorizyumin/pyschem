from PyQt5.QtCore import pyqtSignal, pyqtSlot, Qt, QObject, QModelIndex, QPoint
from PyQt5.QtWidgets import QDockWidget, QMenu, QAction, QWidget
from sch.uic.ui_inspectordock import Ui_InspectorDock


class InspectorDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.ui = Ui_InspectorDock()
        self.ui.setupUi(self)
        self._child = None

    @pyqtSlot(QWidget)
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