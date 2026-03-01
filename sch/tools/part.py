from PySide6.QtCore import QObject, Signal, Slot, QPoint, QRect, QMargins, Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QTransform
from PySide6.QtWidgets import QWidget, QListWidgetItem
import sch.document
import sch.controller
from sch.utils import LayerType, Layer, Geom
from sch.obj.part import PartObj
from sch.view import Event
from sch.obj.proptext import PropTextObj
from sch.uic.ui_partinspector import Ui_PartInspector
from sch.tools.base import BaseEditor
import copy


class PartTool(QObject):
    sigUpdate = Signal()

    def __init__(self, ctrl):
        QObject.__init__(self)
        self._ctrl = ctrl
        self._pos = QPoint()
        self._obj = PartObj(lib=self._ctrl.lib)
        self._inspector = PartInspector(self._ctrl)
        self._inspector.masterChanged.connect(self.onMasterChanged)

    def finish(self):
        self._obj = None
        self.sigUpdate.emit()

    @property
    def inspector(self):
        return self._inspector

    @staticmethod
    def name():
        return "Place Part"

    def draw(self, painter):
        if self._obj:
            self._obj.draw(painter)

    def handleEvent(self, e):
        if e.evType == sch.controller.Event.Type.MouseMoved:
            self._obj.pos = self._ctrl.snapPt(e.pos) - (self._obj.bbox().topLeft() - self._obj.pos)
            self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.MouseReleased:
            if self._hasValidMaster():
                cmd = sch.document.ObjAddCmd(self._obj)
                self._ctrl.doc.doCommand(cmd)
                self._obj = copy.copy(self._obj)
                self._inspector.obj = self._obj
            e.handled = True

    def _hasValidMaster(self):
        """Check if the part has a valid master symbol selected."""
        return self._obj._master is not None

    @Slot(str, str)
    def onMasterChanged(self, path, sym):
        self._obj.name = sym
        self._obj.path = path


class PartInspector(QWidget):
    edited = Signal()
    masterChanged = Signal(str, str)

    def __init__(self, ctrl, obj=None, parent=None):
        super().__init__(parent)
        self.ui = Ui_PartInspector()
        self.ui.setupUi(self)
        self._ctrl = ctrl
        self._populateList()
        self._obj = None
        self.obj = obj

    @property
    def obj(self):
        return self._obj

    @obj.setter
    def obj(self, new):
        self._obj = new
        self._loadProperties(new)

    def _populateList(self):
        for i in self._ctrl.lib.getSymList():
            for j in i[1]:
                item = QListWidgetItem()
                item.setText("{} : {}".format(i[0], j))
                item.setData(Qt.UserRole, (i[0], j))
                self.ui.masterList.addItem(item)

    def _loadProperties(self, obj: PartObj):
        if obj is None:
            return
        for i in range(0, self.ui.masterList.count()):
            path, name = self.ui.masterList.item(i).data(Qt.UserRole)
            if path == obj.path and name == obj.name:
                self.ui.masterList.setCurrentRow(i)
                break

    @Slot(QListWidgetItem, QListWidgetItem)
    def on_masterList_currentItemChanged(self, curr, prev):
        d = curr.data(Qt.UserRole)
        self.masterChanged.emit(d[0], d[1])


class PartEditor(BaseEditor):

    def __init__(self, ctrl, obj):
        self._dragging = False
        self._startPos = QPoint()
        self._grabOffset = QPoint()
        super().__init__(ctrl, obj)
        self._inspector = PartInspector(ctrl, obj)
        self._inspector.edited.connect(self._commit)
        self._inspector.masterChanged.connect(self._masterChanged)

    def create_handles(self):
        """Part editor doesn't use traditional handles."""
        self._handles = []

    def testHit(self, pt):
        """Test hit using the object's own hit testing."""
        return self._obj.testHit(pt, 0)

    def draw_custom(self, painter):
        """Draw selection rectangle around the part."""
        from PySide6.QtCore import QMargins
        painter.drawRect(self._obj.bbox().marginsAdded(QMargins(500,500,500,500)))

    def handle_custom_event(self, event):
        """Handle mouse dragging and keyboard events."""
        super().handle_custom_event(event)
        if event.handled:
            return
        if event.evType == Event.Type.MouseMoved:
            if self._dragging:
                self._obj.pos = self._ctrl.snapPt(self._grabOffset + event.pos)
                event.handled = True
                self.sigUpdate.emit()
        elif event.evType == Event.Type.MousePressed:
            if self.testHit(event.pos):
                self._dragging = True
                self._startPos = self._obj.pos
                self._grabOffset = self._obj.pos - event.pos
                event.handled = True
        elif event.evType == Event.Type.MouseReleased:
            if self._dragging:
                self._dragging = False
                if self._startPos != self._obj.pos:
                    self._commit()
                event.handled = True
        elif event.evType == Event.Type.KeyPressed:
            if event.key == Qt.Key_R:
                rot = -90 if self._obj.mirror else 90
                self._obj.rot = (self._obj.rot + rot) % 360
                self._commit()
            if event.key == Qt.Key_H:
                self._obj.rot = (self._obj.rot + 180) % 360
                self._obj.mirror = not self._obj.mirror
                self._commit()
            if event.key == Qt.Key_V:
                self._obj.mirror = not self._obj.mirror
                self._commit()

    @Slot(str, str)
    def _masterChanged(self, path, name):
        self._obj.path = path
        self._obj.name = name
        self._commit()

    @Slot()
    def _commit(self):
        super()._commit()
