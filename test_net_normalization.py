"""Unit tests for net normalization algorithm."""

import unittest
from PySide6.QtCore import QPoint
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from sch.obj.net import NetObj
from sch.utils import Geom


class TestNetObjUniquePoints(unittest.TestCase):
    """Tests for _uniquePoints helper function."""
    
    def test_no_duplicates(self):
        """Test that unique points remain unchanged."""
        points = [QPoint(0, 0), QPoint(5, 5), QPoint(10, 10)]
        result = NetObj._uniquePoints(points)
        self.assertEqual(len(result), 3)
    
    def test_with_duplicates(self):
        """Test that duplicates are removed."""
        points = [QPoint(0, 0), QPoint(5, 5), QPoint(0, 0), QPoint(10, 10), QPoint(5, 5)]
        result = NetObj._uniquePoints(points)
        self.assertEqual(len(result), 3)
    
    def test_all_duplicates(self):
        """Test when all points are duplicates."""
        points = [QPoint(0, 0), QPoint(0, 0), QPoint(0, 0)]
        result = NetObj._uniquePoints(points)
        self.assertEqual(len(result), 1)


class TestNetObjSortAlongLine(unittest.TestCase):
    """Tests for _sortAlongLine helper function."""
    
    def test_horizontal_line(self):
        """Test sorting points along horizontal line."""
        net = NetObj(QPoint(0, 0), QPoint(10, 0))
        points = [QPoint(5, 0), QPoint(0, 0), QPoint(10, 0), QPoint(3, 0)]
        result = NetObj._sortAlongLine(points, net)
        self.assertEqual(result[0], QPoint(0, 0))
        self.assertEqual(result[-1], QPoint(10, 0))
    
    def test_vertical_line(self):
        """Test sorting points along vertical line."""
        net = NetObj(QPoint(0, 0), QPoint(0, 10))
        points = [QPoint(0, 5), QPoint(0, 0), QPoint(0, 10), QPoint(0, 3)]
        result = NetObj._sortAlongLine(points, net)
        self.assertEqual(result[0], QPoint(0, 0))
        self.assertEqual(result[-1], QPoint(0, 10))


class TestNetObjSplitNetAtPoints(unittest.TestCase):
    """Tests for _splitNetAtPoints helper function."""
    
    def test_no_split_points(self):
        """Test that net without split points returns itself."""
        net = NetObj(QPoint(0, 0), QPoint(10, 0))
        result = NetObj._splitNetAtPoints(net, [])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].pt1, net.pt1)
        self.assertEqual(result[0].pt2, net.pt2)
    
    def test_split_at_middle(self):
        """Test splitting a net in the middle."""
        net = NetObj(QPoint(0, 0), QPoint(10, 0))
        split_points = [QPoint(5, 0)]
        result = NetObj._splitNetAtPoints(net, split_points)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].pt1, QPoint(0, 0))
        self.assertEqual(result[0].pt2, QPoint(5, 0))
        self.assertEqual(result[1].pt1, QPoint(5, 0))
        self.assertEqual(result[1].pt2, QPoint(10, 0))
    
    def test_split_at_multiple_points(self):
        """Test splitting a net at multiple points."""
        net = NetObj(QPoint(0, 0), QPoint(10, 0))
        split_points = [QPoint(3, 0), QPoint(7, 0)]
        result = NetObj._splitNetAtPoints(net, split_points)
        self.assertEqual(len(result), 3)
        self.assertEqual(result[0].pt1, QPoint(0, 0))
        self.assertEqual(result[0].pt2, QPoint(3, 0))
        self.assertEqual(result[1].pt1, QPoint(3, 0))
        self.assertEqual(result[1].pt2, QPoint(7, 0))
        self.assertEqual(result[2].pt1, QPoint(7, 0))
        self.assertEqual(result[2].pt2, QPoint(10, 0))
    
    def test_split_vertical_net(self):
        """Test splitting a vertical net."""
        net = NetObj(QPoint(0, 0), QPoint(0, 10))
        split_points = [QPoint(0, 5)]
        result = NetObj._splitNetAtPoints(net, split_points)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].pt1, QPoint(0, 0))
        self.assertEqual(result[0].pt2, QPoint(0, 5))
        self.assertEqual(result[1].pt1, QPoint(0, 5))
        self.assertEqual(result[1].pt2, QPoint(0, 10))


class TestNetObjMergeCollinearSegments(unittest.TestCase):
    """Tests for _mergeCollinearSegments helper function."""
    
    def test_no_segments(self):
        """Test merging empty list."""
        result = NetObj._mergeCollinearSegments([])
        self.assertEqual(result, [])
    
    def test_single_segment(self):
        """Test merging single segment."""
        segments = [NetObj(QPoint(0, 0), QPoint(10, 0))]
        result = NetObj._mergeCollinearSegments(segments)
        self.assertEqual(len(result), 1)
    
    def test_merge_adjacent_horizontal(self):
        """Test merging adjacent horizontal segments."""
        segments = [
            NetObj(QPoint(0, 0), QPoint(5, 0)),
            NetObj(QPoint(5, 0), QPoint(10, 0))
        ]
        result = NetObj._mergeCollinearSegments(segments)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].pt1, QPoint(0, 0))
        self.assertEqual(result[0].pt2, QPoint(10, 0))
    
    def test_merge_adjacent_vertical(self):
        """Test merging adjacent vertical segments."""
        segments = [
            NetObj(QPoint(0, 0), QPoint(0, 5)),
            NetObj(QPoint(0, 5), QPoint(0, 10))
        ]
        result = NetObj._mergeCollinearSegments(segments)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].pt1, QPoint(0, 0))
        self.assertEqual(result[0].pt2, QPoint(0, 10))
    
    def test_non_adjacent_segments(self):
        """Test that non-adjacent segments are not merged."""
        segments = [
            NetObj(QPoint(0, 0), QPoint(3, 0)),
            NetObj(QPoint(7, 0), QPoint(10, 0))
        ]
        result = NetObj._mergeCollinearSegments(segments)
        self.assertEqual(len(result), 2)
    
    def test_remove_zero_length(self):
        """Test that zero-length segments are removed."""
        segments = [
            NetObj(QPoint(0, 0), QPoint(0, 0)),  # zero-length
            NetObj(QPoint(0, 0), QPoint(5, 0))
        ]
        result = NetObj._mergeCollinearSegments(segments)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].pt1, QPoint(0, 0))
        self.assertEqual(result[0].pt2, QPoint(5, 0))


class TestNetObjFindTJunctions(unittest.TestCase):
    """Tests for findTJunctions function."""
    
    def test_no_tjunctions(self):
        """Test when there are no T-junctions."""
        nets = [
            NetObj(QPoint(0, 0), QPoint(5, 0)),
            NetObj(QPoint(5, 0), QPoint(10, 0))
        ]
        tjunctions = NetObj.findTJunctions(nets)
        self.assertEqual(len(tjunctions), 0)
    
    def test_tjunction_endpoint_touching_middle(self):
        """Test T-junction where endpoint touches middle of another net."""
        nets = [
            NetObj(QPoint(0, 0), QPoint(10, 0)),  # horizontal net
            NetObj(QPoint(5, 0), QPoint(5, 5))    # vertical net touching at middle
        ]
        tjunctions = NetObj.findTJunctions(nets)
        # Should find the T-junction
        self.assertGreater(len(tjunctions), 0)
    
    def test_endpoint_touching_endpoint(self):
        """Test that endpoint-to-endpoint touching is not a T-junction."""
        nets = [
            NetObj(QPoint(0, 0), QPoint(5, 0)),
            NetObj(QPoint(5, 0), QPoint(10, 0))
        ]
        tjunctions = NetObj.findTJunctions(nets)
        self.assertEqual(len(tjunctions), 0)
    
    def test_crossing_without_endpoint(self):
        """Test that crossing without endpoint touching is not a T-junction."""
        nets = [
            NetObj(QPoint(0, 5), QPoint(10, 5)),  # horizontal
            NetObj(QPoint(5, 0), QPoint(5, 10))   # vertical crossing
        ]
        tjunctions = NetObj.findTJunctions(nets)
        # Crossing without endpoint touching should not be a T-junction
        self.assertEqual(len(tjunctions), 0)


class TestNetObjNormalizeNets(unittest.TestCase):
    """Tests for normalize_nets function."""
    
    def test_no_moved_nets(self):
        """Test normalization with no moved nets."""
        class MockDoc:
            def objects(self, objType=None):
                return []
        
        doc = MockDoc()
        result = NetObj.normalize_nets(doc, [])
        self.assertEqual(result, [])
    
    def test_single_net(self):
        """Test normalization with single net."""
        class MockDoc:
            def __init__(self):
                self._nets = [NetObj(QPoint(0, 0), QPoint(10, 0))]
            
            def objects(self, objType=None):
                return self._nets
        
        doc = MockDoc()
        result = NetObj.normalize_nets(doc, [NetObj(QPoint(0, 0), QPoint(10, 0))])
        self.assertEqual(len(result), 1)
    
    def test_split_wire_at_endpoint(self):
        """Test that a wire is split when another endpoint touches its middle."""
        class MockDoc:
            def __init__(self):
                self._nets = [
                    NetObj(QPoint(0, 0), QPoint(10, 0)),  # horizontal
                    NetObj(QPoint(5, 0), QPoint(5, 5))    # vertical touching middle
                ]
            
            def objects(self, objType=None):
                return self._nets
        
        doc = MockDoc()
        result = NetObj.normalize_nets(doc, [NetObj(QPoint(0, 0), QPoint(10, 0))])
        
        # The horizontal net should be split into two segments
        horizontal_segments = [n for n in result if n.pt1.y() == 0 and n.pt2.y() == 0]
        self.assertEqual(len(horizontal_segments), 2)
    
    def test_merge_collinear_after_split(self):
        """Test that collinear segments are merged when junction is removed."""
        class MockDoc:
            def __init__(self):
                # Two collinear segments that should merge
                self._nets = [
                    NetObj(QPoint(0, 0), QPoint(5, 0)),
                    NetObj(QPoint(5, 0), QPoint(10, 0))
                ]
            
            def objects(self, objType=None):
                return self._nets
        
        doc = MockDoc()
        result = NetObj.normalize_nets(doc, list(doc._nets))
        
        # Should merge into single segment
        horizontal_segments = [n for n in result if n.pt1.y() == 0 and n.pt2.y() == 0]
        self.assertEqual(len(horizontal_segments), 1)
        self.assertEqual(horizontal_segments[0].pt1, QPoint(0, 0))
        self.assertEqual(horizontal_segments[0].pt2, QPoint(10, 0))


class TestNetObjNormalizeAfterMove(unittest.TestCase):
    """Tests for normalize_after_move function."""
    
    def test_move_creating_tjunction(self):
        """Test moving a net endpoint to create a T-junction."""
        class MockDoc:
            def __init__(self):
                self._nets = [NetObj(QPoint(0, 0), QPoint(10, 0))]  # horizontal
            
            def objects(self, objType=None):
                return self._nets
        
        doc = MockDoc()
        original = NetObj(QPoint(0, 0), QPoint(5, 0))
        new_net = NetObj(QPoint(5, 0), QPoint(5, 5))  # vertical touching middle
        
        result = NetObj.normalize_after_move(doc, original, new_net)
        
        # The horizontal net should be split
        horizontal_segments = [n for n in result if n.pt1.y() == 0 and n.pt2.y() == 0]
        self.assertEqual(len(horizontal_segments), 2)


class TestNetObjNormalizeJunctionDrag(unittest.TestCase):
    """Tests for normalize_junction_drag function."""
    
    def test_drag_junction(self):
        """Test dragging a junction point."""
        class MockDoc:
            def __init__(self):
                self._nets = [
                    NetObj(QPoint(0, 0), QPoint(5, 0)),
                    NetObj(QPoint(5, 0), QPoint(10, 0)),
                    NetObj(QPoint(5, 0), QPoint(5, 5))
                ]
            
            def objects(self, objType=None):
                return self._nets
        
        doc = MockDoc()
        junction_point = QPoint(5, 0)
        new_junction_point = QPoint(6, 0)
        connected_nets = [doc._nets[0], doc._nets[1], doc._nets[2]]
        
        result = NetObj.normalize_junction_drag(doc, junction_point, connected_nets, new_junction_point)
        
        # Should have normalized the nets after moving the junction
        self.assertGreater(len(result), 0)


class TestNetObjGeometricHelpers(unittest.TestCase):
    """Tests for geometric helper functions."""
    
    def test_is_collinear_horizontal(self):
        """Test collinearity check for horizontal segments."""
        net1 = NetObj(QPoint(0, 0), QPoint(5, 0))
        net2 = NetObj(QPoint(5, 0), QPoint(10, 0))
        self.assertTrue(NetObj._isCollinear(net1, net2))
    
    def test_is_collinear_vertical(self):
        """Test collinearity check for vertical segments."""
        net1 = NetObj(QPoint(0, 0), QPoint(0, 5))
        net2 = NetObj(QPoint(0, 5), QPoint(0, 10))
        self.assertTrue(NetObj._isCollinear(net1, net2))
    
    def test_not_collinear_perpendicular(self):
        """Test that perpendicular segments are not collinear."""
        net1 = NetObj(QPoint(0, 0), QPoint(5, 0))  # horizontal
        net2 = NetObj(QPoint(5, 0), QPoint(5, 5))  # vertical
        self.assertFalse(NetObj._isCollinear(net1, net2))
    
    def test_not_collinear_diagonal(self):
        """Test that diagonal segments are not collinear."""
        net1 = NetObj(QPoint(0, 0), QPoint(5, 5))
        net2 = NetObj(QPoint(5, 5), QPoint(10, 0))
        self.assertFalse(NetObj._isCollinear(net1, net2))


if __name__ == '__main__':
    unittest.main()
