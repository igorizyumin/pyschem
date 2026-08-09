"""Editing support shared by a multi-object selection."""

import copy

from PySide6.QtCore import QObject, QPoint, QRect, Qt, Signal, QMargins
from PySide6.QtGui import QPainter, QPen, QTransform

from sch.view import Event
from sch.utils import Layer, LayerType
from sch.document import BaseUndoCmd
from sch.obj.line import LineObj
from sch.obj.net import NetObj
from sch.obj.text import TextObj
from sch.obj.part import PartObj
from sch.obj.proptext import PropTextObj
from sch.obj.sheetref import SheetRefObj
from sch.tools.drag import DragController, DragCommand


class GroupPropertyProxy:
    """A property-editor facade that writes a changed value to every object."""

    def __init__(self, objects, before_change=None):
        object.__setattr__(self, "_objects", tuple(objects))
        object.__setattr__(self, "_before_change", before_change)

    def __getattr__(self, name):
        values = [getattr(obj, name) for obj in self._objects]
        return values[0] if values and all(value == values[0] for value in values) else None

    def __setattr__(self, name, value):
        if name == "_objects":
            object.__setattr__(self, name, value)
            return
        if self._before_change is not None:
            self._before_change()
        for obj in self._objects:
            setattr(obj, name, value)

    def __getitem__(self, key):
        return self._objects[0][key]

    def setObjects(self, objects):
        object.__setattr__(self, "_objects", tuple(objects))


class GroupChangeCmd(BaseUndoCmd):
    def __init__(self, doc, objects, before, after):
        super().__init__("edit selection", doc=doc)
        self._objects = tuple(objects)
        self._before = before
        self._after = after
        self._first = True
        self.current = list(objects)

    @staticmethod
    def _state(obj):
        if isinstance(obj, NetObj):
            return (obj.pt1, obj.pt2)
        # Text objects contain non-pickleable Qt caches (QStaticText).  Their
        # fields are replaced, rather than mutated in place, so a shallow
        # dictionary memento is sufficient and matches ObjChangeCmd.
        return copy.copy(getattr(obj, "__dict__", {}))

    def _restore(self, states):
        net_indices = []
        net_targets = []
        for index, (obj, state) in enumerate(zip(self.current, states)):
            if isinstance(obj, NetObj):
                net_indices.append(index)
                net_targets.append(obj)
                continue
            obj.__dict__.clear()
            obj.__dict__.update(copy.copy(state))
        if net_indices:
            # References held by an undo command can be stale after another
            # net operation. Resolve the actual document instances first,
            # then replace them atomically so an old instance cannot remain
            # alongside the restored one.
            remove = [existing for existing in self.doc.objects(NetObj)
                      if any(existing is target or existing == target
                             for target in net_targets)]
            replacements = [NetObj(states[index][0], states[index][1])
                            for index in net_indices]
            self.doc.replaceObjects(remove, replacements)
            for index, replacement in zip(net_indices, replacements):
                self.current[index] = replacement
        self.doc.sigChanged.emit()

    def redo(self):
        self._restore(self._after)

    def undo(self):
        self._restore(self._before)


class CompositeGroupDragCmd(BaseUndoCmd):
    """Commit ordinary-object and net-graph previews as one undo step."""

    def __init__(self, doc, obj_before, obj_after, net_before, net_after):
        super().__init__("drag selection", doc=doc)
        self._obj_before = list(obj_before)
        self._obj_after = list(obj_after)
        self._net_before = list(net_before)
        self._net_after = list(net_after)

    def redo(self):
        self.doc.replaceObjects(self._obj_before, self._obj_after)
        self.doc.replaceObjects(self._net_before, self._net_after, objType=NetObj)

    def undo(self):
        self.doc.replaceObjects(self._obj_after, self._obj_before)
        self.doc.replaceObjects(self._net_after, self._net_before, objType=NetObj)


class GroupEditor(QObject):
    sigUpdate = Signal()
    sigDone = Signal()

    def __init__(self, ctrl, objects):
        super().__init__()
        self._ctrl = ctrl
        self._objects = list(objects)
        self._dragging = False
        self._drag_moved = False
        self._drag_origin_inside = False
        self._drag_start = None
        self._before = None
        self._inspector = None
        self._proxy = GroupPropertyProxy(self._objects, self._begin)
        self._net_source = None
        self._net_selected_ids = set()
        self._net_preview = None
        self._net_selected_preview = None
        self._drag_controller = None
        self._make_inspector()

    @staticmethod
    def _state(obj):
        if isinstance(obj, NetObj):
            return (obj.pt1, obj.pt2)
        return copy.copy(getattr(obj, "__dict__", {}))

    def _make_inspector(self):
        from sch.tools.text import TextInspector
        from sch.tools.part import PartInspector
        from sch.tools.proptext import PropTextInspector
        types = {type(obj) for obj in self._objects}
        if len(types) != 1:
            return
        typ = type(self._objects[0])
        if typ is TextObj:
            self._inspector = TextInspector(self._proxy)
        elif typ is PartObj:
            self._inspector = PartInspector(self._ctrl, self._proxy)
            self._inspector.masterChanged.connect(self._master_changed)
        elif typ is PropTextObj:
            self._inspector = PropTextInspector(self._proxy)
        if self._inspector is not None and hasattr(self._inspector, "edited"):
            self._inspector.edited.connect(self._commit)

    @property
    def inspector(self):
        return self._inspector

    def hiddenObjects(self):
        if self._net_preview is not None:
            non_nets = (tuple(self._drag_controller.selected)
                        if self._drag_controller is not None else ())
            return tuple(self._net_source or ()) + non_nets
        if self._drag_controller is not None:
            return tuple(self._drag_controller.selected)
        return ()

    def previewObjects(self):
        return list(self._net_preview) if self._net_preview is not None else None

    def previewDrawables(self):
        return ()

    def draw(self, painter: QPainter):
        pen = QPen(Layer.color(LayerType.selection))
        pen.setWidth(0)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        if self._net_preview is not None:
            # Net normalization may split/merge segments, so the preview is
            # the only reliable geometry from which to draw the selected
            # envelope during the drag.  The preview itself contains the
            # complete graph, including nets that were not selected.
            objects = self._selected_net_preview_objects()
            if self._drag_controller is not None:
                objects.extend(self._drag_controller.preview)
        elif self._drag_controller is not None:
            objects = self._drag_controller.preview
        else:
            objects = self._objects
        for obj in objects:
            painter.drawRect(obj.bbox().marginsAdded(QMargins(500, 500, 500, 500)))
        preview = list(self._net_preview or ())
        if self._drag_controller is not None:
            preview.extend(self._drag_controller.preview)
        if preview:
            for obj in preview:
                obj.draw(painter)

    def _selected_net_preview_objects(self):
        """Return normalized preview segments that belong to the selection."""
        return self._segments_for_selected_geometry(
            self._net_preview or (), self._selected_preview_segments())

    def _begin(self):
        if self._before is None:
            self._before = [self._state(obj) for obj in self._objects]

    def _commit(self):
        if self._net_preview is not None:
            selected_preview = self._selected_preview_segments()
            non_net_preview = (self._drag_controller.preview
                               if self._drag_controller is not None else [])
            non_net_source = (self._drag_controller.selected
                              if self._drag_controller is not None else [])
            if non_net_source:
                before = [NetObj(net.pt1, net.pt2) for net in self._net_source]
                after = [NetObj(net.pt1, net.pt2) for net in self._net_preview]
                self._ctrl.doc.doCommand(CompositeGroupDragCmd(
                    self._ctrl.doc, non_net_source, non_net_preview,
                    before, after))
                self._objects = (self._segments_for_selected_geometry(
                    after, selected_preview) + list(non_net_preview))
                self._proxy.setObjects(self._objects)
                self._net_source = None
                self._net_preview = None
                self._net_selected_preview = None
                self._drag_controller = None
                self._before = None
                self.sigUpdate.emit()
                return
            from sch.tools.net import NetGraphCmd
            before = [NetObj(net.pt1, net.pt2) for net in self._net_source]
            after = [NetObj(net.pt1, net.pt2) for net in self._net_preview]
            self._ctrl.doc.doCommand(NetGraphCmd(
                self._ctrl.doc, self._net_source, before, after))
            self._objects = self._segments_for_selected_geometry(
                after, selected_preview)
            self._proxy.setObjects(self._objects)
            self._net_source = None
            self._net_preview = None
            self._net_selected_preview = None
            self._before = None
            self.sigUpdate.emit()
            return
        if self._before is None:
            return
        after = [self._state(obj) for obj in self._objects]
        cmd = GroupChangeCmd(self._ctrl.doc, self._objects, self._before, after)
        self._ctrl.doc.doCommand(cmd)
        self._objects = cmd.current
        self._before = None
        self.sigUpdate.emit()

    def _selected_preview_segments(self):
        """Return the pre-normalization geometry for selected nets only."""
        return list(self._net_selected_preview or ())

    @staticmethod
    def _point_on_segment(point, start, end):
        cross = ((point.x() - start.x()) * (end.y() - start.y()) -
                 (point.y() - start.y()) * (end.x() - start.x()))
        if cross != 0:
            return False
        return (min(start.x(), end.x()) <= point.x() <= max(start.x(), end.x()) and
                min(start.y(), end.y()) <= point.y() <= max(start.y(), end.y()))

    @classmethod
    def _segments_for_selected_geometry(cls, segments, selected_geometry):
        """Keep normalized pieces belonging to the selected net geometry."""
        if not selected_geometry:
            return []
        return [segment for segment in segments
                if any(cls._point_on_segment(segment.pt1, selected.pt1, selected.pt2)
                       and cls._point_on_segment(segment.pt2, selected.pt1, selected.pt2)
                       for selected in selected_geometry)]

    @staticmethod
    def _map_point(transform, point):
        return transform.map(point)

    def _transform(self, transform, angle=0, flip=None):
        self._begin()
        if any(isinstance(obj, NetObj) for obj in self._objects):
            self._net_source = list(self._ctrl.doc.objects(objType=NetObj))
            self._net_selected_ids = {id(obj) for obj in self._objects
                                      if isinstance(obj, NetObj)}
            self._transform_preview(transform)
            self._commit()
            return
        for obj in self._objects:
            if isinstance(obj, NetObj):
                replacement = NetObj(self._map_point(transform, obj.pt1),
                                     self._map_point(transform, obj.pt2))
                self._ctrl.doc.removeObj(obj)
                self._ctrl.doc.addObj(replacement)
                self._objects[self._objects.index(obj)] = replacement
                continue
            if isinstance(obj, LineObj):
                obj.pt1 = self._map_point(transform, obj.pt1)
                obj.pt2 = self._map_point(transform, obj.pt2)
            elif isinstance(obj, (TextObj, PartObj, SheetRefObj)):
                obj.pos = self._map_point(transform, obj.pos)
                if hasattr(obj, "rot"):
                    obj.rot = (obj.rot + angle) % 360
                if flip is not None and hasattr(obj, "mirror"):
                    obj.mirror = not obj.mirror
            elif isinstance(obj, PropTextObj):
                obj.setPosGlobal(self._map_point(transform, obj.posGlobal()))
                obj.rot = (obj.rot + angle) % 360
        self._commit()

    def _center(self):
        return self.bbox().center()

    def bbox(self):
        """Return the exact union of the selected objects' bounding boxes."""
        box = QRect()
        for obj in self._objects:
            box = obj.bbox() if box.isNull() else box.united(obj.bbox())
        return box

    def _hit(self, point):
        # Use the same forgiving envelope as the selection artwork.  A raw
        # bbox test is too strict for thin lines and text glyphs, causing the
        # event to fall through to SelectTool, which collapses the group to a
        # single object.
        try:
            margin = max(500, int(self._ctrl.view.hitRadius()))
        except (AttributeError, TypeError):
            margin = 500
        return self.bbox().marginsAdded(QMargins(margin, margin, margin, margin)).contains(point)

    def testHit(self, point):
        return self._hit(point)

    def startDrag(self, point):
        self._drag_origin_inside = self.bbox().contains(point)
        nets = [obj for obj in self._objects if isinstance(obj, NetObj)]
        others = [obj for obj in self._objects if not isinstance(obj, NetObj)]
        if nets:
            self._begin()
            self._net_source = list(self._ctrl.doc.objects(objType=NetObj))
            self._net_selected_ids = {id(obj) for obj in nets}
        if others:
            self._drag_start = point
            self._drag_controller = DragController(
                others, others, self._build_group_preview)
        self._dragging = True
        self._drag_moved = False
        self._drag_start = point

    def _build_group_preview(self, baseline, cursor):
        delta = (self._ctrl.snapPt(cursor) - self._ctrl.snapPt(self._drag_start))
        transform = QTransform()
        transform.translate(delta.x(), delta.y())
        result = []
        for original in baseline:
            obj = copy.copy(original)
            if isinstance(obj, LineObj):
                obj.pt1 = transform.map(original.pt1)
                obj.pt2 = transform.map(original.pt2)
            elif isinstance(obj, (TextObj, PartObj, SheetRefObj)):
                obj.pos = transform.map(original.pos)
            elif isinstance(obj, PropTextObj):
                obj.setPosGlobal(transform.map(original.posGlobal()))
            result.append(obj)
        return result

    def handleEvent(self, event):
        if event.evType == Event.Type.MousePressed:
            self.startDrag(event.pos)
            event.handled = True
        elif event.evType == Event.Type.MouseMoved and self._dragging:
            if not self._drag_origin_inside:
                event.handled = True
                return
            if self._drag_controller is not None:
                self._drag_controller.update(event.pos)
                delta = (self._ctrl.snapPt(event.pos) -
                         self._ctrl.snapPt(self._drag_start))
                self._drag_moved = delta != QPoint(0, 0)
                if self._net_source is not None:
                    delta = (self._ctrl.snapPt(event.pos) -
                             self._ctrl.snapPt(self._drag_start))
                    tr = QTransform()
                    tr.translate(delta.x(), delta.y())
                    self._transform_preview(tr)
                self.sigUpdate.emit()
                event.handled = True
                return
            # Snap the displacement, rather than each object's absolute
            # position, so the selection keeps its relative geometry.
            delta = (self._ctrl.snapPt(event.pos) -
                     self._ctrl.snapPt(self._drag_start))
            self._drag_moved = delta != QPoint(0, 0)
            tr = QTransform()
            tr.translate(delta.x(), delta.y())
            # Restore the live preview to the original state before applying
            # the current delta, so dragging does not accumulate rounding.
            for obj, state in zip(self._objects, self._before):
                if isinstance(obj, NetObj):
                    # Net previews are rendered separately; never mutate the
                    # document while the pointer is still moving.
                    continue
                else:
                    obj.__dict__.clear(); obj.__dict__.update(copy.copy(state))
            self._transform_preview(tr)
            self.sigUpdate.emit()
            event.handled = True
        elif event.evType == Event.Type.MouseReleased and self._dragging:
            self._dragging = False
            if (not self._drag_origin_inside or
                    (not self._drag_moved and not self.bbox().contains(event.pos))):
                self.sigDone.emit()
                event.handled = True
                return
            if self._net_preview is not None:
                self._commit()
                event.handled = True
                return
            if self._drag_controller is not None:
                preview = self._drag_controller.preview
                self._ctrl.doc.doCommand(DragCommand(
                    self._ctrl.doc, self._objects, preview))
                self._objects = list(preview)
                self._proxy.setObjects(self._objects)
                if self._inspector is not None:
                    self._inspector.obj = self._proxy
                self._drag_controller = None
                self.sigUpdate.emit()
                event.handled = True
                return
            self._commit()
            event.handled = True
        elif event.evType == Event.Type.KeyPressed:
            if event.key == Qt.Key_Delete:
                for obj in self._objects:
                    self._ctrl.doc.removeObj(obj)
                self.sigDone.emit(); event.handled = True
            elif event.key in (Qt.Key_R, Qt.Key_H, Qt.Key_V):
                center = self._center()
                tr = QTransform()
                tr.translate(center.x(), center.y())
                if event.key == Qt.Key_R:
                    tr.rotate(90); angle = 90; flip = None
                else:
                    tr.scale(-1 if event.key == Qt.Key_H else 1,
                             -1 if event.key == Qt.Key_V else 1)
                    angle = 0; flip = True
                tr.translate(-center.x(), -center.y())
                self._transform(tr, angle, flip)
                event.handled = True

    def _transform_preview(self, transform):
        if self._net_source is not None:
            preview = []
            selected_preview = []
            for net in self._net_source:
                if id(net) in self._net_selected_ids:
                    moved = NetObj(transform.map(net.pt1),
                                   transform.map(net.pt2))
                    preview.append(moved)
                    selected_preview.append(moved)
                else:
                    preview.append(NetObj(net.pt1, net.pt2))
            self._net_selected_preview = selected_preview
            self._net_preview = NetObj._normalizeGeometry(preview)
            return
        for obj in self._objects:
            if isinstance(obj, NetObj):
                replacement = NetObj(transform.map(obj.pt1), transform.map(obj.pt2))
                self._ctrl.doc.removeObj(obj)
                self._ctrl.doc.addObj(replacement)
                self._objects[self._objects.index(obj)] = replacement
            elif isinstance(obj, LineObj):
                obj.pt1 = transform.map(obj.pt1); obj.pt2 = transform.map(obj.pt2)
            elif isinstance(obj, (TextObj, PartObj, SheetRefObj)):
                obj.pos = transform.map(obj.pos)
            elif isinstance(obj, PropTextObj):
                obj.setPosGlobal(transform.map(obj.posGlobal()))

    def _master_changed(self, path, name):
        self._begin()
        for obj in self._objects:
            obj.path = path; obj.name = name
        self._commit()

    def dispose(self):
        self._objects = []
        self._inspector = None
