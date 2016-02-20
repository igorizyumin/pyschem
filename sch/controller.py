from enum import Enum
from PyQt5.QtCore import *
from PyQt5.QtGui import QPainter
from sch.obj.line import LineTool, LineObj, LineEditor
import sch.obj.net
import sch.obj.text
from sch.view import Event


class ToolType(Enum):
        SelectTool = 0
        LineTool = 1
        NetTool = 2


class Controller(QObject):
    sigUpdate = pyqtSignal()
    sigToolChanged = pyqtSignal(ToolType)

    def __init__(self, doc=None, view=None):
        super().__init__()
        self._view = None
        self._doc = None
        self._tool = None
        self._toolType = ToolType.SelectTool
        self._grid = 5000
        # properties
        self.view = view
        self.doc = doc

    def handleEvent(self, event):
        if self._tool is not None:
            self._tool.handleEvent(event)
            if event.handled:
                return
        if event.evType == Event.Type.KeyPressed:
            event.handled = True
            if event.key == Qt.Key_Escape:
                self.handleEvent(Event(evType=Event.Type.Cancel))
            elif event.key == Qt.Key_Space:
                self.view.recenter()
            elif event.key == Qt.Key_Enter:
                self.handleEvent(Event(evType=Event.Type.Done))
            elif event.key == Qt.Key_L:
                self.changeTool(ToolType.LineTool)
            elif event.key == Qt.Key_N:
                self.changeTool(ToolType.NetTool)
            elif event.key == Qt.Key_S:
                self.changeTool(ToolType.SelectTool)
            else:
                event.handled = False

    def _installTool(self, tool):
        if self._tool is not None:
            self._tool.finish()
            self._tool = None
        if self.view is None:
            return
        self._tool = tool
        self._tool.sigUpdate.connect(self.sigUpdate)
        self.sigToolChanged.emit(self.toolType)

    def snapPt(self, pt: QPoint):
        g = self.grid
        return QPoint(int(round(float(pt.x())/g))*g, int(round(float(pt.y())/g))*g)

    @property
    def toolType(self):
        return self._toolType

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
        self.sigUpdate.emit()

    def getDrawables(self):
        class JunctionDrawable:
            @staticmethod
            def draw(painter):
                sch.obj.net.NetObj.drawJunctions(self.doc, painter)
        out = list(self.doc.objects())
        out.append(JunctionDrawable())
        if self._tool is not None:
            out.append(self._tool)
        return out

    @pyqtSlot(ToolType)
    def changeTool(self, tool):
        if self._toolType == tool:
            return
        self._toolType = tool
        if tool == ToolType.LineTool:
            self._installTool(LineTool(self))
        elif tool == ToolType.NetTool:
            self._installTool(sch.obj.net.NetTool(self))
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

    def finish(self):
        self.releaseSelection()
        self.sigUpdate.emit()

    def draw(self, painter: QPainter):
        if self._editor:
            self._editor.draw(painter)
            return
        for obj in self._selection:
            painter.drawRect(obj.bbox())

    def handleEvent(self, event: Event):
        if self._editor is not None:
            self._editor.handleEvent(event)
            if event.handled:
                return
        if event.evType == Event.Type.MousePressed:
            objs = list(self._ctrl.doc.findObjsNear(event.pos, self._ctrl.view.hitRadius()))
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
        elif len(self._selection) == 1 and type(self._selection[0]) is sch.obj.net.NetObj:
            self._editor = sch.obj.net.NetEditor(self._ctrl, self._selection[0])
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)
        elif len(self._selection) == 1 and type(self._selection[0]) is sch.obj.text.TextObj:
            self._editor = sch.obj.text.TextEditor(self._ctrl, self._selection[0])
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)


# TODO: property inspector / editor
class EditHandle(QObject):
    sigDragged = pyqtSignal('QPoint')
    sigMoved = pyqtSignal('QPoint')

    def __init__(self, ctrl, pos=QPoint()):
        super().__init__()
        self._ctrl = ctrl
        self.pos = QPoint(pos)
        self._dragging = False

    def draw(self, painter: QPainter):
        r = self._ctrl.view.hitRadius() * 0.7
        x, y = self.pos.x(), self.pos.y()
        painter.drawRect(QRect(QPoint(x-r, y-r), QPoint(x+r, y+r)))

    def testHit(self, pt: QPoint):
        return (self.pos - self._ctrl.snapPt(pt)).manhattanLength() <= self._ctrl.view.hitRadius()

    def handleEvent(self, event: Event):
        if event.evType == Event.Type.MouseMoved:
            if self._dragging:
                self.pos = self._ctrl.snapPt(event.pos)
                self.sigDragged.emit(self.pos)
                event.handled = True
        elif event.evType == Event.Type.MousePressed:
            if self.testHit(event.pos):
                self._dragging = True
                event.handled = True
        elif event.evType == Event.Type.MouseReleased:
            if self._dragging:
                self._dragging = False
                self.pos = self._ctrl.snapPt(event.pos)
                self.sigMoved.emit(self.pos)
                event.handled = True


class TextHandle(EditHandle):
    def __init__(self, ctrl, txt):
        super().__init__(ctrl, txt.pos)
        self._txt = txt
        self._start = QPoint()

    def testHit(self, pt: QPoint):
        return self._txt.testHit(pt, 0)

    def draw(self, painter: QPainter):
        painter.drawRect(self._txt.bbox())

    def handleEvent(self, event: Event):
        if event.evType == Event.Type.MouseMoved:
            if self._dragging:
                self.pos = self._ctrl.snapPt(self._start + event.pos)
                self.sigDragged.emit(self.pos)
                event.handled = True
        elif event.evType == Event.Type.MousePressed:
            if self.testHit(event.pos):
                self._start = self.pos - event.pos
                self._dragging = True
                event.handled = True
        elif event.evType == Event.Type.MouseReleased:
            if self._dragging:
                self._dragging = False
                # self.pos = self._ctrl.snapPt(event.pos)
                self.sigMoved.emit(self.pos)
                event.handled = True
