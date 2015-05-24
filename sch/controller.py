from PyQt5.QtCore import *
from PyQt5.QtGui import QPainter
from enum import Enum

from sch.line import LineTool, LineObj, LineEditor


class ToolType(Enum):
        SelectTool = 0
        LineTool = 1


class Controller(QObject):
    sigUpdate = pyqtSignal()

    def __init__(self, doc=None, view=None):
        super().__init__()
        self._view = None
        self._doc = None
        self._tool = None
        self._grid = 5000
        # properties
        self.view = view
        self.doc = doc

    def _installTool(self, tool):
        if self.view is None:
            self._tool = None
            return
        self._tool = tool
        self.view.sigMouseMoved.connect(self._tool.onMouseMoved)
        self.view.sigMouseReleased.connect(self._tool.onMouseReleased)
        self._tool.sigUpdate.connect(self.sigUpdate)

    def snapPt(self, pt: QPoint):
        g = self.grid
        return QPoint(int(round(float(pt.x())/g))*g, int(round(float(pt.y())/g))*g)

    @property
    def view(self):
        return self._view

    @view.setter
    def view(self, view):
        self._view = view
        self.sigUpdate.connect(self._view.slotUpdate)
        self._installTool(SelectTool(self))

    @property
    def grid(self):
        return self._grid

    @grid.setter
    def grid(self, value):
        self._grid = value
        self.sigUpdate.emit()

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

    @pyqtSlot(ToolType)
    def changeTool(self, tool):
        if tool == ToolType.LineTool:
            self._installTool(LineTool(self))
        elif tool == ToolType.SelectTool:
            self._installTool(SelectTool(self))


class SelectTool(QObject):
    sigUpdate = pyqtSignal()

    def __init__(self, ctrl):
        QObject.__init__(self)
        self._ctrl = ctrl
        self._selection = []
        self._lastFind = []
        self._editor = None

    def draw(self, painter: QPainter):
        if self._editor:
            self._editor.draw(painter)
            return
        for obj in self._selection:
            painter.drawRect(obj.bbox())


    @pyqtSlot('QMouseEvent', 'QPoint')
    def onMouseMoved(self, event, pos: QPoint):
        pass

    @pyqtSlot('QPoint')
    def onMouseReleased(self, pos):
        if self._editor and self._editor.testHit(pos):
            return
        objs = self._ctrl.doc.findObjsNear(pos, self._ctrl.view.hitRadius())
        if len(objs) > 0:
            # cycle through objects under cursor
            if set(self._lastFind) == set(objs) and len(self._selection) == 1:
                ind = self._lastFind.index(self._selection[0])+1
                if ind >= len(self._lastFind):
                    ind = 0
                self._selection = [objs[ind]]

            else:
                self._lastFind = objs
                self._selection = [objs[0]]
            self.sigUpdate.emit()
        else:
            if self._selection:
                self._selection = []
                self._lastFind = []
                self.sigUpdate.emit()
        self.selectionChanged()

    @pyqtSlot()
    def releaseSelection(self):
        self._selection.clear()
        self.selectionChanged()

    def selectionChanged(self):
        self._editor = None
        if len(self._selection) == 1 and type(self._selection[0]) is LineObj:
            self._editor = LineEditor(self._ctrl, self._selection[0])
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)


# TODO: use chain of responsibility here instead of signals/slots for events; translate keyboard/mouse events into abstract cursor motion, etc.
# TODO: property inspector / editor
class EditHandle(QObject):
    sigDragged = pyqtSignal('QPoint')
    sigMoved = pyqtSignal('QPoint')

    def __init__(self, ctrl, pos=QPoint()):
        super().__init__()
        self._ctrl = ctrl
        self._pos = QPoint(pos)
        self._dragging = False

    def draw(self, painter: QPainter):
        r = self._ctrl.view.hitRadius()
        x, y = self._pos.x(), self._pos.y()
        painter.drawRect(QRect(QPoint(x-r, y-r), QPoint(x+r, y+r)))

    def testHit(self, pt: QPoint):
        return (self._pos - self._ctrl.snapPt(pt)).manhattanLength() <= self._ctrl.view.hitRadius()

    @pyqtSlot('QMouseEvent', 'QPoint')
    def onMouseMoved(self, event, pos: QPoint):
        if self._dragging:
            self._pos = self._ctrl.snapPt(pos)
            self.sigDragged.emit(self._pos)

    @pyqtSlot('QPoint')
    def onMousePressed(self, pos):
        if self.testHit(pos):
            self._dragging = True

    @pyqtSlot('QPoint')
    def onMouseReleased(self, pos):
        if self._dragging:
            self._dragging = False
            self._pos = self._ctrl.snapPt(pos)
            self.sigMoved.emit(self._pos)

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, newpos):
        self._pos = newpos

