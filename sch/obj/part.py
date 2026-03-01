from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPainter, QTransform
import sch.obj.proptext
from lxml import etree
import copy

class PartObj(object):
    def __init__(self, lib, path=None, name=None, pos=QPoint(0, 0), rot=0, mirror=False):
        self._lib = lib
        self._master = None
        self._path = path
        self._name = name
        self.path = None
        self._rot = None
        self._mirror = None
        self._pos = None
        self._tr = None
        self._bb = None
        self.pos = QPoint(pos)
        self.rot = rot
        self.mirror = mirror
        self._masterBbox = None
        self._proptexts = []

    def children(self):
        return self._proptexts

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, new):
        self._pos = new
        self._tr = None
        self._bb = None

    @property
    def rot(self):
        return self._rot

    @rot.setter
    def rot(self, new):
        self._rot = new
        self._tr = None
        self._bb = None

    @property
    def mirror(self):
        return self._mirror

    @mirror.setter
    def mirror(self, new):
        self._mirror = new
        self._tr = None
        self._bb = None

    @property
    def path(self):
        return self._path

    @path.setter
    def path(self, new):
        self._path = new
        self._updateMaster()
        self._resetProps()

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, new):
        self._name = new
        self._updateMaster()

    def _updateMaster(self):
        self._master = self._lib.getSym(self.path, self.name)
        self._updateMasterBbox()
        self._bb = None

    def _updateTransform(self):
        if self._tr is None:
            self._tr = QTransform()
            self._tr.translate(self.pos.x(), self.pos.y())
            self._tr.scale(-1 if self.mirror else 1, 1)
            self._tr.rotate(-self.rot)

    def transform(self):
        self._updateTransform()
        return self._tr

    def _updateMasterBbox(self):
        bb = None
        if self._master:
            for obj in self._master.objects(exclude={sch.obj.proptext.PropTextObj}):
                if bb is not None:
                    bb |= obj.bbox()
                else:
                    bb = obj.bbox()
        self._masterBbox = bb

    def _updateBbox(self):
        self._updateTransform()
        if self._masterBbox is None:
            self._bb = QRect()
            self._mbb = QRect()
            return
        self._bb = QRect(self._tr.map(self._masterBbox.topLeft()),
                         self._tr.map(self._masterBbox.bottomRight())).normalized()

    def _resetProps(self):
        self._proptexts = []
        if self._master:
            for prop in self._master.objects(objType=sch.obj.proptext.PropTextObj):
                c = copy.copy(prop)
                c.doc = self
                self._proptexts.append(c)

    def draw(self, painter: QPainter):
        if self._master is None:
            return
        self._updateTransform()
        painter.save()
        painter.setTransform(self._tr, True)
        for obj in self._master.objects(exclude={sch.obj.proptext.PropTextObj}):
            obj.draw(painter)
        painter.restore()

    def bbox(self):
        if self._bb is None:
            self._updateBbox()
        return self._bb

    def testHit(self, pt: QPoint, radius: int):
        if self._bb is None:
            self._updateBbox()
        for txt in self._proptexts:
            if txt.bbox().contains(self._tr.inverted()[0].map(pt)):
                return True
        return self.bbox().contains(pt)

    def getProp(self, attr):
        return "default"

    def setProp(self, attr, value):
        pass

    def toXml(self, parent):
        part = etree.SubElement(parent, "part",
                         schPath=self.path,
                         partId=self.name,
                         x=str(self.pos.x()),
                         y=str(self.pos.y()),
                         rot=str(self.rot),
                         mirror="1" if self.mirror else "0"
                         )
        for pt in self._proptexts:
            pt.toXml(part)

    @staticmethod
    def fromXml(elem, lib):
        obj = PartObj(lib)
        obj.name = elem.attrib['partId']
        obj.pos = QPoint(int(elem.attrib['x']), int(elem.attrib['y']))
        obj.rot = int(elem.attrib['rot'])
        obj.mirror = (elem.attrib['mirror'] == '1')
        obj.path = elem.attrib['schPath']
        obj._proptexts = []
        for sub in elem:
            if sub.tag == 'proptext':
                obj._proptexts.append(sch.obj.proptext.PropTextObj.fromXml(sub, obj))
        return obj
