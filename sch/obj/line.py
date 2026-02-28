from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QPen
from sch.utils import LayerType, Layer, Geom
from lxml import etree

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
