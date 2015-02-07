from PyQt5.QtCore import *
from sch.line import LineTool


class Controller(QObject):
    sigUpdate = pyqtSignal()

    def __init__(self, doc=None, view=None):
        super().__init__()
        self._view = None
        self._doc = None
        self._tool = None
        # properties
        self.view = view
        self.doc = doc

    def _installTool(self, tool):
        if self.view is None:
            self._tool = None
            return
        self._tool = tool
        self.view.sigMouseMoved.connect(self._tool.onMouseMoved)
        self.view.sigMouseClicked.connect(self._tool.onMouseClicked)
        self._tool.sigUpdate.connect(self.sigUpdate)

    @property
    def view(self):
        return self._view

    @view.setter
    def view(self, view):
        self._view = view
        self.sigUpdate.connect(self._view.slotUpdate)
        self._installTool(LineTool(self))

    @property
    def doc(self):
        return self._doc

    @doc.setter
    def doc(self, doc):
        self._doc = doc
        self._doc.sigChanged.connect(self.sigUpdate)

    def getDrawables(self):
        out = self.doc.objects()
        if self._tool is not None:
            out.append(self._tool)
        return out
