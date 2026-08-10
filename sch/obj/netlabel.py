"""Graphical, semantics-neutral annotations attached to wire geometry."""

from PySide6.QtCore import QPoint, Qt
from lxml import etree

from sch.obj.text import TextBase
from sch.obj.property import PropertyDefinition, PropertyStore


class NetLabelObj(TextBase):
    """A graphical label and property carrier for a local net attachment.

    The label does not assign electrical meaning to its text.  Its current
    attachment is resolved geometrically against the page's normalized wire
    segments; future netlist code may interpret the label properties later.
    """

    STANDARD_PROPERTY_DEFINITIONS = (
        PropertyDefinition(
            "net.name", standard=True, label="Net name", display_order=-20
        ),
    )

    def __init__(self, name="", pos=QPoint(0, 0), alignment=Qt.AlignCenter,
                 family="Helvetica", size=12 * 500, rot=0, visible=True):
        super().__init__(str(name), QPoint(pos), alignment, family, size, rot)
        self._name = str(name)
        self._visible = bool(visible)
        self._proptexts = []
        label_definitions = [definition.copy()
                             for definition in self.STANDARD_PROPERTY_DEFINITIONS]
        label_definitions[0].default_value = self._name
        self._properties = PropertyStore(
            definitions=label_definitions,
            getters={"net.name": lambda: self.name},
            setters={"net.name": self._set_name},
            allow_unknown=True,
        )

    def _set_name(self, value):
        self.name = value

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, value):
        self._name = "" if value is None else str(value)
        self._text = self._name
        self._dirty = True

    @property
    def value(self):
        return self.name

    @property
    def text(self):
        return self.name

    @text.setter
    def text(self, value):
        self.name = value

    @property
    def properties(self):
        return self._properties

    def getPropertyDefinitions(self):
        return self.properties.definitions()

    def getProp(self, name):
        try:
            return self.properties.get(name)
        except KeyError:
            return ""

    def setProp(self, name, value):
        try:
            self.properties.set(name, value)
        except KeyError:
            return

    @property
    def visible(self):
        return self._visible

    @visible.setter
    def visible(self, value):
        self._visible = bool(value)
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

    def children(self):
        return list(self._proptexts)

    def __copy__(self):
        """Copy visual and property state without sharing accessors."""
        clone = NetLabelObj(
            self.name, self.pos, self.alignment, self.family,
            self.ptSize, self.rot, self.visible,
        )
        clone.properties.apply_overrides(self.properties.get_overrides())
        import copy
        clone._proptexts = [copy.copy(prop) for prop in self._proptexts]
        for prop in clone._proptexts:
            prop.parent = clone
        return clone

    def draw(self, painter):
        if self.visible:
            super().draw(painter)
        for proptext in self._proptexts:
            proptext.draw(painter)

    def attached_nets(self, page):
        """Return normalized wire segments touched by this label anchor."""
        from sch.obj.net import NetObj
        return [net for net in page.objects(objType=NetObj)
                if net.touchesPt(self.pos)]

    def is_attached(self, page):
        return bool(self.attached_nets(page))

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
        label = etree.SubElement(
            parent, "netLabel",
            x=str(self.pos.x()),
            y=str(self.pos.y()),
            rot=str(self.rot),
            hAlign=halign,
            vAlign=valign,
            fontFamily=self.family,
            fontSize=str(self.ptSize),
            visible="1" if self.visible else "0",
            name=self.name,
        )
        overrides = self.properties.get_overrides()
        if overrides:
            props = etree.SubElement(label, "props")
            for name, value in overrides.items():
                prop = etree.SubElement(props, "prop", name=name)
                prop.text = value
        for proptext in self._proptexts:
            proptext.toXml(label)

    @staticmethod
    def fromXml(elem):
        hd = {"left": Qt.AlignLeft, "center": Qt.AlignCenter,
              "right": Qt.AlignRight}
        vd = {"top": Qt.AlignTop, "middle": Qt.AlignVCenter,
              "bottom": Qt.AlignBottom}
        alignment = hd[elem.attrib.get("hAlign", "center")] | \
            vd[elem.attrib.get("vAlign", "middle")]
        label = NetLabelObj(
            elem.attrib.get("name", ""),
            QPoint(int(elem.attrib.get("x", "0")),
                   int(elem.attrib.get("y", "0"))),
            alignment,
            elem.attrib.get("fontFamily", "Helvetica"),
            int(elem.attrib.get("fontSize", str(12 * 500))),
            int(elem.attrib.get("rot", "0")),
            elem.attrib.get("visible", "1") == "1",
        )
        props_elem = elem.find("props")
        if props_elem is not None:
            label.properties.apply_overrides({
                child.attrib["name"]: child.text or ""
                for child in props_elem
                if child.tag == "prop" and "name" in child.attrib
            })
        import sch.obj.proptext
        for child in elem:
            if child.tag == "proptext":
                label._proptexts.append(
                    sch.obj.proptext.PropTextObj.fromXml(child, label))
        return label
