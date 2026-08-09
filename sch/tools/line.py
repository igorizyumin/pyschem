from PySide6.QtCore import *
from PySide6.QtGui import QPainter, QPen
from PySide6.QtCore import Signal, Slot
import sch.document
import sch.controller
from sch.utils import LayerType, Layer, Geom
from lxml import etree
from sch.view import Event
from sch.tools.base import EditHandle, BaseEditor


class LineTool(QObject):
    sigUpdate = Signal()

    def __init__(self, ctrl):
        QObject.__init__(self)
        self._ctrl = ctrl
        self._firstPt = None
        self._pos = QPoint()

    @property
    def inspector(self):
        return None

    @staticmethod
    def name():
        return "Draw Line"

    def finish(self):
        self._firstPt = None
        self.sigUpdate.emit()

    def draw(self, painter):
        pen = QPen(Layer.color(LayerType.annotate))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setWidth(0)
        painter.setPen(pen)
        if self._firstPt is not None:
            painter.drawLine(self._firstPt, self._pos)

    def handleEvent(self, e):
        if e.evType == sch.controller.Event.Type.MouseMoved:
            self._pos = self._ctrl.snapPt(e.pos)
            if self._firstPt is not None:
                self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.MouseReleased:
            if self._firstPt is None:
                self._firstPt = self._pos
            else:
                from sch.obj.line import LineObj
                self._ctrl.doc.doCommand(sch.document.ObjAddCmd(LineObj(self._firstPt, self._pos)))
                self._firstPt = None
                self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.Cancel:
            self._firstPt = None
            self.sigUpdate.emit()
            e.handled = True


class LineEditor(BaseEditor):

    def __init__(self, ctrl, obj):
        self._body_dragging = False
        self._body_drag_start = None
        self._body_drag_before = None
        super().__init__(ctrl, obj)

    def create_handles(self):
        """Create edit handles for line endpoints."""
        self._handles = [EditHandle(self._ctrl, self._obj.pt1), EditHandle(self._ctrl, self._obj.pt2)]

    def _setup_handle_connections(self):
        """Set up specific connections for line handles."""
        self._handles[0].sigDragged.connect(self._dragPt1)
        self._handles[1].sigDragged.connect(self._dragPt2)
        for h in self._handles:
            h.sigMoved.connect(self._commit)

    def update_handles(self):
        """Update handle positions to match line endpoints."""
        self._handles[0].pos = self._obj.pt1
        self._handles[1].pos = self._obj.pt2

    def draw_custom(self, painter):
        """Draw the line itself."""
        painter.drawLine(self._obj.pt1, self._obj.pt2)

    def draw_handles(self, painter):
        """Hide endpoint handles while the line body is being dragged."""
        if self._body_dragging:
            return
        super().draw_handles(painter)

    def _hit_radius(self):
        view = getattr(self._ctrl, "view", None)
        if view is not None and hasattr(view, "hitRadius"):
            return view.hitRadius()
        return 1

    def _snap(self, pos):
        snap = getattr(self._ctrl, "snapPt", None)
        return QPoint(snap(pos) if snap is not None else pos)

    def _begin_body_drag(self, pos):
        self._body_dragging = True
        self._body_drag_start = self._snap(pos)
        self._body_drag_before = (QPoint(self._obj.pt1), QPoint(self._obj.pt2))

    def _update_body_drag(self, pos):
        delta = self._snap(pos) - self._body_drag_start
        self._obj.pt1 = self._body_drag_before[0] + delta
        self._obj.pt2 = self._body_drag_before[1] + delta
        self.update_handles()
        self.sigUpdate.emit()

    def _finish_body_drag(self, commit):
        before = self._body_drag_before
        moved = (before is not None and
                 (self._obj.pt1 != before[0] or self._obj.pt2 != before[1]))
        self._body_dragging = False
        self._body_drag_start = None
        self._body_drag_before = None
        if commit and moved:
            self._commit()
        else:
            if not commit and before is not None:
                self._obj.pt1 = before[0]
                self._obj.pt2 = before[1]
            self.update_handles()
            self.sigUpdate.emit()

    @Slot('QPoint')
    def _dragPt1(self, pos):
        self._obj.pt1 = pos
        self.sigUpdate.emit()

    @Slot('QPoint')
    def _dragPt2(self, pos):
        self._obj.pt2 = pos
        self.sigUpdate.emit()

    @Slot('QPoint')
    def _commit(self):
        self._obj.pt1 = self._handles[0].pos
        self._obj.pt2 = self._handles[1].pos
        super()._commit()

    def handle_custom_event(self, event):
        if event.evType == Event.Type.MousePressed:
            # Endpoint handles get first refusal in BaseEditor.handleEvent.
            # A body drag therefore starts only when the click is on the line
            # itself and away from both endpoint handles.
            if (event.pos is not None
                    and not any(handle.testHit(event.pos)
                                for handle in self._handles)
                    and self._obj.testHit(event.pos, self._hit_radius())):
                self._begin_body_drag(event.pos)
                event.handled = True
                return
        elif event.evType == Event.Type.MouseMoved and self._body_dragging:
            self._update_body_drag(event.pos)
            event.handled = True
            return
        elif event.evType == Event.Type.MouseReleased and self._body_dragging:
            self._update_body_drag(event.pos)
            self._finish_body_drag(commit=True)
            event.handled = True
            return
        elif event.evType == Event.Type.Cancel and self._body_dragging:
            self._finish_body_drag(commit=False)
            event.handled = True
            return
        super().handle_custom_event(event)
