from PyQt5.QtCore import *
from PyQt5.QtWidgets import QUndoStack, QUndoCommand


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

    def isModified(self):
        return not self._undoStack.isClean()

    def doCommand(self, cmd):
        cmd.doc = self
        self._undoStack.push(cmd)
        self.sigChanged.emit()

    def objects(self):
        return list(self._objs)

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
