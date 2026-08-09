import copy
from pathlib import Path
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

    def __init__(self, lib, project_root=None, document_cache=None):
        QObject.__init__(self)
        self._uuid = uuid4()
        self._symbols = []
        self._pages = []
        self.lib = lib
        self._project_root = Path(project_root).resolve() if project_root else None
        self._project_documents = document_cache if document_cache is not None else {}
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

    @property
    def projectRoot(self):
        """Root directory containing every document in this project."""
        if self._project_root is not None:
            return self._project_root
        if self.fileName is not None:
            return Path(self.fileName).resolve().parent
        return None

    def loadProjectDocument(self, file_path):
        """Load and cache a child document from this project's directory."""
        canonical = Path(file_path).resolve()
        cache = self._project_documents
        if str(canonical) not in cache:
            child = MasterDocument(self.lib, project_root=self.projectRoot,
                                   document_cache=cache)
            child.loadFromFile(str(canonical))
            cache[str(canonical)] = child
        return cache[str(canonical)]

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
        if file is None:
            raise ValueError("No document file was supplied")

        schema_file = Path(__file__).resolve().parent.parent / "xml" / "schschema.rng"
        with schema_file.open("rb") as f:
            rngdoc = etree.parse(f)
        rng = etree.RelaxNG(rngdoc)
        with open(file, "rb") as f:
            doc = etree.parse(f)
        rng.assertValid(doc)
        # Parse into detached collections first.  Validation above protects
        # against schema-invalid input, while this second boundary protects
        # an already-open document from partial replacement when a value is
        # malformed or an object parser raises.
        new_symbols = []
        new_pages = []
        new_sym_props = {}
        new_uuid = self._uuid
        root = doc.getroot()
        for child in root:
            if child.tag == "props":
                uuid = child.find("uuid")
                new_uuid = UUID(uuid.text)
            elif child.tag == "symbol":
                for obj in child:
                    if obj.tag == "symPart":
                        newp = SymbolPage(self)
                        newp.fromXml(obj)
                        newp.sigChanged.connect(self.sigCleanChanged)
                        new_symbols.append(newp)
                    elif obj.tag == "props":
                        for pr in obj:
                            if pr.tag == 'prop':
                                new_sym_props[pr.attrib['name']] = pr.text
            elif child.tag == "pages":
                for pg in child:
                    newp = DocPage(self)
                    newp.fromXml(pg)
                    newp.sigChanged.connect(self.sigCleanChanged)
                    new_pages.append(newp)
        self._uuid = new_uuid
        self._symbols = new_symbols
        self._pages = new_pages
        self.symProps = new_sym_props
        self.fileName = file
        if self._project_root is None:
            self._project_root = Path(file).resolve().parent
        self._project_documents[str(Path(file).resolve())] = self
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
        if self._project_root is None:
            self._project_root = Path(file).resolve().parent

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
        half_dist = dist // 2
        hitRect = QRect(pt.x()-half_dist, pt.y()-half_dist, dist, dist)
        return {obj for obj in self.findObjsInRect(hitRect, objType) if obj.testHit(pt, dist)}

    def addObj(self, obj):
        self._objs.add(obj)
        self.sigChanged.emit()

    def removeObj(self, obj):
        self._objs.remove(obj)
        self.sigChanged.emit()

    def replaceObjects(self, remove, add, objType=None):
        """Atomically replace objects and emit one document-change signal.

        When ``objType`` is supplied, the operation replaces the complete
        object graph of that exact type.  This supports commands whose
        snapshots contain newly-created instances rather than the instances
        currently held by the document.
        """
        remove = list(remove)
        add = list(add)
        if objType is None:
            for obj in list(self._objs):
                if any(obj is target for target in remove):
                    self._objs.remove(obj)
        else:
            for obj in list(self._objs):
                if type(obj) is objType:
                    self._objs.remove(obj)
        for obj in add:
            self._objs.add(obj)
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

    def addObj(self, obj):
        if isinstance(obj, sch.obj.sheetref.SheetRefObj):
            if obj not in self._sheet_refs:
                self.addSheetReference(obj)
            self.sigChanged.emit()
            return
        super().addObj(obj)

    def removeSheetReference(self, ref: sch.obj.sheetref.SheetRefObj) -> None:
        """
        Remove a sheet reference from this page.
        
        Args:
            ref: SheetRefObj to remove
        """
        if ref in self._sheet_refs:
            self._sheet_refs.remove(ref)
        self._objs.discard(ref)

    def removeObj(self, obj):
        if isinstance(obj, sch.obj.sheetref.SheetRefObj):
            self.removeSheetReference(obj)
            self.sigChanged.emit()
            return
        super().removeObj(obj)

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
        # Property inspectors mutate a PartPropertyStore nested under a
        # PropTextObj's parent.  A shallow object snapshot therefore misses
        # those edits.  Keep the small, serializable override map alongside
        # the regular object state so inspector changes undo reliably.
        property_parent = state.get('_parent')
        property_overrides = None
        if property_parent is not None and hasattr(property_parent, 'properties'):
            try:
                property_overrides = property_parent.properties.get_overrides()
            except (AttributeError, KeyError):
                property_overrides = None

        def Restore():
            obj.__dict__.clear()
            obj.__dict__.update(state)
            if property_overrides is not None:
                store = property_parent.properties
                store.reset_all()
                for name, value in property_overrides.items():
                    store.set(name, value)
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
