import copy
from typing import List
from uuid import UUID, uuid4
from PySide6.QtCore import *
from PySide6.QtGui import QUndoStack, QUndoCommand
from PySide6.QtWidgets import *
from lxml import etree
import sch.obj.line
import sch.obj.net
import sch.obj.text
import sch.obj.part
import sch.obj.proptext
import sch.obj.property
import sch.obj.sheetref
import sch.obj.port

class MasterDocument(QObject):
    # indicates document structure has changed (NOT sub-documents; those have their own signals)
    sigChanged = Signal()
    sigCleanChanged = Signal()

    def __init__(self, lib):
        QObject.__init__(self)
        self._uuid = uuid4()
        self._symbols = []
        self._pages = []
        self.lib = lib
        self.fileName = None
        self.symProps = {}

    def name(self):
        if self.fileName is not None:
            fi = QFileInfo(self.fileName)
            return fi.fileName()
        else:
            return "untitled.xsch"

    @property
    def symbols(self):
        return self._symbols

    @property
    def pages(self):
        return self._pages

    @staticmethod
    def _uniqueName(names, prefix):
        # find unique name
        idx = 1
        while prefix+str(idx) in names:
            idx += 1
        return prefix + str(idx)

    def appendNewSymbol(self):
        symNames = [s.name for s in self._symbols]
        newp = SymbolPage(self)
        newp.sigChanged.connect(self.sigCleanChanged)
        newp.name = self._uniqueName(symNames, "symbol")
        self._symbols.append(newp)
        self.sigChanged.emit()

    def appendNewPage(self):
        pageNames = [p.name for p in self._pages]
        newp = DocPage(self)
        newp.sigChanged.connect(self.sigCleanChanged)
        newp.name = self._uniqueName(pageNames, "Page")
        self._pages.append(newp)
        self.sigChanged.emit()

    def isModified(self):
        for d in self._symbols+self._pages:
            if d.isModified():
                return True
        return False

    def loadFromFile(self, file=None):
        if file is None:
            file = self.fileName
        with open("xml/schschema.rng", "rb") as f:
            rngdoc = etree.parse(f)
        rng = etree.RelaxNG(rngdoc)
        with open(file, "rb") as f:
            doc = etree.parse(f)
        rng.assertValid(doc)
        root = doc.getroot()
        for child in root:
            if child.tag == "props":
                uuid = child.find("uuid")
                self._uuid = UUID(uuid.text)
            elif child.tag == "symbol":
                for obj in child:
                    if obj.tag == "symPart":
                        newp = SymbolPage(self)
                        newp.fromXml(obj)
                        newp.sigChanged.connect(self.sigCleanChanged)
                        self._symbols.append(newp)
                    elif obj.tag == "props":
                        for pr in obj:
                            if pr.tag == 'prop':
                                self.symProps[pr.attrib['name']] = pr.text
            elif child.tag == "pages":
                for pg in child:
                    newp = DocPage(self)
                    newp.fromXml(pg)
                    newp.sigChanged.connect(self.sigCleanChanged)
                    self._pages.append(newp)
        self.fileName = file
        self.sigChanged.emit()

    def saveToFile(self, file=None):
        if file is None:
            file = self.fileName
        root = etree.Element("xSchematic")
        self.toXml(root)
        with open(file, "wb") as h:
            h.write(etree.tostring(root, pretty_print=True))
        for d in self._symbols+self._pages:
            d.undoStack.setClean()
        self.fileName = file

    def toXml(self, parentNode):
        props = etree.SubElement(parentNode, "props")
        uuid = etree.SubElement(props, "uuid")
        uuid.text = str(self._uuid)
        if self._symbols:
            sym = etree.SubElement(parentNode, "symbol")
            symProps = etree.SubElement(sym, "props")
            for s in self._symbols:
                s.toXml(sym)
        if self._pages:
            pages = etree.SubElement(parentNode, "pages")
            for p in self._pages:
                p.toXml(pages)


class AbstractPage(QObject):
    sigChanged = Signal()

    def __init__(self, parent: MasterDocument):
        super().__init__()
        self._objs = set()
        self._parent = parent
        self.undoStack = QUndoStack()
        self._name = "untitled"

    @property
    def name(self):
        return self._name

    @name.setter
    def name(self, n):
        self._name = n
        self.sigChanged.emit()

    @property
    def parentDoc(self):
        return self._parent

    def isModified(self):
        return not self.undoStack.isClean()

    def doCommand(self, cmd):
        cmd.doc = self
        self.undoStack.push(cmd)
        self.sigChanged.emit()

    def objects(self, objType=None, exclude=None):
        if not objType and not exclude:
            return set(self._objs)
        if exclude is None:
            exclude = ()
        if objType:
            return {obj for obj in self._objs if type(obj) is objType and not (type(obj) in exclude)}
        else:
            return {obj for obj in self._objs if not (type(obj) in exclude)}

    def hasObject(self, obj):
        return obj in self._objs

    def findObjsInRect(self, rect: QRect, objType=None):
        return {obj for obj in self.objects(objType) if rect.intersects(obj.bbox())}

    def findObjsNear(self, pt: QPoint, dist=1, objType=None):
        hitRect = QRect(pt.x()-dist/2, pt.y()-dist/2, dist, dist)
        return {obj for obj in self.findObjsInRect(hitRect, objType) if obj.testHit(pt, dist)}

    def addObj(self, obj):
        self._objs.add(obj)
        self.sigChanged.emit()

    def removeObj(self, obj):
        self._objs.remove(obj)
        self.sigChanged.emit()

    @Slot()
    def undo(self):
        self.undoStack.undo()
        self.sigChanged.emit()

    @Slot()
    def redo(self):
        self.undoStack.redo()
        self.sigChanged.emit()

    def fromXml(self, pageNode):
        raise NotImplementedError()

    def toXml(self, parentNode):
        raise NotImplementedError()


class DocPage(AbstractPage):
    def __init__(self, parent: MasterDocument):
        super().__init__(parent)
        self._name = "Page1"
        self._sheet_refs: List[sch.obj.sheetref.SheetRefObj] = []

    def sheetReferences(self) -> List[sch.obj.sheetref.SheetRefObj]:
        """Get all sheet references on this page."""
        return list(self._sheet_refs)

    def addSheetReference(self, ref: sch.obj.sheetref.SheetRefObj) -> None:
        """
        Add a sheet reference to this page.
        
        Args:
            ref: SheetRefObj to add
        """
        self._sheet_refs.append(ref)
        self._objs.add(ref)
        ref.setDoc(self._parent)

    def removeSheetReference(self, ref: sch.obj.sheetref.SheetRefObj) -> None:
        """
        Remove a sheet reference from this page.
        
        Args:
            ref: SheetRefObj to remove
        """
        if ref in self._sheet_refs:
            self._sheet_refs.remove(ref)
        self._objs.discard(ref)

    def fromXml(self, pageNode):
        self._name = pageNode.attrib["name"]
        objs = pageNode.find("objects")
        for obj in objs:
            if obj.tag == "line":
                self._objs.add(sch.obj.line.LineObj.fromXml(obj))
            elif obj.tag == "net":
                self._objs.add(sch.obj.net.NetObj.fromXml(obj))
            elif obj.tag == "text":
                self._objs.add(sch.obj.text.TextObj.fromXml(obj))
            elif obj.tag == "part":
                part = sch.obj.part.PartObj.fromXml(obj, self._parent.lib)
                self._objs.add(part)
                self._objs |= set(part.children())
            elif obj.tag == "sheetRef":
                sheet_ref = sch.obj.sheetref.SheetRefObj.fromXml(obj, self._parent)
                self.addSheetReference(sheet_ref)

    def toXml(self, parentNode):
        page = etree.SubElement(parentNode, "page", name=self.name)
        objs = etree.SubElement(page, "objects")
        for obj in self.objects(exclude={sch.obj.proptext.PropTextObj}):
            obj.toXml(objs)


class SymbolPage(AbstractPage):
    """
    Represents a symbol master definition.
    
    Contains property templates that define the properties available
    when parts of this symbol type are instantiated on schematics.
    """
    
    def __init__(self, parent: MasterDocument):
        super().__init__(parent)
        self._name = "symbol"
        self._property_templates: List[sch.obj.property.PropertyTemplate] = []

    @property
    def property_templates(self) -> List[sch.obj.property.PropertyTemplate]:
        """Get all property templates defined for this symbol."""
        return list(self._property_templates)

    def add_property_template(self, template: sch.obj.property.PropertyTemplate) -> None:
        """Add a property template to this symbol."""
        self._property_templates.append(template)

    def get_property_template(self, name: str) -> sch.obj.property.PropertyTemplate:
        """
        Get a property template by name.
        
        Args:
            name: The property name
            
        Returns:
            The PropertyTemplate or None if not found
        """
        for template in self._property_templates:
            if template.name == name:
                return template
        return None

    def fromXml(self, symNode):
        """
        Parse symbol from XML element.
        
        Args:
            symNode: XML element containing symPart data
        """
        self._name = symNode.attrib["name"]
        
        # Parse property templates
        self._property_templates = []
        props_elem = symNode.find("props")
        if props_elem is not None:
            for prop in props_elem:
                if prop.tag == 'prop':
                    template = sch.obj.property.PropertyTemplate(
                        name=prop.attrib.get('name', ''),
                        default_value=prop.text or '',
                        editable=(prop.attrib.get('editable', '1') == '1'),
                        visible=(prop.attrib.get('visible', '1') == '1'),
                        required=(prop.attrib.get('required', '0') == '1'),
                        property_type=prop.attrib.get('type', 'text'),
                        enum_values=[],  # Will need to parse from attribute if present
                        display_order=int(prop.attrib.get('order', '0'))
                    )
                    self._property_templates.append(template)
        
        # Parse objects
        objs = symNode.find("objects")
        if objs is not None:
            for obj in objs:
                if obj.tag == "line":
                    self._objs.add(sch.obj.line.LineObj.fromXml(obj))
                elif obj.tag == 'proptext':
                    self._objs.add(sch.obj.proptext.PropTextObj.fromXml(obj, self))
                elif obj.tag == 'text':
                    self._objs.add(sch.obj.text.TextObj.fromXml(obj))

    def toXml(self, parentNode):
        """
        Serialize symbol to XML element.
        
        Args:
            parentNode: Parent XML element to append to
        """
        page = etree.SubElement(parentNode, "symPart", name=self.name)
        
        # Write property templates
        props = etree.SubElement(page, "props")
        for template in self._property_templates:
            pp = etree.SubElement(props, "prop", name=template.name)
            pp.text = template.default_value
            if template.editable:
                pp.set('editable', '1')
            else:
                pp.set('editable', '0')
            if template.visible:
                pp.set('visible', '1')
            else:
                pp.set('visible', '0')
            if template.required:
                pp.set('required', '1')
            else:
                pp.set('required', '0')
            if template.property_type != 'text':
                pp.set('type', template.property_type)
            if template.display_order != 0:
                pp.set('order', str(template.display_order))
        
        # Write objects
        objs = etree.SubElement(page, "objects")
        for obj in self._objs:
            obj.toXml(objs)


# This should not be necessary but PySide is a buggy POS and QUndoCommand fails to
# take ownership of children, so they get deleted on the Python side and everything
# breaks.
class BaseUndoCmd(QUndoCommand):
    def __init__(self, name='base command', parent=None, doc=None):
        super().__init__(name, parent)
        if parent is not None:
            parent._children.append(self)
        # Python's copy of the children so they do not get gc'ed.
        self._doc = doc
        self._children = []

    @property
    def doc(self):
        return self._doc
    
    @doc.setter
    def doc(self, doc):
        self._doc = doc

class ObjAddCmd(BaseUndoCmd):
    def __init__(self, obj, doc=None, parent=None):
        print(parent)
        super().__init__('add {}'.format(type(obj).__name__), parent=parent, doc=doc)
        self._obj = obj

    def redo(self):
        print("redo add obj")
        self.doc.addObj(self._obj)

    def undo(self):
        print("undo add obj")
        self.doc.removeObj(self._obj)


class ObjDelCmd(BaseUndoCmd):
    def __init__(self, obj, doc=None, parent=None):
        print(parent)
        super().__init__('delete {}'.format(type(obj).__name__), parent=parent, doc=doc)
        self._obj = obj
        
    def redo(self):
        print("redo del object")
        self.doc.removeObj(self._obj)

    def undo(self):
        self.doc.addObj(self._obj)


class ObjChangeCmd(BaseUndoCmd):
    @staticmethod
    def _Memento(obj, deep=False):
        state = (copy.copy, copy.deepcopy)[bool(deep)](obj.__dict__)

        def Restore():
            obj.__dict__.clear()
            obj.__dict__.update(state)
        return Restore

    # this should be called with the unmodified object, which is then changed
    # during the transaction.  The command should be submitted when the object
    # is in its final state.
    def __init__(self, obj, doc=None, parent=None):
        super().__init__("change command", parent, doc=doc)
        self._obj = obj
        self._restore = ObjChangeCmd._Memento(obj)
        self._undone = False

    def _restoreState(self):
        # swap memento with object state
        r = self._restore
        self._restore = ObjChangeCmd._Memento(self._obj)
        r()
        self._undone = not self._undone

    def redo(self):
        if self._undone:
            self._restoreState()

    def undo(self):
        if not self._undone:
            self._restoreState()
