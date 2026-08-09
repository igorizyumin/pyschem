from PySide6.QtCore import *
from PySide6.QtGui import *
from PySide6.QtWidgets import QWidget
from PySide6.QtCore import Signal, Slot, QSignalBlocker
from sch.utils import *
import sch.controller
import sch.document
from sch.view import Event
from sch.uic.ui_proptextinspector import Ui_PropTextInspector
import copy
import sch.obj.text
import sch.obj.proptext
from sch.tools.base import TextHandle, BaseEditor


class PropTextTool(QObject):
    sigUpdate = Signal()

    def __init__(self, ctrl):
        QObject.__init__(self)
        self._ctrl = ctrl
        self._pos = QPoint()
        self._obj = sch.obj.proptext.PropTextObj(self._ctrl.doc)
        self._inspector = PropTextInspector(self._obj)
        # self._inspector.edited.connect(self._commit)

    def finish(self):
        self._obj = None
        self.sigUpdate.emit()
        pass

    @property
    def inspector(self):
        return self._inspector

    @staticmethod
    def name():
        return "Add Attribute Display"

    def draw(self, painter):
        if self._obj is not None:
            self._obj.draw(painter)

    def handleEvent(self, e):
        if e.evType == sch.controller.Event.Type.MouseMoved:
            self._obj.pos = self._ctrl.snapPt(e.pos)
            self.sigUpdate.emit()
            e.handled = True
        elif e.evType == sch.controller.Event.Type.MouseReleased:
            cmd = sch.document.ObjAddCmd(self._obj)
            self._ctrl.doc.doCommand(cmd)
            self._obj = copy.copy(self._obj)
            self._inspector.obj = self._obj
            e.handled = True


class PropTextEditor(BaseEditor):

    def __init__(self, ctrl, obj):
        super().__init__(ctrl, obj)
        self._inspector = PropTextInspector(obj)
        self._inspector.edited.connect(self._commit)

    def create_handles(self):
        """Create a text handle for the prop text object."""
        self._handles = [TextHandle(self._ctrl, self._obj)]

    def _setup_handle_connections(self):
        """Set up specific connections for text handle."""
        self._handles[0].sigDragged.connect(self._drag)
        self._handles[0].sigMoved.connect(self._commit)

    def update_handles(self):
        """Update handle position to match text position."""
        self._handles[0].pos = self._obj.posGlobal()

    def handle_custom_event(self, event):
        """Handle keyboard events for rotation."""
        if event.evType == Event.Type.KeyPressed:
            if event.key == Qt.Key_R:
                self._obj.rot = (self._obj.rot + 90) % 360
                self._commit()

    @Slot('QPoint')
    def _drag(self, pos):
        self._obj.setPosGlobal(pos)
        self.sigUpdate.emit()

    @Slot()
    def _commit(self):
        self._obj.setPosGlobal(self._handles[0].pos)
        super()._commit()


class PropTextInspector(QWidget):
    edited = Signal()

    def __init__(self, obj, parent=None):
        super().__init__(parent)
        self.ui = Ui_PropTextInspector()
        self.ui.setupUi(self)
        self._obj = None
        fontSizes = list(range(6, 16)) + list(range(16, 34, 2)) + list(range(36, 48, 4)) + \
            list(range(48, 66, 6)) + list(range(66, 98, 8))
        self.ui.fontSize.addItems([str(i) for i in fontSizes])
        self._obj = obj
        self._loadProperties(obj)

    @property
    def obj(self):
        return self._obj

    @obj.setter
    def obj(self, new):
        self._obj = new
        self._loadProperties(new)

    def _loadProperties(self, obj: sch.obj.proptext.PropTextObj):
        blockers = [QSignalBlocker(widget) for widget in
                    (self.ui.cbProp, self.ui.leValue, self.ui.cbVis,
                     self.ui.cbShowName, self.ui.alignGroup,
                     self.ui.fontFace, self.ui.fontSize)]
        if obj.name is None:
            self.ui.cbProp.setCurrentIndex(-1)
        else:
            self.ui.cbProp.setCurrentText(obj.name)
        self.ui.leValue.setPlaceholderText("(mixed)" if obj.value is None else "")
        self.ui.leValue.setText("" if obj.value is None else obj.value)
        self.ui.cbVis.setTristate(obj.vis is None)
        self.ui.cbVis.setCheckState(Qt.PartiallyChecked if obj.vis is None else
                                    (Qt.Checked if obj.vis else Qt.Unchecked))
        self.ui.cbShowName.setTristate(obj.showName is None)
        self.ui.cbShowName.setCheckState(Qt.PartiallyChecked if obj.showName is None else
                                         (Qt.Checked if obj.showName else Qt.Unchecked))
        if obj.alignment is None:
            self.ui.alignGroup.setExclusive(False)
            for button in self.ui.alignGroup.buttons():
                button.setChecked(False)
            self.ui.alignGroup.setExclusive(True)
        elif obj.alignment & Qt.AlignLeft:
            if obj.alignment & Qt.AlignTop:
                self.ui.btnTopLeft.setChecked(True)
            elif obj.alignment & Qt.AlignBottom:
                self.ui.btnBotLeft.setChecked(True)
            else:
                self.ui.btnMidLeft.setChecked(True)
        elif obj.alignment & Qt.AlignRight:
            if obj.alignment & Qt.AlignTop:
                self.ui.btnTopRight.setChecked(True)
            elif obj.alignment & Qt.AlignBottom:
                self.ui.btnBotRight.setChecked(True)
            else:
                self.ui.btnMidRight.setChecked(True)
        else:
            if obj.alignment & Qt.AlignTop:
                self.ui.btnTopCtr.setChecked(True)
            elif obj.alignment & Qt.AlignBottom:
                self.ui.btnBotCtr.setChecked(True)
            else:
                self.ui.btnMidCtr.setChecked(True)
        if obj.family is None:
            self.ui.fontFace.setCurrentIndex(-1)
            self.ui.fontFace.setEditText("(mixed)")
        else:
            self.ui.fontFace.setCurrentText(obj.family)
        if obj.ptSize is None:
            self.ui.fontSize.setCurrentIndex(-1)
            self.ui.fontSize.setEditText("(mixed)")
        else:
            self.ui.fontSize.setCurrentText("{:g}".format(obj.ptSize/500))

    @Slot(int)
    def on_alignGroup_buttonClicked(self, id):
        if self.ui.btnTopLeft.isChecked():
            align = Qt.AlignTop | Qt.AlignLeft
        elif self.ui.btnTopCtr.isChecked():
            align = Qt.AlignTop | Qt.AlignVCenter
        elif self.ui.btnTopRight.isChecked():
            align = Qt.AlignTop | Qt.AlignRight
        elif self.ui.btnMidLeft.isChecked():
            align = Qt.AlignHCenter | Qt.AlignLeft
        elif self.ui.btnMidCtr.isChecked():
            align = Qt.AlignHCenter | Qt.AlignVCenter
        elif self.ui.btnMidRight.isChecked():
            align = Qt.AlignHCenter | Qt.AlignRight
        elif self.ui.btnBotLeft.isChecked():
            align = Qt.AlignBottom| Qt.AlignLeft
        elif self.ui.btnBotCtr.isChecked():
            align = Qt.AlignBottom | Qt.AlignVCenter
        else:
            align = Qt.AlignBottom | Qt.AlignRight
        self.obj.alignment = align
        self.edited.emit()

    @Slot(QFont)
    def on_fontFace_currentFontChanged(self, font):
        if self.obj:
            self.obj.family = font.family()
            self.edited.emit()

    @Slot(str)
    def on_fontSize_editTextChanged(self, text):
        if self.obj:
            self.obj.ptSize = int(float(text)*500)
            self.edited.emit()

    @Slot(str)
    def on_cbProp_currentTextChanged(self, text):
        if self.obj:
            self.obj.name = text
            self.edited.emit()

    @Slot(str)
    def on_leValue_textEdited(self, text):
        if self.obj:
            self.obj.value = text
            self.edited.emit()

    @Slot(bool)
    def on_cbVis_toggled(self, chkd):
        if self.obj:
            self.obj.vis = chkd
            self.edited.emit()

    @Slot(bool)
    def on_cbShowName_toggled(self, chkd):
        if self.obj:
            self.obj.showName = chkd
            self.edited.emit()
