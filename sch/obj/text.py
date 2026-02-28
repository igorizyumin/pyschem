from PySide6.QtCore import QPoint, Qt, QPointF, QSize, QRect
from PySide6.QtGui import QFont, QFontMetrics, QPainter, QPen, QBrush, QTextOption, QStaticText, QTransform
from lxml import etree
from sch.utils import *
import math


class TextBase(object):
    def __init__(self, text, pos, alignment, family, size, rot, parent=None):
        self._text = text
        self.pos = pos
        self.rot = rot
        self.alignment = alignment
        self._family = family
        self._ptSize = size
        self._alignment = 0
        self._scale = 1
        self._rot = -1
        self._pos = QPoint()
        self._dirty = True
        self._statictext = QStaticText()
        self._parent = parent

    def _getOffset(self):
        # 0, 0 = lower left when rot <= 180
        # 0.5, 0.5 = center
        # 1, 1 = upper right when rot <= 180
        if self.alignment & Qt.AlignLeft:
            h = -1
        elif self.alignment & Qt.AlignRight:
            h = 1
        else:
            h = 0
        if self.alignment & Qt.AlignBottom:
            v = -1
        elif self.alignment & Qt.AlignTop:
            v = 1
        else:
            v = 0
        if self.rot >= 180:
            h = -h
            v = -v
        return (h+1)/2.0, (v+1)/2.0

    def setPosGlobal(self, pos):
        if self._parent:
            self.pos = self._parent.transform().inverted()[0].map(pos)
        else:
            self.pos = pos
        self._dirty = True

    def posGlobal(self):
        if self._parent:
            return self._parent.transform().map(self.pos)
        else:
            return self.pos

    def _updateStaticText(self, scale, pos, rot):
        if self._scale == scale and self._rot == self.rot and self._pos == pos \
                and self._alignment == self.alignment and not self._dirty:
            return
        self._dirty = False
        self._scale = scale
        self._alignment = self.alignment
        self._rot = self.rot
        self._font = QFont(self.family, self.ptSize*scale)
        self._fm = QFontMetrics(self._font)
        self._pos = pos
        self._tr = QTransform()
        self._tr.translate(pos.x(), pos.y())
        self._tr.rotate(-((self.rot+rot) % 180))
        osx, osy = self._getOffset()
        bound = self._fm.boundingRect(self._text)
        self._tr.translate(-bound.width()*osx, bound.height()*(osy-1))
        self._statictext = QStaticText(self._text)
        self._statictext.setTextOption(QTextOption(self.alignment))
        self._statictext.prepare(font=self._font, matrix=self._tr)

    def draw(self, painter: QPainter):
        painter.save()
        tr = painter.transform()
        if self._parent:
            tr = self._parent.transform() * tr
        pen = QPen(Layer.color(LayerType.annotate))
        brush = QBrush(Layer.color(LayerType.annotate))
        painter.setPen(pen)
        painter.setBrush(brush)
        pos = tr.map(self.pos)
        pt0 = tr.map(QPointF(0, 0))
        pt1 = tr.map(QPointF(1, 0))
        delta = pt1-pt0
        rot = int(math.atan2(delta.y(), delta.x())/math.pi*180)
        scale = abs(delta.x() + delta.y())
        self._updateStaticText(scale=scale, pos=pos, rot=rot)
        painter.setTransform(self._tr)
        painter.setFont(self._font)
        painter.drawStaticText(QPoint(0, 0), self._statictext)
        painter.restore()


    def bbox(self):
        sz = (self._statictext.size() / self._scale).toSize().expandedTo(QSize(5000, 5000))
        tr = QTransform()
        tr.translate(self.pos.x(), self.pos.y())
        tr.rotate(self.rot % 180)
        osx, osy = self._getOffset()
        tr.translate(-sz.width()*osx, -sz.height()*osy)
        br = tr.mapRect(QRect(QPoint(), sz))
        if self._parent:
            return self._parent.transform().mapRect(br)
        else:
            return br

    def testHit(self, pt: QPoint, radius: int):
        return self.bbox().contains(pt)


class TextObj(TextBase):
    def __init__(self, text, pos=QPoint(0, 0), alignment=Qt.AlignCenter,
                 family="Helvetica", size=12*500, rot=0):
        super().__init__(text, pos, alignment, family, size, rot)

    @property
    def text(self):
        return self._text

    @text.setter
    def text(self, txt):
        self._text = txt
        self._dirty = True

    @property
    def family(self):
        return self._family

    @family.setter
    def family(self, fam):
        self._family = fam
        self._dirty = True

    @property
    def ptSize(self):
        return self._ptSize

    @ptSize.setter
    def ptSize(self, sz):
        self._ptSize = sz
        self._dirty = True

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


