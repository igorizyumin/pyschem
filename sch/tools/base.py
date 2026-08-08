from PySide6.QtCore import Signal, QObject, Qt, QPoint, QRect
from PySide6.QtGui import QPainter, QPen
from sch.view import Event
from sch.utils import LayerType, Layer
import sch.document


# TODO: property inspector / editor
class EditHandle(QObject):
    sigDragged = Signal('QPoint')
    sigMoved = Signal('QPoint')

    def __init__(self, ctrl, pos=QPoint()):
        super().__init__()
        self._ctrl = ctrl
        self.pos = QPoint(pos)
        self._dragging = False
        self._moved = False

    def draw(self, painter: QPainter):
        r = self._ctrl.view.hitRadius() * 0.7
        x, y = self.pos.x(), self.pos.y()
        painter.drawRect(QRect(QPoint(x-r, y-r), QPoint(x+r, y+r)))

    def testHit(self, pt: QPoint):
        return (self.pos - self._ctrl.snapPt(pt)).manhattanLength() <= self._ctrl.view.hitRadius()

    def handleEvent(self, event: Event):
        if event.evType == Event.Type.MouseMoved:
            if self._dragging:
                if self.pos != self._ctrl.snapPt(event.pos):
                    self.pos = self._ctrl.snapPt(event.pos)
                    self.sigDragged.emit(self.pos)
                    self._moved = True
                event.handled = True
        elif event.evType == Event.Type.MousePressed:
            if self.testHit(event.pos):
                self._dragging = True
                self._moved = False
                event.handled = True
        elif event.evType == Event.Type.MouseReleased:
            if self._dragging:
                self._dragging = False
                if self._moved or self.pos != self._ctrl.snapPt(event.pos):
                    self.pos = self._ctrl.snapPt(event.pos)
                    self.sigMoved.emit(self.pos)
                event.handled = True


class BaseEditor(QObject):
    sigUpdate = Signal()
    sigDone = Signal()

    def __init__(self, ctrl, obj):
        super().__init__()
        self._ctrl = ctrl
        self._obj = obj
        self._disposed = False
        self._handles = []
        self._inspector = None
        self._cmd = None
        
        # Set up document change monitoring
        self._ctrl.doc.sigChanged.connect(self._docChanged)
        self._cmd = self._create_change_command()
        
        # Create handles and connect signals
        self.create_handles()
        self._setup_handle_connections()

    def create_handles(self):
        """Create edit handles for the object. Override in subclasses."""
        pass

    def _create_change_command(self):
        """Create the appropriate change command. Override in subclasses if needed."""
        import sch.document
        return sch.document.ObjChangeCmd(self._obj)

    def _setup_handle_connections(self):
        """Set up connections between handles and commit/drag methods."""
        for h in self._handles:
            if hasattr(h, 'sigDragged'):
                h.sigDragged.connect(self._handle_dragged)
            if hasattr(h, 'sigMoved'):
                h.sigMoved.connect(self._commit)

    def _handle_dragged(self, pos):
        """Handle handle drag events. Override in subclasses for custom behavior."""
        self.sigUpdate.emit()

    def update_handles(self):
        """Update handle positions based on object state. Override in subclasses."""
        pass

    def testHit(self, pt):
        """Default hit testing using handles."""
        for h in self._handles:
            if h.testHit(pt):
                return True
        return False

    def draw(self, painter):
        """Common drawing with selection styling."""
        pen = QPen(Layer.color(LayerType.selection))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setWidth(0)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        
        # Draw handles
        for h in self._handles:
            h.draw(painter)
        
        # Draw custom selection UI
        self.draw_custom(painter)

    def draw_custom(self, painter):
        """Draw object-specific selection UI. Override in subclasses."""
        pass

    def handleEvent(self, event):
        """Common event handling with delegation."""
        # Let handles handle events first
        for h in self._handles:
            h.handleEvent(event)
            if event.handled:
                return
        
        # Handle custom events
        self.handle_custom_event(event)

    def handle_custom_event(self, event):
        """Handle object-specific events. Override in subclasses."""
        if event.evType == Event.Type.KeyPressed and event.key == Qt.Key_Delete:
            self.delete()
            event.handled = True

    def delete(self):
        """Delete the edited object from the document."""
        delete_cmd = sch.document.ObjDelCmd(self._obj)
        self._ctrl.doc.doCommand(delete_cmd)
        self.sigDone.emit()

    @property
    def inspector(self):
        """Return the inspector widget."""
        return self._inspector

    def _commit(self):
        """Standard commit pattern."""
        self.update_handles()
        self._ctrl.doc.doCommand(self._cmd)
        self._cmd = self._create_change_command()
        self.sigUpdate.emit()

    def _docChanged(self):
        """Standard document change handling."""
        if self._disposed:
            return
        # Check that object is still part of the document
        if not self._ctrl.doc.hasObject(self._obj):
            self.sigDone.emit()
            return
        # Object still there, update handle positions
        self.update_handles()

    def dispose(self):
        """Disconnect this editor from document and UI signals."""
        if self._disposed:
            return
        self._disposed = True
        try:
            self._ctrl.doc.sigChanged.disconnect(self._docChanged)
        except (RuntimeError, TypeError):
            pass
        try:
            self.sigUpdate.disconnect()
        except (RuntimeError, TypeError):
            pass
        try:
            self.sigDone.disconnect()
        except (RuntimeError, TypeError):
            pass


class TextHandle(EditHandle):
    def __init__(self, ctrl, txt):
        super().__init__(ctrl, txt.posGlobal())
        self._txt = txt
        self._start = QPoint()

    def testHit(self, pt: QPoint):
        return self._txt.testHit(pt, 0)

    def draw(self, painter: QPainter):
        painter.drawRect(self._txt.bbox())

    def handleEvent(self, event: Event):
        if event.evType == Event.Type.MouseMoved:
            if self._dragging:
                if self.pos != self._ctrl.snapPt(self._start + event.pos):
                    self.pos = self._ctrl.snapPt(self._start + event.pos)
                    self.sigDragged.emit(self.pos)
                    self._moved = True
                event.handled = True
        elif event.evType == Event.Type.MousePressed:
            if self.testHit(event.pos):
                self._start = self.pos - event.pos
                self._dragging = True
                self._moved = False
                event.handled = True
        elif event.evType == Event.Type.MouseReleased:
            if self._dragging:
                self._dragging = False
                # self.pos = self._ctrl.snapPt(event.pos)
                if self._moved:
                    self.sigMoved.emit(self.pos)
                event.handled = True
