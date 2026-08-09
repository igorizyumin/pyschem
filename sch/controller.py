from enum import Enum
from PySide6.QtCore import Signal, Slot, Qt, QObject, QPoint, QRect, QMargins
from PySide6.QtGui import QPainter, QPen, QUndoStack, QUndoCommand
import sch.obj.line
import sch.tools.line
import sch.obj.net
import sch.obj.text
import sch.obj.part
import sch.tools.select
import sch.tools.hierarchy
from sch.view import Event
from sch.utils import Layer, LayerType
import sch.document
from copy import copy
import sch.obj.proptext


class ToolType(Enum):
        SelectTool = 0
        LineTool = 1
        NetTool = 2
        TextTool = 3
        PartTool = 4
        SheetRefTool = 5


def getCtrl(doc):
    if type(doc) is sch.document.DocPage:
        return SchController
    elif type(doc) is sch.document.SymbolPage:
        return SymController
    else:
        raise NotImplementedError()


class Controller(QObject):
    sigUpdate = Signal()
    sigToolChanged = Signal(int)
    sigInspectorChanged = Signal()

    def __init__(self, doc=None, view=None, lib=None):
        super().__init__()
        self._view = None
        self._doc = None
        self._tool = None
        self._toolId = 0
        self._grid = 5000
        self.lib = lib
        # properties
        self.view = view
        self.doc = doc

    def handleEvent(self, event):
        if self._tool is not None:
            self._tool.handleEvent(event)
            if event.handled:
                return
        if event.evType == Event.Type.KeyPressed:
            event.handled = True
            if event.key == Qt.Key_Escape:
                self.handleEvent(Event(evType=Event.Type.Cancel))
            elif event.key == Qt.Key_Space:
                self.view.recenter()
            elif event.key == Qt.Key_Enter:
                self.handleEvent(Event(evType=Event.Type.Done))
            # elif event.key == Qt.Key_L:
            #     self.changeTool(ToolType.LineTool)
            # elif event.key == Qt.Key_N:
            #     self.changeTool(ToolType.NetTool)
            # elif event.key == Qt.Key_S:
            #     self.changeTool(ToolType.SelectTool)
            # elif event.key == Qt.Key_T:
            #     self.changeTool(ToolType.TextTool)
            else:
                event.handled = False

    def _installTool(self, tool):
        if self._tool is not None:
            self._tool.finish()
            self._tool = None
        if self.view is None:
            return
        self._tool = tool
        self._tool.sigUpdate.connect(self.sigUpdate)
        self.sigToolChanged.emit(self.toolId)

    def snapPt(self, pt: QPoint):
        g = self.grid

        def snap_coord(value):
            quotient, remainder = divmod(value, g)
            if remainder * 2 >= g:
                quotient += 1
            return quotient * g

        return QPoint(snap_coord(pt.x()), snap_coord(pt.y()))

    @property
    def toolId(self):
        return self._toolId

    @property
    def view(self):
        return self._view

    @view.setter
    def view(self, view):
        self._view = view
        self.sigUpdate.connect(self._view.slotUpdate)
        self._installTool(sch.tools.select.SelectTool(self))

    @property
    def grid(self):
        return self._grid

    @grid.setter
    def grid(self, value):
        self._grid = value
        self.sigUpdate.emit()

    @property
    def doc(self):
        return self._doc

    @doc.setter
    def doc(self, doc):
        self._doc = doc
        self._doc.sigChanged.connect(self.sigUpdate)
        self.sigUpdate.emit()

    @property
    def inspector(self):
        return self._tool.inspector

    def getDrawables(self):
        class JunctionDrawable:
            @staticmethod
            def draw(painter):
                preview = None
                if self._tool is not None and hasattr(self._tool, 'previewObjects'):
                    preview = self._tool.previewObjects()
                if preview is None:
                    sch.obj.net.NetObj.drawJunctions(self.doc, painter)
                else:
                    sch.obj.net.NetObj.drawJunctionsForNets(preview, painter)
        hidden = ()
        if self._tool is not None and hasattr(self._tool, 'hiddenObjects'):
            hidden = tuple(self._tool.hiddenObjects())
        out = [obj for obj in self.doc.objects()
               if not any(obj is item for item in hidden)]
        if self._tool is not None and hasattr(self._tool, 'previewDrawables'):
            out.extend(self._tool.previewDrawables())
        out.append(JunctionDrawable())
        if self._tool is not None:
            out.append(self._tool)
        return out

    @Slot(int)
    def changeTool(self, tool_id):
        if self._toolId == tool_id:
            return
        self._toolId = tool_id
        self._installTool(self.tools()[tool_id](self))
        self.sigInspectorChanged.emit()

    @staticmethod
    def tools():
        raise NotImplementedError()


class SchController(Controller):
    def __init__(self, doc=None, view=None, lib=None):
        super().__init__(doc, view, lib)

    @staticmethod
    def tools():
        return (sch.tools.select.SelectTool, sch.tools.line.LineTool,
                sch.tools.net.NetTool, sch.tools.text.TextTool,
                sch.tools.part.PartTool, sch.tools.hierarchy.SheetRefTool)


class SymController(Controller):
    def __init__(self, doc=None, view=None, lib=None):
        super().__init__(doc, view, lib)

    @staticmethod
    def tools():
        return sch.tools.select.SelectTool, sch.tools.line.LineTool, sch.tools.text.TextTool, sch.tools.proptext.PropTextTool


