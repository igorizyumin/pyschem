from PySide6.QtCore import QObject, Signal, Slot, QPoint, Qt
from PySide6.QtGui import QPainter, QPen
import sch.document
import sch.controller
from sch.utils import LayerType, Layer
from sch.obj.net import NetObj
from sch.tools.base import EditHandle, BaseEditor
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

    @property
    def inspector(self):
        return None

    @staticmethod
    def name():
        return "Draw Net"

    def finish(self):
        self._firstPt = None
        self.sigUpdate.emit()

    def draw(self, painter):
        pen = QPen(Layer.color(LayerType.wire))
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
                if self._pos != self._firstPt:
                    self.addNet(NetObj(self._firstPt, self._pos))
                    self._firstPt = None
                    self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.Cancel:
            self._firstPt = None
            self.sigUpdate.emit()
            e.handled = True



    def addNet(self, newNet):
        """Add a wire by normalizing the complete integer-coordinate graph."""
        assert type(newNet.pt1) is QPoint and type(newNet.pt2) is QPoint
        current = list(self._ctrl.doc.objects(objType=NetObj))
        before = [NetObj(net.pt1, net.pt2) for net in current]
        normalized = NetObj._normalizeGeometry(current + [newNet])
        _trace("add net current={} normalized={}".format(len(current), len(normalized)))
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


class NetDragSession:
    """Immutable preview transaction for moving a net endpoint/junction."""

    def __init__(self, nets, selected, handle_index):
        self._source = list(nets)
        self._baseline = [NetObj(net.pt1, net.pt2) for net in self._source]
        self._selected_index = next(
            index for index, net in enumerate(self._source) if net is selected)
        selected_net = self._baseline[self._selected_index]
        self._anchor = selected_net.pt1 if handle_index == 0 else selected_net.pt2
        self._affected = tuple(
            index for index, net in enumerate(self._baseline)
            if net.pt1 == self._anchor or net.pt2 == self._anchor)
        self._preview = list(self._baseline)
        self._cursor = QPoint(self._anchor)

    @property
    def source(self):
        return list(self._source)

    @property
    def affected_source(self):
        return [self._source[index] for index in self._affected]

    @property
    def anchor(self):
        return QPoint(self._anchor)

    @property
    def cursor(self):
        return QPoint(self._cursor)

    @property
    def preview(self):
        return list(self._preview)

    @property
    def selected_preview(self):
        return self._preview[self._selected_index]

    def update(self, cursor):
        self._cursor = QPoint(cursor)
        offset = self._cursor - self._anchor
        preview = []
        affected = set(self._affected)
        for index, net in enumerate(self._baseline):
            if index not in affected:
                preview.append(net)
                continue
            pt1 = net.pt1 + offset if net.pt1 == self._anchor else net.pt1
            pt2 = net.pt2 + offset if net.pt2 == self._anchor else net.pt2
            preview.append(net.with_endpoints(pt1, pt2))
        self._preview = preview
        return self.preview


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
        for index in self._drag._affected:
            net = self._drag.preview[index]
            if net.pt1 != net.pt2:
                painter.drawLine(net.pt1, net.pt2)

    def _begin_drag(self, handle_index, pos):
        if self._drag is None:
            self._drag = NetDragSession(
                self._ctrl.doc.objects(objType=NetObj), self._obj, handle_index)
        self._drag.update(pos)
        self.update_handles()

    @Slot('QPoint')
    def _dragPt1(self, pos):
        """Handle dragging of pt1 - move connected segments."""
        self._begin_drag(0, pos)
        self.sigUpdate.emit()

    @Slot('QPoint')
    def _dragPt2(self, pos):
        """Handle dragging of pt2 - move connected segments."""
        self._begin_drag(1, pos)
        self.sigUpdate.emit()

    def handle_custom_event(self, event):
        """Net editor doesn't handle custom events currently."""
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
        normalized = NetObj._normalizeGeometry(preview)
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
