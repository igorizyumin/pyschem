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
        """Net editor doesn't use handles currently."""
        self._handles = []

    def draw_custom(self, painter):
        """Draw the net line."""
        painter.drawLine(self._obj.pt1, self._obj.pt2)

    def handle_custom_event(self, event):
        """Net editor doesn't handle custom events currently."""
        super().handle_custom_event(event)
        if event.handled:
            return
