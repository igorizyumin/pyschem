from PyQt5.QtCore import *
from PyQt5.QtGui import QPainter, QPen, QTransform
from PyQt5.QtWidgets import QWidget, QListWidgetItem
import sch.document
import sch.controller
from sch.uic.ui_partinspector import Ui_PartInspector
from sch.utils import LayerType, Layer, Geom
from lxml import etree
from sch.view import Event
import copy


class PartObj(object):
    def __init__(self, lib, path=None, name=None, pos=QPoint(0, 0), rot=0, mirror=False):
        self._lib = lib
        self._master = None
        self._path = path
        self._name = name
        self.path = None
        self.rot = rot
        self.mirror = mirror
        self._pos = None
        self._tr = None
        self._bb = None
        self.pos = QPoint(pos)

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, new):
        self._pos = new
        self._tr = None
        self._bb = None

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, new):
        self._path = new
        self._updateMaster()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new):
        self._name = new
        self._updateMaster()

    def _updateMaster(self):
        self._master = self._lib.getSym(self.path, self.name)
        self._bb = None

    def _updateTransform(self):
        if self._tr is None:
            self._tr = QTransform()
            self._tr.translate(self.pos.x(), self.pos.y())
            self._tr.rotate(-self.rot)

    def _updateBbox(self):
        self._updateTransform()
        if self._master is None:
            self._bb = QRect()
            return
        bb = None
        for obj in self._master.objects():
            if bb is not None:
                bb |= obj.bbox()
            else:
                bb = obj.bbox()
        if bb:
            self._bb = QRect(self._tr.map(bb.topLeft()), self._tr.map(bb.bottomRight())).normalized()
        else:
            self._bb = QRect()

    def draw(self, painter: QPainter):
        if self._master is None:
            return
        self._updateTransform()
        painter.save()
        painter.setTransform(self._tr, True)
        for obj in self._master.objects():
            obj.draw(painter)
        painter.restore()

    def bbox(self):
        if self._bb is None:
            self._updateBbox()
        return self._bb

    def testHit(self, pt: QPoint, radius: int):
        return self.bbox().contains(pt)

    def toXml(self, parent):
        etree.SubElement(parent, "part",
                         schPath=self.path,
                         partId=self.name,
                         x=str(self.pos.x()),
                         y=str(self.pos.y()),
                         rot=str(self.rot),
                         mirror="1" if self.mirror else "0"
                         )

    @staticmethod
    def fromXml(elem, lib):
        obj = PartObj(lib)
        obj.path = elem.attrib['schPath']
        obj.name = elem.attrib['partId']
        obj.pos = QPoint(int(elem.attrib['x']), int(elem.attrib['y']))
        obj.rot = int(elem.attrib['rot'])
        obj.mirror = (elem.attrib['mirror'] == '1')
        return obj


class PartTool(QObject):
    sigUpdate = pyqtSignal()

    def __init__(self, ctrl):
        QObject.__init__(self)
        self._ctrl = ctrl
        self._pos = QPoint()
        self._obj = PartObj(lib=self._ctrl.lib)
        self._inspector = PartInspector(self._ctrl)
        self._inspector.masterChanged.connect(self.onMasterChanged)

    def finish(self):
        self._obj = None
        self.sigUpdate.emit()

    @property
    def inspector(self):
        return self._inspector

    def draw(self, painter):
        if self._obj:
            self._obj.draw(painter)

    def handleEvent(self, e):
        if e.evType == sch.controller.Event.Type.MouseMoved:
            self._obj.pos = self._ctrl.snapPt(e.pos) - (self._obj.bbox().topLeft() - self._obj.pos)
            self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.MouseReleased:
            cmd = sch.document.ObjAddCmd(self._obj)
            self._ctrl.doc.doCommand(cmd)
            self._obj = copy.copy(self._obj)
            self._inspector.obj = self._obj
            e.handled = True

    @pyqtSlot(str, str)
    def onMasterChanged(self, path, sym):
        self._obj.name = sym
        self._obj.path = path


class PartInspector(QWidget):
    edited = pyqtSignal()
    masterChanged = pyqtSignal(str, str)

    def __init__(self, ctrl, obj=None, parent=None):
        super().__init__(parent)
        self.ui = Ui_PartInspector()
        self.ui.setupUi(self)
        self._ctrl = ctrl
        self._obj = None
        self.obj = obj
        self._populateList()

    @property
    def obj(self):
        return self._obj

    @obj.setter
    def obj(self, new):
        self._obj = new
        self._loadProperties(new)

    def _populateList(self):
        for i in self._ctrl.lib.getSymList():
            for j in i[1]:
                item = QListWidgetItem()
                item.setText("{} : {}".format(i[0], j))
                item.setData(Qt.UserRole, (i[0], j))
                self.ui.masterList.addItem(item)

    def _loadProperties(self, obj: PartObj):
        pass

    @pyqtSlot(QListWidgetItem, QListWidgetItem)
    def on_masterList_currentItemChanged(self, curr, prev):
        d = curr.data(Qt.UserRole)
        self.masterChanged.emit(d[0], d[1])
