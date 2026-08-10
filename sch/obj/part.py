from PySide6.QtCore import QPoint, QRect
from PySide6.QtGui import QPainter, QTransform
from typing import List
import sch.obj.proptext
import sch.obj.property
import sch.obj.pin
from lxml import etree
import copy

class PartObj(object):
    """
    Represents an instantiated component on a schematic page.
    
    PartObj uses PartPropertyStore to manage properties, combining
    template definitions from the master symbol with instance-specific overrides.
    """
    
    def __init__(self, lib, path=None, name=None, pos=QPoint(0, 0), rot=0, mirror=False):
        """
        Initialize a part instance.
        
        Args:
            lib: PartLibrary instance for symbol lookup
            path: Path to symbol file (relative to library paths)
            name: Name of symbol within the file
            pos: Position on page
            rot: Rotation (0, 90, 180, 270 degrees)
            mirror: Horizontal flip flag
        """
        self._lib = lib
        self._master = None
        self._path = path
        self._name = name
        self._masterBbox = None
        # Preserve the constructor's library path.  Clearing it here makes
        # newly-created parts serialize with a null ``schPath`` and prevents
        # valid part instances from round-tripping.
        self.path = path
        self._rot = None
        self._mirror = None
        self._pos = None
        self._tr = None
        self._bb = None
        self.pos = QPoint(pos)
        self.rot = rot
        self.mirror = mirror
        self._proptexts = []
        self._properties: sch.obj.property.PartPropertyStore = None
        self._doc = None

    def children(self) -> List[sch.obj.proptext.PropTextObj]:
        """Get all property text objects associated with this part."""
        return self._proptexts

    @property
    def pos(self) -> QPoint:
        return self._pos

    @pos.setter
    def pos(self, new):
        self._pos = new
        self._tr = None
        self._bb = None

    @property
    def rot(self) -> int:
        return self._rot

    @rot.setter
    def rot(self, new):
        self._rot = new
        self._tr = None
        self._bb = None

    @property
    def mirror(self) -> bool:
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

    @property
    def master(self):
        """Get the master symbol this part is based on."""
        return self._master

    @property
    def doc(self):
        return self._doc

    @doc.setter
    def doc(self, value):
        self._doc = value

    def pin_positions(self):
        """Return ``(pin, page_position)`` pairs for this instance."""
        if self._master is None:
            return []
        transform = self.transform()
        return [(pin, transform.map(pin.pos))
                for pin in self._master.objects(objType=sch.obj.pin.PinObj)]

    def pins(self):
        if self._master is None:
            return []
        return list(self._master.objects(objType=sch.obj.pin.PinObj))

    def pinPositions(self):
        """Compatibility alias for callers using the existing Qt-style API."""
        return self.pin_positions()

    def _pinConnected(self, pin, position):
        if self._doc is None:
            return False
        return pin.is_connected(self._doc, position, owner=self)

    @property
    def properties(self) -> sch.obj.property.PartPropertyStore:
        """
        Get the property store for this part.
        
        Initializes from master templates on first access.
        """
        if self._properties is None:
            self._initProperties()
        return self._properties

    def _initProperties(self):
        """Initialize properties from master symbol templates."""
        templates = self._master.property_templates if self._master is not None else []
        self._properties = sch.obj.property.PartPropertyStore(templates)
        # Apply parsed values after the master is known.  The store keeps
        # unknown values so a document can round-trip fields introduced by a
        # newer library or project without silently losing them.
        if hasattr(self, '_overrides_to_apply'):
            self._properties.apply_overrides(self._overrides_to_apply)
            del self._overrides_to_apply

    def _updateMaster(self):
        self._master = self._lib.getSym(self.path, self.name)
        self._updateMasterBbox()
        self._bb = None
        # Reset properties when master changes
        self._properties = None

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
        """Reset property text objects from master symbol."""
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
            if isinstance(obj, sch.obj.pin.PinObj):
                position = self.transform().map(obj.pos)
                obj.draw(painter, highlight=not self._pinConnected(obj, position))
            else:
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

    def getProp(self, name: str) -> str:
        """
        Get a property value.
        
        Args:
            name: The property name
            
        Returns:
            The property value (override or template default)
        """
        return self.properties.get(name)

    def setProp(self, name: str, value: str) -> None:
        """
        Set a property override.
        
        Args:
            name: The property name
            value: The new value
        """
        self.properties.set(name, value)

    @property
    def reference(self) -> str:
        """The annotation/reference value, such as ``R?`` or ``R12``."""
        return self.properties.get("part.reference")

    @reference.setter
    def reference(self, value: str) -> None:
        self.properties.set("part.reference", value)

    @property
    def reference_prefix(self) -> str:
        """Effective master prefix, optionally overridden on this part."""
        return self.properties.get("part.reference_prefix")

    @reference_prefix.setter
    def reference_prefix(self, value: str) -> None:
        self.properties.set("part.reference_prefix", value)

    def getPropertyDefinitions(self):
        """Return standard and master-defined properties for this part."""
        definitions = self.properties.definitions()
        known = {definition.name for definition in definitions}
        for name in self.properties.names():
            if name not in known:
                definitions.append(self.properties.get_property(name).definition)
        return definitions

    def getPropertyTemplates(self) -> List[sch.obj.property.PropertyTemplate]:
        """Get all property templates from the master symbol."""
        if self._master is not None:
            return self._master.property_templates
        return []

    def resetProperty(self, name: str) -> None:
        """Reset a property to its template default."""
        self.properties.unset(name)

    def resetAllProperties(self) -> None:
        """Reset all properties to template defaults."""
        self.properties.reset_all()

    def hasUnsavedChanges(self) -> bool:
        """Check if any properties have unsaved overrides."""
        return len(self.properties.get_overrides()) > 0

    def toXml(self, parent):
        """
        Serialize part to XML element.
        
        Args:
            parent: Parent XML element to append to
        """
        part = etree.SubElement(parent, "part",
                         schPath=self.path,
                         partId=self.name,
                         x=str(self.pos.x()),
                         y=str(self.pos.y()),
                         rot=str(self.rot),
                         mirror="1" if self.mirror else "0"
                         )
        
        # Write property overrides only (not defaults)
        overrides = self.properties.get_overrides()
        if overrides:
            props_elem = etree.SubElement(part, "props")
            for name, value in overrides.items():
                pp = etree.SubElement(props_elem, "prop", name=name)
                pp.text = value
        
        for pt in self._proptexts:
            pt.toXml(part)

    @staticmethod
    def fromXml(elem, lib):
        """
        Create PartObj from XML element.
        
        Args:
            elem: XML element containing part data
            lib: PartLibrary instance
            
        Returns:
            PartObj instance
        """
        obj = PartObj(lib)
        obj._overrides_to_apply = {}
        obj.name = elem.attrib['partId']
        obj.pos = QPoint(int(elem.attrib['x']), int(elem.attrib['y']))
        obj.rot = int(elem.attrib['rot'])
        obj.mirror = (elem.attrib['mirror'] == '1')
        obj.path = elem.attrib['schPath']
        obj._proptexts = []
        
        # Parse property overrides
        props_elem = elem.find("props")
        if props_elem is not None:
            for prop in props_elem:
                if prop.tag == 'prop' and 'name' in prop.attrib:
                    # Store values until the referenced master is available.
                    obj._overrides_to_apply[prop.attrib['name']] = prop.text or ''
        
        for sub in elem:
            if sub.tag == 'proptext':
                obj._proptexts.append(sch.obj.proptext.PropTextObj.fromXml(sub, obj))
        
        return obj
