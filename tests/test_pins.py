import tempfile
import unittest
from pathlib import Path

import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

from sch.document import DocPage, MasterDocument, SymbolPage
from sch.obj.net import NetObj
from sch.obj.part import PartObj
from sch.obj.pin import PinObj
from sch.utils import Layer, LayerType
from sch.tools.part import PartEditor, PartTool
from sch.tools.net import NetTool
from sch.tools.group import GroupEditor
from sch.view import Event


class FakeLibrary:
    def __init__(self, symbol):
        self.symbol = symbol

    def getSym(self, path, name):
        return self.symbol if path == "symbols.xsch" and name == "U" else None

    def getSymList(self):
        return []


class TestPins(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def _symbol(self, pos=QPoint(5, 0)):
        document = MasterDocument(None)
        symbol = SymbolPage(document)
        symbol.name = "U"
        symbol.addObj(PinObj("1", "input", pos))
        return symbol

    def _page_with_part(self, pos=QPoint(0, 0)):
        symbol = self._symbol()
        library = FakeLibrary(symbol)
        document = MasterDocument(library)
        page = DocPage(document)
        part = PartObj(library, "symbols.xsch", "U", pos)
        page.addObj(part)
        return page, part

    def test_part_placement_snaps_origin_not_pin_marker_bbox(self):
        symbol = MasterDocument(None)
        master = SymbolPage(symbol)
        master.name = "U"
        master.addObj(PinObj("1", "input", QPoint(0, 0)))
        library = FakeLibrary(master)
        page = DocPage(MasterDocument(library))

        class Controller:
            doc = page
            lib = library

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        tool = PartTool(Controller())
        tool.onMasterChanged("symbols.xsch", "U")
        event = Event(Event.Type.MouseMoved, QPoint(5000, 10000))
        tool.handleEvent(event)

        self.assertTrue(event.handled)
        self.assertEqual(tool._obj.pos, QPoint(5000, 10000))
        self.assertEqual(tool._obj.pin_positions()[0][1], QPoint(5000, 10000))

    def test_wire_crossing_pin_is_split_and_pin_point_is_preserved(self):
        page, _ = self._page_with_part()
        page.addObj(NetObj(QPoint(0, 0), QPoint(10, 0)))

        actual = sorted(page.objects(NetObj),
                        key=lambda net: (net.pt1.x(), net.pt1.y()))
        self.assertEqual(actual, [
            NetObj(QPoint(0, 0), QPoint(5, 0)),
            NetObj(QPoint(5, 0), QPoint(10, 0)),
        ])

    def test_pin_is_connected_to_wire_and_directly_touching_pin(self):
        page, first = self._page_with_part()
        pin = next(iter(first.master.objects(objType=PinObj)))
        self.assertFalse(pin.is_connected(page, QPoint(5, 0), owner=first))

        page.addObj(NetObj(QPoint(0, 0), QPoint(5, 0)))
        self.assertTrue(pin.is_connected(page, QPoint(5, 0), owner=first))

        second = PartObj(first._lib, "symbols.xsch", "U", QPoint(0, 0))
        page.addObj(second)
        self.assertTrue(pin.is_connected(page, QPoint(5, 0), owner=first))

    def test_net_tool_ends_chain_when_endpoint_reaches_pin(self):
        page, _ = self._page_with_part(QPoint(0, 5))

        class Controller:
            doc = page

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        tool = NetTool(Controller())
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(0, 0)))
        tool.handleEvent(Event(Event.Type.MouseReleased, QPoint(5, 5)))

        self.assertIsNone(tool._firstPt)
        self.assertIn(NetObj(QPoint(0, 0), QPoint(5, 0)),
                      page.objects(NetObj))
        self.assertIn(NetObj(QPoint(5, 0), QPoint(5, 5)),
                      page.objects(NetObj))

    def test_pin_persistence_round_trip(self):
        source = MasterDocument(None)
        symbol = SymbolPage(source)
        symbol.name = "Connector"
        symbol.addObj(PinObj("A", "clock", QPoint(100, -200), 90))
        source._symbols.append(symbol)

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "pins.xsch"
            source.saveToFile(str(path))
            loaded = MasterDocument(None)
            loaded.loadFromFile(str(path))

        pin = next(iter(loaded.symbols[0].objects(objType=PinObj)))
        self.assertEqual((pin.id, pin.desc, pin.pos, pin.rot),
                         ("A", "clock", QPoint(100, -200), 90))

    def test_delete_multiple_pins_with_attached_displays(self):
        document = MasterDocument(None)
        symbol = SymbolPage(document)
        first = PinObj("1", "A", QPoint(0, 0))
        second = PinObj("2", "B", QPoint(5000, 0))
        symbol.addObj(first)
        symbol.addObj(second)

        class Controller:
            def __init__(self, doc):
                self.doc = doc

        selected = [first, *first.children(), second, *second.children()]
        editor = GroupEditor(Controller(symbol), selected)
        event = Event(Event.Type.KeyPressed, key=Qt.Key_Delete)
        editor.handleEvent(event)

        self.assertTrue(event.handled)
        self.assertEqual(symbol.objects(objType=PinObj), set())
        self.assertEqual(symbol.objects(), set())

    def test_pin_marker_uses_a_visible_cosmetic_pen(self):
        class PainterSpy:
            def __init__(self):
                self.pen = None
                self.rects = 0

            def save(self):
                pass

            def restore(self):
                pass

            def setPen(self, pen):
                self.pen = pen

            def setBrush(self, brush):
                pass

            def drawRect(self, rect):
                self.rects += 1

        painter = PainterSpy()
        PinObj().draw(painter)

        self.assertEqual(painter.pen.color(), Layer.color(LayerType.warning))
        self.assertEqual(painter.pen.width(), 0)
        self.assertEqual(painter.rects, 1)

    def _part_editor(self):
        page, part = self._page_with_part()
        page.addObj(NetObj(QPoint(5, 0), QPoint(20, 0)))

        class Controller:
            def __init__(self, page, library):
                self.doc = page
                self.lib = library

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        editor = PartEditor(Controller(page, part._lib), part)
        return page, part, editor

    def test_dragging_part_stretches_pin_wires_and_is_undoable(self):
        page, part, editor = self._part_editor()
        editor.handleEvent(Event(Event.Type.MousePressed, QPoint(5, 0)))
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(8, 5)))

        preview = editor.previewObjects()
        self.assertIn(NetObj(QPoint(8, 5), QPoint(23, 5)), preview)
        self.assertIn(NetObj(QPoint(5, 0), QPoint(20, 0)), page.objects(NetObj))

        editor.handleEvent(Event(Event.Type.MouseReleased, QPoint(8, 5)))
        self.assertEqual(part.pos, QPoint(3, 5))
        self.assertIn(NetObj(QPoint(8, 5), QPoint(23, 5)), page.objects(NetObj))

        page.undo()
        self.assertEqual(part.pos, QPoint(0, 0))
        self.assertIn(NetObj(QPoint(5, 0), QPoint(20, 0)), page.objects(NetObj))
        page.redo()
        self.assertEqual(part.pos, QPoint(3, 5))
        editor.dispose()

    def test_dragging_part_preserves_far_wire_junctions(self):
        page, part = self._page_with_part()
        page.addObj(NetObj(QPoint(5, 0), QPoint(20, 0)))
        page.addObj(NetObj(QPoint(20, 0), QPoint(20, 10)))

        class Controller:
            def __init__(self, page, library):
                self.doc = page
                self.lib = library

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        editor = PartEditor(Controller(page, part._lib), part)
        editor.handleEvent(Event(Event.Type.MousePressed, QPoint(5, 0)))
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(8, 5)))
        editor.handleEvent(Event(Event.Type.MouseReleased, QPoint(8, 5)))

        actual = sorted(((net.pt1, net.pt2) for net in page.objects(NetObj)),
                        key=lambda points: (points[0].x(), points[0].y(),
                                            points[1].x(), points[1].y()))
        self.assertIn((QPoint(8, 5), QPoint(23, 5)), actual)
        self.assertIn((QPoint(23, 5), QPoint(23, 10)), actual)
        editor.dispose()

    def test_dragging_part_does_not_add_connectors_to_a_jog(self):
        page, part = self._page_with_part()
        page.addObj(NetObj(QPoint(5, 0), QPoint(15, 0)))
        page.addObj(NetObj(QPoint(15, 0), QPoint(15, 10)))
        page.addObj(NetObj(QPoint(15, 10), QPoint(25, 10)))

        class Controller:
            def __init__(self, page, library):
                self.doc = page
                self.lib = library

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        editor = PartEditor(Controller(page, part._lib), part)
        editor.handleEvent(Event(Event.Type.MousePressed, QPoint(5, 0)))
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(8, 5)))
        editor.handleEvent(Event(Event.Type.MouseReleased, QPoint(8, 5)))

        actual = set((net.pt1, net.pt2) for net in page.objects(NetObj))
        self.assertEqual(actual, {
            (QPoint(8, 5), QPoint(18, 5)),
            (QPoint(18, 5), QPoint(18, 10)),
            (QPoint(18, 10), QPoint(25, 10)),
        })
        editor.dispose()

    def test_dragging_part_on_a_t_arm_moves_all_junction_branches(self):
        page, part = self._page_with_part(QPoint(15, 0))
        page.addObj(NetObj(QPoint(20, 0), QPoint(10, 0)))
        page.addObj(NetObj(QPoint(0, 0), QPoint(10, 0)))
        page.addObj(NetObj(QPoint(10, 0), QPoint(10, 10)))

        class Controller:
            def __init__(self, page, library):
                self.doc = page
                self.lib = library

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        editor = PartEditor(Controller(page, part._lib), part)
        editor.handleEvent(Event(Event.Type.MousePressed, QPoint(20, 0)))
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(20, 5)))
        editor.handleEvent(Event(Event.Type.MouseReleased, QPoint(20, 5)))

        actual = set((net.pt1, net.pt2) for net in page.objects(NetObj))
        self.assertEqual(actual, {
            (QPoint(0, 5), QPoint(10, 5)),
            (QPoint(10, 5), QPoint(20, 5)),
            (QPoint(10, 5), QPoint(10, 10)),
        })
        editor.dispose()

    def test_dragging_part_keeps_a_jog_break_until_release(self):
        page, part = self._page_with_part()
        page.addObj(NetObj(QPoint(5, 0), QPoint(15, 0)))
        page.addObj(NetObj(QPoint(15, 0), QPoint(15, 10)))
        page.addObj(NetObj(QPoint(15, 10), QPoint(25, 10)))

        class Controller:
            def __init__(self, page, library):
                self.doc = page
                self.lib = library

            @staticmethod
            def snapPt(point):
                return QPoint(point)

        editor = PartEditor(Controller(page, part._lib), part)
        editor.handleEvent(Event(Event.Type.MousePressed, QPoint(5, 0)))
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(5, 5)))
        self.assertEqual(len(editor.previewObjects()), 3)
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(5, 10)))

        preview = editor.previewObjects()
        self.assertIn(NetObj(QPoint(5, 10), QPoint(15, 10)), preview)
        self.assertIn(NetObj(QPoint(15, 10), QPoint(25, 10)), preview)
        self.assertNotIn(NetObj(QPoint(5, 10), QPoint(25, 10)), preview)

        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(5, 15)))
        self.assertIn(NetObj(QPoint(5, 15), QPoint(15, 15)),
                      editor.previewObjects())
        self.assertIn(NetObj(QPoint(15, 15), QPoint(15, 10)),
                      editor.previewObjects())
        self.assertIn(NetObj(QPoint(15, 10), QPoint(25, 10)),
                      editor.previewObjects())

        editor.handleEvent(Event(Event.Type.MouseReleased, QPoint(5, 15)))
        self.assertIn(NetObj(QPoint(5, 15), QPoint(15, 15)),
                      page.objects(NetObj))
        self.assertTrue(any(
            {net.pt1, net.pt2} == {QPoint(15, 15), QPoint(15, 10)}
            for net in page.objects(NetObj)))
        self.assertIn(NetObj(QPoint(15, 10), QPoint(25, 10)),
                      page.objects(NetObj))
        editor.dispose()

    def test_dragging_part_perpendicular_then_parallel_stretches_wire(self):
        page, part, editor = self._part_editor()
        editor.handleEvent(Event(Event.Type.MousePressed, QPoint(5, 0)))
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(5, 5)))
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(8, 5)))
        editor.handleEvent(Event(Event.Type.MouseReleased, QPoint(8, 5)))

        self.assertIn(NetObj(QPoint(8, 5), QPoint(20, 5)), page.objects(NetObj))
        editor.dispose()

    def test_alt_dragging_part_leaves_pin_wires_in_place(self):
        page, part, editor = self._part_editor()
        alt = Qt.AltModifier
        editor.handleEvent(Event(Event.Type.MousePressed, QPoint(5, 0), modifiers=alt))
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(8, 5), modifiers=alt))
        editor.handleEvent(Event(Event.Type.MouseReleased, QPoint(8, 5), modifiers=alt))

        self.assertEqual(part.pos, QPoint(3, 5))
        self.assertIn(NetObj(QPoint(5, 0), QPoint(20, 0)), page.objects(NetObj))
        editor.dispose()

    def test_shift_dragging_part_stretches_directly_to_the_pin(self):
        page, part, editor = self._part_editor()
        shift = Qt.ShiftModifier
        editor.handleEvent(Event(Event.Type.MousePressed, QPoint(5, 0), modifiers=shift))
        editor.handleEvent(Event(Event.Type.MouseMoved, QPoint(8, 5), modifiers=shift))
        editor.handleEvent(Event(Event.Type.MouseReleased, QPoint(8, 5), modifiers=shift))

        self.assertIn(NetObj(QPoint(8, 5), QPoint(20, 0)), page.objects(NetObj))
        editor.dispose()


if __name__ == "__main__":
    unittest.main()
