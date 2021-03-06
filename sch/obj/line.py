from PyQt5.QtCore import *
from PyQt5.QtGui import QPainter, QPen
import sch.document
import sch.controller
from sch.utils import LayerType, Layer, Geom
from lxml import etree
from sch.view import Event

class LineObj(object):
    def __init__(self, pt1=QPoint(0, 0), pt2=QPoint(1, 1), weight=1):
        self.pt1 = QPoint(pt1)
        self.pt2 = QPoint(pt2)
        self.weight = weight

    def draw(self, painter: QPainter):
        pen = QPen(Layer.color(LayerType.annotate))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setWidth(0)
        painter.setPen(pen)
        painter.drawLine(self.pt1, self.pt2)

    def bbox(self):
        return QRect(self.pt1, self.pt2).normalized()

    def testHit(self, pt: QPoint, radius: int):
        return Geom.distPtToSegment(pt, self.pt1, self.pt2) <= radius

    def toXml(self, parent):
        etree.SubElement(parent, "line",
                         weight=str(self.weight),
                         x1=str(self.pt1.x()),
                         y1=str(self.pt1.y()),
                         x2=str(self.pt2.x()),
                         y2=str(self.pt2.y()))

    @staticmethod
    def fromXml(elem):
        wt = int(elem.attrib["weight"])
        p1 = QPoint(int(elem.attrib["x1"]), int(elem.attrib["y1"]))
        p2 = QPoint(int(elem.attrib["x2"]), int(elem.attrib["y2"]))
        return LineObj(p1, p2, wt)


class LineTool(QObject):
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
        return "Draw Line"

    def finish(self):
        self._firstPt = None
        self.sigUpdate.emit()

    def draw(self, painter):
        pen = QPen(Layer.color(LayerType.annotate))
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
                self._ctrl.doc.doCommand(sch.document.ObjAddCmd(LineObj(self._firstPt, self._pos)))
                self._firstPt = None
                self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.Cancel:
            self._firstPt = None
            self.sigUpdate.emit()
            e.handled = True


class LineEditor(QObject):
    sigUpdate = pyqtSignal()
    sigDone = pyqtSignal()

    def __init__(self, ctrl, obj):
        super().__init__()
        self._ctrl = ctrl
        self._obj = obj
        self._handles = [sch.controller.EditHandle(self._ctrl, obj.pt1), sch.controller.EditHandle(self._ctrl, obj.pt2)]
        self._handles[0].sigDragged.connect(self._dragPt1)
        self._handles[1].sigDragged.connect(self._dragPt2)
        self._ctrl.doc.sigChanged.connect(self._docChanged)
        self._cmd = sch.document.ObjChangeCmd(obj)
        for h in self._handles:
            h.sigMoved.connect(self._commit)

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
        painter.setBrush(Qt.NoBrush)
        for h in self._handles:
            h.draw(painter)
        painter.drawLine(self._obj.pt1, self._obj.pt2)

    def handleEvent(self, event: Event):
        for h in self._handles:
            h.handleEvent(event)
            if event.handled:
                return

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
        self._handles[0].pos = self._obj.pt1
        self._handles[1].pos = self._obj.pt2
