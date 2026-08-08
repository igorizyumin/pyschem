"""Regression tests for document persistence and net editing primitives."""

import os
import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QPoint

from sch.document import MasterDocument
from sch.document import DocPage
from sch.obj.net import NetObj
from sch.tools.net import NetEditor, NetTool


class TestNetRegression(unittest.TestCase):
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

        editor._dragPt1(QPoint(5, 5))

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

        editor._dragPt1(QPoint(5, 5))
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


if __name__ == "__main__":
    unittest.main()
