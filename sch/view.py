from PyQt5.QtCore import *
from PyQt5.QtGui import QTransform, QPainter, QPen, QBrush, QCursor, QPolygon, QKeyEvent
from PyQt5.QtWidgets import *
from sch.utils import Coord, Layer, LayerType
from itertools import product
from enum import Enum


class Event(object):
    class Type(Enum):
        MouseMoved = 0
        MousePressed = 1
        MouseReleased = 2
        Done = 3
        Cancel = 4
        KeyPressed = 5
        KeyReleased = 6
        MouseDblClicked = 7

    def __init__(self, evType, pos=None, key=None):
        super().__init__()
        self.evType = evType
        self.pos = pos
        self.key = key
        self.handled = False


class SchView(QWidget):
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        self._transform = QTransform()
        # set up transform
        self._transform.translate(0, 0)
        # set to 100 px = 1 inch
        self._transform.scale(100.0/Coord.inchToSch(1), -100.0/Coord.inchToSch(1))
        self._mousePos = QPoint()
        self._wheelAngle = 0
        self._ctrl = None
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)

    def setCtrl(self, ctrl):
        self._ctrl = ctrl

    def paintEvent(self, event):
        painter = QPainter(self)
        # erase background
        painter.setBackground(QBrush(Layer.color(LayerType.background)))
        painter.setClipping(True)
        painter.eraseRect(self.rect())
        # draw document
        if self._ctrl is not None:
            # draw grid
            painter.setRenderHint(QPainter.Antialiasing, False)
            pen = QPen(Layer.color(LayerType.grid))
            pen.setCapStyle(Qt.RoundCap)
            pen.setJoinStyle(Qt.RoundJoin)
            pen.setWidth(0)
            painter.setTransform(self._transform)
            painter.setPen(pen)
            self._drawGrid(painter)
            # draw drawables
            # painter.setRenderHint(QPainter.Antialiasing)
            for d in self._ctrl.getDrawables():
                d.draw(painter)
        painter.end()

    def _drawGrid(self, painter):
        g = self._ctrl.grid
        if self._transform.map(QLine(QPoint(0, 0), QPoint(g, 0))).dx() <= 5:
            return  # grid points too close, don't draw grid
        viewport = self._transform.inverted()[0].mapRect(self.rect())
        startX = int(viewport.x() / g) * g
        startY = int(viewport.y() / g) * g
        endX = viewport.x() + viewport.width()
        endY = viewport.y() + viewport.height()
        pts = QPolygon((QPoint(i[0], i[1]) for i in product(range(startX, endX, g),
                                                            range(startY, endY, g))))
        painter.drawPoints(pts)

    def _handleEvent(self, event: Event):
        if self._ctrl is not None:
            self._ctrl.handleEvent(event)

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

    def recenter(self, pt=None, world=False):
        if pt is None:
            pt = self._mousePos
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
            dl = QLine(QPoint(0, 0), e.pos() - self._mousePos)
            dl = self._transform.inverted()[0].map(dl)
            self._transform.translate(dl.dx(), dl.dy())
            self.update()
        self._handleEvent(Event(evType=Event.Type.MouseMoved,
                                pos=self._transform.inverted()[0].map(e.pos())))
        self._mousePos = e.pos()

    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._handleEvent(Event(evType=Event.Type.MousePressed,
                                    pos=self._transform.inverted()[0].map(e.pos())))

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._handleEvent(Event(evType=Event.Type.MouseReleased,
                                    pos=self._transform.inverted()[0].map(e.pos())))

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._handleEvent(Event(evType=Event.Type.MouseDblClicked,
                                    pos=self._transform.inverted()[0].map(e.pos())))

    def hitRadius(self):
        return self._transform.inverted()[0].m11()*6     # 6 pixels

    def keyPressEvent(self, e):
        self._handleEvent(Event(evType=Event.Type.KeyPressed,
                                key=e.key()))

    def keyReleaseEvent(self, e: QKeyEvent):
        self._handleEvent(Event(evType=Event.Type.KeyReleased,
                                key=e.key()))

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

    @pyqtSlot()
    def slotUpdate(self):
        self.update()
