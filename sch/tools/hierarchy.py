"""
HierarchyResolver for navigation and validation of hierarchical schematics.

This module provides utilities for navigating and analyzing schematic hierarchy,
including finding child pages, ancestors, and validating the hierarchy structure.
"""

from pathlib import Path
from typing import List, Tuple, Optional, Set
from PySide6.QtCore import Signal, Slot, Qt, QPoint, QObject
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import QCheckBox, QFormLayout, QLineEdit, QWidget
from sch.document import MasterDocument, DocPage, ObjAddCmd
from sch.obj.sheetref import SheetRefObj
from sch.tools.base import BaseEditor, EditHandle


class HierarchyResolver:
    """
    Resolves hierarchical references between pages.
    
    Provides utilities for navigating and analyzing schematic hierarchy.
    """
    
    def __init__(self, master_doc: MasterDocument):
        """
        Initialize resolver for a document.
        
        Args:
            master_doc: The master document containing all pages
        """
        self.master = master_doc
        self._visited_pages: Set[str] = set()  # Track visited pages for cycle detection
    
    def get_child_pages(self, parent_page: DocPage) -> List[Tuple[SheetRefObj, DocPage]]:
        """
        Get all child pages referenced from this page.
        
        Args:
            parent_page: The parent page to get child pages for
            
        Returns:
            List of (sheet_ref, child_page) tuples.
            If a child page cannot be found, the child_page will be None.
        """
        children = []
        for sheet_ref in parent_page.sheetReferences():
            doc, page = sheet_ref.resolve_target()
            children.append((sheet_ref, page))
        return children
    
    def get_ancestors(self, page: DocPage) -> List[DocPage]:
        """
        Get ancestor pages from top-level down to this page.
        
        Args:
            page: The page to get ancestors for
            
        Returns:
            List of ancestor pages, starting from top-level.
            Does not include the page itself.
        """
        ancestors = []
        current_page = page
        visited = set()
        
        # Build a mapping of page name to page for quick lookup
        page_map = {p.name: p for p in self.master.pages}
        
        # Work backwards from the current page
        # Since we don't have direct parent references, we need to search
        # for which page contains this page as a child
        while True:
            found_parent = False
            
            # Check if we've visited this page (cycle detection)
            page_id = id(current_page)
            if page_id in visited:
                break
            visited.add(page_id)
            
            # Search for a page that references current_page
            for candidate_page in self.master.pages:
                if candidate_page is current_page:
                    continue
                    
                for sheet_ref, child_page in self.get_child_pages(candidate_page):
                    if child_page is current_page:
                        # Found the parent
                        if candidate_page not in ancestors:
                            ancestors.insert(0, candidate_page)
                        current_page = candidate_page
                        found_parent = True
                        break
            
            if not found_parent:
                break
        
        return ancestors
    
    def get_full_path(self, page: DocPage) -> List[Tuple[MasterDocument, DocPage]]:
        """
        Get the full hierarchical path to a page.
        
        Args:
            page: The page to get the path for
            
        Returns:
            List of (document, page) tuples from top to current.
        """
        path = []
        ancestors = self.get_ancestors(page)
        
        for ancestor in ancestors:
            path.append((ancestor.parentDoc, ancestor))
        
        # Add the current page
        path.append((page.parentDoc, page))
        
        return path
    
    def find_page(self, doc_path: str, page_name: str) -> Optional[DocPage]:
        """
        Find a page by document path and name.
        
        Args:
            doc_path: Path to the document
            page_name: Name of the page to find
            
        Returns:
            DocPage if found, None otherwise.
        """
        # First, check if the document is already loaded
        for doc in self.master.lib.documents if hasattr(self.master, 'lib') and self.master.lib else []:
            if hasattr(doc, 'fileName') and doc.fileName == doc_path:
                for page in doc.pages:
                    if page.name == page_name:
                        return page
        
        # Check if it's the current document
        if (hasattr(self.master, 'fileName') and 
            self.master.fileName == doc_path):
            for page in self.master.pages:
                if page.name == page_name:
                    return page
        
        # Try to resolve via sheet reference path resolution
        # This would require loading the external document
        return None
    
    def validate_hierarchy(self) -> List[str]:
        """
        Validate the hierarchy for errors.
        
        Checks for:
        - Missing sheet reference files
        - Missing referenced pages
        - Circular references
        - Invalid paths
        
        Args:
            master_doc: The master document to validate
            
        Returns:
            List of error messages (empty if valid).
        """
        errors = []
        active_pages: Set[str] = set()

        def page_key(page: DocPage) -> str:
            doc_path = getattr(page.parentDoc, "fileName", None)
            if doc_path:
                return f"{Path(doc_path).resolve()}::{page.name}"
            return f"memory:{id(page.parentDoc)}::{page.name}"
        
        def validate_page(page: DocPage, path: List[str], depth: int = 0) -> bool:
            """
            Recursively validate a page and its children.
            
            Args:
                page: Page to validate
                path: Current path of page names
                depth: Recursion depth
                
            Returns:
                True if valid, False if error found
            """
            nonlocal errors
            
            # Create a unique identifier for this page in the hierarchy
            path_key = page_key(page)
            
            # Check for circular references
            if path_key in active_pages:
                errors.append(f"Circular reference detected: {' -> '.join(path)}")
                return False

            active_pages.add(path_key)
            
            # Limit recursion depth to prevent infinite loops
            if depth > 100:
                errors.append(f"Maximum hierarchy depth exceeded at: {' -> '.join(path)}")
                active_pages.remove(path_key)
                return False
            
            # Validate each sheet reference on this page
            for sheet_ref in page.sheetReferences():
                ref_path = sheet_ref.path or "(no path)"
                ref_page = sheet_ref.page_name or "(no page name)"
                
                # Try to resolve the target
                doc, target_page = sheet_ref.resolve_target()
                
                if doc is None or target_page is None:
                    # Try to determine the error type
                    if not sheet_ref.path:
                        errors.append(f"Sheet reference '{ref_page}' on page '{page.name}' has no path")
                    elif not sheet_ref.page_name:
                        errors.append(f"Sheet reference with path '{ref_path}' on page '{page.name}' has no page name")
                    else:
                        # Check if file exists
                        import os
                        effective_path = sheet_ref.get_effective_path(page.parentDoc.fileName if hasattr(page.parentDoc, 'fileName') else None)
                        if not os.path.exists(effective_path):
                            errors.append(f"Sheet reference file not found: '{ref_path}' (referenced from page '{page.name}')")
                        else:
                            errors.append(f"Sheet reference page not found: '{ref_page}' in file '{ref_path}' (referenced from page '{page.name}')")
                else:
                    # Recursively validate the child page
                    child_path = path + [f"{ref_page} (from {ref_path})"]
                    validate_page(target_page, child_path, depth + 1)
            active_pages.remove(path_key)
            return True
        
        # Validate all top-level pages
        for page in self.master.pages:
            validate_page(page, [page.name])
        
        return errors
    
    def get_all_pages(self) -> List[DocPage]:
        """
        Get all pages in the hierarchy, including child pages.
        
        Returns:
            List of all DocPage objects in the hierarchy.
        """
        def page_key(page: DocPage) -> str:
            doc_path = getattr(page.parentDoc, "fileName", None)
            if doc_path:
                return f"{Path(doc_path).resolve()}::{page.name}"
            return f"memory:{id(page.parentDoc)}::{page.name}"

        all_pages = list(self.master.pages)
        visited = {page_key(page) for page in all_pages}
        
        def collect_pages(page: DocPage):
            for sheet_ref, child_page in self.get_child_pages(page):
                if child_page is not None and page_key(child_page) not in visited:
                    visited.add(page_key(child_page))
                    all_pages.append(child_page)
                    collect_pages(child_page)
        
        for page in self.master.pages:
            collect_pages(page)
        
        return all_pages
    
    def find_pages_by_name(self, page_name: str) -> List[Tuple[MasterDocument, DocPage]]:
        """
        Find all pages with a given name in the hierarchy.
        
        Args:
            page_name: Name of the page to find
            
        Returns:
            List of (document, page) tuples for all matching pages.
        """
        results = []
        
        for page in self.master.pages:
            if page.name == page_name:
                results.append((page.parentDoc, page))
            
            # Check child pages
            for sheet_ref, child_page in self.get_child_pages(page):
                if child_page is not None and child_page.name == page_name:
                    results.append((child_page.parentDoc, child_page))
        
        return results


class SheetRefInspector(QWidget):
    """Small editor for a sheet reference's project-relative target."""

    changed = Signal()

    def __init__(self, obj=None, parent=None):
        super().__init__(parent)
        self._obj = None
        self.path_edit = QLineEdit()
        self.page_edit = QLineEdit()
        self.label_visible = QCheckBox()
        self.label_visible.setChecked(True)
        form = QFormLayout(self)
        form.addRow("Child document", self.path_edit)
        form.addRow("Child page", self.page_edit)
        form.addRow("Show label", self.label_visible)
        self.path_edit.editingFinished.connect(self._emit_changed)
        self.page_edit.editingFinished.connect(self._emit_changed)
        self.label_visible.toggled.connect(self._emit_changed)
        self.obj = obj

    @property
    def obj(self):
        return self._obj

    @obj.setter
    def obj(self, value):
        self._obj = value
        blocked = self.blockSignals(True)
        if value is not None:
            self.path_edit.setText(value.path)
            self.page_edit.setText(value.page_name)
            self.label_visible.setChecked(value.label_visible)
        else:
            self.path_edit.clear()
            self.page_edit.clear()
        self.blockSignals(blocked)

    @Slot()
    def _emit_changed(self):
        if self._obj is not None:
            self._obj.path = self.path_edit.text().strip()
            self._obj.page_name = self.page_edit.text().strip()
            self._obj.label_visible = self.label_visible.isChecked()
            self.changed.emit()

    def create_object(self, pos: QPoint) -> SheetRefObj:
        obj = SheetRefObj(self.path_edit.text().strip(), self.page_edit.text().strip(), pos)
        obj.label_visible = self.label_visible.isChecked()
        return obj


class SheetRefTool(QObject):
    """Place a project-relative sheet reference at the clicked position."""

    sigUpdate = Signal()

    def __init__(self, ctrl):
        super().__init__()
        self._ctrl = ctrl
        self._pos = QPoint()
        self._inspector = SheetRefInspector()

    @staticmethod
    def name():
        return "Place Sheet Reference"

    @property
    def inspector(self):
        return self._inspector

    def finish(self):
        self.sigUpdate.emit()

    def draw(self, painter: QPainter):
        if self._inspector.page_edit.text().strip():
            preview = self._inspector.create_object(self._pos)
            preview.draw(painter)

    def handleEvent(self, event):
        from sch.view import Event
        if event.evType == Event.Type.MouseMoved:
            self._pos = self._ctrl.snapPt(event.pos)
            self.sigUpdate.emit()
            event.handled = True
        elif event.evType == Event.Type.MouseReleased:
            obj = self._inspector.create_object(self._pos)
            if obj.page_name:
                self._ctrl.doc.doCommand(ObjAddCmd(obj))
                event.handled = True


class SheetRefEditor(BaseEditor):
    """Edit position and target fields of an existing sheet reference."""

    def __init__(self, ctrl, obj):
        super().__init__(ctrl, obj)
        self._inspector = SheetRefInspector(obj)
        self._inspector.changed.connect(self._commit)

    def create_handles(self):
        self._handles = [EditHandle(self._ctrl, self._obj.pos)]

    def _setup_handle_connections(self):
        self._handles[0].sigDragged.connect(self._drag)
        self._handles[0].sigMoved.connect(self._commit)

    def update_handles(self):
        self._handles[0].pos = self._obj.pos

    @Slot('QPoint')
    def _drag(self, pos):
        self._obj.pos = pos
        self.sigUpdate.emit()

    def draw_custom(self, painter):
        painter.drawRect(self._obj.bbox())

    def handle_custom_event(self, event):
        super().handle_custom_event(event)
        if event.handled:
            return
        from sch.view import Event
        if event.evType == Event.Type.KeyPressed:
            if event.key == Qt.Key_R:
                self._obj.rot = self._obj.rot + 90
                self._commit()
                event.handled = True
            elif event.key == Qt.Key_V:
                self._obj.mirror = not self._obj.mirror
                self._commit()
                event.handled = True
