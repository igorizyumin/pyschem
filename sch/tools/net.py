from PySide6.QtCore import QObject, Signal, Slot, QPoint, QPointF, Qt, QRect
from PySide6.QtGui import QPainter, QPen, QBrush, QUndoCommand
import sch.document
import sch.controller
from sch.utils import LayerType, Layer, Geom, Point
from sch.obj.net import NetObj
from sch.tools.base import EditHandle, BaseEditor
from lxml import etree
from collections import defaultdict
from sch.view import Event


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
        print("new net ({},{})->({},{})".format(newNet.pt1.x(), newNet.pt1.y(), newNet.pt2.x(), newNet.pt2.y()))
        # this algorithm normalizes the nets such that nets touch only at endpoints
        assert type(newNet.pt1) is QPoint and type(newNet.pt2) is QPoint
        origin = newNet.pt1
        newDir = newNet.pt2 - newNet.pt1
        unitNewDir = QPointF(newDir)
        unitNewDir /= Geom.norm(unitNewDir)
        # nets to be deleted
        netsDel = set()
        netsAdd = set()
        # find any non-parallel nets that need to be split
        splitP1 = self._ctrl.doc.findObjsNear(newNet.pt1, objType=NetObj)
        splitP2 = self._ctrl.doc.findObjsNear(newNet.pt2, objType=NetObj)
        for net in splitP1:
            if (net.touchesPt(newNet.pt1)
               and not Geom.isParallel(newDir, net.pt2-net.pt1)
               and not net.connVtx(newNet)):
                netsDel.add(net)
                netsAdd.add(NetObj(newNet.pt1, net.pt1))
                netsAdd.add(NetObj(newNet.pt1, net.pt2))
        for net in splitP2:
            if (net.touchesPt(newNet.pt2)
               and not Geom.isParallel(newDir, net.pt2-net.pt1)
               and not net.connVtx(newNet)):
                netsDel.add(net)
                netsAdd.add(NetObj(newNet.pt2, net.pt1))
                netsAdd.add(NetObj(newNet.pt2, net.pt2))
        # find all intersecting nets
        xsnets = {net for net in self._ctrl.doc.findObjsInRect(newNet.bbox(), objType=NetObj)
                  if newNet.intersectsNet(net)}
        # collinear nets (which need to be replaced)
        clnets = {net for net in xsnets if Geom.isParallel(newDir, net.pt2-net.pt1)}
        print("collinear: " + str(clnets))
        xsnets -= clnets    # remove collinear nets from set of intersections
        # compute union of all nets to be replaced
        # coordinates of united nets (projected onto newDir); initialize with new net coords
        coords = {0, Geom.dotProd(unitNewDir, newNet.pt2-origin)}
        for net in clnets:
            if net.touchesPt(newNet.pt1) and net.touchesPt(newNet.pt2):
                # print("Not adding redundant net")
                return  # new net is redundant because it is on top of an existing net
            coords.add(Geom.dotProd(unitNewDir, net.pt1-origin))
            coords.add(Geom.dotProd(unitNewDir, net.pt2-origin))
        netsDel |= clnets
        # find all intersection points
        minc = min(coords)
        maxc = max(coords)
        start_point = origin + (unitNewDir * minc).toPoint()
        end_point = origin + (unitNewDir * maxc).toPoint()
        unitedNet = NetObj(start_point, end_point)
        # these nets touch the new net with an endpoint
        xsP1 = {net for net in xsnets if unitedNet.touchesPt(net.pt1) and not unitedNet.connVtx(net)}
        xsP2 = {net for net in xsnets if unitedNet.touchesPt(net.pt2) and not unitedNet.connVtx(net)}
        # print("touching: " + str(xsP1 | xsP2))
        xscoords = {minc, maxc}
        for net in xsP1:
            xscoords.add(Geom.dotProd(unitNewDir, net.pt1-origin))
        for net in xsP2:
            xscoords.add(Geom.dotProd(unitNewDir, net.pt2-origin))
        xscoords = list(xscoords)
        xscoords.sort()
        # print(xscoords)
        p1 = xscoords.pop(0)
        while xscoords:
            p2 = xscoords.pop(0)
            start_point = origin + (unitNewDir * p1).toPoint()
            end_point = origin + (unitNewDir * p2).toPoint()
            netsAdd.add(NetObj(start_point, end_point))
            p1 = p2
        cmd = sch.document.BaseUndoCmd("add net")
        for obj in netsDel:
            print("deleting {}".format(str(obj)))
            sch.document.ObjDelCmd(obj, doc=self._ctrl.doc, parent=cmd)
        for obj in netsAdd:
            print("adding: {}".format(str(obj)))
            sch.document.ObjAddCmd(obj, doc=self._ctrl.doc, parent=cmd)
        self._ctrl.doc.doCommand(cmd)

class NetEditor(BaseEditor):

    def __init__(self, ctrl, obj):
        super().__init__(ctrl, obj)

    def _create_change_command(self):
        """Create the appropriate change command for NetObj."""
        import sch.document
        return sch.document.ObjChangeCmd(self._obj, self._ctrl.doc)

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
        self._handles[0].pos = self._obj.pt1
        self._handles[1].pos = self._obj.pt2

    def draw_custom(self, painter):
        """Draw the net line."""
        painter.drawLine(self._obj.pt1, self._obj.pt2)

    @Slot('QPoint')
    def _dragPt1(self, pos):
        """Handle dragging of pt1 - move connected segments."""
        offset = pos - self._obj.pt1
        self._move_connected_segments(self._obj.pt1, offset)
        self._obj.pt1 = pos
        self.sigUpdate.emit()

    @Slot('QPoint')
    def _dragPt2(self, pos):
        """Handle dragging of pt2 - move connected segments."""
        offset = pos - self._obj.pt2
        self._move_connected_segments(self._obj.pt2, offset)
        self._obj.pt2 = pos
        self.sigUpdate.emit()

    def _move_connected_segments(self, endpoint, offset):
        """Move all net segments connected to the given endpoint by the offset."""
        connected_nets = self._find_connected_segments(endpoint)
        for net in connected_nets:
            if net.pt1 == endpoint:
                net.pt1 += offset
            elif net.pt2 == endpoint:
                net.pt2 += offset

    def _find_connected_segments(self, endpoint):
        """Find all net segments that share the given endpoint."""
        connected = []
        for net in self._ctrl.doc.objects(objType=NetObj):
            if net != self._obj and (net.pt1 == endpoint or net.pt2 == endpoint):
                connected.append(net)
        return connected

    def handle_custom_event(self, event):
        """Net editor doesn't handle custom events currently."""
        super().handle_custom_event(event)
        if event.handled:
            return

    def _commit(self):
        """Commit the net movement with normalization."""
        # Create parent undo command
        cmd = sch.document.BaseUndoCmd("move net endpoint", doc=self._ctrl.doc)
        
        # Store the current state of the edited net for normalization
        current_net = NetObj(self._obj.pt1, self._obj.pt2)
        
        # Apply normalization - this may delete and create nets
        self._normalize_net(current_net, cmd)
        
        # Execute the command
        self._ctrl.doc.doCommand(cmd)
        
        # Update handles and emit update
        self.update_handles()
        self.sigUpdate.emit()

    def _normalize_net(self, newNet, parent_cmd):
        """Normalize the net system after moving an endpoint."""
        # This is extracted from NetTool.addNet() but adapted for editing
        assert type(newNet.pt1) is QPoint and type(newNet.pt2) is QPoint
        origin = newNet.pt1
        newDir = newNet.pt2 - newNet.pt1
        unitNewDir = QPointF(newDir)
        unitNewDir /= Geom.norm(unitNewDir)
        
        # nets to be deleted
        netsDel = set()
        netsAdd = set()
        
        # Add the original net to be deleted (it will be replaced)
        netsDel.add(self._obj)
        
        # find any non-parallel nets that need to be split
        splitP1 = self._ctrl.doc.findObjsNear(newNet.pt1, objType=NetObj)
        splitP2 = self._ctrl.doc.findObjsNear(newNet.pt2, objType=NetObj)
        for net in splitP1:
            if (net.touchesPt(newNet.pt1)
               and not Geom.isParallel(newDir, net.pt2-net.pt1)
               and not net.connVtx(newNet)):
                netsDel.add(net)
                netsAdd.add(NetObj(newNet.pt1, net.pt1))
                netsAdd.add(NetObj(newNet.pt1, net.pt2))
        for net in splitP2:
            if (net.touchesPt(newNet.pt2)
               and not Geom.isParallel(newDir, net.pt2-net.pt1)
               and not net.connVtx(newNet)):
                netsDel.add(net)
                netsAdd.add(NetObj(newNet.pt2, net.pt1))
                netsAdd.add(NetObj(newNet.pt2, net.pt2))
        
        # find all intersecting nets
        xsnets = {net for net in self._ctrl.doc.findObjsInRect(newNet.bbox(), objType=NetObj)
                  if newNet.intersectsNet(net)}
        # collinear nets (which need to be replaced)
        clnets = {net for net in xsnets if Geom.isParallel(newDir, net.pt2-net.pt1)}
        xsnets -= clnets    # remove collinear nets from set of intersections
        
        # compute union of all nets to be replaced
        coords = {0, Geom.dotProd(unitNewDir, newNet.pt2-origin)}
        for net in clnets:
            if net.touchesPt(newNet.pt1) and net.touchesPt(newNet.pt2):
                return  # new net is redundant because it is on top of an existing net
            coords.add(Geom.dotProd(unitNewDir, net.pt1-origin))
            coords.add(Geom.dotProd(unitNewDir, net.pt2-origin))
        netsDel |= clnets
        
        # find all intersection points
        minc = min(coords)
        maxc = max(coords)
        start_point = origin + (unitNewDir * minc).toPoint()
        end_point = origin + (unitNewDir * maxc).toPoint()
        unitedNet = NetObj(start_point, end_point)
        
        # these nets touch the new net with an endpoint
        xsP1 = {net for net in xsnets if unitedNet.touchesPt(net.pt1) and not unitedNet.connVtx(net)}
        xsP2 = {net for net in xsnets if unitedNet.touchesPt(net.pt2) and not unitedNet.connVtx(net)}
        
        xscoords = {minc, maxc}
        for net in xsP1:
            xscoords.add(Geom.dotProd(unitNewDir, net.pt1-origin))
        for net in xsP2:
            xscoords.add(Geom.dotProd(unitNewDir, net.pt2-origin))
        xscoords = list(xscoords)
        xscoords.sort()
        
        p1 = xscoords.pop(0)
        while xscoords:
            p2 = xscoords.pop(0)
            start_point = origin + (unitNewDir * p1).toPoint()
            end_point = origin + (unitNewDir * p2).toPoint()
            netsAdd.add(NetObj(start_point, end_point))
            p1 = p2
        
        # Create undo commands
        for obj in netsDel:
            sch.document.ObjDelCmd(obj, doc=self._ctrl.doc, parent=parent_cmd)
        for obj in netsAdd:
            sch.document.ObjAddCmd(obj, doc=self._ctrl.doc, parent=parent_cmd)
