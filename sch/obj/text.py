from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QUndoCommand, QWidget
from enum import Enum
from lxml import etree
from sch.utils import *
import sch.controller
import sch.document
from sch.view import Event
from sch.uic.ui_textinspector import Ui_TextInspector
import copy
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
        self._tr.translate(-self._fm.width(self._text)*osx, self._fm.height()*(osy-1))
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


class TextTool(QObject):
    sigUpdate = pyqtSignal()

    def __init__(self, ctrl):
        QObject.__init__(self)
        self._ctrl = ctrl
        self._pos = QPoint()
        self._obj = TextObj("Text")
        self._inspector = TextInspector(self._obj)
        # self._inspector.edited.connect(self._commit)

    def finish(self):
        self._obj = None
        self.sigUpdate.emit()
        pass

    @property
    def inspector(self):
        return self._inspector

    @staticmethod
    def name():
        return "Add Text"

    def draw(self, painter):
        if self._obj is not None:
            self._obj.draw(painter)

    def handleEvent(self, e):
        if e.evType == sch.controller.Event.Type.MouseMoved:
            self._obj.pos = self._ctrl.snapPt(e.pos)
            self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.MouseReleased:
            cmd = sch.document.ObjAddCmd(self._obj)
            self._ctrl.doc.doCommand(cmd)
            self._obj = copy.copy(self._obj)
            self._inspector.obj = self._obj
            e.handled = True


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
        self._inspector = TextInspector(obj)
        self._inspector.edited.connect(self._commit)

    @property
    def inspector(self):
        return self._inspector

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

    @pyqtSlot()
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


class TextInspector(QWidget):
    edited = pyqtSignal()

    def __init__(self, obj, parent=None):
        super().__init__(parent)
        self.ui = Ui_TextInspector()
        self.ui.setupUi(self)
        self._obj = None
        fontSizes = list(range(6, 16)) + list(range(16, 34, 2)) + list(range(36, 48, 4)) + \
            list(range(48, 66, 6)) + list(range(66, 98, 8))
        self.ui.fontSize.addItems([str(i) for i in fontSizes])
        self._obj = obj
        self._loadProperties(obj)

    @property
    def obj(self):
        return self._obj

    @obj.setter
    def obj(self, new):
        self._obj = new
        self._loadProperties(new)

    def _loadProperties(self, obj: TextObj):
        self.ui.text.setText(obj.text)
        if obj.alignment & Qt.AlignLeft:
            if obj.alignment & Qt.AlignTop:
                self.ui.btnTopLeft.setChecked(True)
            elif obj.alignment & Qt.AlignBottom:
                self.ui.btnBotLeft.setChecked(True)
            else:
                self.ui.btnMidLeft.setChecked(True)
        elif obj.alignment & Qt.AlignRight:
            if obj.alignment & Qt.AlignTop:
                self.ui.btnTopRight.setChecked(True)
            elif obj.alignment & Qt.AlignBottom:
                self.ui.btnBotRight.setChecked(True)
            else:
                self.ui.btnMidRight.setChecked(True)
        else:
            if obj.alignment & Qt.AlignTop:
                self.ui.btnTopCtr.setChecked(True)
            elif obj.alignment & Qt.AlignBottom:
                self.ui.btnBotCtr.setChecked(True)
            else:
                self.ui.btnMidCtr.setChecked(True)
        self.ui.fontFace.setCurrentText(obj.family)
        self.ui.fontSize.setCurrentText("{:g}".format(obj.ptSize/500))

    @pyqtSlot(int)
    def on_alignGroup_buttonClicked(self, id):
        if self.ui.btnTopLeft.isChecked():
            align = Qt.AlignTop | Qt.AlignLeft
        elif self.ui.btnTopCtr.isChecked():
            align = Qt.AlignTop | Qt.AlignVCenter
        elif self.ui.btnTopRight.isChecked():
            align = Qt.AlignTop | Qt.AlignRight
        elif self.ui.btnMidLeft.isChecked():
            align = Qt.AlignHCenter | Qt.AlignLeft
        elif self.ui.btnMidCtr.isChecked():
            align = Qt.AlignHCenter | Qt.AlignVCenter
        elif self.ui.btnMidRight.isChecked():
            align = Qt.AlignHCenter | Qt.AlignRight
        elif self.ui.btnBotLeft.isChecked():
            align = Qt.AlignBottom| Qt.AlignLeft
        elif self.ui.btnBotCtr.isChecked():
            align = Qt.AlignBottom | Qt.AlignVCenter
        else:
            align = Qt.AlignBottom | Qt.AlignRight
        self.obj.alignment = align
        self.edited.emit()

    @pyqtSlot(str)
    def on_text_textEdited(self, text):
        if self.obj:
            self.obj.text = text
            self.edited.emit()

    @pyqtSlot(QFont)
    def on_fontFace_currentFontChanged(self, font):
        if self.obj:
            self.obj.family = font.family()
            self.edited.emit()

    @pyqtSlot(str)
    def on_fontSize_editTextChanged(self, text):
        if self.obj:
            self.obj.ptSize = int(float(text)*500)
            self.edited.emit()
