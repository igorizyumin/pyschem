from PyQt5.QtCore import *
from PyQt5.QtGui import QPainter
from sch.document import ObjAddCmd


class LineObj(object):
    def __init__(self, pt1=QPoint(0, 0), pt2=QPoint(1, 1)):
        self.pt1 = QPoint(pt1)
        self.pt2 = QPoint(pt2)

    def draw(self, painter: QPainter):
        painter.drawLine(self.pt1, self.pt2)

    def bbox(self):
        return QRect(self.pt1, self.pt2).normalized()


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
        self._pos = pos
        if self._firstPt is not None:
            self.sigUpdate.emit()

    @pyqtSlot()
    def onMouseClicked(self):
        if self._firstPt is None:
            self._firstPt = self._pos
        else:
            print("Line: ({},{})->({},{})".format(self._firstPt.x(), self._firstPt.y(), self._pos.x(), self._pos.y()))
            self._ctrl.doc.doCommand(ObjAddCmd(LineObj(self._firstPt, self._pos)))
            self._firstPt = None
            self.sigUpdate.emit()
