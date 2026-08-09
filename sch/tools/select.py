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
import sch.tools.hierarchy
import sch.tools.pin
import sch.obj.proptext
import sch.obj.sheetref
import sch.obj.pin
from sch.view import Event
from sch.utils import Layer, LayerType
from sch.tools.base import EditHandle, TextHandle
from sch.tools.group import GroupEditor


class SelectTool(QObject):
    sigUpdate = Signal()

    def __init__(self, ctrl):
        QObject.__init__(self)
        self._ctrl = ctrl
        self._selection = []
        self._lastFind = []
        self._editor = None
        self._rubber_start = None
        self._rubber_rect = None

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
        if self._rubber_rect is not None:
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(self._rubber_rect.normalized())

    def hiddenObjects(self):
        if self._editor is not None and hasattr(self._editor, 'hiddenObjects'):
            return self._editor.hiddenObjects()
        return ()

    def previewObjects(self):
        if self._editor is not None and hasattr(self._editor, 'previewObjects'):
            return self._editor.previewObjects()
        return None

    def previewDrawables(self):
        if self._editor is not None and hasattr(self._editor, 'previewDrawables'):
            return self._editor.previewDrawables()
        return ()

    def _clearRubberband(self):
        """Drop selection-rectangle state when an editor owns the gesture."""
        self._rubber_start = None
        self._rubber_rect = None

    def handleEvent(self, event: Event):
        if self._editor is not None:
            self._editor.handleEvent(event)
            if event.handled:
                if event.evType in (Event.Type.MousePressed,
                                    Event.Type.MouseMoved,
                                    Event.Type.MouseReleased):
                    self._clearRubberband()
                return
        if event.evType == Event.Type.MousePressed:
            # A group owns the complete selection envelope.  Handle this
            # before normal object hit testing so a group drag cannot fall
            # through and collapse the selection to the object under the
            # cursor.
            if len(self._selection) > 1:
                if not isinstance(self._editor, GroupEditor):
                    self.selectionChanged()
                if isinstance(self._editor, GroupEditor):
                    self._editor.handleEvent(event)
                    return
            self._rubber_start = event.pos
            self._rubber_rect = None
            hit_radius = self._ctrl.view.hitRadius()
            objs = list(self._ctrl.doc.findObjsNear(event.pos, hit_radius))
            # Wires are hairlines and are commonly grabbed by their body.
            # Give them the same modest extra tolerance used by NetEditor.
            for net in self._ctrl.doc.findObjsNear(
                    event.pos, sch.obj.net.NetObj.hitRadius(hit_radius),
                    objType=sch.obj.net.NetObj):
                if net not in objs:
                    objs.append(net)
            if len(objs) > 0:
                # cycle through objects under cursor
                if event.modifiers & Qt.ControlModifier:
                    if objs[0] in self._selection:
                        self._selection.remove(objs[0])
                    else:
                        self._selection.append(objs[0])
                    self._lastFind = objs
                elif set(self._lastFind) == set(objs) and len(self._selection) == 1:
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
        elif event.evType == Event.Type.MouseMoved and self._rubber_start is not None:
            if (event.pos - self._rubber_start).manhattanLength() > self._ctrl.view.hitRadius():
                self._rubber_rect = QRect(self._rubber_start, event.pos).normalized()
                self.sigUpdate.emit()
            event.handled = True
        elif event.evType == Event.Type.MouseReleased and self._rubber_start is not None:
            start = self._rubber_start
            rect = self._rubber_rect
            self._rubber_start = None
            self._rubber_rect = None
            if rect is not None:
                selected = [obj for obj in self._ctrl.doc.objects()
                            if rect.contains(obj.bbox().topLeft()) and
                            rect.contains(obj.bbox().bottomRight())]
                if event.modifiers & Qt.ControlModifier:
                    self._selection.extend(obj for obj in selected if obj not in self._selection)
                else:
                    self._selection = selected
                self._lastFind = []
                self.selectionChanged()
                self.sigUpdate.emit()
            event.handled = True

    @Slot()
    def releaseSelection(self):
        self._selection.clear()
        self.selectionChanged()
        self.sigUpdate.emit()

    def selectionChanged(self, event=None):
        if self._editor is not None:
            self._editor.dispose()
        self._editor = None
        if len(self._selection) > 1:
            self._editor = GroupEditor(self._ctrl, self._selection)
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)
        elif len(self._selection) == 1 and type(self._selection[0]) is sch.obj.line.LineObj:
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
        elif len(self._selection) == 1 and type(self._selection[0]) is sch.obj.sheetref.SheetRefObj:
            self._editor = sch.tools.hierarchy.SheetRefEditor(self._ctrl, self._selection[0])
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)
        elif len(self._selection) == 1 and type(self._selection[0]) is sch.obj.pin.PinObj:
            self._editor = sch.tools.pin.PinEditor(self._ctrl, self._selection[0])
            self._editor.sigUpdate.connect(self.sigUpdate)
            self._editor.sigDone.connect(self.releaseSelection)
        self._ctrl.sigInspectorChanged.emit()
        if event and self._editor is not None:
            self._editor.handleEvent(event)
            if event.handled:
                self._clearRubberband()
