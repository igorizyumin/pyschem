"""
HierarchyResolver for navigation and validation of hierarchical schematics.

This module provides utilities for navigating and analyzing schematic hierarchy,
including finding child pages, ancestors, and validating the hierarchy structure.
"""

from typing import List, Tuple, Optional, Set
from sch.document import MasterDocument, DocPage
from sch.obj.sheetref import SheetRefObj


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
        visited_paths: Set[str] = set()
        
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
            nonlocal errors, visited_paths
            
            # Create a unique identifier for this page in the hierarchy
            path_key = "/".join(path)
            
            # Check for circular references
            if path_key in visited_paths:
                errors.append(f"Circular reference detected: {' -> '.join(path)}")
                return False
            
            visited_paths.add(path_key)
            
            # Limit recursion depth to prevent infinite loops
            if depth > 100:
                errors.append(f"Maximum hierarchy depth exceeded at: {' -> '.join(path)}")
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
        all_pages = list(self.master.pages)
        
        def collect_pages(page: DocPage):
            for sheet_ref, child_page in self.get_child_pages(page):
                if child_page is not None and child_page not in all_pages:
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