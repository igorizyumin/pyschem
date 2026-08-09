from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QPainter, QPen, QTransform
from lxml import etree

from sch.utils import Layer, LayerType


class PinObj:
    """A symbol connection point.

    Pin coordinates are stored in the symbol's local coordinate system.  A
    part instance maps them through its normal symbol transform before using
    them for schematic connectivity.
    """

    MARKER_SIZE = 1000

    def __init__(self, pin_id="1", desc="", pos=QPoint(0, 0), rot=0):
        self._id = str(pin_id)
        self._desc = str(desc)
        self._pos = QPoint(pos)
        self._rot = int(rot) % 360
        self._proptexts = []

    @property
    def id(self):
        return self._id

    @id.setter
    def id(self, value):
        self._id = str(value)

    @property
    def desc(self):
        return self._desc

    @desc.setter
    def desc(self, value):
        self._desc = str(value)

    @property
    def description(self):
        return self.desc

    @description.setter
    def description(self, value):
        self.desc = value

    @property
    def pos(self):
        return self._pos

    @pos.setter
    def pos(self, value):
        self._pos = QPoint(value)

    @property
    def rot(self):
        return self._rot

    @rot.setter
    def rot(self, value):
        self._rot = int(value) % 360

    def children(self):
        return list(self._proptexts)

    def transform(self):
        transform = QTransform()
        transform.translate(self.pos.x(), self.pos.y())
        transform.rotate(-self.rot)
        return transform

    def bbox(self):
        half = self.MARKER_SIZE // 2
        return QRect(QPoint(self.pos.x() - half, self.pos.y() - half),
                     QPoint(self.pos.x() + half, self.pos.y() + half)).normalized()

    def testHit(self, pt, radius):
        return self.bbox().adjusted(-radius, -radius, radius, radius).contains(pt)

    def getProp(self, name):
        """Expose pin metadata to optional pin property-text children."""
        if name in ("id", "number", "pin"):
            return self.id
        if name in ("desc", "description", "name"):
            return self.desc
        return ""

    def setProp(self, name, value):
        if name in ("id", "number", "pin"):
            self.id = value
        elif name in ("desc", "description", "name"):
            self.desc = value

    def draw(self, painter: QPainter, highlight=True):
        """Draw the pin marker and any metadata labels.

        Symbol pages call this with the default ``highlight=True``.  Part
        instances pass the derived connection state and only show the red
        marker while the pin is dangling.
        """
        if highlight:
            half = self.MARKER_SIZE // 2
            marker = QRect(QPoint(self.pos.x() - half, self.pos.y() - half),
                           QPoint(self.pos.x() + half, self.pos.y() + half))
            painter.save()
            pen = QPen(Layer.color(LayerType.warning))
            # World coordinates are rendered at a much smaller scale on the
            # canvas.  A zero-width pen remains one device pixel wide;
            # otherwise this 1000-unit marker becomes effectively invisible.
            pen.setWidth(0)
            painter.setPen(pen)
            painter.setBrush(Qt.NoBrush)
            painter.drawRect(marker)
            painter.restore()

        for proptext in self._proptexts:
            proptext.draw(painter)

    def toXml(self, parent):
        pin = etree.SubElement(parent, "pin",
                               id=self.id,
                               desc=self.desc,
                               x=str(self.pos.x()),
                               y=str(self.pos.y()),
                               rot=str(self.rot))
        for proptext in self._proptexts:
            proptext.toXml(pin)

    @staticmethod
    def fromXml(elem, parent=None):
        pin = PinObj(elem.attrib.get("id", ""),
                     elem.attrib.get("desc", ""),
                     QPoint(int(elem.attrib["x"]), int(elem.attrib["y"])),
                     int(elem.attrib.get("rot", "0")))
        import sch.obj.proptext
        for child in elem:
            if child.tag == "proptext":
                pin._proptexts.append(
                    sch.obj.proptext.PropTextObj.fromXml(child, pin))
        return pin

    def is_connected(self, document, position=None, owner=None):
        """Return whether this pin touches a wire or another pin on a page."""
        if document is None:
            return False
        position = QPoint(self.pos if position is None else position)
        nets = document.objects(objType=_net_type())
        if any(net.touchesPt(position) for net in nets):
            return True
        if hasattr(document, "iterPinPositions"):
            for other_owner, other_pin, other_position in document.iterPinPositions():
                if (other_position == position
                        and not (other_pin is self
                                 and (owner is None or other_owner is owner))):
                    return True
        return False

    def isConnected(self, document, position=None, owner=None):
        return self.is_connected(document, position, owner)


def _net_type():
    # Avoid importing NetObj at module import time; document and net modules
    # both import symbol objects.
    from sch.obj.net import NetObj
    return NetObj


# Keep the short name convenient for callers that use the XML/model name
# rather than the repository's ``*Obj`` naming convention.
Pin = PinObj
