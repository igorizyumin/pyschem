"""
Port and PortDirection for hierarchical sheet references.

This module defines the port system that enables communication between
hierarchical schematic levels through sheet references.
"""

from enum import Enum
from typing import List, Tuple
from PySide6.QtCore import QPoint
from lxml import etree


class PortDirection(str, Enum):
    """
    Electrical direction of a port.
    
    Follows IEEE/ANSI standard conventions.
    """
    INPUT = "input"          # Signal flows into the block
    OUTPUT = "output"        # Signal flows out of the block
    BIDIRECTIONAL = "bidirectional"  # Signal can flow either direction
    PASSIVE = "passive"      # No direction (e.g., power, ground)
    UNCERTAIN = "uncertain"  # Direction not specified


class Port:
    """
    A connection point on a sheet reference.
    
    Ports enable communication between hierarchical levels.
    """
    
    def __init__(
        self,
        name: str,
        direction: PortDirection,
        visible: bool = True,
        label_position: QPoint = None,
        is_bus: bool = False,
        bus_width: int = 1,
        bus_start_index: int = 0,
        net_names: List[str] = None
    ):
        """
        Initialize a port.
        
        Args:
            name: Port name (e.g., "CLK", "VCC", "DATA[7:0]")
            direction: Electrical direction of the port
            visible: Should this port be displayed on the schematic?
            label_position: Position of port label relative to port pin
            is_bus: Is this a bus port (multiple signals)?
            bus_width: Width of bus if is_bus is True
            bus_start_index: Starting index for bus (e.g., DATA[0] vs DATA[7])
            net_names: Names of nets connected to this port
        """
        self.name = name
        self.direction = direction
        self.visible = visible
        self.label_position = label_position if label_position is not None else QPoint(0, 0)
        self.is_bus = is_bus
        self.bus_width = bus_width
        self.bus_start_index = bus_start_index
        self.net_names = list(net_names) if net_names else []
    
    def __str__(self) -> str:
        """String representation for display."""
        bus_str = f"[{self.bus_width}]" if self.is_bus else ""
        return f"Port({self.name}{bus_str}, {self.direction.value})"
    
    def is_single_bit(self) -> bool:
        """Check if this is a single-bit port (not a bus)."""
        return not self.is_bus
    
    def get_bus_range(self) -> Tuple[int, int]:
        """
        Get (start, end) indices for bus ports.
        
        Returns:
            Tuple of (start_index, end_index)
        """
        if not self.is_bus:
            return (self.bus_start_index, self.bus_start_index)
        return (self.bus_start_index, self.bus_start_index + self.bus_width - 1)
    
    def toXml(self) -> etree._Element:
        """
        Serialize this port to an XML element.
        
        Returns:
            XML element representing this port
        """
        port_elem = etree.Element("port")
        port_elem.set("name", self.name)
        port_elem.set("direction", self.direction.value)
        port_elem.set("visible", "1" if self.visible else "0")
        port_elem.set("isBus", "1" if self.is_bus else "0")
        
        if self.is_bus:
            port_elem.set("width", str(self.bus_width))
            port_elem.set("startIndex", str(self.bus_start_index))
        
        if self.label_position != QPoint(0, 0):
            port_elem.set("x", str(self.label_position.x()))
            port_elem.set("y", str(self.label_position.y()))
        
        # Store net names as comma-separated string
        if self.net_names:
            port_elem.set("nets", ",".join(self.net_names))
        
        return port_elem
    
    @staticmethod
    def fromXml(elem: etree._Element) -> 'Port':
        """
        Create a Port from an XML element.
        
        Args:
            elem: XML element containing port data
            
        Returns:
            Port instance
        """
        name = elem.attrib.get("name", "")
        direction_str = elem.attrib.get("direction", "uncertain")
        direction = PortDirection(direction_str)
        visible = elem.attrib.get("visible", "1") == "1"
        is_bus = elem.attrib.get("isBus", "0") == "1"
        bus_width = int(elem.attrib.get("width", "1")) if is_bus else 1
        bus_start_index = int(elem.attrib.get("startIndex", "0")) if is_bus else 0
        
        # Parse label position
        x = int(elem.attrib.get("x", "0"))
        y = int(elem.attrib.get("y", "0"))
        label_position = QPoint(x, y)
        
        # Parse net names
        nets_str = elem.attrib.get("nets", "")
        net_names = [n.strip() for n in nets_str.split(",") if n.strip()] if nets_str else []
        
        return Port(
            name=name,
            direction=direction,
            visible=visible,
            label_position=label_position,
            is_bus=is_bus,
            bus_width=bus_width,
            bus_start_index=bus_start_index,
            net_names=net_names
        )