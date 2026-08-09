"""Offscreen end-to-end tests for schematic mouse interactions."""

import os
import unittest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, Qt
from PySide6.QtGui import QMouseEvent, QTransform
from PySide6.QtWidgets import QApplication

from sch.controller import SchController
from sch.document import DocPage, MasterDocument
from sch.obj.line import LineObj
from sch.obj.net import NetObj
from sch.obj.text import TextObj
from sch.tools.group import GroupEditor
from sch.view import SchView


class GuiHarness:
    def __init__(self, objects, grid=5000):
        self.page = DocPage(MasterDocument(None))
        for obj in objects:
            self.page.addObj(obj)
        self.view = SchView()
        self.controller = SchController(self.page, self.view, None)
        self.view.setCtrl(self.controller)
        self.controller.grid = grid

    @property
    def tool(self):
        return self.controller._tool

    def mouse(self, event_type, world_pos, button, buttons):
        screen_pos = self.view._transform.map(world_pos)
        event = QMouseEvent(event_type, QPointF(screen_pos), QPointF(screen_pos),
                            button, buttons, Qt.NoModifier)
        if event_type == QEvent.Type.MouseButtonPress:
            self.view.mousePressEvent(event)
        elif event_type == QEvent.Type.MouseButtonRelease:
            self.view.mouseReleaseEvent(event)
        else:
            self.view.mouseMoveEvent(event)

    def press(self, point):
        self.mouse(QEvent.Type.MouseButtonPress, point,
                   Qt.LeftButton, Qt.LeftButton)

    def move(self, point):
        self.mouse(QEvent.Type.MouseMove, point,
                   Qt.NoButton, Qt.LeftButton)

    def release(self, point):
        self.mouse(QEvent.Type.MouseButtonRelease, point,
                   Qt.LeftButton, Qt.NoButton)


class TestGuiInteractions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_rectangle_selection_creates_group_editor(self):
        first = LineObj(QPoint(0, 0), QPoint(5000, 0))
        second = LineObj(QPoint(0, 10000), QPoint(5000, 10000))
        gui = GuiHarness([first, second])

        gui.press(QPoint(-5000, -5000))
        gui.move(QPoint(10000, 15000))
        gui.release(QPoint(10000, 15000))

        self.assertEqual(set(gui.tool._selection), {first, second})
        self.assertIsInstance(gui.tool._editor, GroupEditor)

    def test_group_drag_moves_lines_and_preserves_selection(self):
        first = LineObj(QPoint(0, 0), QPoint(5000, 0))
        second = LineObj(QPoint(0, 10000), QPoint(5000, 10000))
        gui = GuiHarness([first, second])
        gui.tool._selection = [first, second]
        gui.tool.selectionChanged()

        gui.press(QPoint(0, 0))
        gui.move(QPoint(5100, 0))

        # The document stays unchanged during rubberbanding.
        self.assertEqual(first.pt1, QPoint(0, 0))
        preview = gui.tool.previewDrawables()
        self.assertEqual(len(preview), 0)  # previews are editor-rendered
        self.assertEqual(gui.tool._editor._drag_controller.preview[0].pt1,
                         QPoint(5000, 0))

        gui.release(QPoint(5100, 0))
        moved = sorted(gui.page.objects(LineObj), key=lambda obj: obj.pt1.y())
        self.assertEqual([obj.pt1 for obj in moved],
                         [QPoint(5000, 0), QPoint(5000, 10000)])
        self.assertEqual(len(gui.tool._selection), 2)

    def test_clicking_outside_group_deselects_it(self):
        first = LineObj(QPoint(0, 0), QPoint(5000, 0))
        second = LineObj(QPoint(0, 10000), QPoint(5000, 10000))
        gui = GuiHarness([first, second])
        gui.tool._selection = [first, second]
        gui.tool.selectionChanged()
        self.assertIsInstance(gui.tool._editor, GroupEditor)
        updates = []
        gui.tool.sigUpdate.connect(lambda: updates.append(True))

        gui.press(QPoint(100000, 100000))
        # A real click commonly produces a tiny pointer movement.  It must
        # still count as a click when the snapped displacement is zero.
        gui.move(QPoint(101000, 100000))
        gui.release(QPoint(101000, 100000))

        self.assertEqual(gui.tool._selection, [])
        self.assertIsNone(gui.tool._editor)
        self.assertTrue(updates)

    def test_mixed_group_bounding_box_is_union_of_object_bounds(self):
        net = NetObj(QPoint(0, 0), QPoint(5000, 0))
        line = LineObj(QPoint(-5000, 10000), QPoint(5000, 10000))
        text = TextObj("Label", QPoint(10000, 5000))
        gui = GuiHarness([net, line, text])
        gui.tool._selection = [net, line, text]
        gui.tool.selectionChanged()
        self.assertIsInstance(gui.tool._editor, GroupEditor)

        expected = QRect()
        for obj in (net, line, text):
            expected = obj.bbox() if expected.isNull() else expected.united(obj.bbox())

        self.assertEqual(gui.tool._editor.bbox(), expected)

    def test_click_just_outside_exact_group_bounds_deselects(self):
        first = LineObj(QPoint(0, 0), QPoint(5000, 0))
        second = LineObj(QPoint(0, 10000), QPoint(5000, 10000))
        gui = GuiHarness([first, second])
        gui.tool._selection = [first, second]
        gui.tool.selectionChanged()
        bounds = gui.tool._editor.bbox()
        self.assertIsInstance(gui.tool._editor, GroupEditor)

        # This is outside the exact group box, but within the pixel-sized
        # drag tolerance used to begin a gesture.
        outside = QPoint(bounds.right() + 1000, bounds.center().y())
        gui.press(outside)
        gui.release(outside)

        self.assertEqual(gui.tool._selection, [])
        self.assertIsNone(gui.tool._editor)

    def test_mixed_net_and_text_drag_is_atomic_and_undoable(self):
        net = NetObj(QPoint(0, 0), QPoint(5000, 0))
        text = TextObj("Label", QPoint(0, 10000))
        gui = GuiHarness([net, text])
        gui.tool._selection = [net, text]
        gui.tool.selectionChanged()

        gui.press(QPoint(0, 0))
        gui.move(QPoint(5100, 0))

        editor = gui.tool._editor
        self.assertEqual(editor._net_preview[0].pt1, QPoint(5000, 0))
        self.assertEqual(editor._drag_controller.preview[0].pos,
                         QPoint(5000, 10000))
        self.assertIn(net, gui.page.objects(NetObj))
        self.assertIn(text, gui.page.objects(TextObj))

        gui.release(QPoint(5100, 0))
        moved_net = next(iter(gui.page.objects(NetObj)))
        moved_text = next(iter(gui.page.objects(TextObj)))
        self.assertEqual(moved_net.pt1, QPoint(5000, 0))
        self.assertEqual(moved_text.pos, QPoint(5000, 10000))

        gui.page.undo()
        restored_net = next(iter(gui.page.objects(NetObj)))
        restored_text = next(iter(gui.page.objects(TextObj)))
        self.assertEqual(restored_net.pt1, QPoint(0, 0))
        self.assertEqual(restored_text.pos, QPoint(0, 10000))

        gui.page.redo()
        self.assertEqual(next(iter(gui.page.objects(NetObj))).pt1,
                         QPoint(5000, 0))
        self.assertEqual(next(iter(gui.page.objects(TextObj))).pos,
                         QPoint(5000, 10000))

    def test_group_net_edit_keeps_unselected_nets_out_of_group(self):
        first = NetObj(QPoint(0, 0), QPoint(5000, 0))
        second = NetObj(QPoint(0, 10000), QPoint(5000, 10000))
        unrelated = NetObj(QPoint(30000, 0), QPoint(35000, 0))
        gui = GuiHarness([first, second, unrelated])
        gui.tool._selection = [first, second]
        gui.tool.selectionChanged()
        editor = gui.tool._editor

        move = QTransform()
        move.translate(5000, 0)
        editor._transform(move)

        self.assertEqual(len(editor._objects), 2)
        self.assertEqual(unrelated.pt1, QPoint(30000, 0))

        move_again = QTransform()
        move_again.translate(5000, 0)
        editor._transform(move_again)
        self.assertEqual(unrelated.pt1, QPoint(30000, 0))

    def test_group_net_drag_highlights_only_selected_preview_segments(self):
        first = NetObj(QPoint(0, 0), QPoint(5000, 0))
        second = NetObj(QPoint(0, 10000), QPoint(5000, 10000))
        unrelated = NetObj(QPoint(30000, 0), QPoint(35000, 0))
        gui = GuiHarness([first, second, unrelated])
        gui.tool._selection = [first, second]
        gui.tool.selectionChanged()
        editor = gui.tool._editor

        editor.startDrag(QPoint(0, 0))
        move = QTransform()
        move.translate(5000, 0)
        editor._transform_preview(move)

        self.assertEqual(len(editor.previewObjects()), 3)
        self.assertEqual(len(editor._selected_net_preview_objects()), 2)


if __name__ == "__main__":
    unittest.main()
