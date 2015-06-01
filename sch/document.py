from PyQt5.QtCore import *
from PyQt5.QtWidgets import QUndoStack, QUndoCommand
import copy
from lxml import etree
from uuid import uuid4


class Document(QObject):
    sigChanged = pyqtSignal()
    sigCleanChanged = pyqtSignal('bool')
    sigCanUndoChanged = pyqtSignal('bool')
    sigCanRedoChanged = pyqtSignal('bool')

    def __init__(self):
        QObject.__init__(self)
        self._objs = set()
        self._undoStack = QUndoStack()
        self._undoStack.canUndoChanged.connect(self.sigCanUndoChanged)
        self._undoStack.canRedoChanged.connect(self.sigCanRedoChanged)
        self._undoStack.cleanChanged.connect(self.sigCleanChanged)
        self._uuid = uuid4()

    def isModified(self):
        return not self._undoStack.isClean()

    def doCommand(self, cmd):
        cmd.doc = self
        self._undoStack.push(cmd)
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
        return self.findObjsInRect(hitRect)

    def addObj(self, obj):
        self._objs.add(obj)
        self.sigChanged.emit()

    def removeObj(self, obj):
        self._objs.remove(obj)
        self.sigChanged.emit()

    @pyqtSlot()
    def undo(self):
        self._undoStack.undo()
        self.sigChanged.emit()

    @pyqtSlot()
    def redo(self):
        self._undoStack.redo()
        self.sigChanged.emit()

    def toXml(self):
        root = etree.Element("xSchematic")
        props = etree.SubElement(root, "props")
        uuid = etree.SubElement(props, "uuid")
        uuid.text = str(self._uuid)
        pages = etree.SubElement(root, "pages")
        page = etree.SubElement(pages, "page", name="Page1")
        for obj in self._objs:
            obj.toXml(page)
        return root

    def saveToFile(self, file):
        root = self.toXml()
        with open(file, "wb") as h:
            h.write(etree.tostring(root, pretty_print=True))


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
