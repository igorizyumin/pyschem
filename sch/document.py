import copy
from uuid import UUID, uuid4

from PyQt5.QtCore import *
from PyQt5.QtWidgets import QUndoStack, QUndoCommand
from lxml import etree

import sch.obj.line


class MasterDocument(QObject):
    # indicates document structure has changed (NOT sub-documents; those have their own signals)
    sigChanged = pyqtSignal()
    sigCleanChanged = pyqtSignal()

    def __init__(self):
        QObject.__init__(self)
        self._uuid = uuid4()
        self._symbols = []
        self._pages = []
        self.fileName = None

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
    sigChanged = pyqtSignal()

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

    def objects(self):
        return list(self._objs)

    def hasObject(self, obj):
        return obj in self._objs

    def findObjsInRect(self, rect: QRect):
        out = []
        for obj in self._objs:
            if rect.intersects(obj.bbox()):
                out.append(obj)
        return out

    def findObjsNear(self, pt: QPoint, dist=1):
        hitRect = QRect(pt.x()-dist/2, pt.y()-dist/2, dist, dist)
        inRect = self.findObjsInRect(hitRect)
        out = []
        for obj in inRect:
            if obj.testHit(pt, dist):
                out.append(obj)
        return out

    def addObj(self, obj):
        self._objs.add(obj)
        self.sigChanged.emit()

    def removeObj(self, obj):
        self._objs.remove(obj)
        self.sigChanged.emit()

    @pyqtSlot()
    def undo(self):
        self.undoStack.undo()
        self.sigChanged.emit()

    @pyqtSlot()
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

    def fromXml(self, pageNode):
        self._name = pageNode.attrib["name"]
        objs = pageNode.find("objects")
        for obj in objs:
            if obj.tag == "line":
                self._objs.add(sch.obj.line.LineObj.fromXml(obj))

    def toXml(self, parentNode):
        page = etree.SubElement(parentNode, "page", name=self.name)
        objs = etree.SubElement(page, "objects")
        for obj in self._objs:
            obj.toXml(objs)


class SymbolPage(AbstractPage):
    def __init__(self, parent: MasterDocument):
        super().__init__(parent)
        self._name = "symbol"

    def fromXml(self, symNode):
        self._name = symNode.attrib["name"]
        objs = symNode.find("objects")
        for obj in objs:
            if obj.tag == "line":
                self._objs.add(sch.obj.line.LineObj.fromXml(obj))

    def toXml(self, parentNode):
        page = etree.SubElement(parentNode, "symPart", name=self.name)
        objs = etree.SubElement(page, "objects")
        for obj in self._objs:
            obj.toXml(objs)


class ObjAddCmd(QUndoCommand):
    def __init__(self, obj):
        super().__init__()
        self._doc = None
        self._obj = obj
        self.setText('add {}'.format(type(obj).__name__))

    @property
    def doc(self):
        return self._doc

    @doc.setter
    def doc(self, doc):
        self._doc = doc

    def redo(self):
        self._doc.addObj(self._obj)

    def undo(self):
        self._doc.removeObj(self._obj)


class ObjChangeCmd(QUndoCommand):
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
    def __init__(self, obj):
        super().__init__()
        self._doc = None
        self._obj = obj
        self._restore = ObjChangeCmd._Memento(obj)
        self._undone = False

    @property
    def doc(self):
        return self._doc

    @doc.setter
    def doc(self, doc):
        self._doc = doc

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
