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
