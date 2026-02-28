from PySide6.QtCore import QPoint, Qt, QRect
from PySide6.QtGui import QPainter, QPen, QBrush
from sch.utils import LayerType, Layer, Geom, Point
from lxml import etree
from collections import defaultdict

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







