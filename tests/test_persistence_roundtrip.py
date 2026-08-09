"""Round-trip coverage for the currently persisted document model."""

import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QPoint, Qt

from sch.document import DocPage, MasterDocument, SymbolPage
from sch.library import PartLibrary
from sch.obj.line import LineObj
from sch.obj.net import NetObj
from sch.obj.part import PartObj
from sch.obj.port import Port, PortDirection
from sch.obj.property import PartPropertyStore, PropertyTemplate
from sch.obj.sheetref import SheetRefObj
from sch.obj.text import TextObj
from sch.obj.proptext import PropTextObj
from sch.document import ObjChangeCmd


class TestPersistenceRoundTrip(unittest.TestCase):
    def test_supported_objects_and_properties_round_trip(self):
        lib = PartLibrary()
        source = MasterDocument(lib)

        symbol = SymbolPage(source)
        symbol.name = "Resistor"
        symbol.add_property_template(PropertyTemplate(
            "Value", "10k", editable=False, visible=True,
            required=True, property_type="text", display_order=2,
        ))
        source._symbols.append(symbol)

        page = DocPage(source)
        page.name = "Main"
        page.addObj(LineObj(QPoint(-2, 3), QPoint(4, 5), 7))
        page.addObj(NetObj(QPoint(0, 0), QPoint(10, 0)))
        page.addObj(TextObj("hello", QPoint(8, 9), Qt.AlignRight | Qt.AlignTop,
                            "Courier", 900, 90))

        sheet = SheetRefObj("child.xsch", "Child", QPoint(20, 30), 180, True)
        sheet.label_visible = False
        sheet.port_label_style = "name"
        sheet.addPort(Port("IN", PortDirection.INPUT, visible=False,
                           label_position=QPoint(2, 3), is_bus=True,
                           bus_width=8, bus_start_index=0,
                           net_names=["N1", "N2"]))
        page.addSheetReference(sheet)

        # A missing library master is valid persisted data; the instance is
        # still round-trippable and will be resolved when the library exists.
        part = PartObj(lib, "missing.xsch", "U1", QPoint(40, 50), 270, True)
        page.addObj(part)
        source._pages.append(page)

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "roundtrip.xsch"
            source.saveToFile(str(path))
            loaded = MasterDocument(lib)
            loaded.loadFromFile(str(path))

        self.assertEqual([s.name for s in loaded.symbols], ["Resistor"])
        template = loaded.symbols[0].property_templates[0]
        self.assertEqual((template.name, template.default_value), ("Value", "10k"))
        self.assertFalse(template.editable)
        self.assertTrue(template.required)
        self.assertEqual(template.display_order, 2)

        loaded_page = loaded.pages[0]
        self.assertEqual(loaded_page.name, "Main")
        self.assertEqual(len(loaded_page.objects(LineObj)), 1)
        self.assertEqual(len(loaded_page.objects(NetObj)), 1)
        text = next(iter(loaded_page.objects(TextObj)))
        self.assertEqual((text.text, text.pos, text.rot, text.family, text.ptSize),
                         ("hello", QPoint(8, 9), 90, "Courier", 900))
        loaded_sheet = loaded_page.sheetReferences()[0]
        self.assertEqual((loaded_sheet.path, loaded_sheet.page_name,
                          loaded_sheet.pos, loaded_sheet.rot, loaded_sheet.mirror),
                         ("child.xsch", "Child", QPoint(20, 30), 180, True))
        loaded_port = loaded_sheet.ports[0]
        self.assertEqual(loaded_port.direction, PortDirection.INPUT)
        self.assertEqual(loaded_port.label_position, QPoint(2, 3))
        self.assertEqual(loaded_port.net_names, ["N1", "N2"])
        loaded_part = next(obj for obj in loaded_page.objects(PartObj))
        self.assertEqual((loaded_part.path, loaded_part.name, loaded_part.pos,
                          loaded_part.rot, loaded_part.mirror),
                         ("missing.xsch", "U1", QPoint(40, 50), 270, True))

    def test_failed_load_does_not_replace_existing_document(self):
        document = MasterDocument(PartLibrary())
        document.appendNewPage()
        original_page = document.pages[0]

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "invalid.xsch"
            path.write_text("<xSchematic><props></props></xSchematic>", encoding="utf-8")
            with self.assertRaises(Exception):
                document.loadFromFile(str(path))

        self.assertIs(document.pages[0], original_page)

    def test_property_text_edit_restores_nested_part_property(self):
        lib = PartLibrary()
        page = DocPage(MasterDocument(lib))
        part = PartObj(lib)
        part._properties = part_property_store = PartPropertyStore(
            [PropertyTemplate("Value", "old")]
        )
        prop_text = PropTextObj(part, "Value")
        page.addObj(prop_text)

        command = ObjChangeCmd(prop_text)
        prop_text.value = "new"
        page.doCommand(command)
        self.assertEqual(part_property_store.get("Value"), "new")

        page.undo()
        self.assertEqual(part_property_store.get("Value"), "old")
        page.redo()
        self.assertEqual(part_property_store.get("Value"), "new")


if __name__ == "__main__":
    unittest.main()
