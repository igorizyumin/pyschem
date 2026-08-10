from PySide6.QtCore import Qt, QPoint
from lxml import etree
from sch.utils import *
from sch.obj.text import TextBase


class PropertyDisplay(TextBase):
    """A text child that displays a property from its parent object.

    The display owns presentation state only.  Its parent remains the source
    of the displayed value, which lets the same class work for pin-master
    properties, symbol-master defaults, and per-part display copies.
    """

    def __init__(self, parent, name='attr', pos=QPoint(0, 0), alignment=Qt.AlignCenter,
                 family="Helvetica", size=12 * 500, rot=0, vis=True,
                 showName=False, visible=None):
        super().__init__('', pos, alignment, family, size, rot, parent=parent)
        self._name = name
        self._vis = bool(vis if visible is None else visible)
        self._showName = bool(showName)
        self._updText()

    def _updText(self):
        old_text = getattr(self, "_text", None)
        try:
            value = self.value
        except (AttributeError, KeyError):
            value = ""
        value = "" if value is None else str(value)
        self._text = "{}={}".format(self.name, value) if self._showName else value
        if self._text != old_text:
            # TextBase caches its QStaticText representation.  Property
            # values can change without changing the display object, so the
            # cache must be invalidated when the resolved text changes.
            self._dirty = True

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = value
        self._updText()
        self._dirty = True

    @property
    def value(self):
        return self._parent.getProp(self.name)

    @value.setter
    def value(self, value):
        self._parent.setProp(self.name, value)
        self._updText()
        self._dirty = True

    @property
    def family(self):
        return self._family

    @family.setter
    def family(self, value):
        self._family = value
        self._dirty = True

    @property
    def ptSize(self):
        return self._ptSize

    @ptSize.setter
    def ptSize(self, value):
        self._ptSize = value
        self._dirty = True

    @property
    def vis(self):
        return self._vis

    @vis.setter
    def vis(self, value):
        self._vis = bool(value)
        self._dirty = True

    @property
    def visible(self):
        return self.vis

    @visible.setter
    def visible(self, value):
        self.vis = value

    @property
    def parent(self):
        return self._parent

    @parent.setter
    def parent(self, newparent):
        self._parent = newparent
        self._updText()
        self._dirty = True

    @property
    def doc(self):
        """Compatibility alias for older callers that used ``doc``."""
        return self.parent

    @doc.setter
    def doc(self, newparent):
        self.parent = newparent

    @property
    def showName(self):
        return self._showName

    @showName.setter
    def showName(self, value):
        self._showName = bool(value)
        self._updText()
        self._dirty = True

    def draw(self, painter):
        self._updText()
        if self.vis:
            super().draw(painter)

    def testHit(self, pt, radius):
        return self.vis and super().testHit(pt, radius)

    def clone(self, parent):
        """Clone this display while binding it to a new coordinate parent."""
        import copy
        clone = copy.copy(self)
        clone.parent = parent
        return clone

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
        etree.SubElement(
            parent, "proptext",
            x=str(self.pos.x()), y=str(self.pos.y()), rot=str(self.rot),
            hAlign=halign, vAlign=valign,
            fontFamily=self.family, fontSize=str(self.ptSize),
            visible="1" if self.vis else "0",
            showName="1" if self._showName else "0",
            prop=self.name,
        )

    @staticmethod
    def fromXml(elem, parent):
        pos = QPoint(int(elem.attrib['x']), int(elem.attrib['y']))
        ha = elem.attrib['hAlign']
        va = elem.attrib['vAlign']
        hd = {"left": Qt.AlignLeft, "center": Qt.AlignCenter,
              "right": Qt.AlignRight}
        vd = {"top": Qt.AlignTop, "middle": Qt.AlignVCenter,
              "bottom": Qt.AlignBottom}
        alignment = hd[ha] | vd[va]
        return PropertyDisplay(
            parent, elem.attrib['prop'], pos, alignment,
            elem.attrib['fontFamily'], int(elem.attrib['fontSize']),
            int(elem.attrib['rot']), elem.attrib['visible'] == '1',
            elem.attrib['showName'] == '1',
        )


# Keep the old model name as an API and XML compatibility alias.
PropTextObj = PropertyDisplay
