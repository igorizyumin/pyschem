from PySide6.QtCore import QObject, Signal, Slot, QPoint, Qt
from PySide6.QtGui import QPainter, QPen
import sch.document
import sch.controller
from sch.utils import LayerType, Layer
from sch.obj.net import NetObj
from sch.tools.base import EditHandle, BaseEditor
from sch.tools.drag import DragController
from sch.view import Event

import os
import sys


_NET_TRACE_ENABLED = os.environ.get("PYSCHEM_NET_TRACE", "0") not in ("", "0", "false", "False")


def _trace(message):
    if _NET_TRACE_ENABLED:
        print("[NETTRACE] {}".format(message), file=sys.stderr, flush=True)


def _fmt_net(net):
    return "{}@{:x}({},{})-({},{})".format(
        type(net).__name__, id(net), net.pt1.x(), net.pt1.y(),
        net.pt2.x(), net.pt2.y())


def _fmt_graph(doc):
    nets = list(doc.objects(objType=NetObj))
    nets.sort(key=lambda net: (net.pt1.x(), net.pt1.y(), net.pt2.x(), net.pt2.y(), id(net)))
    return "[{}]".format(", ".join(_fmt_net(net) for net in nets))


class NetTool(QObject):
    sigUpdate = Signal()

    def __init__(self, ctrl):
        QObject.__init__(self)
        self._ctrl = ctrl
        self._firstPt = None
        self._pos = QPoint()
        self._modifiers = Qt.NoModifier
        self._ignore_next_release = False
        self._vertical_first = False

    @property
    def inspector(self):
        return None

    @staticmethod
    def name():
        return "Draw Net"

    def finish(self):
        self._firstPt = None
        self._ignore_next_release = False
        self.sigUpdate.emit()

    def _snap(self, pos):
        return self._ctrl.snapPt(pos)

    def _preview_points(self, pos=None, modifiers=None):
        """Return the live one- or two-segment route from the chain start."""
        if pos is None:
            pos = self._pos
        if modifiers is None:
            modifiers = self._modifiers
        pos = self._snap(pos)
        if self._firstPt is None or pos == self._firstPt:
            return []
        if modifiers & Qt.ShiftModifier:
            return [(QPoint(self._firstPt), pos)]
        if pos.x() == self._firstPt.x() or pos.y() == self._firstPt.y():
            return [(QPoint(self._firstPt), pos)]
        if self._vertical_first:
            bend = QPoint(self._firstPt.x(), pos.y())
        else:
            bend = QPoint(pos.x(), self._firstPt.y())
        return [(QPoint(self._firstPt), bend), (bend, pos)]

    def _toggle_polarity(self):
        self._vertical_first = not self._vertical_first

    def _endpoint(self, pos=None, modifiers=None):
        """Return the final point of the current live route."""
        points = self._preview_points(pos, modifiers)
        fallback = pos if pos is not None else self._pos
        return points[-1][1] if points else self._snap(fallback)

    def draw(self, painter):
        # The live segment is a preview, so distinguish it from committed
        # wires using the selection/yellow color.
        pen = QPen(Layer.color(LayerType.selection))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setWidth(0)
        painter.setPen(pen)
        if self._firstPt is not None:
            for start, end in self._preview_points():
                painter.drawLine(start, end)

    def handleEvent(self, e):
        if e.evType == sch.controller.Event.Type.MouseMoved:
            self._modifiers = e.modifiers
            self._pos = self._snap(e.pos)
            if self._firstPt is not None:
                self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.MouseReleased:
            if self._ignore_next_release:
                self._ignore_next_release = False
                e.handled = True
                return
            self._modifiers = e.modifiers
            self._pos = self._snap(e.pos)
            if self._firstPt is None:
                self._firstPt = self._pos
            else:
                points = self._preview_points()
                if not points:
                    self._firstPt = None
                else:
                    start, endpoint = points[0]
                    existing_nets = list(self._ctrl.doc.objects(objType=NetObj))
                    connection_points = (self._ctrl.doc.connection_points()
                                         if hasattr(self._ctrl.doc,
                                                    "connection_points")
                                         else ())
                    final_endpoint = points[-1][1]
                    reaches_first_leg_target = (
                        any(net.touchesPt(endpoint) for net in existing_nets)
                        or any(point == endpoint
                               for point in connection_points))
                    reaches_final_target = (
                        any(net.touchesPt(final_endpoint)
                            for net in existing_nets)
                        or any(point == final_endpoint
                               for point in connection_points))
                    if reaches_final_target:
                        # A click on a wire or pin completes the whole live
                        # route, including its pending corner segment.
                        self.addNets(NetObj(route_start, route_end)
                                     for route_start, route_end in points)
                        self._firstPt = None
                    elif reaches_first_leg_target:
                        self.addNet(NetObj(start, endpoint))
                        self._firstPt = None
                    else:
                        self.addNet(NetObj(start, endpoint))
                        # Commit only the first leg.  The remaining leg stays
                        # live, and the next click starts with the opposite
                        # polarity.
                        self._firstPt = endpoint
                    self._toggle_polarity()
                self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.MouseDblClicked:
            self._modifiers = e.modifiers
            self._pos = self._snap(e.pos)
            # A double-click finishes the complete live route, unlike a
            # normal click which commits only its first L leg.
            for start, end in self._preview_points():
                if start != end:
                    self.addNet(NetObj(start, end))
            self._firstPt = None
            # Qt normally sends a release after the double-click event.  Do
            # not let that release start a fresh chain.
            self._ignore_next_release = True
            self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.KeyPressed and e.key == Qt.Key_Space:
            self._toggle_polarity()
            self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.Done:
            # Finish the current chain but remain in the NetTool so another
            # chain can be started with the next click.
            self._firstPt = None
            self._ignore_next_release = False
            self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.Cancel:
            self._firstPt = None
            self._ignore_next_release = False
            self.sigUpdate.emit()
            e.handled = True



    def addNet(self, newNet):
        """Add a wire by normalizing the complete integer-coordinate graph."""
        assert type(newNet.pt1) is QPoint and type(newNet.pt2) is QPoint
        self.addNets([newNet])

    def addNets(self, newNets):
        """Add multiple wires in one normalized graph/undo operation."""
        newNets = list(newNets)
        for new_net in newNets:
            assert type(new_net.pt1) is QPoint and type(new_net.pt2) is QPoint
        current = list(self._ctrl.doc.objects(objType=NetObj))
        before = [NetObj(net.pt1, net.pt2) for net in current]
        connection_points = (self._ctrl.doc.connection_points()
                             if hasattr(self._ctrl.doc, "connection_points")
                             else None)
        normalized = NetObj._normalizeGeometry(
            current + newNets, connection_points)
        _trace("add nets current={} added={} normalized={}".format(
            len(current), len(newNets), len(normalized)))
        cmd = NetGraphCmd(self._ctrl.doc, current, before, normalized)
        self._ctrl.doc.doCommand(cmd)


class NetGraphCmd(sch.document.BaseUndoCmd):
    """Undo command for replacing the complete net topology of a page."""

    def __init__(self, doc, initial, before, after):
        super().__init__("normalize net graph", doc=doc)
        self._initial = list(initial)
        self._before = list(before)
        self._after = list(after)
        self._first_redo = True
        _trace("cmd create id={:x} initial={} before={} after={}".format(
            id(self), len(self._initial), len(self._before), len(self._after)))

    def _replace(self, remove, add):
        _trace("cmd replace id={:x} remove={} add={} graph_before={}".format(
            id(self), len(remove), len(add), _fmt_graph(self.doc)))
        # Snapshot objects are intentionally new instances. Replace the
        # complete net graph instead of relying on object identity.
        self.doc.replaceObjects(remove, add, objType=NetObj)
        _trace("cmd replace id={:x} graph_after={}".format(id(self), _fmt_graph(self.doc)))

    def redo(self):
        remove = self._initial if self._first_redo else self._before
        _trace("cmd redo id={:x} first={} stack_index={} remove={} add={}".format(
            id(self), self._first_redo, self.doc.undoStack.index(), len(remove), len(self._after)))
        self._replace(remove, self._after)
        self._first_redo = False

    def undo(self):
        _trace("cmd undo id={:x} stack_index={} remove={} add={}".format(
            id(self), self.doc.undoStack.index(), len(self._after), len(self._before)))
        self._replace(self._after, self._before)


class NetDragSession(DragController):
    """Immutable preview transaction for moving a net.

    In the default orthogonal mode, horizontal and vertical segments move
    along their own axes.  Dragging an endpoint perpendicular to its segment
    switches to the same translation used by a body drag, keeping parallel
    attached wires parallel instead of adding a connector.  Free mode (used
    by Shift) moves every attached endpoint by the complete cursor delta.  Alt
    disables attached-endpoint movement entirely.  Interior crossings are
    deliberately not treated as connections.
    """

    def __init__(self, nets, selected, handle_index=None, grab_point=None,
                 orthogonal=True, maintain_connectivity=True):
        source = list(nets)
        self._selected_index = next(
            index for index, net in enumerate(source) if net is selected)
        selected_net = source[self._selected_index]
        self._orthogonal = bool(orthogonal)
        self._maintain_connectivity = bool(maintain_connectivity)
        if handle_index is None:
            if grab_point is None:
                raise ValueError("segment drags require a grab point")
            self._mode = "segment"
            self._anchor = QPoint(grab_point)
            self._moved_points = self._unique_points(
                (selected_net.pt1, selected_net.pt2))
        else:
            if handle_index not in (0, 1):
                raise ValueError("handle_index must be 0 or 1")
            self._mode = "endpoint"
            self._anchor = selected_net.pt1 if handle_index == 0 else selected_net.pt2
            self._moved_points = (QPoint(self._anchor),)
        if self._maintain_connectivity:
            self._affected = tuple(
                index for index, net in enumerate(source)
                if any(net.pt1 == point or net.pt2 == point
                       for point in self._moved_points))
        else:
            self._affected = (self._selected_index,)
        self._cursor = QPoint(self._anchor)
        self._effective_cursor = QPoint(self._anchor)
        self._preview_additions = ()
        self._active_affected = self._affected
        super().__init__(source, source, self._build_preview)

    @staticmethod
    def _unique_points(points):
        result = []
        for point in points:
            if not any(point == existing for existing in result):
                result.append(QPoint(point))
        return tuple(result)

    @classmethod
    def for_segment(cls, nets, selected, grab_point, orthogonal=True,
                    maintain_connectivity=True):
        """Create a session for grabbing the body of ``selected``."""
        return cls(nets, selected, grab_point=grab_point,
                   orthogonal=orthogonal,
                   maintain_connectivity=maintain_connectivity)

    @property
    def mode(self):
        return self._mode

    @property
    def orthogonal(self):
        return self._orthogonal

    @property
    def maintain_connectivity(self):
        return self._maintain_connectivity

    def set_orthogonal(self, orthogonal):
        """Change drag constraint mode without changing the baseline graph."""
        self._orthogonal = bool(orthogonal)

    def set_maintain_connectivity(self, maintain_connectivity):
        """Change whether attached graph vertices follow the drag."""
        self._maintain_connectivity = bool(maintain_connectivity)
        if self._maintain_connectivity:
            self._affected = tuple(
                index for index, net in enumerate(self._source)
                if any(net.pt1 == point or net.pt2 == point
                       for point in self._moved_points))
        else:
            self._affected = (self._selected_index,)

    @property
    def moved_points(self):
        return tuple(QPoint(point) for point in self._moved_points)

    @property
    def moved(self):
        return self._effective_cursor != self._anchor

    @staticmethod
    def _axis(net):
        if net.pt1.y() == net.pt2.y():
            return "horizontal"
        if net.pt1.x() == net.pt2.x():
            return "vertical"
        return None

    def _effective_cursor_for(self, baseline, cursor):
        # The cursor remains the requested vertex position.
        return QPoint(cursor)

    def _perpendicular_endpoint_drag(self, cursor):
        if (self._mode != "endpoint" or not self._orthogonal
                or not self._maintain_connectivity):
            return False
        selected = self._source[self._selected_index]
        axis = self._axis(selected)
        delta = cursor - self._anchor
        if axis == "horizontal":
            return delta.y() != 0 and delta.x() == 0
        if axis == "vertical":
            return delta.x() != 0 and delta.y() == 0
        return False

    def _diagonal_endpoint_drag(self, cursor):
        if (self._mode != "endpoint" or not self._orthogonal
                or not self._maintain_connectivity):
            return False
        selected = self._source[self._selected_index]
        axis = self._axis(selected)
        delta = cursor - self._anchor
        if axis in ("horizontal", "vertical"):
            return delta.x() != 0 and delta.y() != 0
        return False

    def _affected_for(self, moved_points):
        if not self._maintain_connectivity:
            return (self._selected_index,)
        return tuple(
            index for index, net in enumerate(self._source)
            if any(net.pt1 == point or net.pt2 == point
                   for point in moved_points)
        )

    def _preserved_endpoint(self, net, old_point, new_point):
        if not self._orthogonal:
            return QPoint(new_point)
        axis = self._axis(net)
        if axis == "horizontal":
            return QPoint(new_point.x(), old_point.y())
        if axis == "vertical":
            return QPoint(old_point.x(), new_point.y())
        return QPoint(new_point)

    @staticmethod
    def _segment_key(net):
        first = (net.pt1.x(), net.pt1.y())
        second = (net.pt2.x(), net.pt2.y())
        return (first, second) if first <= second else (second, first)

    @staticmethod
    def _add_connector_segments(additions, addition_keys, start, end,
                                 preferred_axis=None):
        """Add an orthogonal connector without introducing a diagonal edge."""
        if start == end:
            return
        if preferred_axis == "horizontal":
            bend = QPoint(start.x(), end.y())
        else:
            bend = QPoint(end.x(), start.y())
        for first, second in ((start, bend), (bend, end)):
            connector = NetObj(first, second)
            if connector.pt1 == connector.pt2:
                continue
            key = NetDragSession._segment_key(connector)
            if key not in addition_keys:
                addition_keys.add(key)
                additions.append(connector)

    @staticmethod
    def _segment_covers(outer, inner):
        """Return whether a preview segment already covers ``inner``."""
        if NetDragSession._axis(outer) != NetDragSession._axis(inner):
            return False
        axis = NetDragSession._axis(outer)
        if axis == "horizontal":
            return (outer.pt1.y() == inner.pt1.y()
                    and min(outer.pt1.x(), outer.pt2.x())
                    <= min(inner.pt1.x(), inner.pt2.x())
                    and max(outer.pt1.x(), outer.pt2.x())
                    >= max(inner.pt1.x(), inner.pt2.x()))
        if axis == "vertical":
            return (outer.pt1.x() == inner.pt1.x()
                    and min(outer.pt1.y(), outer.pt2.y())
                    <= min(inner.pt1.y(), inner.pt2.y())
                    and max(outer.pt1.y(), outer.pt2.y())
                    >= max(inner.pt1.y(), inner.pt2.y()))
        return False

    def _build_preview(self, baseline, cursor):
        self._effective_cursor = self._effective_cursor_for(baseline, cursor)
        offset = self._effective_cursor - self._anchor
        body_drag = (self._mode == "segment" or
                     self._perpendicular_endpoint_drag(cursor))
        diagonal_endpoint_drag = self._diagonal_endpoint_drag(cursor)
        if body_drag:
            moved_points_source = (self._source[self._selected_index].pt1,
                                    self._source[self._selected_index].pt2)
        elif diagonal_endpoint_drag:
            moved_points_source = (self._source[self._selected_index].pt1,
                                    self._source[self._selected_index].pt2)
        else:
            moved_points_source = self._moved_points
        moved_points = {
            (point.x(), point.y()): point + offset
            for point in moved_points_source
        }
        if diagonal_endpoint_drag:
            selected = self._source[self._selected_index]
            anchor = self._moved_points[0]
            other = (selected.pt2 if selected.pt1 == anchor
                     else selected.pt1)
            axis = self._axis(selected)
            if axis == "horizontal":
                perpendicular = QPoint(0, offset.y())
            else:
                perpendicular = QPoint(offset.x(), 0)
            moved_points[(other.x(), other.y())] = other + perpendicular
        preview = []
        additions = []
        addition_keys = set()
        affected = set(self._affected_for(moved_points_source))
        self._active_affected = tuple(sorted(affected))
        for index, net in enumerate(baseline):
            if diagonal_endpoint_drag and index == self._selected_index:
                selected = self._source[self._selected_index]
                anchor = self._moved_points[0]
                other = (selected.pt2 if selected.pt1 == anchor
                         else selected.pt1)
                moved_anchor = moved_points[(anchor.x(), anchor.y())]
                moved_other = moved_points[(other.x(), other.y())]
                if selected.pt1 == anchor:
                    preview.append(NetObj(moved_anchor, moved_other))
                else:
                    preview.append(NetObj(moved_other, moved_anchor))
                continue
            if (diagonal_endpoint_drag and index in affected
                    and index != self._selected_index):
                selected_axis = self._axis(
                    self._source[self._selected_index])
                net_axis = self._axis(net)
                if selected_axis and net_axis and selected_axis != net_axis:
                    moved_endpoint = next(
                        (endpoint for endpoint in (net.pt1, net.pt2)
                         if (endpoint.x(), endpoint.y()) in moved_points),
                        None)
                    if moved_endpoint is None:
                        preview.append(net)
                        continue
                    moved = moved_points[(moved_endpoint.x(),
                                          moved_endpoint.y())]
                    if selected_axis == "horizontal":
                        parallel = QPoint(moved.x() - moved_endpoint.x(), 0)
                        perpendicular = QPoint(
                            0, moved.y() - moved_endpoint.y())
                    else:
                        parallel = QPoint(0, moved.y() - moved_endpoint.y())
                        perpendicular = QPoint(
                            moved.x() - moved_endpoint.x(), 0)
                    endpoints = [net.pt1 + parallel, net.pt2 + parallel]
                    for endpoint_index, endpoint in enumerate((net.pt1,
                                                                net.pt2)):
                        if endpoint == moved_endpoint:
                            endpoints[endpoint_index] += perpendicular
                    preview.append(NetObj(*endpoints))
                    continue
            if body_drag and index == self._selected_index:
                preview.append(net.translated(offset))
                continue
            if index not in affected:
                preview.append(net)
                continue
            pt1 = net.pt1
            pt2 = net.pt2
            for endpoint_name in ("pt1", "pt2"):
                endpoint = getattr(net, endpoint_name)
                moved = moved_points.get((endpoint.x(), endpoint.y()))
                if moved is None:
                    continue
                if index == self._selected_index and (
                        body_drag or diagonal_endpoint_drag
                        or not self._maintain_connectivity):
                    replacement = moved
                else:
                    replacement = self._preserved_endpoint(net, endpoint, moved)
                    if (body_drag and self._orthogonal
                            and index != self._selected_index
                            and self._axis(net) == self._axis(
                                self._source[self._selected_index])):
                        # A continuation parallel to the dragged body should
                        # retain its original junction coordinate along the
                        # body.  Route the displaced junction around it rather
                        # than moving that endpoint and creating a loop.
                        replacement = QPoint(endpoint)
                    if replacement != moved:
                        self._add_connector_segments(
                            additions, addition_keys, replacement, moved,
                            preferred_axis=(self._axis(
                                self._source[self._selected_index])
                                if self._orthogonal else None))
                if endpoint_name == "pt1":
                    pt1 = replacement
                else:
                    pt2 = replacement
            if (body_drag and pt1 == pt2
                    and net.pt1 != net.pt2):
                # The moved junction has reached the branch's far endpoint.
                # Keep the original branch only when another wire still
                # anchors the old junction (the T case).  Otherwise the
                # branch has collapsed as part of a jog and must disappear;
                # retaining it would leave a dangling perpendicular stub.
                moved_endpoint = next(
                    (endpoint for endpoint in (net.pt1, net.pt2)
                     if (endpoint.x(), endpoint.y()) in moved_points), None)
                anchored = any(
                    other_index not in (index, self._selected_index)
                    and (other.pt1 == moved_endpoint
                         or other.pt2 == moved_endpoint)
                    for other_index, other in enumerate(self._source))
                if anchored:
                    preview.append(net)
                else:
                    # Preserve the source-index slot for selected_preview
                    # and affected preview drawing.  Zero-length segments are
                    # ignored by rendering and geometry normalization.
                    preview.append(NetObj(pt1, pt2))
                continue
            preview.append(net.with_endpoints(pt1, pt2))
        additions = [addition for addition in additions
                     if not any(self._segment_covers(net, addition)
                                for net in preview)]
        self._preview_additions = tuple(additions)
        return preview + additions

    @property
    def source(self):
        return list(self._source)

    @property
    def affected_source(self):
        return [self._source[index] for index in self._active_affected]

    @property
    def anchor(self):
        return QPoint(self._anchor)

    @property
    def cursor(self):
        return QPoint(self._cursor)

    @property
    def preview(self):
        return super().preview

    @property
    def preview_additions(self):
        return list(self._preview_additions)

    @property
    def selected_preview(self):
        return self.preview[self._selected_index]

    def update(self, cursor):
        self._cursor = QPoint(cursor)
        return super().update(self._cursor)


class NetEditor(BaseEditor):

    def __init__(self, ctrl, obj):
        super().__init__(ctrl, obj)
        self._drag = None
        # Normalization replaces nets with new segment objects.  Track undo
        # stack transitions so this editor follows those replacements.
        self._ctrl.doc.undoStack.indexChanged.connect(self._onUndoIndexChanged)
        _trace("editor create id={:x} obj={} graph={}".format(
            id(self), _fmt_net(obj), _fmt_graph(self._ctrl.doc)))

    def _create_change_command(self):
        """Net edits use NetGraphCmd, not mutable-object mementos."""
        return None

    def create_handles(self):
        """Create edit handles for net endpoints."""
        self._handles = [EditHandle(self._ctrl, self._obj.pt1), EditHandle(self._ctrl, self._obj.pt2)]

    def _hit_radius(self):
        view = getattr(self._ctrl, "view", None)
        if view is not None and hasattr(view, "hitRadius"):
            return NetObj.hitRadius(view.hitRadius())
        return 1

    def _snap(self, pos):
        snap = getattr(self._ctrl, "snapPt", None)
        return QPoint(snap(pos) if snap is not None else pos)

    def testHit(self, pt):
        """Hit either an endpoint handle or the body of the selected net."""
        return (super().testHit(pt)
                or self._obj.testHit(pt, self._hit_radius()))

    def _setup_handle_connections(self):
        """Set up specific connections for net handles."""
        self._handles[0].sigDragged.connect(self._dragPt1)
        self._handles[1].sigDragged.connect(self._dragPt2)
        for h in self._handles:
            h.sigMoved.connect(self._commit)

    def update_handles(self):
        """Update handle positions to match net endpoints."""
        net = self._drag.selected_preview if self._drag else self._obj
        self._handles[0].pos = net.pt1
        self._handles[1].pos = net.pt2

    def hiddenObjects(self):
        """Return document nets replaced by the active preview."""
        if self._drag is None:
            return ()
        return self._drag.affected_source

    def previewObjects(self):
        """Return the complete temporary graph for preview rendering."""
        return self._drag.preview if self._drag is not None else None

    def _replacementFor(self, endpoints, allow_partial=False):
        """Find a replacement for the edited segment.

        Commits require an exact match so a removed segment cannot select a
        neighboring net. Undo/redo may split a segment, so it can use a
        unique one-endpoint match as a fallback.
        """
        nets = list(self._ctrl.doc.objects(objType=NetObj))
        for net in nets:
            if net is self._obj:
                return net

        first, second = endpoints
        for net in nets:
            if ((net.pt1 == first and net.pt2 == second)
                    or (net.pt1 == second and net.pt2 == first)):
                return net
        if allow_partial:
            candidates = [net for net in nets
                          if net.pt1 == first or net.pt2 == first
                          or net.pt1 == second or net.pt2 == second]
            if len(candidates) == 1:
                return candidates[0]
        return None

    def _rebind(self, endpoints, allow_partial=False):
        replacement = self._replacementFor(endpoints, allow_partial=allow_partial)
        if replacement is None:
            return False
        self._obj = replacement
        self.update_handles()
        return True

    def _onUndoIndexChanged(self, _index):
        if self._disposed or self._drag is not None:
            return
        # QUndoStack emits this after the complete command has been applied,
        # unlike the intermediate sigChanged signals from child commands.
        _trace("editor indexChanged editor={:x} index={} obj={} graph={}".format(
            id(self), _index, _fmt_net(self._obj), _fmt_graph(self._ctrl.doc)))
        if not self._rebind((self._obj.pt1, self._obj.pt2), allow_partial=True):
            _trace("editor rebind FAILED editor={:x} obj={} graph={}".format(
                id(self), _fmt_net(self._obj), _fmt_graph(self._ctrl.doc)))
            self.sigDone.emit()
        else:
            _trace("editor rebind OK editor={:x} obj={}".format(id(self), _fmt_net(self._obj)))

    def _docChanged(self):
        if self._disposed:
            return
        # Child add/delete commands can emit sigChanged while a compound
        # command is only half-applied.  Do not destroy the editor there;
        # indexChanged performs the final rebind once the command completes.
        if self._ctrl.doc.hasObject(self._obj):
            self.update_handles()
        else:
            _trace("editor docChanged stale editor={:x} obj={} graph={}".format(
                id(self), _fmt_net(self._obj), _fmt_graph(self._ctrl.doc)))

    def dispose(self):
        if self._disposed:
            return
        try:
            self._ctrl.doc.undoStack.indexChanged.disconnect(self._onUndoIndexChanged)
        except (RuntimeError, TypeError):
            pass
        super().dispose()

    def draw_custom(self, painter):
        """Draw the net line."""
        if self._drag is None:
            painter.drawLine(self._obj.pt1, self._obj.pt2)
            return
        # The affected set can change when an endpoint drag enters or leaves
        # perpendicular body-drag mode.  Draw the set used to hide the
        # document's source segments so every preview branch remains visible.
        for index in self._drag._active_affected:
            net = self._drag.preview[index]
            if net.pt1 != net.pt2:
                painter.drawLine(net.pt1, net.pt2)
        for net in self._drag.preview_additions:
            if net.pt1 != net.pt2:
                painter.drawLine(net.pt1, net.pt2)

    def draw_handles(self, painter):
        """Hide endpoint handles while the net body is being dragged."""
        if self._drag is not None and self._drag.mode == "segment":
            return
        super().draw_handles(painter)

    def _begin_drag(self, handle_index, pos, orthogonal=True,
                    maintain_connectivity=True):
        if self._drag is None:
            self._drag = NetDragSession(
                self._ctrl.doc.objects(objType=NetObj), self._obj, handle_index,
                orthogonal=orthogonal,
                maintain_connectivity=maintain_connectivity)
        elif self._drag.mode == "endpoint":
            self._drag.set_orthogonal(orthogonal)
            self._drag.set_maintain_connectivity(maintain_connectivity)
        self._drag.update(pos)
        self.update_handles()

    def _begin_segment_drag(self, pos, orthogonal=True,
                            maintain_connectivity=True):
        """Start or update a drag that grabbed the body of the net."""
        snapped = self._snap(pos)
        if self._drag is None:
            self._drag = NetDragSession.for_segment(
                self._ctrl.doc.objects(objType=NetObj), self._obj, snapped,
                orthogonal=orthogonal,
                maintain_connectivity=maintain_connectivity)
        elif self._drag.mode == "segment":
            self._drag.set_orthogonal(orthogonal)
            self._drag.set_maintain_connectivity(maintain_connectivity)
        self._drag.update(snapped)
        self.update_handles()

    def _dragSegment(self, pos):
        self._begin_segment_drag(pos)
        self.sigUpdate.emit()

    @Slot('QPoint')
    def _dragPt1(self, pos):
        """Handle dragging of pt1 - move connected segments."""
        orthogonal = not bool(self._handles[0].modifiers & Qt.ShiftModifier)
        maintain_connectivity = not bool(self._handles[0].modifiers & Qt.AltModifier)
        self._begin_drag(0, pos, orthogonal=orthogonal,
                         maintain_connectivity=maintain_connectivity)
        self.sigUpdate.emit()

    @Slot('QPoint')
    def _dragPt2(self, pos):
        """Handle dragging of pt2 - move connected segments."""
        orthogonal = not bool(self._handles[1].modifiers & Qt.ShiftModifier)
        maintain_connectivity = not bool(self._handles[1].modifiers & Qt.AltModifier)
        self._begin_drag(1, pos, orthogonal=orthogonal,
                         maintain_connectivity=maintain_connectivity)
        self.sigUpdate.emit()

    def handle_custom_event(self, event):
        """Handle dragging from the body of a wire, away from its handles."""
        if event.evType == sch.controller.Event.Type.MousePressed:
            # Endpoint handles get first refusal in BaseEditor.handleEvent.
            # The explicit check also keeps this method safe when called
            # directly by a test or another editor.
            if (event.pos is not None
                    and not any(handle.testHit(event.pos)
                                for handle in self._handles)
                    and self._obj.testHit(event.pos, self._hit_radius())):
                orthogonal = not bool(event.modifiers & Qt.ShiftModifier)
                maintain_connectivity = not bool(event.modifiers & Qt.AltModifier)
                self._begin_segment_drag(
                    event.pos, orthogonal=orthogonal,
                    maintain_connectivity=maintain_connectivity)
                self.sigUpdate.emit()
                event.handled = True
                return
        elif event.evType == sch.controller.Event.Type.MouseMoved:
            if self._drag is not None and self._drag.mode == "segment":
                orthogonal = not bool(event.modifiers & Qt.ShiftModifier)
                maintain_connectivity = not bool(event.modifiers & Qt.AltModifier)
                self._begin_segment_drag(
                    event.pos, orthogonal=orthogonal,
                    maintain_connectivity=maintain_connectivity)
                self.sigUpdate.emit()
                event.handled = True
                return
        elif event.evType == sch.controller.Event.Type.MouseReleased:
            if self._drag is not None and self._drag.mode == "segment":
                orthogonal = not bool(event.modifiers & Qt.ShiftModifier)
                maintain_connectivity = not bool(event.modifiers & Qt.AltModifier)
                self._begin_segment_drag(
                    event.pos, orthogonal=orthogonal,
                    maintain_connectivity=maintain_connectivity)
                moved = self._drag.moved
                if moved:
                    self._commit()
                else:
                    self._drag = None
                    self.update_handles()
                    self.sigUpdate.emit()
                event.handled = True
                return
        if event.evType == sch.controller.Event.Type.Cancel and self._drag is not None:
            self._drag = None
            self.update_handles()
            self.sigUpdate.emit()
            event.handled = True
            return
        super().handle_custom_event(event)
        if event.handled:
            return

    def _commit(self):
        """Normalize the current graph and commit it as one topology change."""
        if self._drag is None:
            return
        current_nets = self._drag.source
        before = [NetObj(net.pt1, net.pt2) for net in current_nets]
        preview = self._drag.preview
        connection_points = (self._ctrl.doc.connection_points()
                             if hasattr(self._ctrl.doc, "connection_points")
                             else None)
        normalized = NetObj._normalizeGeometry(preview, connection_points)
        edited = self._drag.selected_preview
        edited_endpoints = (QPoint(edited.pt1), QPoint(edited.pt2))

        _trace("commit editor={:x} current={} normalized={} endpoints=({},{})->({},{})".format(
            id(self), len(current_nets), len(normalized),
            edited_endpoints[0].x(), edited_endpoints[0].y(),
            edited_endpoints[1].x(), edited_endpoints[1].y()))
        _trace("commit graph_current={} graph_normalized={}".format(
            _fmt_graph(self._ctrl.doc),
            "[{}]".format(", ".join(_fmt_net(net) for net in normalized))))

        cmd = NetGraphCmd(self._ctrl.doc, current_nets, before, normalized)

        self._ctrl.doc.doCommand(cmd)
        self._drag = None
        rebound = self._rebind(edited_endpoints)
        if not rebound:
            # Normalization may remove or merge the edited segment. There is
            # no unambiguous object to keep selected in that case.
            self.sigDone.emit()
        _trace("commit complete editor={:x} rebound={} graph={}".format(
            id(self), rebound, _fmt_graph(self._ctrl.doc)))
        self.sigUpdate.emit()
