"""
SheetRefObj for hierarchical schematic references.

This module defines the sheet reference object that enables multi-level
schematic design by referencing child pages.
"""

from pathlib import Path
from typing import List, Tuple, Dict, Optional
from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QBrush, QPainter, QPen, QTransform
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
        self._resolution_error = None
        self._resolved = None
    
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
        
        if Path(self.path).is_absolute():
            raise ValueError("Sheet references must use a relative project path")
        if not parent_doc_path:
            raise ValueError("A parent document path is required for sheet resolution")
        project_root = getattr(self._doc, "projectRoot", None)
        if project_root is None:
            project_root = Path(parent_doc_path).resolve().parent
        project_root = Path(project_root).resolve()
        candidate = (Path(parent_doc_path).resolve().parent / self.path).resolve()
        try:
            candidate.relative_to(project_root)
        except ValueError as error:
            raise ValueError("Sheet reference escapes the project directory") from error
        return str(candidate)

    @property
    def resolution_error(self):
        return self._resolution_error
    
    def resolve_target(self) -> Tuple[Optional['sch.document.MasterDocument'], Optional['sch.document.DocPage']]:
        """
        Resolve to actual document and page objects.
        
        Returns:
            Tuple of (MasterDocument, DocPage) if found, (None, None) otherwise.
        """
        if self._doc is None:
            return (None, None)
        self._resolution_error = None
        if not self.path:
            target_doc = self._doc
        else:
            try:
                effective_path = self.get_effective_path(self._doc.fileName)
                target_doc = self._doc.loadProjectDocument(effective_path)
            except Exception as error:
                self._resolution_error = str(error)
                return (None, None)

        if self._resolved is not None and self._resolved[0] is target_doc:
            return self._resolved
        for page in target_doc.pages:
            if page.name == self.page_name:
                self._resolved = (target_doc, page)
                return self._resolved

        self._resolution_error = f"Page '{self.page_name}' was not found"
        return (None, None)


    def getPortConnections(self) -> Dict[str, List[str]]:
        """
        Get port-to-net mappings.
        
        Returns:
            Dictionary mapping port names to list of connected net names.
            Used by netlist plugins.
        """
        return {port.name: port.net_names for port in self._ports}

    def _local_rect(self) -> QRect:
        return QRect(-self.WIDTH // 2, -self.HEIGHT // 2, self.WIDTH, self.HEIGHT)

    def _port_position(self, index: int) -> Tuple[QPoint, bool]:
        """Return a local port anchor and whether its label is on the left."""
        port = self._ports[index]
        side_ports = [p for p in self._ports
                      if p.direction in (PortDirection.INPUT, PortDirection.PASSIVE)]
        side_index = side_ports.index(port) if port in side_ports else index
        count = max(len(side_ports), 1) if port.direction in (
            PortDirection.INPUT, PortDirection.PASSIVE) else max(
                len(self._ports) - len(side_ports), 1)
        y = int(-self.HEIGHT // 2 + (side_index + 1) * self.HEIGHT / (count + 1))
        left = port.direction in (PortDirection.INPUT, PortDirection.PASSIVE)
        x = -self.WIDTH // 2 if left else self.WIDTH // 2
        return QPoint(x, y), left

    def draw(self, painter: QPainter) -> None:
        """Draw a sheet as a labeled rectangle with directional ports."""
        painter.save()
        painter.translate(self.pos)
        painter.rotate(self.rot)
        painter.scale(-1 if self.mirror else 1, 1)
        rect = self._local_rect()
        painter.setPen(QPen(Qt.darkBlue, 0))
        painter.setBrush(QBrush(Qt.NoBrush))
        painter.drawRect(rect)
        if self.label_visible:
            painter.drawText(rect, Qt.AlignCenter, self.page_name or "<sheet>")
        for index, port in enumerate(self._ports):
            anchor, left = self._port_position(index)
            painter.drawLine(anchor, QPoint(anchor.x() + (-1000 if left else 1000), anchor.y()))
            if self.port_label_style != "none" and port.visible:
                if self.port_label_style == "name":
                    label = port.name
                elif self.port_label_style == "direction":
                    label = port.direction.value
                else:
                    label = f"{port.name} ({port.direction.value})"
                label_rect = QRect(anchor.x() + (-5000 if left else 1200),
                                   anchor.y() - 500, 4800, 1000)
                painter.drawText(label_rect, Qt.AlignLeft if left else Qt.AlignRight, label)
        painter.restore()

    def bbox(self) -> QRect:
        transform = QTransform()
        transform.translate(self.pos.x(), self.pos.y())
        transform.rotate(self.rot)
        transform.scale(-1 if self.mirror else 1, 1)
        return transform.mapRect(self._local_rect()).normalized()

    def testHit(self, pt: QPoint, radius: int = 0) -> bool:
        return self.bbox().adjusted(-radius, -radius, radius, radius).contains(pt)
    
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
    WIDTH = 12000
    HEIGHT = 7000
