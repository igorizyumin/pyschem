from enum import Enum
from PyQt5.QtCore import *
from PyQt5.QtGui import QPainter, QPen
from sch.obj.line import LineTool, LineObj, LineEditor
import sch.obj.net
import sch.obj.text
import sch.obj.part
from sch.view import Event
from sch.utils import Layer, LayerType
import sch.document
from copy import copy


class ToolType(Enum):
        SelectTool = 0
        LineTool = 1
        NetTool = 2
        TextTool = 3
        PartTool = 4


def getCtrl(doc):
    if type(doc) is sch.document.DocPage:
        return SchController
    elif type(doc) is sch.document.SymbolPage:
        return SymController
    else:
        raise NotImplementedError()


class Controller(QObject):
    sigUpdate = pyqtSignal()
    sigToolChanged = pyqtSignal(int)
    sigInspectorChanged = pyqtSignal()

    def __init__(self, doc=None, view=None, lib=None):
        super().__init__()
        self._view = None
        self._doc = None
        self._tool = None
        self._toolId = 0
        self._grid = 5000
        self.lib = lib
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
            # elif event.key == Qt.Key_L:
            #     self.changeTool(ToolType.LineTool)
            # elif event.key == Qt.Key_N:
            #     self.changeTool(ToolType.NetTool)
            # elif event.key == Qt.Key_S:
            #     self.changeTool(ToolType.SelectTool)
            # elif event.key == Qt.Key_T:
            #     self.changeTool(ToolType.TextTool)
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
        self.sigToolChanged.emit(self.toolId)

    def snapPt(self, pt: QPoint):
        g = self.grid
        return QPoint(int(round(float(pt.x())/g))*g, int(round(float(pt.y())/g))*g)

    @property
    def toolId(self):
        return self._toolId

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

    @property
    def inspector(self):
        return self._tool.inspector

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

    @pyqtSlot(int)
    def changeTool(self, tool_id):
        if self._toolId == tool_id:
            return
        self._toolId = tool_id
        self._installTool(self.tools()[tool_id](self))
        self.sigInspectorChanged.emit()

    @staticmethod
    def tools():
        raise NotImplementedError()


class SchController(Controller):
    def __init__(self, doc=None, view=None, lib=None):
        super().__init__(doc, view, lib)

    @staticmethod
    def tools():
        return SelectTool, LineTool, sch.obj.net.NetTool,  sch.obj.text.TextTool, sch.obj.part.PartTool


class SymController(Controller):
    def __init__(self, doc=None, view=None, lib=None):
        super().__init__(doc, view, lib)

    @staticmethod
    def tools():
        return SelectTool, LineTool, sch.obj.text.TextTool


class SelectTool(QObject):
    sigUpdate = pyqtSignal()

    def __init__(self, ctrl):
        QObject.__init__(self)
        self._ctrl = ctrl
        self._selection = []
        self._lastFind = []
        self._editor = None

    @property
    def inspector(self):
        if self._editor:
            return self._editor.inspector
        return None

    @staticmethod
    def name():
        return "Select"

    def finish(self):
        self.releaseSelection()
        self.sigUpdate.emit()

    def draw(self, painter: QPainter):
        if self._editor:
            self._editor.draw(painter)
            return
        pen = QPen(Layer.color(LayerType.selection))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setWidth(0)
        painter.setBrush(Qt.NoBrush)
        painter.setPen(pen)
        for obj in self._selection:
            painter.drawRect(obj.bbox().marginsAdded(QMargins(500,500,500,500)))

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
            self.selectionChanged(event)

    @pyqtSlot()
    def releaseSelection(self):
        self._selection.clear()
        self.selectionChanged()

    def selectionChanged(self, event=None):
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
        elif len(self._selection) == 1 and type(self._selection[0]) is sch.obj.part.PartObj:
            self._editor = sch.obj.part.PartEditor(self._ctrl, self._selection[0])
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)
        self._ctrl.sigInspectorChanged.emit()
        if event and self._editor is not None:
            self._editor.handleEvent(event)


# TODO: property inspector / editor
class EditHandle(QObject):
    sigDragged = pyqtSignal('QPoint')
    sigMoved = pyqtSignal('QPoint')

    def __init__(self, ctrl, pos=QPoint()):
        super().__init__()
        self._ctrl = ctrl
        self.pos = QPoint(pos)
        self._dragging = False
        self._moved = False

    def draw(self, painter: QPainter):
        r = self._ctrl.view.hitRadius() * 0.7
        x, y = self.pos.x(), self.pos.y()
        painter.drawRect(QRect(QPoint(x-r, y-r), QPoint(x+r, y+r)))

    def testHit(self, pt: QPoint):
        return (self.pos - self._ctrl.snapPt(pt)).manhattanLength() <= self._ctrl.view.hitRadius()

    def handleEvent(self, event: Event):
        if event.evType == Event.Type.MouseMoved:
            if self._dragging:
                if self.pos != self._ctrl.snapPt(event.pos):
                    self.pos = self._ctrl.snapPt(event.pos)
                    self.sigDragged.emit(self.pos)
                    self._moved = True
                event.handled = True
        elif event.evType == Event.Type.MousePressed:
            if self.testHit(event.pos):
                self._dragging = True
                self._moved = False
                event.handled = True
        elif event.evType == Event.Type.MouseReleased:
            if self._dragging:
                self._dragging = False
                if self._moved or self.pos != self._ctrl.snapPt(event.pos):
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
                if self.pos != self._ctrl.snapPt(self._start + event.pos):
                    self.pos = self._ctrl.snapPt(self._start + event.pos)
                    self.sigDragged.emit(self.pos)
                    self._moved = True
                event.handled = True
        elif event.evType == Event.Type.MousePressed:
            if self.testHit(event.pos):
                self._start = self.pos - event.pos
                self._dragging = True
                self._moved = False
                event.handled = True
        elif event.evType == Event.Type.MouseReleased:
            if self._dragging:
                self._dragging = False
                # self.pos = self._ctrl.snapPt(event.pos)
                if self._moved:
                    self.sigMoved.emit(self.pos)
                event.handled = True
