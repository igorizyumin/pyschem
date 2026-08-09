from PySide6.QtCore import QPoint, Qt, QRect
from PySide6.QtGui import QPainter, QPen, QBrush
from sch.utils import LayerType, Layer, Geom, Point
from lxml import etree
from collections import defaultdict
from typing import List, Set, Tuple

class NetObj(object):
    __slots__ = ('_pt1', '_pt2')
    HIT_RADIUS_SCALE = 1.5

    def __init__(self, pt1=QPoint(0, 0), pt2=QPoint(1, 1)):
        object.__setattr__(self, '_pt1', QPoint(pt1))
        object.__setattr__(self, '_pt2', QPoint(pt2))

    @property
    def pt1(self):
        """Return a copy of the first endpoint."""
        return QPoint(self._pt1)

    @property
    def pt2(self):
        """Return a copy of the second endpoint."""
        return QPoint(self._pt2)

    def __setattr__(self, name, value):
        raise AttributeError("NetObj is immutable; use with_endpoints()")

    def with_endpoints(self, pt1, pt2):
        """Return a new net with the supplied integer endpoints."""
        return NetObj(pt1, pt2)

    def translated(self, offset):
        """Return a translated copy of this net."""
        return self.with_endpoints(self.pt1 + offset, self.pt2 + offset)

    def __eq__(self, other):
        """Check if two nets are equal (same endpoints)."""
        if not isinstance(other, NetObj):
            return False
        return self.pt1 == other.pt1 and self.pt2 == other.pt2

    def __ne__(self, other):
        """Check if two nets are not equal."""
        return not self.__eq__(other)

    def __hash__(self):
        return hash((self._pt1.x(), self._pt1.y(), self._pt2.x(), self._pt2.y()))

    def __str__(self):
        return "<Net: ({},{})<->({},{})>".format(self.pt1.x(), self.pt1.y(), self.pt2.x(), self.pt2.y())

    def draw(self, painter: QPainter):
        pen = QPen(Layer.color(LayerType.wire))
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setWidth(0)
        painter.setPen(pen)
        painter.drawLine(self.pt1, self.pt2)

    def bbox(self):
        return QRect(self.pt1, self.pt2).normalized().adjusted(-1, -1, 1, 1)

    def testHit(self, pt: QPoint, radius: int):
        return Geom.distPtToSegment(pt, self.pt1, self.pt2) <= radius

    @staticmethod
    def hitRadius(radius):
        """Return the slightly forgiving body-hit radius for a wire."""
        return radius * NetObj.HIT_RADIUS_SCALE

    def connVtx(self, otherNet):
        # check if they share a vertex
        xs = {Point(self.pt1), Point(self.pt2)}.intersection({Point(otherNet.pt1), Point(otherNet.pt2)})
        if xs:
            return xs.pop()
        else:
            return None

    def touchesPt(self, pt):
        # check if point is on this segment
        # print("net touch: {} {} : {}".format(str(self), pt, Geom.pointOnSegment(self.pt1, self.pt2, pt)))
        return Geom.pointOnSegment(self.pt1, self.pt2, pt)

    def intersectsNet(self, net):
        return Geom.segsIntersect(self.pt1, self.pt2, net.pt1, net.pt2)

    def toXml(self, parent):
        etree.SubElement(parent, "net",
                         x1=str(self.pt1.x()),
                         y1=str(self.pt1.y()),
                         x2=str(self.pt2.x()),
                         y2=str(self.pt2.y()))

    @staticmethod
    def fromXml(elem):
        p1 = QPoint(int(elem.attrib["x1"]), int(elem.attrib["y1"]))
        p2 = QPoint(int(elem.attrib["x2"]), int(elem.attrib["y2"]))
        return NetObj(p1, p2)

    @staticmethod
    def drawJunctions(doc, painter: QPainter):
        NetObj.drawJunctionsForNets(doc.objects(objType=NetObj), painter)

    @staticmethod
    def drawJunctionsForNets(nets, painter: QPainter):
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(Layer.color(LayerType.junction)))
        nets = set(nets)
        juncts = defaultdict(set)
        while nets:
            n = nets.pop()
            # check net against every other net in set
            for n2 in nets:
                v = n.connVtx(n2)
                if v:
                    juncts[v].add(n)
                    juncts[v].add(n2)
        for pt, nets in juncts.items():
            if len(nets) > 2:
                painter.drawEllipse(QPoint(pt.x, pt.y), 500, 500)

    @staticmethod
    def _uniquePoints(points: List[QPoint]) -> List[QPoint]:
        """Remove duplicate integer-coordinate points."""
        unique = []
        for pt in points:
            is_dup = False
            for u in unique:
                if pt == u:
                    is_dup = True
                    break
            if not is_dup:
                unique.append(pt)
        return unique

    @staticmethod
    def _sortAlongLine(points: List[QPoint], net: 'NetObj') -> List[QPoint]:
        """Sort points along the line defined by the net."""
        if len(points) <= 1:
            return points
        
        dir_vec = net.pt2 - net.pt1
        if dir_vec.x() == 0 and dir_vec.y() == 0:
            return points
        
        # Project points onto the direction vector
        def project(p):
            if abs(dir_vec.x()) > abs(dir_vec.y()):
                return p.x()
            return p.y()
        
        return sorted(points, key=project)

    @staticmethod
    def _splitNetAtPoints(net: 'NetObj', split_points: List[QPoint]) -> List['NetObj']:
        """Split a segment at points that lie on it."""
        points = NetObj._uniqueExactPoints(
            [net.pt1, net.pt2] + [p for p in split_points if net.touchesPt(p)]
        )
        dx = net.pt2.x() - net.pt1.x()
        dy = net.pt2.y() - net.pt1.y()
        points.sort(key=lambda p: (p.x() - net.pt1.x()) * dx
                    + (p.y() - net.pt1.y()) * dy)
        return [NetObj(points[i], points[i + 1])
                for i in range(len(points) - 1)
                if points[i] != points[i + 1]]

    @staticmethod
    def _uniqueExactPoints(points: List[QPoint]) -> List[QPoint]:
        """Remove only identical points; topology must not use hit tolerance."""
        unique = []
        seen = set()
        for point in points:
            key = NetObj._pointKey(point)
            if key not in seen:
                seen.add(key)
                unique.append(QPoint(point))
        return unique

    @staticmethod
    def _isCollinear(net1: 'NetObj', net2: 'NetObj') -> bool:
        """Return whether two non-zero segments lie on the same infinite line."""
        if net1.pt1 == net1.pt2 or net2.pt1 == net2.pt2:
            return False
        d1 = net1.pt2 - net1.pt1
        d2 = net2.pt2 - net2.pt1
        offset = net2.pt1 - net1.pt1
        return (d1.x() * d2.y() - d1.y() * d2.x() == 0
                and d1.x() * offset.y() - d1.y() * offset.x() == 0)

    @staticmethod
    def _countSegmentsAtPoint(segments: List['NetObj'], pt: QPoint) -> int:
        """Count how many segments have this point as an endpoint."""
        count = 0
        for seg in segments:
            if seg.pt1 == seg.pt2:
                continue
            if seg.pt1 == pt or seg.pt2 == pt:
                count += 1
        return count

    @staticmethod
    def _mergeCollinearSegments(segments: List['NetObj'], 
                                 junction_points: Set[QPoint] = None) -> List['NetObj']:
        """Merge edges through degree-two collinear vertices.

        ``junction_points`` remains accepted for compatibility, but topology
        is derived directly from the edge graph.  A branch (degree > 2) and a
        corner (degree 2 but non-collinear) are therefore never collapsed.
        """
        edges = NetObj._deduplicateSegments(segments)
        while True:
            adjacency = defaultdict(list)
            for index, edge in enumerate(edges):
                adjacency[NetObj._pointKey(edge.pt1)].append(index)
                adjacency[NetObj._pointKey(edge.pt2)].append(index)

            changed = False
            for key, incident in adjacency.items():
                if len(incident) != 2:
                    continue
                first, second = edges[incident[0]], edges[incident[1]]
                vertex = QPoint(*key)
                if not NetObj._isCollinear(first, second):
                    continue
                a = first.pt2 if first.pt1 == vertex else first.pt1
                b = second.pt2 if second.pt1 == vertex else second.pt1
                keep = [edge for i, edge in enumerate(edges)
                        if i not in incident]
                keep.append(NetObj(a, b))
                edges = NetObj._deduplicateSegments(keep)
                changed = True
                break
            if not changed:
                return edges

    @staticmethod
    def findTJunctions(nets: List['NetObj']) -> List[Tuple[QPoint, 'NetObj', 'NetObj']]:
        """
        Find all T-junctions in a set of nets.
        Returns list of (junction_point, touching_net, touched_net) tuples.
        A T-junction is when an endpoint of one net touches the middle of another.
        """
        result = []
        for i, first in enumerate(nets):
            if first.pt1 == first.pt2:
                continue
            for second in nets[i + 1:]:
                if second.pt1 == second.pt2 or first == second:
                    continue
                candidates = (
                    (first.pt1, first, second), (first.pt2, first, second),
                    (second.pt1, second, first), (second.pt2, second, first)
                )
                for endpoint, touching, touched in candidates:
                    if touched.touchesPt(endpoint):
                        if endpoint != touched.pt1 and endpoint != touched.pt2:
                            result.append((QPoint(endpoint), touching, touched))
        return result

    @staticmethod
    def normalize_nets(document, moved_nets: List['NetObj']) -> List['NetObj']:
        """
        Normalize a set of nets after modification.
        
        Args:
            document: The document object containing all nets
            moved_nets: List of nets that were moved/modified
        
        Returns:
            List of normalized net segments
        """
        all_nets = list(document.objects(objType=NetObj))
        if not moved_nets:
            return all_nets
        return NetObj._normalizeGeometry(all_nets)

    @staticmethod
    def normalize_after_move(document, original_net: 'NetObj', new_net: 'NetObj') -> List['NetObj']:
        """
        Normalize nets after a single net has been moved.
        This is the classic case where a user drags one endpoint of a wire.
        
        Args:
            document: The document object
            original_net: The net before the move
            new_net: The net after the move
        
        Returns:
            List of normalized net segments
        """
        all_nets = list(document.objects(objType=NetObj))
        removed = False
        replacement = []
        for net in all_nets:
            if not removed and (net is original_net or net == original_net):
                removed = True
                continue
            replacement.append(net)
        all_nets = replacement
        all_nets.append(new_net)
        return NetObj._normalizeGeometry(all_nets)

    @staticmethod
    def normalize_junction_drag(document, junction_point: QPoint, connected_nets: List['NetObj'], 
                                  new_junction_point: QPoint) -> List['NetObj']:
        """
        Normalize nets after dragging a junction (multiple connected wires).
        
        Args:
            document: The document object
            junction_point: The old junction position
            connected_nets: All nets that were connected to the old junction
            new_junction_point: The new junction position
        
        Returns:
            List of normalized net segments
        """
        all_nets = list(document.objects(objType=NetObj))
        moved = []
        for net in all_nets:
            copy_net = NetObj(net.pt1, net.pt2)
            if any(net is connected for connected in connected_nets):
                new_pt1 = new_junction_point if copy_net.pt1 == junction_point else copy_net.pt1
                new_pt2 = new_junction_point if copy_net.pt2 == junction_point else copy_net.pt2
                copy_net = copy_net.with_endpoints(new_pt1, new_pt2)
            moved.append(copy_net)
        return NetObj._normalizeGeometry(moved)

    @staticmethod
    def _pointKey(point: QPoint) -> Tuple[int, int]:
        return point.x(), point.y()

    @staticmethod
    def _canonicalSegment(net: 'NetObj') -> 'NetObj':
        if NetObj._pointKey(net.pt1) <= NetObj._pointKey(net.pt2):
            return NetObj(net.pt1, net.pt2)
        return NetObj(net.pt2, net.pt1)

    @staticmethod
    def _deduplicateSegments(segments: List['NetObj']) -> List['NetObj']:
        result = []
        seen = set()
        for segment in segments:
            if segment.pt1 == segment.pt2:
                continue
            canonical = NetObj._canonicalSegment(segment)
            key = (NetObj._pointKey(canonical.pt1), NetObj._pointKey(canonical.pt2))
            if key not in seen:
                seen.add(key)
                result.append(canonical)
        return result

    @staticmethod
    def _normalizeGeometry(nets: List['NetObj']) -> List['NetObj']:
        """Normalize segments as an explicit endpoint/intersection graph.

        Endpoints lying on another segment create graph vertices.  Pure
        interior crossings do not, preserving schematic crossing semantics.
        Atomic edges are then merged only through degree-two collinear nodes.
        """
        source = [net for net in nets if net.pt1 != net.pt2]
        atomic = []
        for index, net in enumerate(source):
            split_points = []
            for other_index, other in enumerate(source):
                if index == other_index:
                    continue
                if net.touchesPt(other.pt1):
                    split_points.append(other.pt1)
                if net.touchesPt(other.pt2):
                    split_points.append(other.pt2)
            atomic.extend(NetObj._splitNetAtPoints(net, split_points))
        return NetObj._mergeCollinearSegments(atomic)



