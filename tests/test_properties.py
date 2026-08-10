import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QPoint

from sch.document import DocPage, MasterDocument, SymbolPage, ObjChangeCmd
from sch.obj.net import NetObj
from sch.obj.netlabel import NetLabelObj
from sch.obj.part import PartObj
from sch.obj.pin import PinObj
from sch.obj.property import PropertyTemplate


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
