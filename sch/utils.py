from enum import Enum
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QColor


# hashable version of QPoint
class Point:
    def __init__(self, pt: QPoint):
        self.x = pt.x()
        self.y = pt.y()

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __hash__(self):
        return self.x ^ self.y


class Geom:
    # computes perpendicular vector
    @staticmethod
    def perp(pt):
        return QPoint(-pt.y(), pt.x())

    # dot product
    @staticmethod
    def dotProd(pt1, pt2):
        return pt1.x() * pt2.x() + pt1.y() * pt2.y()

    @staticmethod
    def isParallel(dir1: QPoint, dir2: QPoint):
        return dir1.x() * dir2.y() - dir2.x() * dir1.y() == 0

    @staticmethod
    def norm(p):
        return Geom.dotProd(p, p)**0.5

    @staticmethod
    def dist(pt1: QPoint, pt2: QPoint):
        return Geom.norm(pt1-pt2)

    # finds the line intersection of the two lines given by (pt1, dir1) and (pt2, dir2)
    # returns scale factor for dir1 vector (xsect_pt = pt1 + retVal * dir1)
    # check for parallel-ness before using this
    @staticmethod
    def lineIntersect(pt1: QPoint, dir1: QPoint, pt2: QPoint, dir2: QPoint):
        w = pt1 - pt2
        return float(dir2.y() * w.x() - dir2.x() * w.y()) / (dir2.x() * dir1.y() - dir2.y()*dir1.x())

    # given three collinear points, returns True if ptTest is on the (pt1,pt2) segment
    @staticmethod
    def collinearPointOnSegment(pt1, pt2, ptTest):
        return (min(pt1.x(), pt2.x()) <= ptTest.x() <= max(pt1.x(), pt2.x()) and
                min(pt1.y(), pt2.y()) <= ptTest.y() <= max(pt1.y(), pt2.y()))

    @staticmethod
    def pointOnSegment(pt1, pt2, ptTest):
        # check for collinearity
        dirTest = ptTest - pt1
        dirSeg = pt2 - pt1
        if not Geom.isParallel(dirTest, dirSeg):
            return False    # not collinear, cannot be on segment
        return Geom.collinearPointOnSegment(pt1, pt2, ptTest)

    # returns orientation of ordered triplet (p,q,r)
    # -1 = CCW, 0 = collinear, 1 = CW
    @staticmethod
    def orient(p, q, r):
        v = (q.y() - p.y()) * (r.x() - q.x()) - (q.x() - p.x()) * (r.y() - q.y())
        if v == 0:
            return 0
        return -1 if v < 0 else 1

    # returns true if the segments (a1,a2) and (b1,b2) intersect
    @staticmethod
    def segsIntersect(a1, a2, b1, b2):
        orient = Geom.orient
        onseg = Geom.collinearPointOnSegment
        o1 = orient(a1, a2, b1)
        o2 = orient(a1, a2, b2)
        o3 = orient(b1, b2, a1)
        o4 = orient(b1, b2, a2)

        if o1 != o2 and o3 != o4:
            return True
        # b1 on (a1,a2)
        if o1 == 0 and onseg(a1, a2, b1):
            return True
        # b2 on (a1,a2)
        if o2 == 0 and onseg(a1, a2, b2):
            return True
        # a1 on (b1,b2)
        if o3 == 0 and onseg(b1, b2, a1):
            return True
        # a2 on (b1,b2)
        if o4 == 0 and onseg(b1, b2, a2):
            return True
        return False

    @staticmethod
    def distPtToSegment(p: QPoint, pt1: QPoint, pt2: QPoint):
        v = pt2 - pt1
        w = p - pt1
        c1 = Geom.dotProd(w, v)
        if c1 <= 0:
            return Geom.dist(p, pt1)
        c2 = Geom.dotProd(v, v)
        if c2 <= c1:
            return Geom.dist(p, pt2)
        b = float(c1)/c2
        pb = pt1 + v*b
        return Geom.dist(p, pb)


class Coord:
    # database unit is the micron
    DBU_PER_MM = 1000
    DBU_PER_INCH = 25400

    @staticmethod
    def inchToSch(x):
        return int(x*Coord.DBU_PER_INCH)

    @staticmethod
    def mmToSch(x):
        return int(x*Coord.DBU_PER_MM)

    @staticmethod
    def schToMm(x):
        return float(x) / Coord.DBU_PER_MM

    @staticmethod
    def schToInch(x):
        return float(x) / Coord.DBU_PER_INCH


class LayerType(Enum):
    """Layer type enumeration"""
    background = 0,  # page background
    grid = 1,        # grid dots / lines
    annotate = 2,    # annotation elements (lines, text, etc)
    symbol = 3,      # symbol graphical elements
    wire = 4,        # wires
    junction = 5,    # wire junctions
    titleblock = 6,  # title blocks
    warning = 7,     # warning elements (e.g. dangling nets)
    selection = 8,   # selection rubberband
    attribute = 9    # attribute text


class Layer:
    COLORS = {LayerType.background:     QColor(0, 0, 0),
              LayerType.grid:           QColor(128, 128, 128),
              LayerType.annotate:       QColor(98, 209, 118),
              LayerType.symbol:         QColor(98, 209, 118),
              LayerType.wire:           QColor(137, 188, 232),
              LayerType.junction:       QColor(137, 188, 232),
              LayerType.titleblock:     QColor(128, 128, 128),
              LayerType.warning:        QColor(227, 116, 116),
              LayerType.selection:      QColor(219, 240, 34),
              LayerType.attribute:      QColor(214, 222, 144)
              }

    @staticmethod
    def color(t):
        return Layer.COLORS[t]
