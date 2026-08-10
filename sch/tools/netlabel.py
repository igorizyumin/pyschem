from PySide6.QtCore import QObject, Signal, Slot, QPoint, Qt

import copy

import sch.document
from sch.obj.netlabel import NetLabelObj
from sch.tools.base import BaseEditor, TextHandle
from sch.tools.text import TextInspector
from sch.view import Event


class NetLabelTool(QObject):
    """Place simple, semantics-neutral graphical net labels."""

    sigUpdate = Signal()

    def __init__(self, ctrl):
        super().__init__()
        self._ctrl = ctrl
        self._obj = NetLabelObj("net")
        self._inspector = TextInspector(self._obj)

    @staticmethod
    def name():
        return "Add Net Label"

    @property
    def inspector(self):
        return self._inspector

    def finish(self):
        self._obj = None
        self.sigUpdate.emit()

    def draw(self, painter):
        if self._obj is not None:
            self._obj.draw(painter)

    def handleEvent(self, event):
        if self._obj is None:
            return
        if event.evType == Event.Type.MouseMoved:
            self._obj.pos = self._ctrl.snapPt(event.pos)
            self.sigUpdate.emit()
            event.handled = True
        elif event.evType == Event.Type.MouseReleased:
            self._ctrl.doc.doCommand(sch.document.ObjAddCmd(self._obj))
            self._obj = copy.copy(self._obj)
            self._inspector.obj = self._obj
            event.handled = True
        elif event.evType == Event.Type.KeyPressed and event.key == Qt.Key_R:
            self._obj.rot = (self._obj.rot + 90) % 360
            self.sigUpdate.emit()
            event.handled = True


class NetLabelEditor(BaseEditor):
    def __init__(self, ctrl, obj):
        super().__init__(ctrl, obj)
        self._inspector = TextInspector(obj)
        self._inspector.edited.connect(self._commit)

    def create_handles(self):
        self._handles = [TextHandle(self._ctrl, self._obj)]

    def _setup_handle_connections(self):
        self._handles[0].sigDragged.connect(self._drag)
        self._handles[0].sigMoved.connect(self._commit)

    def update_handles(self):
        self._handles[0].pos = self._obj.posGlobal()

    def handle_custom_event(self, event):
        super().handle_custom_event(event)
        if event.handled:
            return
        if event.evType == Event.Type.KeyPressed and event.key == Qt.Key_R:
            self._obj.rot = (self._obj.rot + 90) % 360
            self._commit()
            event.handled = True

    @Slot("QPoint")
    def _drag(self, pos):
        self._obj.setPosGlobal(pos)
        self.sigUpdate.emit()

    @Slot()
    def _commit(self):
        self._obj.setPosGlobal(self._handles[0].pos)
        super()._commit()
