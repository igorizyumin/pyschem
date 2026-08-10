import os
import copy
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint, Qt
from PySide6.QtWidgets import QApplication

from sch.document import DocPage, MasterDocument, SymbolPage, ObjChangeCmd
from sch.obj.net import NetObj
from sch.obj.netlabel import NetLabelObj
from sch.obj.part import PartObj
from sch.obj.pin import PinObj
from sch.obj.proptext import PropertyDisplay
from sch.obj.property import PropertyTemplate
from sch.tools.proptext import PropertyDisplayInspector
from sch.tools.proptext import PropTextTool
from sch.tools.select import SelectTool
from sch.tools.symbol import SymbolInspector
from sch.tools.pin import PinEditor, PinInspector


class FakeLibrary:
    def __init__(self, symbol):
        self.symbol = symbol

    def getSym(self, path, name):
        if path == "symbols.xsch" and name == self.symbol.name:
            return self.symbol
        return None


class TestProperties(unittest.TestCase):
    def _library(self):
        source = MasterDocument(None)
        symbol = SymbolPage(source)
        symbol.name = "Connector"
        symbol.add_property_template(
            PropertyTemplate("part.reference_prefix", "J", standard=True)
        )
        symbol.add_property_template(PropertyTemplate("part.value", "USB"))
        symbol.add_property_template(PropertyTemplate("part.tolerance", "1%"))
        symbol.addObj(PinObj("1", "A"))
        return FakeLibrary(symbol)

    def test_part_defaults_overrides_and_non_unique_references(self):
        library = self._library()
        page = DocPage(MasterDocument(library))
        first = PartObj(library, "symbols.xsch", "Connector")
        second = PartObj(library, "symbols.xsch", "Connector")
        page.addObj(first)
        page.addObj(second)

        self.assertEqual(first.reference_prefix, "J")
        self.assertEqual(first.reference, "J?")
        self.assertEqual(first.getProp("part.value"), "USB")
        self.assertEqual(second.getProp("part.tolerance"), "1%")

        first.reference_prefix = "CN"
        first.setProp("part.tolerance", "5%")
        first.reference = "J1"
        second.reference = "J1"

        self.assertEqual(first.reference_prefix, "CN")
        self.assertEqual(first.reference, "J1")
        self.assertEqual(second.reference, "J1")
        self.assertEqual(first.getProp("part.tolerance"), "5%")
        self.assertEqual(second.getProp("part.tolerance"), "1%")

    def test_pin_properties_are_shared_by_part_instances(self):
        library = self._library()
        first = PartObj(library, "symbols.xsch", "Connector")
        second = PartObj(library, "symbols.xsch", "Connector")
        first_pin = first.pins()[0]
        second_pin = second.pins()[0]

        self.assertIs(first_pin, second_pin)
        self.assertEqual(first_pin.getProp("pin.number"), "1")
        first_pin.setProp("pin.name", "DATA")
        first_pin.setProp("pin.electrical_type", "bidirectional")

        self.assertEqual(second_pin.getProp("pin.name"), "DATA")
        self.assertEqual(second_pin.getProp("pin.electrical_type"),
                         "bidirectional")

    def test_property_displays_are_attached_and_instance_specific(self):
        library = self._library()
        symbol = library.symbol
        pin = symbol.pins[0]

        pin_displays = pin.children()
        self.assertEqual({display.name for display in pin_displays},
                         {"pin.number", "pin.name"})
        self.assertTrue(all(display.parent is pin for display in pin_displays))
        self.assertTrue(all(display in symbol.objects() for display in pin_displays))

        first = PartObj(library, "symbols.xsch", "Connector")
        second = PartObj(library, "symbols.xsch", "Connector")
        self.assertIs(first.pins()[0].children()[0],
                      second.pins()[0].children()[0])
        first_displays = first.children()
        self.assertEqual({display.name for display in first_displays},
                         {"part.reference", "part.value"})
        self.assertTrue(all(display.parent is first for display in first_displays))

        first.reference = "J1"
        first_reference = next(display for display in first_displays
                               if display.name == "part.reference")
        second_reference = next(display for display in second.children()
                                if display.name == "part.reference")
        self.assertEqual(first_reference.value, "J1")
        self.assertEqual(second_reference.value, "J?")

        first_reference.pos = QPoint(1200, -800)
        first_reference.rot = 90
        first_reference.vis = False
        self.assertEqual((first_reference.pos, first_reference.rot),
                         (QPoint(1200, -800), 90))
        self.assertFalse(first_reference.vis)
        self.assertTrue(next(display for display in second.children()
                             if display.name == "part.reference").vis)
        self.assertTrue(next(display for display in symbol.objects()
                             if isinstance(display, PropertyDisplay)
                             and display.parent is symbol
                             and display.name == "part.reference").vis)

        third = copy.copy(first)
        self.assertTrue(all(display.parent is third
                            for display in third.children()))
        self.assertTrue(all(left is not right for left, right in
                            zip(first.children(), third.children())))

    def test_property_display_inspector_edits_visibility_without_editing_value(self):
        app = QApplication.instance() or QApplication([])
        pin = PinObj("1", "A")
        display = PropertyDisplay(pin, "pin.name")
        inspector = PropertyDisplayInspector(display)

        self.assertEqual(inspector.ui.cbProp.currentData(), "pin.name")
        self.assertEqual(inspector.ui.leValue.text(), "A")
        self.assertTrue(inspector.ui.leValue.isReadOnly())

        inspector.ui.cbVis.setChecked(False)
        self.assertFalse(display.vis)
        display.value = "DATA"
        self.assertEqual(pin.desc, "DATA")
        app.processEvents()

    def test_pin_display_text_refreshes_after_pin_property_edit(self):
        pin = PinObj("1", "A")
        display = PropertyDisplay(pin, "pin.number")
        self.assertEqual(display._text, "1")

        pin.setProp("pin.number", "2")
        display._updText()
        self.assertEqual(display._text, "2")

    def test_reference_display_exists_for_parts_without_templates(self):
        symbol = SymbolPage(MasterDocument(None))
        library = FakeLibrary(symbol)
        part = PartObj(library, "symbols.xsch", symbol.name)

        self.assertEqual(symbol.getProp("part.reference"), "?")
        self.assertIn("part.reference",
                      {display.name for display in part.children()})

    def test_symbol_attribute_display_tool_uses_a_real_property(self):
        app = QApplication.instance() or QApplication([])
        symbol = SymbolPage(MasterDocument(None))

        class FakeController:
            def __init__(self, doc):
                self.doc = doc

        tool = PropTextTool(FakeController(symbol))
        self.assertEqual(tool._obj.name, "part.reference")
        self.assertEqual(tool.inspector.ui.leValue.text(), "?")
        app.processEvents()

    def test_symbol_inspector_edits_global_defaults_and_is_default_selection_inspector(self):
        app = QApplication.instance() or QApplication([])
        symbol = SymbolPage(MasterDocument(None))
        symbol.add_property_template(PropertyTemplate("part.value", "10k"))

        class FakeController:
            def __init__(self, doc):
                self.doc = doc

        ctrl = FakeController(symbol)
        inspector = SymbolInspector(ctrl, symbol)
        self.assertIn("part.reference_prefix", inspector._property_widgets)
        self.assertIn("part.value", inspector._property_widgets)
        self.assertNotIn("part.reference", inspector._property_widgets)
        self.assertIsInstance(SelectTool(ctrl).inspector, SymbolInspector)

        value_editor = inspector._property_widgets["part.value"]
        value_editor.setText("47k")
        value_editor.editingFinished.emit()
        self.assertEqual(symbol.getProp("part.value"), "47k")
        symbol.undo()
        self.assertEqual(symbol.getProp("part.value"), "10k")
        symbol.redo()
        self.assertEqual(symbol.getProp("part.value"), "47k")
        app.processEvents()

    def test_symbol_reference_display_is_not_duplicated_on_reload(self):
        source = MasterDocument(None)
        symbol = SymbolPage(source)
        symbol.name = "Connector"
        symbol.add_property_template(
            PropertyTemplate("part.reference_prefix", "J", standard=True)
        )
        source._symbols.append(symbol)

        with tempfile.TemporaryDirectory() as temp:
            first_path = Path(temp) / "first.xsch"
            second_path = Path(temp) / "second.xsch"
            source.saveToFile(str(first_path))
            loaded = MasterDocument(None)
            loaded.loadFromFile(str(first_path))
            loaded.saveToFile(str(second_path))
            reopened = MasterDocument(None)
            reopened.loadFromFile(str(second_path))

        displays = [obj for obj in reopened.symbols[0].objects()
                    if isinstance(obj, PropertyDisplay)
                    and obj.parent is reopened.symbols[0]
                    and obj.name == "part.reference"]
        self.assertEqual(len(displays), 1)

    def test_pin_inspector_edits_standard_and_custom_properties(self):
        app = QApplication.instance() or QApplication([])
        pin = PinObj("1", "A")
        pin.setProp("pin.electrical_type", "passive")
        inspector = PinInspector(pin)

        self.assertIn("pin.number", inspector._property_widgets)
        self.assertIn("pin.name", inspector._property_widgets)
        self.assertIn("pin.electrical_type", inspector._property_widgets)

        name_editor = inspector._property_widgets["pin.name"]
        name_editor.setText("DATA")
        inspector._propertyEdited("pin.name", name_editor)
        self.assertEqual(pin.desc, "DATA")

        electrical_editor = inspector._property_widgets["pin.electrical_type"]
        electrical_editor.setText("bidirectional")
        inspector._propertyEdited("pin.electrical_type", electrical_editor)
        self.assertEqual(pin.getProp("pin.electrical_type"), "bidirectional")
        app.processEvents()

    def test_pin_editor_commits_property_edits_with_undo_redo(self):
        app = QApplication.instance() or QApplication([])
        page = SymbolPage(MasterDocument(None))
        pin = PinObj("1", "A")
        page.addObj(pin)

        class FakeController:
            def __init__(self, doc):
                self.doc = doc

            @staticmethod
            def snapPt(pos):
                return QPoint(pos)

        editor = PinEditor(FakeController(page), pin)
        name_editor = editor.inspector._property_widgets["pin.name"]
        name_editor.setText("DATA")
        name_editor.editingFinished.emit()
        self.assertEqual(pin.desc, "DATA")

        page.undo()
        self.assertEqual(pin.desc, "A")
        page.redo()
        self.assertEqual(pin.desc, "DATA")
        editor.dispose()
        app.processEvents()

    def test_part_property_override_undo_redo(self):
        library = self._library()
        page = DocPage(MasterDocument(library))
        part = PartObj(library, "symbols.xsch", "Connector")
        page.addObj(part)

        command = ObjChangeCmd(part)
        part.setProp("part.tolerance", "0.5%")
        page.doCommand(command)
        self.assertEqual(part.getProp("part.tolerance"), "0.5%")

        page.undo()
        self.assertEqual(part.getProp("part.tolerance"), "1%")
        page.redo()
        self.assertEqual(part.getProp("part.tolerance"), "0.5%")

    def test_net_label_is_graphical_and_semantics_neutral(self):
        page = DocPage(MasterDocument(None))
        label = NetLabelObj("CLK", QPoint(5, 0))
        label.setProp("net.diff_pair", "CLK_P")
        page.addObj(label)
        page.addObj(NetObj(QPoint(0, 0), QPoint(10, 0)))

        self.assertTrue(label.is_attached(page))
        self.assertEqual(len(label.attached_nets(page)), 2)
        self.assertEqual(label.getProp("net.name"), "CLK")
        self.assertEqual(label.getProp("net.diff_pair"), "CLK_P")

        other = NetLabelObj("CLK", QPoint(100, 100))
        page.addObj(other)
        self.assertFalse(other.is_attached(page))

    def test_part_and_net_label_properties_round_trip(self):
        library = self._library()
        source = MasterDocument(library)
        source._symbols.append(library.symbol)
        page = DocPage(source)
        part = PartObj(library, "symbols.xsch", "Connector")
        part.reference_prefix = "CN"
        part.reference = "CN?"
        part.setProp("part.tolerance", "0.5%")
        part.setProp("part.future_field", "preserve me")
        page.addObj(part)
        label = NetLabelObj("CLK", QPoint(5, 0))
        label.setProp("net.diff_pair", "CLK_P")
        page.addObj(label)
        page.addObj(NetObj(QPoint(0, 0), QPoint(10, 0)))
        source._pages.append(page)

        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "properties.xsch"
            source.saveToFile(str(path))
            loaded = MasterDocument(library)
            loaded.loadFromFile(str(path))

        loaded_page = loaded.pages[0]
        loaded_part = next(iter(loaded_page.objects(objType=PartObj)))
        self.assertEqual(loaded_part.reference_prefix, "CN")
        self.assertEqual(loaded_part.reference, "CN?")
        self.assertEqual(loaded_part.getProp("part.tolerance"), "0.5%")
        self.assertEqual(loaded_part.getProp("part.future_field"), "preserve me")

        loaded_label = next(iter(loaded_page.objects(objType=NetLabelObj)))
        self.assertEqual(loaded_label.getProp("net.name"), "CLK")
        self.assertEqual(loaded_label.getProp("net.diff_pair"), "CLK_P")
        self.assertTrue(loaded_label.is_attached(loaded_page))


if __name__ == "__main__":
    unittest.main()
