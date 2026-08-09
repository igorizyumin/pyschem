import tempfile
import unittest
from pathlib import Path

from PySide6.QtCore import QPoint

from sch.document import MasterDocument
from sch.library import PartLibrary
from sch.obj.sheetref import SheetRefObj
from sch.tools.hierarchy import HierarchyResolver


def save_symbol(path, name):
    document = MasterDocument(None)
    document.appendNewSymbol()
    document.symbols[0].name = name
    document.saveToFile(str(path))


def save_page_document(path, page_names, references=()):
    document = MasterDocument(None)
    for name in page_names:
        document.appendNewPage()
        document.pages[-1].name = name
    for page_index, ref in references:
        document.pages[page_index].addSheetReference(ref)
    document.saveToFile(str(path))


class TestLibraryPriority(unittest.TestCase):
    def test_project_then_user_then_system_precedence(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / "project"
            user = root / "user"
            system = root / "system"
            (project / "schlib").mkdir(parents=True)
            user.mkdir()
            system.mkdir()
            save_symbol(project / "schlib" / "shared.xsch", "Shared")
            save_symbol(user / "shared.xsch", "Shared")
            save_symbol(user / "user.xsch", "UserOnly")
            save_symbol(system / "shared.xsch", "Shared")
            save_symbol(system / "system.xsch", "SystemOnly")
            (system / "broken.xsch").write_text("<not-a-schematic/>", encoding="utf-8")

            library = PartLibrary(project_root=project,
                                  user_paths=[user], system_paths=[system])
            names = {name: path for path, values in library.getSymList()
                     for name in values}

            self.assertEqual(names["Shared"], str((project / "schlib" / "shared.xsch").resolve()))
            self.assertIn("UserOnly", names)
            self.assertIn("SystemOnly", names)
            self.assertTrue(any("broken.xsch" in message for message in library.diagnostics))


class TestProjectHierarchy(unittest.TestCase):
    def test_external_child_is_loaded_from_project_and_cached(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "sub").mkdir()
            save_page_document(root / "sub" / "child.xsch", ["Child"])
            root_doc = MasterDocument(None)
            root_doc.appendNewPage()
            root_doc.pages[0].name = "Root"
            root_doc.pages[0].addSheetReference(SheetRefObj("sub/child.xsch", "Child"))
            root_doc.saveToFile(str(root / "root.xsch"))

            loaded = MasterDocument(None)
            loaded.loadFromFile(str(root / "root.xsch"))
            ref = loaded.pages[0].sheetReferences()[0]
            doc, page = ref.resolve_target()

            self.assertIsNotNone(doc)
            self.assertEqual(page.name, "Child")
            self.assertIs(doc, ref.resolve_target()[0])
            self.assertEqual(doc.projectRoot, root.resolve())

    def test_absolute_and_escape_paths_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_page_document(root / "root.xsch", ["Root"])
            loaded = MasterDocument(None)
            loaded.loadFromFile(str(root / "root.xsch"))
            page = loaded.pages[0]
            absolute = SheetRefObj(str((root / "outside.xsch").resolve()), "Page")
            escape = SheetRefObj("../outside.xsch", "Page")
            missing = SheetRefObj("root.xsch", "Missing")
            page.addSheetReference(absolute)
            page.addSheetReference(escape)
            page.addSheetReference(missing)

            for ref in page.sheetReferences():
                self.assertEqual(ref.resolve_target(), (None, None))
                self.assertTrue(ref.resolution_error)

    def test_duplicate_page_names_use_document_order(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "child.xsch"
            save_page_document(path, ["Child", "Other"])
            document = MasterDocument(None)
            document.loadFromFile(str(path))
            document.pages[1].name = "Child"
            document.saveToFile(str(path))

            root = MasterDocument(None)
            root.appendNewPage()
            root.pages[0].addSheetReference(SheetRefObj("child.xsch", "Child"))
            root.saveToFile(str(Path(tmp) / "root.xsch"))
            loaded = MasterDocument(None)
            loaded.loadFromFile(str(Path(tmp) / "root.xsch"))
            _, page = loaded.pages[0].sheetReferences()[0].resolve_target()
            self.assertEqual(page.name, "Child")
            doc, _ = loaded.pages[0].sheetReferences()[0].resolve_target()
            self.assertIs(page, doc.pages[0])

    def test_external_cycle_is_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            save_page_document(root / "a.xsch", ["A"], [
                (0, SheetRefObj("b.xsch", "B"))
            ])
            save_page_document(root / "b.xsch", ["B"], [
                (0, SheetRefObj("a.xsch", "A"))
            ])
            document = MasterDocument(None)
            document.loadFromFile(str(root / "a.xsch"))
            resolver = HierarchyResolver(document)

            self.assertEqual(len(resolver.get_all_pages()), 2)
            self.assertTrue(any("Circular reference" in error
                                for error in resolver.validate_hierarchy()))


if __name__ == "__main__":
    unittest.main()
