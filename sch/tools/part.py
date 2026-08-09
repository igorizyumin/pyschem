from PySide6.QtCore import QObject, Signal, Slot, QPoint, QRect, QMargins, Qt
from PySide6.QtGui import QPainter, QPen, QBrush, QTransform
from PySide6.QtWidgets import QWidget, QListWidgetItem
import sch.document
import sch.controller
from sch.utils import LayerType, Layer, Geom
from sch.obj.part import PartObj
from sch.obj.net import NetObj
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


class PartDragCmd(sch.document.BaseUndoCmd):
    """Atomically move a part and the wires attached to its pins."""

    def __init__(self, doc, part, before, after, nets_before, nets_after):
        super().__init__("drag part", doc=doc)
        self._part = part
        self._before = copy.copy(before)
        self._after = copy.copy(after)
        self._nets_before = list(nets_before)
        self._nets_after = list(nets_after)
        self._first_redo = True

    def _set_part(self, state):
        self._part.__dict__.clear()
        self._part.__dict__.update(copy.copy(state))

    def _set_nets(self, nets):
        self.doc.replaceObjects(nets, nets, objType=NetObj)

    def redo(self):
        if not self._first_redo:
            self._set_part(self._after)
        self._set_nets(self._nets_after)
        self._first_redo = False

    def undo(self):
        self._set_part(self._before)
        self._set_nets(self._nets_before)


class PartEditor(BaseEditor):

    def __init__(self, ctrl, obj):
        self._dragging = False
        self._startPos = QPoint()
        self._grabOffset = QPoint()
        self._drag_before = None
        self._wire_source = None
        self._working_wire_source = None
        self._wire_preview = None
        self._pin_positions = None
        self._last_drag_cursor = None
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
        painter.drawRect(self._obj.bbox().marginsAdded(QMargins(500, 500, 500, 500)))

    def hiddenObjects(self):
        return tuple(self._wire_source or ()) if self._wire_preview is not None else ()

    def previewObjects(self):
        return list(self._wire_preview) if self._wire_preview is not None else None

    def previewDrawables(self):
        return list(self._wire_preview or ())

    @staticmethod
    def _axis(net):
        if net.pt1.y() == net.pt2.y():
            return "horizontal"
        if net.pt1.x() == net.pt2.x():
            return "vertical"
        return None

    @staticmethod
    def _point_key(point):
        return point.x(), point.y()

    @classmethod
    def _perpendicular_move(cls, net, delta):
        axis = cls._axis(net)
        if axis == "horizontal":
            return delta.y() != 0
        if axis == "vertical":
            return delta.x() != 0
        return False

    def _build_orthogonal_wire_preview(self, delta):
        """Move the pin-connected wire graph without routing detours."""
        source = self._working_wire_source
        pin_moves = {
            self._point_key(old): old + delta
            for old in self._pin_positions
        }
        body_indices = {
            index for index, net in enumerate(source)
            if any(self._point_key(endpoint) in pin_moves
                   for endpoint in (net.pt1, net.pt2))
            and self._perpendicular_move(net, delta)
        }

        point_moves = dict(pin_moves)
        preview = [None] * len(source)
        processed = set()
        pending = list(point_moves.items())

        for index in body_indices:
            net = source[index]
            preview[index] = net.translated(delta)
            processed.add(index)
            for endpoint in (net.pt1, net.pt2):
                key = self._point_key(endpoint)
                point_moves[key] = endpoint + delta
                pending.append((key, point_moves[key]))

        while pending:
            old_key, _ = pending.pop(0)
            moved = point_moves[old_key]
            for index, net in enumerate(source):
                if index in processed:
                    continue
                endpoint_keys = (self._point_key(net.pt1),
                                 self._point_key(net.pt2))
                if old_key not in endpoint_keys:
                    continue

                pt1 = point_moves.get(endpoint_keys[0], net.pt1)
                pt2 = point_moves.get(endpoint_keys[1], net.pt2)
                moved_first = endpoint_keys[0] in point_moves
                moved_second = endpoint_keys[1] in point_moves
                if moved_first != moved_second:
                    axis = self._axis(net)
                    if moved_first and axis == "horizontal":
                        pt2 = QPoint(pt2.x(), pt1.y())
                    elif moved_first and axis == "vertical":
                        pt2 = QPoint(pt1.x(), pt2.y())
                    elif moved_second and axis == "horizontal":
                        pt1 = QPoint(pt1.x(), pt2.y())
                    elif moved_second and axis == "vertical":
                        pt1 = QPoint(pt2.x(), pt1.y())

                processed.add(index)
                if pt1 == pt2:
                    preview[index] = None
                    continue
                preview[index] = NetObj(pt1, pt2)
                for old_endpoint, new_endpoint in ((net.pt1, pt1),
                                                    (net.pt2, pt2)):
                    key = self._point_key(old_endpoint)
                    if key not in point_moves and old_endpoint != new_endpoint:
                        point_moves[key] = new_endpoint
                        pending.append((key, new_endpoint))

        for index, net in enumerate(source):
            if preview[index] is None and index not in processed:
                preview[index] = NetObj(net.pt1, net.pt2)
        points = (self._ctrl.doc.connection_points()
                  if hasattr(self._ctrl.doc, "connection_points") else None)
        return NetObj._normalizeGeometry(
            [net for net in preview if net is not None], points)

    def _build_wire_preview(self, delta, orthogonal, maintain_connectivity):
        if self._working_wire_source is None:
            return None
        if not maintain_connectivity:
            return [NetObj(net.pt1, net.pt2)
                    for net in self._working_wire_source]
        if orthogonal:
            return self._build_orthogonal_wire_preview(delta)

        moved_pin_points = {
            self._point_key(old): old + delta for old in self._pin_positions
        }
        body_indices = set()
        body_points = {}
        if orthogonal:
            for index, net in enumerate(self._working_wire_source):
                attached = any(self._point_key(endpoint) in moved_pin_points
                               for endpoint in (net.pt1, net.pt2))
                if attached and self._perpendicular_move(net, delta):
                    body_indices.add(index)
                    for endpoint in (net.pt1, net.pt2):
                        body_points[self._point_key(endpoint)] = endpoint + delta

        # Perpendicular pin moves use the same body-drag graph behavior as a
        # wire endpoint: the attached segment translates, and any branch at
        # its far endpoint follows that junction so it cannot detach.
        moved_points = dict(moved_pin_points)
        moved_points.update(body_points)
        preview = []
        additions = []
        addition_keys = set()
        for index, net in enumerate(self._working_wire_source):
            if index in body_indices:
                preview.append(net.translated(delta))
                continue
            pt1, pt2 = net.pt1, net.pt2
            for endpoint_name in ("pt1", "pt2"):
                endpoint = pt1 if endpoint_name == "pt1" else pt2
                moved = moved_points.get(self._point_key(endpoint))
                if moved is None:
                    continue
                replacement = moved
                if orthogonal:
                    axis = self._axis(net)
                    if axis == "horizontal":
                        replacement = QPoint(moved.x(), endpoint.y())
                    elif axis == "vertical":
                        replacement = QPoint(endpoint.x(), moved.y())
                if replacement != moved:
                    connector = NetObj(replacement, moved)
                    key = tuple(sorted((self._point_key(connector.pt1),
                                        self._point_key(connector.pt2))))
                    if connector.pt1 != connector.pt2 and key not in addition_keys:
                        addition_keys.add(key)
                        additions.append(connector)
                if endpoint_name == "pt1":
                    pt1 = replacement
                else:
                    pt2 = replacement
            preview.append(NetObj(pt1, pt2))

        points = (self._ctrl.doc.connection_points()
                  if hasattr(self._ctrl.doc, "connection_points") else None)
        return NetObj._normalizeGeometry(preview + additions, points)

    def _update_drag_preview(self, cursor, modifiers):
        new_pos = self._ctrl.snapPt(self._grabOffset + cursor)
        self._obj.pos = new_pos
        delta = (new_pos - self._startPos if self._last_drag_cursor is None
                 else new_pos - self._last_drag_cursor)
        self._wire_preview = self._build_wire_preview(
            delta,
            orthogonal=not bool(modifiers & Qt.ShiftModifier),
            maintain_connectivity=not bool(modifiers & Qt.AltModifier))
        self._working_wire_source = [NetObj(net.pt1, net.pt2)
                                     for net in self._wire_preview]
        self._pin_positions = [position + delta
                               for position in self._pin_positions]
        self._last_drag_cursor = QPoint(new_pos)

    def _begin_drag(self, event):
        self._dragging = True
        self._startPos = QPoint(self._obj.pos)
        self._grabOffset = self._obj.pos - event.pos
        self._drag_before = copy.copy(self._obj.__dict__)
        self._wire_source = list(self._ctrl.doc.objects(objType=NetObj))
        self._working_wire_source = [NetObj(net.pt1, net.pt2)
                                     for net in self._wire_source]
        self._pin_positions = [position for _, position in self._obj.pin_positions()]
        self._wire_preview = [NetObj(net.pt1, net.pt2) for net in self._wire_source]
        self._last_drag_cursor = None

    def _cancel_drag(self):
        if self._drag_before is not None:
            self._obj.__dict__.clear()
            self._obj.__dict__.update(copy.copy(self._drag_before))
        self._dragging = False
        self._drag_before = None
        self._wire_source = None
        self._working_wire_source = None
        self._wire_preview = None
        self._pin_positions = None
        self._last_drag_cursor = None

    def _commit_drag(self):
        after = copy.copy(self._obj.__dict__)
        before_nets = [NetObj(net.pt1, net.pt2) for net in self._wire_source]
        after_nets = [NetObj(net.pt1, net.pt2) for net in self._wire_preview]
        self._ctrl.doc.doCommand(PartDragCmd(
            self._ctrl.doc, self._obj, self._drag_before, after,
            before_nets, after_nets))
        self._dragging = False
        self._drag_before = None
        self._wire_source = None
        self._working_wire_source = None
        self._wire_preview = None
        self._pin_positions = None
        self._last_drag_cursor = None

    def handle_custom_event(self, event):
        """Handle mouse dragging and keyboard events."""
        super().handle_custom_event(event)
        if event.handled:
            return
        if event.evType == Event.Type.MouseMoved:
            if self._dragging:
                self._update_drag_preview(event.pos, event.modifiers)
                event.handled = True
                self.sigUpdate.emit()
        elif event.evType == Event.Type.MousePressed:
            if self.testHit(event.pos):
                self._begin_drag(event)
                event.handled = True
        elif event.evType == Event.Type.MouseReleased:
            if self._dragging:
                self._update_drag_preview(event.pos, event.modifiers)
                if self._startPos != self._obj.pos:
                    self._commit_drag()
                else:
                    self._cancel_drag()
                event.handled = True
        elif event.evType == Event.Type.Cancel and self._dragging:
            self._cancel_drag()
            self.sigUpdate.emit()
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
