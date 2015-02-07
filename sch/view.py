from PyQt5.QtCore import *
from PyQt5.QtGui import QTransform, QPainter, QPen, QBrush, QCursor
from PyQt5.QtWidgets import *
from sch.utils import Coord, Layer, LayerType


class SchView(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._transform = QTransform()
        # set up transform
        self._transform.translate(0, 0)
        # set to 100 px = 1 inch
        self._transform.scale(100.0/Coord.inchToSch(1), -100.0/Coord.inchToSch(1))
        self._grid = Coord.mmToSch(5)
        self._mousePos = QPoint()
        self._wheelAngle = 0
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def setGrid(self, grid):
        self._grid = int(grid)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        # erase background
        painter.setBackground(QBrush(Layer.color(LayerType.background)))
        painter.setClipping(True)
        painter.eraseRect(self.rect())
        # draw document
        if True or self._doc is not None:
            # draw grid
            pen = QPen(Layer.color(LayerType.grid))
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            pen.setWidth(0)
            painter.setTransform(self._transform)
            painter.setPen(pen)
            self._drawGrid(painter)
        painter.end()

    def _drawGrid(self, painter):
        if self._transform.map(QLine(QPoint(0, 0), QPoint(self._grid, 0))).dx() <= 5:
            return  # grid points too close, don't draw grid
        viewport = self._transform.inverted()[0].mapRect(self.rect())
        startX = int(viewport.x() / self._grid) * self._grid
        startY = int(viewport.y() / self._grid) * self._grid
        endX = viewport.x() + viewport.width()
        endY = viewport.y() + viewport.height()
        for x in range(startX, endX, self._grid):
            for y in range(startY, endY, self._grid):
                painter.drawPoint(x, y)

    def zoom(self, factor, pos):
        self.recenter(pos)
        p = self._transform.inverted()[0].map(self.rect().center())
        test = QTransform(self._transform)
        test.scale(factor, factor)
        # check if the bounding rectangle does not enclose the view
        # refuse to zoom out (factor < 1) if this is the case
        # XXX TODO
        self._transform.scale(factor, factor)
        self.recenter(p, True)

    def recenter(self, pt, world = False):
        ctr = self._transform.inverted()[0].map(self.rect().center())
        if not world:
            pt = self._transform.inverted()[0].map(pt)
        ctr -= pt
        self._transform.translate(ctr.x(), ctr.y())
        # move cursor to center of window
        QCursor.setPos(self.mapToGlobal(self.rect().center()))
        self.update()

    def mouseMoveEvent(self, e):
        if e.buttons() & Qt.MidButton:
            dl = QLine(QPoint(0,0), e.pos() - self._mousePos)
            dl = self._transform.inverted()[0].map(dl)
            self._transform.translate(dl.dx(), dl.dy())
            self.update()
        self._mousePos = e.pos()

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Space:
            self.recenter(self._mousePos)
        else:
            e.ignore()

    def wheelEvent(self, e):
        self._wheelAngle += e.angleDelta().y()
        if self._wheelAngle >= 120:
            self._wheelAngle -= 120
            self.zoom(1.25, e.pos())
        elif self._wheelAngle <= -120:
            self._wheelAngle += 120
            self.zoom(0.8, e.pos())

    def enterEvent(self, e):
        self.setFocus(Qt.MouseFocusReason)

    def leaveEvent(self, e):
        self.clearFocus()