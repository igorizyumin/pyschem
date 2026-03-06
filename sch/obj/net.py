from PySide6.QtCore import QPoint, Qt, QRect, QPointF
from PySide6.QtGui import QPainter, QPen, QBrush
from sch.utils import LayerType, Layer, Geom, Point
from lxml import etree
from collections import defaultdict
from typing import List, Set, Tuple, Dict

class NetObj(object):
    def __init__(self, pt1=QPoint(0, 0), pt2=QPoint(1, 1)):
        self.pt1 = QPoint(pt1)
        self.pt2 = QPoint(pt2)

    def __eq__(self, other):
        """Check if two nets are equal (same endpoints)."""
        if not isinstance(other, NetObj):
            return False
        return self.pt1 == other.pt1 and self.pt2 == other.pt2

    def __ne__(self, other):
        """Check if two nets are not equal."""
        return not self.__eq__(other)

    def __hash__(self):
        """Make NetObj hashable for use in sets and as dict keys."""
        return hash((self.pt1.x(), self.pt1.y(), self.pt2.x(), self.pt2.y()))

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
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(Layer.color(LayerType.junction)))
        nets = doc.objects(objType=NetObj)
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
    def _uniquePoints(points: List[QPoint], epsilon: float = 1.0) -> List[QPoint]:
        """Remove duplicate points within epsilon tolerance."""
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
        """Split a net at given points, returning list of segments."""
        if not split_points:
            return [net]
        
        # Collect all points including endpoints
        all_points = split_points.copy()
        all_points.extend([net.pt1, net.pt2])
        
        # Remove duplicates and sort
        all_points = NetObj._uniquePoints(all_points)
        sorted_points = NetObj._sortAlongLine(all_points, net)
        
        # Create segments between consecutive points
        segments = []
        for i in range(len(sorted_points) - 1):
            if not NetObj._pointEqual(sorted_points[i], sorted_points[i+1]):
                segments.append(NetObj(sorted_points[i], sorted_points[i+1]))
        
        return segments

    @staticmethod
    def _isCollinear(net1: 'NetObj', net2: 'NetObj') -> bool:
        """Check if two nets are collinear (lie on the same line)."""
        if net1.pt1 == net1.pt2 or net2.pt1 == net2.pt2:
            return False  # Zero-length nets
        
        dir1 = net1.pt2 - net1.pt1
        dir2 = net2.pt2 - net2.pt1
        
        # Check if directions are parallel
        if not Geom.isParallel(dir1, dir2):
            return False
        
        # Check if net2's endpoints lie on net1's line
        # Use cross product to check collinearity
        test_dir = net2.pt1 - net1.pt1
        return Geom.isParallel(test_dir, dir1)

    @staticmethod
    def _getCollinearLineKey(net: 'NetObj') -> Tuple[float, float, float]:
        """Get a unique key for the line containing this net (Ax + By + C = 0)."""
        if net.pt1 == net.pt2:
            return (0.0, 0.0, 0.0)
        
        A = float(net.pt2.y() - net.pt1.y())
        B = float(net.pt1.x() - net.pt2.x())
        C = -A * net.pt1.x() - B * net.pt1.y()
        
        # Normalize to handle floating point issues
        length = (A * A + B * B) ** 0.5
        if length > 0:
            A, B, C = A / length, B / length, C / length
        
        # Round to handle floating point precision
        return (round(A, 6), round(B, 6), round(C, 6))

    @staticmethod
    def _countSegmentsAtPoint(segments: List['NetObj'], pt: QPoint) -> int:
        """Count how many segments have this point as an endpoint."""
        count = 0
        for seg in segments:
            if seg.pt1 == seg.pt2:
                continue
            if NetObj._pointEqual(seg.pt1, pt) or NetObj._pointEqual(seg.pt2, pt):
                count += 1
        return count

    @staticmethod
    def _mergeCollinearSegments(segments: List['NetObj'], 
                                 junction_points: Set[QPoint] = None) -> List['NetObj']:
        """
        Merge adjacent collinear segments into longer segments.
        
        Args:
            segments: List of segments to merge
            junction_points: Optional set of points that should not be merged across.
                           If provided, segments sharing a junction point will not be merged.
                           A junction point is one where more than 2 segments meet.
        """
        if not segments:
            return []
        
        # If no junction points provided, compute them from the segments
        if junction_points is None:
            junction_points = set()
            # A junction point is where more than 2 segments meet
            for seg in segments:
                if seg.pt1 == seg.pt2:
                    continue
                # Check both endpoints
                for pt in [seg.pt1, seg.pt2]:
                    if NetObj._countSegmentsAtPoint(segments, pt) > 2:
                        junction_points.add(pt)
        
        # Group segments by their line
        line_groups: Dict[Tuple[float, float, float], List[NetObj]] = defaultdict(list)
        
        for seg in segments:
            line_key = NetObj._getCollinearLineKey(seg)
            line_groups[line_key].append(seg)
        
        merged = []
        
        for line_key, group in line_groups.items():
            if len(group) == 1:
                merged.append(group[0])
                continue
            
            # Sort segments by position along the line
            def sort_key(n):
                # Horizontal line (A ≈ 0): sort by x
                # Vertical line (A ≠ 0): sort by y
                return n.pt1.x() if abs(line_key[0]) < 1e-9 else n.pt1.y()
            
            group.sort(key=sort_key)
            
            # Merge overlapping/adjacent segments
            current = group[0]
            for next_seg in group[1:]:
                # Check if adjacent (share an endpoint)
                shared_pt = None
                if NetObj._pointEqual(current.pt2, next_seg.pt1):
                    shared_pt = current.pt2
                elif NetObj._pointEqual(current.pt1, next_seg.pt2):
                    shared_pt = current.pt1
                elif NetObj._pointEqual(current.pt2, next_seg.pt2):
                    shared_pt = current.pt2
                elif NetObj._pointEqual(current.pt1, next_seg.pt1):
                    shared_pt = current.pt1
                
                if shared_pt is not None:
                    # Check if this shared point is a junction (more than 2 segments meet here)
                    is_junction = shared_pt in junction_points
                    if not is_junction:
                        # Merge into one segment
                        pts = [current.pt1, current.pt2, next_seg.pt1, next_seg.pt2]
                        # Find min and max along the line
                        # For line Ax + By + C = 0:
                        # - Horizontal: A ≈ 0, B ≠ 0 (y = constant)
                        # - Vertical: A ≠ 0, B ≈ 0 (x = constant)
                        is_horizontal = abs(line_key[0]) < 1e-9
                        if is_horizontal:
                            min_pt = min(pts, key=lambda p: p.x())
                            max_pt = max(pts, key=lambda p: p.x())
                        else:
                            min_pt = min(pts, key=lambda p: p.y())
                            max_pt = max(pts, key=lambda p: p.y())
                        current = NetObj(min_pt, max_pt)
                        continue
                
                # Cannot merge, add current and start new
                merged.append(current)
                current = next_seg
            
            merged.append(current)
        
        # Remove zero-length segments
        result = [s for s in merged if not NetObj._pointEqual(s.pt1, s.pt2)]
        
        return result

    @staticmethod
    def findTJunctions(nets: List['NetObj']) -> List[Tuple[QPoint, 'NetObj', 'NetObj']]:
        """
        Find all T-junctions in a set of nets.
        Returns list of (junction_point, touching_net, touched_net) tuples.
        A T-junction is when an endpoint of one net touches the middle of another.
        """
        t_junctions = []
        
        for net1 in nets:
            if net1.pt1 == net1.pt2:
                continue
            for net2 in nets:
                if net1 == net2 or net2.pt1 == net2.pt2:
                    continue
                
                # Check if net1's endpoint touches middle of net2
                for endpoint in [net1.pt1, net1.pt2]:
                    if net2.touchesPt(endpoint) and not net2.connVtx(net1):
                        t_junctions.append((endpoint, net1, net2))
                
                # Check if net2's endpoint touches middle of net1
                for endpoint in [net2.pt1, net2.pt2]:
                    if net1.touchesPt(endpoint) and not net1.connVtx(net2):
                        t_junctions.append((endpoint, net2, net1))
        
        return t_junctions

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
        
        # If no nets moved, return as-is
        if not moved_nets:
            return all_nets
        
        # Step 1: Find all T-junctions in the entire net system
        t_junctions = NetObj.findTJunctions(all_nets)
        
        # Step 2: Identify nets that need splitting
        nets_to_split = set()
        split_points: Dict['NetObj', List[QPoint]] = defaultdict(list)
        
        for pt, touching_net, touched_net in t_junctions:
            # The touched_net needs to be split at pt
            if touched_net not in nets_to_split:
                nets_to_split.add(touched_net)
            split_points[touched_net].append(pt)
        
        # Step 3: Create split segments
        new_segments = []
        for net in all_nets:
            if net in nets_to_split:
                segments = NetObj._splitNetAtPoints(net, split_points[net])
                new_segments.extend(segments)
            else:
                new_segments.append(net)
        
        # Step 4: Identify junction points (points where more than 2 segments meet)
        junction_points = set()
        for seg in new_segments:
            if seg.pt1 == seg.pt2:
                continue
            for pt in [seg.pt1, seg.pt2]:
                if NetObj._countSegmentsAtPoint(new_segments, pt) > 2:
                    junction_points.add(pt)
        
        # Step 5: Merge collinear adjacent segments (avoiding junction points)
        final_nets = NetObj._mergeCollinearSegments(new_segments, junction_points)
        
        # Step 6: Remove zero-length segments
        final_nets = [n for n in final_nets if not NetObj._pointEqual(n.pt1, n.pt2)]
        
        return final_nets

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
        # Get all current nets
        all_nets = list(document.objects(objType=NetObj))
        
        # Remove the original net (it's being replaced)
        all_nets = [n for n in all_nets if n != original_net]
        
        # Add the new net position
        all_nets.append(new_net)
        
        # Find T-junctions
        t_junctions = NetObj.findTJunctions(all_nets)
        
        # Identify nets to split
        nets_to_split = set()
        split_points: Dict['NetObj', List[QPoint]] = defaultdict(list)
        
        for pt, touching_net, touched_net in t_junctions:
            if touched_net not in nets_to_split:
                nets_to_split.add(touched_net)
            split_points[touched_net].append(pt)
        
        # Create split segments
        new_segments = []
        for net in all_nets:
            if net in nets_to_split:
                segments = NetObj._splitNetAtPoints(net, split_points[net])
                new_segments.extend(segments)
            else:
                new_segments.append(net)
        
        # Identify junction points (points where more than 2 segments meet)
        junction_points = set()
        for seg in new_segments:
            if seg.pt1 == seg.pt2:
                continue
            for pt in [seg.pt1, seg.pt2]:
                if NetObj._countSegmentsAtPoint(new_segments, pt) > 2:
                    junction_points.add(pt)
        
        # Merge collinear segments (avoiding junction points)
        final_nets = NetObj._mergeCollinearSegments(new_segments, junction_points)
        
        # Remove zero-length segments
        final_nets = [n for n in final_nets if not NetObj._pointEqual(n.pt1, n.pt2)]
        
        return final_nets

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
        # Get all current nets
        all_nets = list(document.objects(objType=NetObj))
        
        # Update positions of connected nets (move their endpoints)
        for net in connected_nets:
            if net.pt1 == junction_point:
                net.pt1 = new_junction_point
            elif net.pt2 == junction_point:
                net.pt2 = new_junction_point
        
        # Find all nets touching the new junction position
        nets_at_new_junction = [n for n in all_nets 
                                if n.touchesPt(new_junction_point) and n in connected_nets]
        
        # Find T-junctions involving the moved nets
        t_junctions = []
        for net in all_nets:
            if net in connected_nets:
                # Check if this moved net's other endpoint creates a T-junction
                for endpoint in [net.pt1, net.pt2]:
                    if endpoint != new_junction_point:
                        for other_net in all_nets:
                            if other_net != net and other_net.pt1 != other_net.pt2:
                                if other_net.touchesPt(endpoint) and not other_net.connVtx(net):
                                    t_junctions.append((endpoint, net, other_net))
        
        # Also check for T-junctions where moved nets create T-junctions on other nets
        for net in connected_nets:
            for endpoint in [net.pt1, net.pt2]:
                if endpoint == new_junction_point:
                    continue
                for other_net in all_nets:
                    if other_net != net and other_net.pt1 != other_net.pt2:
                        if other_net.touchesPt(endpoint) and not other_net.connVtx(net):
                            t_junctions.append((endpoint, net, other_net))
        
        # Identify nets to split
        nets_to_split = set()
        split_points: Dict['NetObj', List[QPoint]] = defaultdict(list)
        
        for pt, touching_net, touched_net in t_junctions:
            if touched_net not in nets_to_split:
                nets_to_split.add(touched_net)
            split_points[touched_net].append(pt)
        
        # Create split segments
        new_segments = []
        for net in all_nets:
            if net in nets_to_split:
                segments = NetObj._splitNetAtPoints(net, split_points[net])
                new_segments.extend(segments)
            else:
                new_segments.append(net)
        
        # Merge collinear segments
        final_nets = NetObj._mergeCollinearSegments(new_segments)
        
        # Remove zero-length segments
        final_nets = [n for n in final_nets if not NetObj._pointEqual(n.pt1, n.pt2)]
        
        return final_nets



