from PySide6.QtCore import Qt, QPoint
from lxml import etree
from sch.utils import *
import sch.obj.text


class PropTextObj(sch.obj.text.TextBase):
    def __init__(self, parent, name='attr', pos=QPoint(0, 0), alignment=Qt.AlignCenter,
                 family="Helvetica", size=12*500, rot=0, vis=True, showName=False):
        super().__init__('', pos, alignment, family, size, rot, parent=parent)
        self._name = name
        self._vis = vis
        self._showName = showName
        self._updText()

    def _updText(self):
        if self._showName:
            self._text = "{}={}".format(self.name, self.value)
        else:
            self._text = self.value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, v):
        self._name = v
        self._updText()
        self._dirty = True

    @property
    def value(self):
        return self._parent.getProp(self.name)

    @value.setter
    def value(self, v):
        self._parent.setProp(self.name, v)
        self._updText()
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

    @property
    def vis(self):
        return self._vis

    @vis.setter
    def vis(self, v):
        self._vis = v
        self._dirty = True

    @property
    def parent(self):
        return self._doc

    @parent.setter
    def parent(self, newparent):
        self._parent = newparent
        self._updText()
        self._dirty = True

    @property
    def showName(self):
        return self._showName

    @showName.setter
    def showName(self, v):
        self._showName = v
        self._updText()
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
        t = etree.SubElement(parent, "proptext",
                             x=str(self.pos.x()),
                             y=str(self.pos.y()),
                             rot=str(self.rot),
                             hAlign=halign,
                             vAlign=valign,
                             fontFamily=self.family,
                             fontSize=str(self.ptSize),
                             visible="1" if self._vis else "0",
                             showName="1" if self._showName else "0",
                             prop=self.name)

    @staticmethod
    def fromXml(elem, parent):
        pos = QPoint(int(elem.attrib['x']), int(elem.attrib['y']))
        ha = elem.attrib['hAlign']
        va = elem.attrib['vAlign']
        hd = {"left": Qt.AlignLeft, "center": Qt.AlignCenter, "right": Qt.AlignRight}
        vd = {"top": Qt.AlignTop, "middle": Qt.AlignVCenter, "bottom": Qt.AlignBottom}
        alignment = hd[ha] | vd[va]
        rot = int(elem.attrib['rot'])
        ff = elem.attrib['fontFamily']
        fs = int(elem.attrib['fontSize'])
        name = elem.attrib['prop']
        vis = elem.attrib['visible'] == '1'
        namevis = elem.attrib['showName'] == '1'
        return PropTextObj(parent, name, pos, alignment, ff, fs, rot, vis, namevis)


