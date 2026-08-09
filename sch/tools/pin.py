from PySide6.QtCore import QPoint, QMargins, Qt, QObject, Signal, Slot
from PySide6.QtGui import QPainter

import sch.document
from sch.obj.pin import PinObj
from sch.tools.base import BaseEditor, EditHandle
from sch.view import Event


class PinTool(QObject):
    """Place connection points in a symbol master."""

    sigUpdate = Signal()

    def __init__(self, ctrl):
        super().__init__()
        self._ctrl = ctrl
        self._pos = QPoint()
        self._obj = PinObj(self._next_id(), pos=self._pos)

    @property
    def inspector(self):
        return None

    @staticmethod
    def name():
        return "Add Pin"

    def finish(self):
        self._obj = None
        self.sigUpdate.emit()

    def _next_id(self):
        existing = []
        if self._ctrl.doc is not None:
            for pin in self._ctrl.doc.objects(objType=PinObj):
                try:
                    existing.append(int(pin.id))
                except (TypeError, ValueError):
                    continue
        return str(max(existing, default=0) + 1)

    def draw(self, painter: QPainter):
        if self._obj is not None:
            self._obj.draw(painter)

    def handleEvent(self, event):
        if self._obj is None:
            return
        if event.evType == Event.Type.MouseMoved:
            self._pos = self._ctrl.snapPt(event.pos)
            self._obj.pos = self._pos
            self.sigUpdate.emit()
            event.handled = True
        elif event.evType == Event.Type.MouseReleased:
            self._pos = self._ctrl.snapPt(event.pos)
            self._obj.pos = self._pos
            self._ctrl.doc.doCommand(sch.document.ObjAddCmd(self._obj))
            self._obj = PinObj(self._next_id(), pos=self._pos)
            self.sigUpdate.emit()
            event.handled = True
        elif event.evType == Event.Type.KeyPressed and event.key == Qt.Key_R:
            self._obj.rot = self._obj.rot + 90
            self.sigUpdate.emit()
            event.handled = True
        elif event.evType == Event.Type.Cancel:
            self._obj = None
            self.sigUpdate.emit()
            event.handled = True


class PinEditor(BaseEditor):
    """Move and rotate a pin in a symbol master."""

    def create_handles(self):
        self._handles = [EditHandle(self._ctrl, self._obj.pos)]

    def _setup_handle_connections(self):
        self._handles[0].sigDragged.connect(self._drag)
        self._handles[0].sigMoved.connect(self._commit)

    def update_handles(self):
        self._handles[0].pos = self._obj.pos

    def draw_custom(self, painter):
        painter.drawRect(self._obj.bbox().marginsAdded(QMargins(500, 500, 500, 500)))

    def handle_custom_event(self, event):
        if event.evType == Event.Type.KeyPressed and event.key == Qt.Key_R:
            self._obj.rot = self._obj.rot + 90
            self._commit()
            event.handled = True
            return
        super().handle_custom_event(event)

    @Slot('QPoint')
    def _drag(self, pos):
        self._obj.pos = pos
        self.sigUpdate.emit()
