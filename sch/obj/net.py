from PyQt5.QtCore import *
from PyQt5.QtGui import QPainter, QPen, QBrush
from PyQt5.QtWidgets import QUndoCommand
import sch.document
import sch.controller
from sch.utils import LayerType, Layer, Geom, Point
# from sch.controller import EditHandle
from lxml import etree
from collections import defaultdict
from sch.view import Event


class NetObj(object):
    def __init__(self, pt1=QPoint(0, 0), pt2=QPoint(1, 1)):
        self.pt1 = QPoint(pt1)
        self.pt2 = QPoint(pt2)

    def __str__(self):
        return "<Net: ({},{})<->({},{})>".format(self.pt1.x(), self.pt1.y(), self.pt2.x(), self.pt2.y())

    def draw(self, painter: QPainter):
        pen = QPen(Layer.color(LayerType.wire))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setWidth(0)
        painter.setPen(pen)
        painter.drawLine(self.pt1, self.pt2)

    def bbox(self):
        return QRect(self.pt1, self.pt2).normalized().adjusted(-1, -1, 1, 1)

    def testHit(self, pt: QPoint, radius: int):
        return Geom.distPtToSegment(pt, self.pt1, self.pt2) <= radius

    def connVtx(self, otherNet):
        # check if they share a vertex
        xs = {Point(self.pt1), Point(self.pt2)}.intersection({Point(otherNet.pt1), Point(otherNet.pt2)})
        if xs:
            return xs.pop()
        else:
            return None

    def touchesPt(self, pt):
        # check if point is on this segment
        # print("net touch: {} {} : {}".format(str(self), pt, Geom.pointOnSegment(self.pt1, self.pt2, pt)))
        return Geom.pointOnSegment(self.pt1, self.pt2, pt)

    def intersectsNet(self, net):
        return Geom.segsIntersect(self.pt1, self.pt2, net.pt1, net.pt2)

    def toXml(self, parent):
        etree.SubElement(parent, "net",
                         x1=str(self.pt1.x()),
                         y1=str(self.pt1.y()),
                         x2=str(self.pt2.x()),
                         y2=str(self.pt2.y()))

    @staticmethod
    def fromXml(elem):
        p1 = QPoint(int(elem.attrib["x1"]), int(elem.attrib["y1"]))
        p2 = QPoint(int(elem.attrib["x2"]), int(elem.attrib["y2"]))
        return NetObj(p1, p2)

    @staticmethod
    def drawJunctions(doc, painter: QPainter):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(Layer.color(LayerType.junction)))
        nets = doc.objects(objType=NetObj)
        juncts = defaultdict(set)
        while nets:
            n = nets.pop()
            # check net against every other net in set
            for n2 in nets:
                v = n.connVtx(n2)
                if v:
                    juncts[v].add(n)
                    juncts[v].add(n2)
        for pt, nets in juncts.items():
            if len(nets) > 2:
                painter.drawEllipse(QPoint(pt.x, pt.y), 500, 500)


class NetTool(QObject):
    sigUpdate = pyqtSignal()

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
        # print("new net ({},{})->({},{})".format(newNet.pt1.x(), newNet.pt1.y(), newNet.pt2.x(), newNet.pt2.y()))
        # this algorithm normalizes the nets such that nets touch only at endpoints
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
        # print("collinear: " + str(clnets))
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
        unitedNet = NetObj((origin+minc*unitNewDir).toPoint(), (origin+maxc*unitNewDir).toPoint())
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
            netsAdd.add(NetObj((origin+p1*unitNewDir).toPoint(), (origin+p2*unitNewDir).toPoint()))
            p1 = p2
        cmd = QUndoCommand()
        for obj in netsDel:
            # print("deleting {}".format(str(obj)))
            sch.document.ObjDelCmd(obj, doc=self._ctrl.doc, parent=cmd)
        for obj in netsAdd:
            # print("adding: {}".format(str(obj)))
            sch.document.ObjAddCmd(obj, doc=self._ctrl.doc, parent=cmd)
        self._ctrl.doc.doCommand(cmd)


class NetEditor(QObject):
    sigUpdate = pyqtSignal()
    sigDone = pyqtSignal()

    def __init__(self, ctrl, obj):
        super().__init__()
        self._ctrl = ctrl
        self._obj = obj
        #self._handles = []
        #self._handles = [sch.controller.EditHandle(self._ctrl, obj.pt1), sch.controller.EditHandle(self._ctrl, obj.pt2)]
        #self._handles[0].sigDragged.connect(self._dragPt1)
        #self._handles[1].sigDragged.connect(self._dragPt2)
        self._ctrl.doc.sigChanged.connect(self._docChanged)
        self._cmd = sch.document.ObjChangeCmd(obj)
        #for h in self._handles:
        #    h.sigMoved.connect(self._commit)

    def testHit(self, pt):
        for h in self._handles:
            if h.testHit(pt):
                return True
        return False

    def draw(self, painter):
        pen = QPen(Layer.color(LayerType.selection))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setWidth(0)
        painter.setPen(pen)
        #for h in self._handles:
        #    h.draw(painter)
        painter.drawLine(self._obj.pt1, self._obj.pt2)

    def handleEvent(self, e: Event):
        pass

    @property
    def inspector(self):
        return None

    @pyqtSlot('QPoint')
    def _dragPt1(self, pos):
        self._obj.pt1 = pos
        self.sigUpdate.emit()

    @pyqtSlot('QPoint')
    def _dragPt2(self, pos):
        self._obj.pt2 = pos
        self.sigUpdate.emit()

    @pyqtSlot('QPoint')
    def _commit(self):
        self._obj.pt1 = self._handles[0].pos
        self._obj.pt2 = self._handles[1].pos
        self._ctrl.doc.doCommand(self._cmd)
        self._cmd = sch.document.ObjChangeCmd(self._obj)
        self.sigUpdate.emit()

    @pyqtSlot()
    def _docChanged(self):
        # if document changed, it might be because the object got deleted; update state
        # check that object is still part of the document
        if not self._ctrl.doc.hasObject(self._obj):
            self.sigDone.emit()
            return
        # object still there, just update handle positions
        #self._handles[0].pos = self._obj.pt1
        #self._handles[1].pos = self._obj.pt2







