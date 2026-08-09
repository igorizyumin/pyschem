import unittest

from sch.document import DocPage, MasterDocument
from sch.library import PartLibrary
from sch.obj.sheetref import SheetRefObj
from sch.tools.hierarchy import HierarchyResolver


class TestHierarchyCycles(unittest.TestCase):
    def test_self_reference_does_not_recurse_forever(self):
        document = MasterDocument(PartLibrary())
        document.appendNewPage()
        page = document.pages[0]
        page.addSheetReference(SheetRefObj("", page.name))

        resolver = HierarchyResolver(document)
        self.assertEqual(resolver.get_all_pages(), [page])
        errors = resolver.validate_hierarchy()
        self.assertTrue(any("Circular reference" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
