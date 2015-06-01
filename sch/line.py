from PyQt5.QtCore import *
from PyQt5.QtGui import QPainter
from sch.document import ObjAddCmd, ObjChangeCmd
import sch.controller
# from sch.controller import EditHandle
from lxml import etree


class LineObj(object):
    def __init__(self, pt1=QPoint(0, 0), pt2=QPoint(1, 1), weight=1):
        self.pt1 = QPoint(pt1)
        self.pt2 = QPoint(pt2)
        self.weight = weight

    def draw(self, painter: QPainter):
        painter.drawLine(self.pt1, self.pt2)

    def bbox(self):
        return QRect(self.pt1, self.pt2).normalized()

    def testHit(self, pt: QPoint, radius: int):
        return self.bbox().intersects(QRect(QPoint(pt.x()-radius/2.0, pt.y()-radius/2.0),
                                            QPoint(pt.x()+radius/2.0, pt.y()+radius/2.0)))

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

    def draw(self, painter):
        if self._firstPt is not None:
            painter.drawLine(self._firstPt, self._pos)

    @pyqtSlot('QMouseEvent', 'QPoint')
    def onMouseMoved(self, event, pos: QPoint):
        self._pos = self._ctrl.snapPt(pos)
        if self._firstPt is not None:
            self.sigUpdate.emit()

    @pyqtSlot()
    def onMouseReleased(self):
        if self._firstPt is None:
            self._firstPt = self._pos
        else:
            self._ctrl.doc.doCommand(ObjAddCmd(LineObj(self._firstPt, self._pos)))
            self._firstPt = None
            self.sigUpdate.emit()


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
        self._cmd = ObjChangeCmd(obj)
        for h in self._handles:
            h.sigMoved.connect(self._commit)
            self._ctrl.view.sigMouseMoved.connect(h.onMouseMoved)
            self._ctrl.view.sigMousePressed.connect(h.onMousePressed)
            self._ctrl.view.sigMouseReleased.connect(h.onMouseReleased)

    def testHit(self, pt):
        for h in self._handles:
            if h.testHit(pt):
                return True
        return False

    def draw(self, painter):
        for h in self._handles:
            h.draw(painter)


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
        self._cmd = ObjChangeCmd(self._obj)
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
