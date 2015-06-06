from enum import Enum
from PyQt5.QtCore import QPoint
from PyQt5.QtGui import QColor


class Geom:
    # computes perpendicular vector
    @staticmethod
    def perp(pt: QPoint):
        return QPoint(-pt.y(), pt.x())

    # dot product
    @staticmethod
    def dotProd(pt1: QPoint, pt2: QPoint):
        return pt1.x() * pt2.x() + pt1.y() * pt2.y()

    @staticmethod
    def isParallel(dir1: QPoint, dir2: QPoint):
        return Geom.dotProd(dir1, Geom.perp(dir2)) != 0

    @staticmethod
    def norm(p: QPoint):
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
