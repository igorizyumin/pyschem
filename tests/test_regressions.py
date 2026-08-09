"""Regression tests for document persistence and net editing primitives."""

import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QPoint, Qt

from sch.document import MasterDocument
from sch.document import DocPage
from sch.obj.net import NetObj
from sch.tools.net import NetDragSession, NetEditor, NetTool
from sch.utils import Layer, LayerType
from sch.view import Event


class TestNetRegression(unittest.TestCase):
    def test_find_objs_near_uses_the_full_hit_radius_for_thin_nets(self):
        page = DocPage(MasterDocument(None))
        net = NetObj(QPoint(0, 0), QPoint(100, 0))
        page.addObj(net)

        self.assertIn(net, page.findObjsNear(QPoint(50, 8), dist=10))

    def test_net_tool_add_uses_integer_graph_normalization(self):
        class Controller:
            pass

        page = DocPage(MasterDocument(None))
        ctrl = Controller()
        ctrl.doc = page
        NetTool(ctrl).addNet(NetObj(QPoint(0, 0), QPoint(10, 0)))
        self.assertEqual(len(page.objects(NetObj)), 1)
        result = next(iter(page.objects(NetObj)))
        self.assertEqual(result.pt1, QPoint(0, 0))
        self.assertEqual(result.pt2, QPoint(10, 0))

    def test_net_tool_continues_an_orthogonal_chain_until_enter(self):
        class Controller:
            def __init__(self, page):
                self.doc = page

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        page = DocPage(MasterDocument(None))
        tool = NetTool(Controller(page))
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(0, 0)))
        tool.handleEvent(Event(Event.Type.MouseMoved, QPoint(10, 4)))

        self.assertEqual(tool._endpoint(), QPoint(10, 4))
        self.assertEqual(tool._preview_points(), [
            (QPoint(0, 0), QPoint(10, 0)),
            (QPoint(10, 0), QPoint(10, 4)),
        ])
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(10, 4)))
        self.assertEqual(tool._firstPt, QPoint(10, 0))
        self.assertTrue(tool._vertical_first)

        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(10, 10)))
        self.assertEqual(tool._firstPt, QPoint(10, 10))
        self.assertFalse(tool._vertical_first)
        self.assertIn(NetObj(QPoint(0, 0), QPoint(10, 0)),
                      page.objects(NetObj))
        self.assertIn(NetObj(QPoint(10, 0), QPoint(10, 10)),
                      page.objects(NetObj))

        tool.handleEvent(Event(Event.Type.Done))
        self.assertIsNone(tool._firstPt)
        self.assertEqual(len(page.objects(NetObj)), 2)

    def test_net_tool_shift_allows_an_angled_chain_segment(self):
        class Controller:
            def __init__(self, page):
                self.doc = page

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        page = DocPage(MasterDocument(None))
        tool = NetTool(Controller(page))
        shift = Qt.ShiftModifier
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(0, 0)))
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(10, 4),
                               modifiers=shift))

        self.assertEqual(tool._firstPt, QPoint(10, 4))
        self.assertIn(NetObj(QPoint(0, 0), QPoint(10, 4)),
                      page.objects(NetObj))

    def test_net_tool_ends_a_chain_when_the_new_endpoint_touches_a_wire(self):
        class Controller:
            def __init__(self, page):
                self.doc = page

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        page = DocPage(MasterDocument(None))
        existing = NetObj(QPoint(10, 0), QPoint(10, 10))
        page.addObj(existing)
        tool = NetTool(Controller(page))
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(0, 0)))
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(10, 0)))

        self.assertIsNone(tool._firstPt)
        self.assertIn(existing, page.objects(NetObj))
        self.assertIn(NetObj(QPoint(0, 0), QPoint(10, 0)),
                      page.objects(NetObj))

    def test_net_tool_preview_is_drawn_in_yellow(self):
        class Controller:
            def __init__(self, page):
                self.doc = page

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        class PainterSpy:
            def __init__(self):
                self.pen = None
                self.lines = []

            def setPen(self, pen):
                self.pen = pen

            def drawLine(self, start, end):
                self.lines.append((start, end))

        page = DocPage(MasterDocument(None))
        tool = NetTool(Controller(page))
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(0, 0)))
        tool.handleEvent(Event(Event.Type.MouseMoved, QPoint(10, 5)))
        painter = PainterSpy()
        tool.draw(painter)

        self.assertEqual(painter.pen.color(), Layer.color(LayerType.selection))
        self.assertEqual(painter.lines, [
            (QPoint(0, 0), QPoint(10, 0)),
            (QPoint(10, 0), QPoint(10, 5)),
        ])

    def test_net_tool_space_toggles_l_order(self):
        class Controller:
            def __init__(self, page):
                self.doc = page

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        page = DocPage(MasterDocument(None))
        tool = NetTool(Controller(page))
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(0, 0)))
        tool.handleEvent(Event(Event.Type.KeyPressed, key=Qt.Key_Space))
        tool.handleEvent(Event(Event.Type.MouseMoved, QPoint(10, 5)))

        self.assertEqual(tool._preview_points(), [
            (QPoint(0, 0), QPoint(0, 5)),
            (QPoint(0, 5), QPoint(10, 5)),
        ])

    def test_net_tool_zero_length_segment_terminates_the_chain(self):
        class Controller:
            def __init__(self, page):
                self.doc = page

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        page = DocPage(MasterDocument(None))
        tool = NetTool(Controller(page))
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(0, 0)))
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(10, 0)))
        self.assertEqual(tool._firstPt, QPoint(10, 0))

        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(10, 0)))

        self.assertIsNone(tool._firstPt)
        self.assertEqual(len(page.objects(NetObj)), 1)

    def test_net_tool_double_click_terminates_without_starting_a_new_chain(self):
        class Controller:
            def __init__(self, page):
                self.doc = page

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        page = DocPage(MasterDocument(None))
        tool = NetTool(Controller(page))
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(0, 0)))
        tool.handleEvent(Event(Event.Type.MouseDblClicked, QPoint(10, 10)))
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(10, 10)))

        self.assertIsNone(tool._firstPt)
        self.assertIn(NetObj(QPoint(0, 0), QPoint(10, 0)),
                      page.objects(NetObj))
        self.assertIn(NetObj(QPoint(10, 0), QPoint(10, 10)),
                      page.objects(NetObj))

    def test_net_is_immutable_and_hashable_by_value(self):
        net = NetObj(QPoint(0, 0), QPoint(10, 0))
        nets = {net}
        self.assertIn(net, nets)
        with self.assertRaises(AttributeError):
            net.pt2 = QPoint(20, 0)
        moved = net.with_endpoints(net.pt1, QPoint(20, 0))
        self.assertNotEqual(net, moved)
        self.assertEqual(len(nets), 1)

    def test_t_junction_is_preserved_as_three_edges(self):
        nets = [
            NetObj(QPoint(0, 0), QPoint(10, 0)),
            NetObj(QPoint(5, 0), QPoint(5, 5)),
        ]
        result = NetObj._normalizeGeometry(nets)
        self.assertEqual(len(result), 3)
        self.assertEqual(sum(n.pt1 == QPoint(5, 0) or n.pt2 == QPoint(5, 0)
                             for n in result), 3)

    def test_crossing_interiors_are_not_connected(self):
        nets = [
            NetObj(QPoint(0, 5), QPoint(10, 5)),
            NetObj(QPoint(5, 0), QPoint(5, 10)),
        ]
        result = NetObj._normalizeGeometry(nets)
        self.assertEqual(len(result), 2)

    def test_overlapping_collinear_segments_become_one_edge(self):
        nets = [
            NetObj(QPoint(0, 0), QPoint(10, 0)),
            NetObj(QPoint(5, 0), QPoint(15, 0)),
        ]
        result = NetObj._normalizeGeometry(nets)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].pt1, QPoint(0, 0))
        self.assertEqual(result[0].pt2, QPoint(15, 0))

    def test_corner_is_not_collapsed(self):
        nets = [
            NetObj(QPoint(0, 0), QPoint(5, 0)),
            NetObj(QPoint(5, 0), QPoint(5, 5)),
        ]
        result = NetObj._normalizeGeometry(nets)
        self.assertEqual(len(result), 2)

    def test_crossing_past_endpoint_preserves_reversed_net(self):
        result = NetObj._normalizeGeometry(
            [NetObj(QPoint(20, 0), QPoint(10, 0))]
        )
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].pt1, QPoint(10, 0))
        self.assertEqual(result[0].pt2, QPoint(20, 0))

    def test_nonzero_short_net_is_not_removed(self):
        result = NetObj._normalizeGeometry(
            [NetObj(QPoint(10, 0), QPoint(11, 0))]
        )
        self.assertEqual(len(result), 1)

    def test_multiple_net_commands_restore_exact_graph_on_undo_redo(self):
        class Controller:
            pass

        page = DocPage(MasterDocument(None))
        ctrl = Controller()
        ctrl.doc = page
        tool = NetTool(ctrl)

        for endpoints in (
            (QPoint(0, 0), QPoint(10, 0)),
            (QPoint(10, 0), QPoint(20, 0)),
            (QPoint(20, 0), QPoint(30, 0)),
            (QPoint(20, 0), QPoint(20, 10)),
        ):
            tool.addNet(NetObj(*endpoints))

        self.assertEqual(len(page.objects(NetObj)), 3)
        for expected in (1, 1, 1, 0):
            page.undo()
            self.assertEqual(len(page.objects(NetObj)), expected)

        for expected in (1, 1, 1, 3):
            page.redo()
            self.assertEqual(len(page.objects(NetObj)), expected)


class TestDocumentRegression(unittest.TestCase):
    def test_schema_resolution_does_not_depend_on_working_directory(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "document.xsch"
            source = MasterDocument(None)
            source.saveToFile(str(path))

            old_cwd = os.getcwd()
            try:
                os.chdir(tempfile.gettempdir())
                loaded = MasterDocument(None)
                loaded.loadFromFile(str(path))
            finally:
                os.chdir(old_cwd)

            self.assertEqual(loaded.fileName, str(path))

    def test_load_replaces_existing_pages(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "document.xsch"
            source = MasterDocument(None)
            source.appendNewPage()
            source.saveToFile(str(path))

            loaded = MasterDocument(None)
            loaded.loadFromFile(str(path))
            loaded.loadFromFile(str(path))
            self.assertEqual(len(loaded.pages), 1)


class TestNetEditorUndoRegression(unittest.TestCase):
    def test_removed_segment_clears_selection_instead_of_rebinding_randomly(self):
        class Controller:
            pass

        page = DocPage(MasterDocument(None))
        net = NetObj(QPoint(0, 0), QPoint(10, 0))
        neighbor = NetObj(QPoint(10, 0), QPoint(10, 10))
        page.addObj(net)
        page.addObj(neighbor)
        ctrl = Controller()
        ctrl.doc = page
        editor = NetEditor(ctrl, net)
        done = []
        editor.sigDone.connect(lambda: done.append(True))

        editor._dragPt1(QPoint(10, 0))
        editor._commit()

        self.assertEqual(len(page.objects(NetObj)), 1)
        self.assertTrue(done)
        self.assertIsNot(editor._obj, neighbor)

    def test_rubberband_preview_does_not_mutate_document(self):
        class Controller:
            pass

        page = DocPage(MasterDocument(None))
        horizontal = NetObj(QPoint(0, 0), QPoint(10, 0))
        branch = NetObj(QPoint(0, 0), QPoint(0, 5))
        page.addObj(horizontal)
        page.addObj(branch)
        ctrl = Controller()
        ctrl.doc = page
        editor = NetEditor(ctrl, horizontal)

        editor._begin_drag(0, QPoint(5, 5), orthogonal=False)

        self.assertIn(horizontal, page.objects(NetObj))
        self.assertIn(branch, page.objects(NetObj))
        self.assertEqual(len(page.objects(NetObj)), 2)
        self.assertEqual(len(editor.hiddenObjects()), 2)
        self.assertEqual(editor._drag.selected_preview.pt1, QPoint(5, 5))
        self.assertTrue(any(net.pt1 == QPoint(5, 5) or net.pt2 == QPoint(5, 5)
                            for net in editor._drag.preview))

        editor._commit()
        self.assertEqual(len(page.objects(NetObj)), 2)

    def test_dragging_left_endpoint_past_right_endpoint_keeps_net(self):
        class Controller:
            pass

        page = DocPage(MasterDocument(None))
        net = NetObj(QPoint(0, 0), QPoint(10, 0))
        page.addObj(net)
        ctrl = Controller()
        ctrl.doc = page
        editor = NetEditor(ctrl, net)

        # Include the zero-length intermediate position encountered while
        # crossing the other endpoint.
        editor._dragPt1(QPoint(10, 0))
        editor._dragPt1(QPoint(20, 0))
        editor._commit()

        self.assertEqual(len(page.objects(NetObj)), 1)
        result = next(iter(page.objects(NetObj)))
        self.assertEqual({result.pt1, result.pt2}, {QPoint(10, 0), QPoint(20, 0)})

    def test_editor_rebinds_after_commit_undo_redo(self):
        class Controller:
            pass

        page = DocPage(MasterDocument(None))
        original = NetObj(QPoint(0, 0), QPoint(10, 0))
        page.addObj(original)
        ctrl = Controller()
        ctrl.doc = page
        editor = NetEditor(ctrl, original)

        editor._dragPt2(QPoint(20, 0))
        editor._commit()
        self.assertTrue(any(net is editor._obj for net in page.objects(NetObj)))

        page.undo()
        self.assertTrue(any(net is editor._obj for net in page.objects(NetObj)))
        self.assertEqual(len(page.objects(NetObj)), 1)
        self.assertEqual(next(iter(page.objects(NetObj))).pt2, QPoint(10, 0))

        page.redo()
        self.assertTrue(any(net is editor._obj for net in page.objects(NetObj)))
        self.assertEqual(next(iter(page.objects(NetObj))).pt2, QPoint(20, 0))

        # A second edit must operate on the restored/rebound document object.
        editor._dragPt2(QPoint(30, 0))
        editor._commit()
        self.assertEqual(next(iter(page.objects(NetObj))).pt2, QPoint(30, 0))

    def test_normalized_split_survives_undo_and_redo(self):
        class Controller:
            pass

        page = DocPage(MasterDocument(None))
        horizontal = NetObj(QPoint(0, 0), QPoint(10, 0))
        vertical = NetObj(QPoint(5, 0), QPoint(5, 10))
        page.addObj(horizontal)
        page.addObj(vertical)
        ctrl = Controller()
        ctrl.doc = page
        editor = NetEditor(ctrl, horizontal)

        editor._begin_drag(0, QPoint(5, 5), orthogonal=False)
        editor._commit()
        self.assertEqual(len(page.objects(NetObj)), 3)

        page.undo()
        self.assertEqual(len(page.objects(NetObj)), 2)
        self.assertTrue(any(net.pt1 == QPoint(0, 0) and net.pt2 == QPoint(10, 0)
                            for net in page.objects(NetObj)))

        page.redo()
        self.assertEqual(len(page.objects(NetObj)), 3)
        self.assertTrue(any(net.pt1 == QPoint(5, 0) and net.pt2 == QPoint(5, 5)
                            for net in page.objects(NetObj)))


class TestNetSegmentDrag(unittest.TestCase):
    @staticmethod
    def _coords(net):
        return (net.pt1.x(), net.pt1.y(), net.pt2.x(), net.pt2.y())

    def test_segment_drag_moves_the_selected_leg_and_l_corner(self):
        horizontal = NetObj(QPoint(0, 0), QPoint(10, 0))
        vertical = NetObj(QPoint(10, 0), QPoint(10, 10))
        unrelated = NetObj(QPoint(30, 0), QPoint(30, 10))
        session = NetDragSession.for_segment(
            [horizontal, vertical, unrelated], horizontal, QPoint(5, 0))

        session.update(QPoint(5, 5))

        self.assertEqual(self._coords(session.selected_preview), (0, 5, 10, 5))
        self.assertEqual(self._coords(session.preview[1]), (10, 5, 10, 10))
        self.assertEqual(self._coords(session.preview[2]), (30, 0, 30, 10))

    def test_default_segment_drag_preserves_a_t_shape_with_a_stretched_stem(self):
        left = NetObj(QPoint(0, 0), QPoint(10, 0))
        right = NetObj(QPoint(10, 0), QPoint(20, 0))
        stem = NetObj(QPoint(10, 0), QPoint(10, -10))
        session = NetDragSession.for_segment(
            [left, right, stem], left, QPoint(5, 0))

        session.update(QPoint(5, 5))

        self.assertEqual(self._coords(session.preview[0]), (0, 5, 10, 5))
        self.assertEqual(self._coords(session.preview[1]), (10, 0, 20, 0))
        self.assertEqual(self._coords(session.preview[2]), (10, 5, 10, -10))
        self.assertIn(NetObj(QPoint(10, 0), QPoint(10, 5)),
                      session.preview_additions)

    def test_default_vertex_drag_keeps_attached_segments_orthogonal(self):
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        branch = NetObj(QPoint(0, 0), QPoint(0, 10))
        session = NetDragSession(
            [selected, branch], selected, handle_index=0)

        session.update(QPoint(5, 5))

        self.assertEqual(self._coords(session.preview[0]), (5, 0, 10, 0))
        self.assertEqual(self._coords(session.preview[1]), (0, 5, 0, 10))
        self.assertIn(NetObj(QPoint(5, 0), QPoint(5, 5)),
                      session.preview_additions)
        self.assertIn(NetObj(QPoint(0, 5), QPoint(5, 5)),
                      session.preview_additions)

    def test_shift_segment_drag_restores_free_endpoint_stretching(self):
        left = NetObj(QPoint(0, 0), QPoint(10, 0))
        right = NetObj(QPoint(10, 0), QPoint(20, 0))
        stem = NetObj(QPoint(10, 0), QPoint(10, -10))
        session = NetDragSession.for_segment(
            [left, right, stem], left, QPoint(5, 0), orthogonal=False)

        session.update(QPoint(5, 5))

        self.assertEqual(self._coords(session.preview[1]), (10, 5, 20, 0))
        self.assertEqual(self._coords(session.preview[2]), (10, 5, 10, -10))
        self.assertEqual(session.preview_additions, [])

    def test_shift_vertex_drag_restores_free_form_endpoint_motion(self):
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        branch = NetObj(QPoint(0, 0), QPoint(0, 10))
        session = NetDragSession(
            [selected, branch], selected, handle_index=0, orthogonal=False)

        session.update(QPoint(5, 5))

        self.assertEqual(self._coords(session.preview[0]), (5, 5, 10, 0))
        self.assertEqual(self._coords(session.preview[1]), (5, 5, 0, 10))
        self.assertEqual(session.preview_additions, [])

    def test_alt_segment_drag_moves_only_the_selected_wire(self):
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        attached = NetObj(QPoint(10, 0), QPoint(20, 0))
        stem = NetObj(QPoint(10, 0), QPoint(10, -10))
        session = NetDragSession.for_segment(
            [selected, attached, stem], selected, QPoint(5, 0),
            maintain_connectivity=False)

        session.update(QPoint(5, 5))

        self.assertEqual(self._coords(session.preview[0]), (0, 5, 10, 5))
        self.assertEqual(self._coords(session.preview[1]), (10, 0, 20, 0))
        self.assertEqual(self._coords(session.preview[2]), (10, 0, 10, -10))
        self.assertEqual(session.preview_additions, [])

    def test_alt_vertex_drag_moves_only_the_selected_wire_endpoint(self):
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        attached = NetObj(QPoint(0, 0), QPoint(0, 10))
        session = NetDragSession(
            [selected, attached], selected, handle_index=0,
            maintain_connectivity=False)

        session.update(QPoint(5, 5))

        self.assertEqual(self._coords(session.preview[0]), (5, 5, 10, 0))
        self.assertEqual(self._coords(session.preview[1]), (0, 0, 0, 10))
        self.assertEqual(session.preview_additions, [])

    def test_segment_drag_stretches_wires_at_both_endpoints(self):
        left = NetObj(QPoint(-5, 0), QPoint(0, 0))
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        right = NetObj(QPoint(10, 0), QPoint(15, 0))
        session = NetDragSession.for_segment(
            [left, selected, right], selected, QPoint(5, 0), orthogonal=False)

        session.update(QPoint(7, 3))

        self.assertEqual(self._coords(session.preview[0]), (-5, 0, 2, 3))
        self.assertEqual(self._coords(session.selected_preview), (2, 3, 12, 3))
        self.assertEqual(self._coords(session.preview[2]), (12, 3, 15, 0))

    def test_segment_drag_moves_all_branches_at_a_grabbed_junction(self):
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        branch_a = NetObj(QPoint(10, 0), QPoint(10, 10))
        branch_b = NetObj(QPoint(10, 0), QPoint(15, 5))
        session = NetDragSession.for_segment(
            [selected, branch_a, branch_b], selected, QPoint(5, 0))

        session.update(QPoint(5, -4))

        self.assertEqual(self._coords(session.selected_preview), (0, -4, 10, -4))
        self.assertEqual(self._coords(session.preview[1]), (10, -4, 10, 10))
        self.assertEqual(self._coords(session.preview[2]), (10, -4, 15, 5))

    def test_segment_drag_does_not_propagate_through_the_remote_endpoint(self):
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        attached = NetObj(QPoint(10, 0), QPoint(20, 0))
        remote_branch = NetObj(QPoint(20, 0), QPoint(20, 10))
        session = NetDragSession.for_segment(
            [selected, attached, remote_branch], selected, QPoint(5, 0),
            orthogonal=False)

        session.update(QPoint(5, 5))

        self.assertEqual(self._coords(session.preview[1]), (10, 5, 20, 0))
        self.assertEqual(self._coords(session.preview[2]), (20, 0, 20, 10))

    def test_segment_drag_does_not_attach_to_an_interior_crossing(self):
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        crossing = NetObj(QPoint(5, -5), QPoint(5, 5))
        session = NetDragSession.for_segment(
            [selected, crossing], selected, QPoint(5, 0))

        session.update(QPoint(5, 5))

        self.assertEqual(self._coords(session.preview[1]), (5, -5, 5, 5))

    def test_segment_drag_reports_no_move_for_a_same_grid_click(self):
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        session = NetDragSession.for_segment([selected], selected, QPoint(5, 0))

        session.update(QPoint(5, 0))

        self.assertFalse(session.moved)
        self.assertEqual(self._coords(session.selected_preview), (0, 0, 10, 0))

    def test_collapsed_stretched_branch_is_removed_by_commit_normalization(self):
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        branch = NetObj(QPoint(10, 0), QPoint(10, 10))
        session = NetDragSession.for_segment(
            [selected, branch], selected, QPoint(5, 0))
        session.update(QPoint(5, 10))

        normalized = NetObj._normalizeGeometry(session.preview)

        self.assertEqual(len(normalized), 1)
        self.assertEqual(self._coords(normalized[0]), (0, 10, 10, 10))

    def test_mouse_events_start_a_body_drag_and_commit_one_undoable_graph_change(self):
        class View:
            @staticmethod
            def hitRadius():
                return 1

        class Controller:
            def __init__(self, page):
                self.doc = page
                self.view = View()

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        page = DocPage(MasterDocument(None))
        horizontal = NetObj(QPoint(0, 0), QPoint(10, 0))
        vertical = NetObj(QPoint(10, 0), QPoint(10, 10))
        page.addObj(horizontal)
        page.addObj(vertical)
        editor = NetEditor(Controller(page), horizontal)
        updates = []
        editor.sigUpdate.connect(lambda: updates.append(True))

        pressed = Event(Event.Type.MousePressed, QPoint(5, 0))
        moved = Event(Event.Type.MouseMoved, QPoint(5, 5))
        released = Event(Event.Type.MouseReleased, QPoint(5, 5))
        editor.handleEvent(pressed)
        editor.handleEvent(moved)

        # The document remains unchanged, but the editor must expose the
        # rubberband preview and request a repaint before mouse release.
        self.assertTrue(updates)
        self.assertIsNotNone(editor.previewObjects())
        self.assertIn(NetObj(QPoint(0, 5), QPoint(10, 5)),
                      editor.previewObjects())
        self.assertIn(NetObj(QPoint(10, 5), QPoint(10, 10)),
                      editor.previewObjects())
        self.assertIn(horizontal, page.objects(NetObj))
        self.assertIn(vertical, page.objects(NetObj))

        editor.handleEvent(released)

        self.assertTrue(pressed.handled)
        self.assertTrue(moved.handled)
        self.assertTrue(released.handled)
        self.assertEqual(page.undoStack.count(), 1)
        self.assertIn(NetObj(QPoint(0, 5), QPoint(10, 5)), page.objects(NetObj))
        self.assertIn(NetObj(QPoint(10, 5), QPoint(10, 10)), page.objects(NetObj))

        page.undo()
        self.assertIn(horizontal, page.objects(NetObj))
        self.assertIn(vertical, page.objects(NetObj))
        page.redo()
        self.assertIn(NetObj(QPoint(0, 5), QPoint(10, 5)), page.objects(NetObj))
        editor.dispose()

    def test_shift_modifier_selects_free_body_drag_mode(self):
        class View:
            @staticmethod
            def hitRadius():
                return 1

        class Controller:
            def __init__(self, page):
                self.doc = page
                self.view = View()

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        page = DocPage(MasterDocument(None))
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        attached = NetObj(QPoint(10, 0), QPoint(20, 0))
        page.addObj(selected)
        page.addObj(attached)
        editor = NetEditor(Controller(page), selected)

        shift = Qt.ShiftModifier
        editor.handleEvent(Event(Event.Type.MousePressed, QPoint(5, 0),
                                 modifiers=shift))
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(5, 5),
                                 modifiers=shift))

        self.assertEqual(self._coords(editor.previewObjects()[1]), (10, 5, 20, 0))
        self.assertEqual(editor._drag.preview_additions, [])
        editor.handleEvent(Event(Event.Type.MouseReleased, QPoint(5, 5),
                                 modifiers=shift))
        editor.dispose()

    def test_shift_modifier_selects_free_vertex_drag_mode(self):
        class View:
            @staticmethod
            def hitRadius():
                return 1

        class Controller:
            def __init__(self, page):
                self.doc = page
                self.view = View()

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        page = DocPage(MasterDocument(None))
        selected = NetObj(QPoint(0, 0), QPoint(10, 0))
        branch = NetObj(QPoint(0, 0), QPoint(0, 10))
        page.addObj(selected)
        page.addObj(branch)
        editor = NetEditor(Controller(page), selected)
        shift = Qt.ShiftModifier

        editor.handleEvent(Event(Event.Type.MousePressed, QPoint(0, 0),
                                 modifiers=shift))
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(5, 5),
                                 modifiers=shift))

        self.assertEqual(self._coords(editor.previewObjects()[0]), (5, 5, 10, 0))
        self.assertEqual(self._coords(editor.previewObjects()[1]), (5, 5, 0, 10))
        self.assertEqual(editor._drag.preview_additions, [])
        editor.handleEvent(Event(Event.Type.MouseReleased, QPoint(5, 5),
                                 modifiers=shift))
        editor.dispose()

    def test_body_drag_suppresses_endpoint_handles(self):
        class View:
            @staticmethod
            def hitRadius():
                return 1

        class Controller:
            def __init__(self, page):
                self.doc = page
                self.view = View()

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        class PainterSpy:
            def __init__(self):
                self.rects = 0

            def drawRect(self, *args):
                self.rects += 1

        page = DocPage(MasterDocument(None))
        net = NetObj(QPoint(0, 0), QPoint(10, 0))
        page.addObj(net)
        editor = NetEditor(Controller(page), net)
        editor._begin_segment_drag(QPoint(5, 0))

        spy = PainterSpy()
        editor.draw_handles(spy)

        self.assertEqual(spy.rects, 0)
        editor.dispose()

    def test_same_grid_body_click_does_not_create_an_undo_command(self):
        class View:
            @staticmethod
            def hitRadius():
                return 1

        class Controller:
            def __init__(self, page):
                self.doc = page
                self.view = View()

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        page = DocPage(MasterDocument(None))
        net = NetObj(QPoint(0, 0), QPoint(10, 0))
        page.addObj(net)
        editor = NetEditor(Controller(page), net)
        editor.handleEvent(Event(Event.Type.MousePressed, QPoint(5, 0)))
        editor.handleEvent(Event(Event.Type.MouseReleased, QPoint(5, 0)))

        self.assertEqual(page.undoStack.count(), 0)
        self.assertIn(net, page.objects(NetObj))
        editor.dispose()


if __name__ == "__main__":
    unittest.main()
