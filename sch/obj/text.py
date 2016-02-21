from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QUndoCommand
from enum import Enum
from lxml import etree
from sch.utils import *
import sch.controller
import sch.document
from sch.view import Event


class TextObj(object):
    def __init__(self, text, pos=QPoint(0, 0), alignment=Qt.AlignCenter,
                 family="Helvetica", size=12, rot=0):
        self.text = text
        self.pos = pos
        self.rot = rot
        self.alignment = alignment
        self.family = family
        self.ptSize = size
        self._scale = 1
        self._rot = -1
        self._pos = QPoint()

    def _updateStaticText(self, scale, pos):
        if self._scale == scale and self._rot == self.rot and self._pos == pos:
            return
        self._scale = scale
        self._rot = self.rot
        self._font = QFont(self.family, self.ptSize*scale)
        self._fm = QFontMetrics(self._font)
        self._pos = pos
        self._tr = QTransform()
        self._tr.translate(pos.x(), pos.y())
        self._tr.rotate(-self.rot)
        self._tr.translate(0, -self._fm.height())
        self._statictext = QStaticText(self.text)
        self._statictext.setTextOption(QTextOption(self.alignment))
        self._statictext.prepare(font=self._font, matrix=self._tr)

    def draw(self, painter: QPainter):
        painter.save()
        tr = painter.transform()
        pos = tr.map(self.pos)
        self._updateStaticText(scale=abs(tr.m22()), pos=pos)
        painter.setTransform(self._tr)
        painter.setFont(self._font)
        painter.drawStaticText(QPoint(0, 0), self._statictext)
        painter.restore()

    def bbox(self):
        sz = (self._statictext.size() / self._scale).toSize()
        tr = QTransform()
        tr.translate(self.pos.x(), self.pos.y())
        tr.rotate(self.rot)
        return tr.mapRect(QRect(QPoint(), sz))

    def testHit(self, pt: QPoint, radius: int):
        return self.bbox().contains(pt)

    def toXml(self, parent):
        halign = "center"
        valign = "middle"
        if self.alignment & Qt.AlignLeft:
            halign = "left"
        elif self.alignment & Qt.AlignRight:
            halign = "right"
        if self.alignment & Qt.AlignTop:
            valign = "top"
        elif self.alignment & Qt.AlignBottom:
            valign = "bottom"
        t = etree.SubElement(parent, "text",
                             x=str(self.pos.x()),
                             y=str(self.pos.y()),
                             rot=str(self.rot),
                             hAlign=halign,
                             vAlign=valign,
                             fontFamily=self.family,
                             fontSize=str(self.ptSize))
        t.text = self.text

    @staticmethod
    def fromXml(elem):
        text = elem.text
        pos = QPoint(int(elem.attrib['x']), int(elem.attrib['y']))
        ha = elem.attrib['hAlign']
        va = elem.attrib['vAlign']
        hd = {"left": Qt.AlignLeft, "center": Qt.AlignCenter, "right": Qt.AlignRight}
        vd = {"top": Qt.AlignTop, "middle": Qt.AlignVCenter, "bottom": Qt.AlignBottom}
        alignment = hd[ha] | vd[va]
        rot = int(elem.attrib['rot'])
        return TextObj(text, pos, alignment, elem.attrib['fontFamily'], int(elem.attrib['fontSize']), rot)


class TextEditor(QObject):
    sigUpdate = pyqtSignal()
    sigDone = pyqtSignal()

    def __init__(self, ctrl, obj):
        super().__init__()
        self._ctrl = ctrl
        self._obj = obj
        self._handle = sch.controller.TextHandle(self._ctrl, self._obj)
        self._handle.sigDragged.connect(self._drag)
        self._handle.sigMoved.connect(self._commit)
        self._ctrl.doc.sigChanged.connect(self._docChanged)
        self._cmd = sch.document.ObjChangeCmd(obj)

    def testHit(self, pt):
        return self._handle.testHit(pt)

    def handleEvent(self, e):
        if e.evType == Event.Type.KeyPressed:
            if e.key == Qt.Key_R:
                self._obj.rot = (self._obj.rot + 90) % 360
                self._commit()
        elif e.evType == Event.Type.MouseDblClicked:
            print("dbl click event")
        self._handle.handleEvent(e)

    def draw(self, painter):
        pen = QPen(Layer.color(LayerType.selection))
        # pen.setCapStyle(Qt.RoundCap)
        # pen.setJoinStyle(Qt.RoundJoin)
        pen.setWidth(0)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        self._handle.draw(painter)

    @pyqtSlot('QPoint')
    def _drag(self, pos):
        self._obj.pos = pos
        self.sigUpdate.emit()

    @pyqtSlot('QPoint')
    def _commit(self):
        self._obj.pos = self._handle.pos
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
        self._handle.pos = self._obj.pos
