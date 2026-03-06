"""
SheetRefObj for hierarchical schematic references.

This module defines the sheet reference object that enables multi-level
schematic design by referencing child pages.
"""

from typing import List, Tuple, Dict, Optional
from PySide6.QtCore import QPoint
from lxml import etree
import sch.obj.port
from sch.obj.port import Port, PortDirection


class SheetRefObj:
    """
    Represents a sheet reference on a schematic page.
    
    Sheet refs enable hierarchical schematic design by referencing
    other pages (in the same or different documents).
    """
    
    def __init__(
        self,
        doc_path: str,
        page_name: str,
        pos: QPoint = None,
        rot: int = 0,
        mirror: bool = False
    ):
        """
        Initialize a sheet reference.
        
        Args:
            doc_path: Path to child document (relative or absolute)
            page_name: Name of page within child document
            pos: Position on parent page
            rot: Rotation (0, 90, 180, 270 degrees)
            mirror: Horizontal flip flag
        """
        self.path = doc_path
        self.page_name = page_name
        self.pos = pos if pos is not None else QPoint(0, 0)
        self._rot = rot
        self._mirror = mirror
        self._ports: List[Port] = []
        self._label_visible = True
        self._port_label_style = "full"  # Options: "full", "name", "direction", "none"
        self._doc = None  # Reference to parent document (set when added to page)
    
    @property
    def rot(self) -> int:
        """Rotation (0, 90, 180, 270 degrees)."""
        return self._rot
    
    @rot.setter
    def rot(self, value: int):
        """Set rotation, normalizing to valid values."""
        self._rot = value % 360
        self._mirror = False  # Mirror is cleared on rotation change
    
    @property
    def mirror(self) -> bool:
        """Horizontal flip flag."""
        return self._mirror
    
    @mirror.setter
    def mirror(self, value: bool):
        self._mirror = value
    
    @property
    def ports(self) -> List[Port]:
        """Get list of ports defined on this sheet reference."""
        return list(self._ports)
    
    @property
    def label_visible(self) -> bool:
        """Check if the sheet reference label is visible."""
        return self._label_visible
    
    @label_visible.setter
    def label_visible(self, value: bool):
        self._label_visible = value
    
    @property
    def port_label_style(self) -> str:
        """Get the port label display style."""
        return self._port_label_style
    
    @port_label_style.setter
    def port_label_style(self, value: str):
        valid_styles = ["full", "name", "direction", "none"]
        if value in valid_styles:
            self._port_label_style = value
    
    def addPort(self, port: Port) -> None:
        """
        Add a port to this sheet reference.
        
        Args:
            port: Port to add
            
        Raises:
            ValueError: If a port with the same name already exists
        """
        for p in self._ports:
            if p.name == port.name:
                raise ValueError(f"Port '{port.name}' already exists on this sheet reference")
        self._ports.append(port)
    
    def removePort(self, port_name: str) -> bool:
        """
        Remove a port by name.
        
        Args:
            port_name: Name of port to remove
            
        Returns:
            True if port was removed, False if not found
        """
        for i, port in enumerate(self._ports):
            if port.name == port_name:
                del self._ports[i]
                return True
        return False
    
    def getPort(self, name: str) -> Optional[Port]:
        """
        Get a port by name.
        
        Args:
            name: Port name to find
            
        Returns:
            Port if found, None otherwise
        """
        for port in self._ports:
            if port.name == name:
                return port
        return None
    
    def get_effective_path(self, parent_doc_path: str = None) -> str:
        """
        Resolve relative path to absolute path.
        
        Args:
            parent_doc_path: Path to parent document (for resolving relative paths)
        
        Returns:
            Absolute path to child document.
        """
        if not self.path:
            return ""
        
        # If path is already absolute, return as-is
        if self.path.startswith("/") or (len(self.path) > 1 and self.path[1] == ":"):
            return self.path
        
        # If parent_doc_path is provided, resolve relative to it
        if parent_doc_path:
            import os
            parent_dir = os.path.dirname(parent_doc_path)
            return os.path.join(parent_dir, self.path)
        
        return self.path
    
    def resolve_target(self) -> Tuple[Optional['sch.document.MasterDocument'], Optional['sch.document.DocPage']]:
        """
        Resolve to actual document and page objects.
        
        Returns:
            Tuple of (MasterDocument, DocPage) if found, (None, None) otherwise.
        """
        if self._doc is None:
            return (None, None)
        
        # Try to find the page in the current document
        for page in self._doc.pages:
            if page.name == self.page_name:
                return (self._doc, page)
        
        # Try to load from external file
        try:
            effective_path = self.get_effective_path()
            import os
            if os.path.exists(effective_path):
                # Load the external document
                from sch.document import MasterDocument
                from sch.library import PartLibrary
                lib = PartLibrary()
                external_doc = MasterDocument(lib)
                external_doc.loadFromFile(effective_path)
                
                # Find the page
                for page in external_doc.pages:
                    if page.name == self.page_name:
                        return (external_doc, page)
        except Exception:
            pass
        
        return (None, None)
    
    def getPortConnections(self) -> Dict[str, List[str]]:
        """
        Get port-to-net mappings.
        
        Returns:
            Dictionary mapping port names to list of connected net names.
            Used by netlist plugins.
        """
        return {port.name: port.net_names for port in self._ports}
    
    def setDoc(self, doc: 'sch.document.MasterDocument') -> None:
        """
        Set the parent document reference.
        
        Args:
            doc: The parent MasterDocument
        """
        self._doc = doc
    
    def toXml(self, parent) -> None:
        """
        Serialize sheet reference to XML element.
        
        Args:
            parent: Parent XML element to append to
        """
        sheet_ref = etree.SubElement(
            parent, "sheetRef",
            docPath=self.path,
            pageName=self.page_name,
            x=str(self.pos.x()),
            y=str(self.pos.y()),
            rot=str(self.rot),
            mirror="1" if self.mirror else "0"
        )
        
        # Write label properties
        props = etree.SubElement(sheet_ref, "props")
        label_visible_prop = etree.SubElement(props, "prop", name="LabelVisible")
        label_visible_prop.text = "1" if self._label_visible else "0"
        
        port_label_style_prop = etree.SubElement(props, "prop", name="PortLabelStyle")
        port_label_style_prop.text = self._port_label_style
        
        # Write ports
        if self._ports:
            ports_elem = etree.SubElement(sheet_ref, "ports")
            for port in self._ports:
                ports_elem.append(port.toXml())
    
    @staticmethod
    def fromXml(elem, doc) -> 'SheetRefObj':
        """
        Create SheetRefObj from XML element.
        
        Args:
            elem: XML element containing sheet reference data
            doc: Parent MasterDocument instance
            
        Returns:
            SheetRefObj instance
        """
        doc_path = elem.attrib.get("docPath", "")
        page_name = elem.attrib.get("pageName", "")
        x = int(elem.attrib.get("x", "0"))
        y = int(elem.attrib.get("y", "0"))
        rot = int(elem.attrib.get("rot", "0"))
        mirror = elem.attrib.get("mirror", "0") == "1"
        
        obj = SheetRefObj(doc_path, page_name, QPoint(x, y), rot, mirror)
        obj.setDoc(doc)
        
        # Parse label properties
        props_elem = elem.find("props")
        if props_elem is not None:
            for prop in props_elem:
                if prop.tag == 'prop':
                    name = prop.attrib.get('name', '')
                    value = prop.text or ''
                    if name == "LabelVisible":
                        obj._label_visible = value == "1"
                    elif name == "PortLabelStyle":
                        obj._port_label_style = value
        
        # Parse ports
        ports_elem = elem.find("ports")
        if ports_elem is not None:
            for port_elem in ports_elem:
                if port_elem.tag == 'port':
                    port = Port.fromXml(port_elem)
                    obj._ports.append(port)
        
        return obj