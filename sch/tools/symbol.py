"""Inspector for symbol-master-level part properties."""

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFormLayout, QLineEdit, QWidget

import sch.document


class SymbolInspector(QWidget):
    """Edit global property defaults while no symbol object is selected."""

    edited = Signal()

    def __init__(self, ctrl, obj, parent=None):
        super().__init__(parent)
        self._ctrl = ctrl
        self._obj = None
        self._property_layout = QFormLayout(self)
        self._property_widgets = {}
        self.obj = obj

    @property
    def obj(self):
        return self._obj

    @obj.setter
    def obj(self, value):
        self._obj = value
        self._loadProperties(value)

    def _clearProperties(self):
        while self._property_layout.count():
            item = self._property_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self._property_widgets.clear()

    def _loadProperties(self, obj):
        self._clearProperties()
        if obj is None:
            return
        definitions = sorted(
            obj.getMasterPropertyDefinitions(),
            key=lambda definition: (definition.display_order, definition.name),
        )
        for definition in definitions:
            editor = QLineEdit()
            try:
                editor.setText(obj.getProp(definition.name))
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
        command = sch.document.ObjChangeCmd(self._obj)
        self._obj.setProp(name, editor.text())
        self._ctrl.doc.doCommand(command)
        self._loadProperties(self._obj)
        self.edited.emit()
