from PySide6.QtCore import Signal, QObject, Slot, Qt, QPoint, QRect, QMargins
from PySide6.QtGui import QPainter, QPen
import sch.obj.line
import sch.obj.net
import sch.obj.text
import sch.obj.part
import sch.tools.line
import sch.tools.net
import sch.tools.text
import sch.tools.part
import sch.tools.proptext
import sch.obj.proptext
from sch.view import Event
from sch.utils import Layer, LayerType
from sch.tools.base import EditHandle, TextHandle


class SelectTool(QObject):
    sigUpdate = Signal()

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

    @Slot()
    def releaseSelection(self):
        self._selection.clear()
        self.selectionChanged()

    def selectionChanged(self, event=None):
        self._editor = None
        if len(self._selection) == 1 and type(self._selection[0]) is sch.obj.line.LineObj:
            self._editor = sch.tools.line.LineEditor(self._ctrl, self._selection[0])
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)
        elif len(self._selection) == 1 and type(self._selection[0]) is sch.obj.net.NetObj:
            self._editor = sch.tools.net.NetEditor(self._ctrl, self._selection[0])
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)
        elif len(self._selection) == 1 and type(self._selection[0]) is sch.obj.text.TextObj:
            self._editor = sch.tools.text.TextEditor(self._ctrl, self._selection[0])
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)
        elif len(self._selection) == 1 and type(self._selection[0]) is sch.obj.part.PartObj:
            self._editor = sch.tools.part.PartEditor(self._ctrl, self._selection[0])
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)
        elif len(self._selection) == 1 and type(self._selection[0]) is sch.obj.proptext.PropTextObj:
            self._editor = sch.tools.proptext.PropTextEditor(self._ctrl, self._selection[0])
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)
        self._ctrl.sigInspectorChanged.emit()
        if event and self._editor is not None:
            self._editor.handleEvent(event)
