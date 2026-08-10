from PySide6.QtCore import QPoint, QMargins, Qt, QObject, Signal, Slot
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QWidget, QFormLayout, QLineEdit

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

    def __init__(self, ctrl, obj):
        super().__init__(ctrl, obj)
        self._inspector = PinInspector(obj)
        self._inspector.edited.connect(self._commit)

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


class PinInspector(QWidget):
    """Edit the properties of a pin in a symbol master."""

    edited = Signal()

    def __init__(self, obj=None, parent=None):
        super().__init__(parent)
        self._property_layout = QFormLayout(self)
        self._property_widgets = {}
        self._obj = None
        self.obj = obj

    @property
    def obj(self):
        return self._obj

    @obj.setter
    def obj(self, new):
        self._obj = new
        self._loadProperties(new)

    def _loadProperties(self, obj):
        while self._property_layout.count():
            item = self._property_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._property_widgets.clear()
        if obj is None:
            return

        definitions = sorted(
            (definition for definition in obj.getPropertyDefinitions()
             if definition.visible),
            key=lambda definition: (definition.display_order, definition.name),
        )
        for definition in definitions:
            editor = QLineEdit()
            try:
                editor.setText(obj.properties.get(definition.name))
            except KeyError:
                editor.setText("")
            editor.setReadOnly(not definition.editable)
            editor.editingFinished.connect(
                lambda name=definition.name, widget=editor:
                    self._propertyEdited(name, widget)
            )
            self._property_layout.addRow(definition.display_name, editor)
            self._property_widgets[definition.name] = editor

    def _propertyEdited(self, name, editor):
        if self._obj is None:
            return
        self._obj.setProp(name, editor.text())
        self.edited.emit()
