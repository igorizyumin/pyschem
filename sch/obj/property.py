"""
Property system for PySchem.

This module defines the property template and storage system that enables
template/instance separation for component properties.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any
import copy
from lxml import etree


@dataclass
class PropertyTemplate:
    """
    Defines a property on a symbol master.
    
    Templates are inherited by part instances, which can override values.
    """
    name: str
    """Unique name of the property (e.g., "Resistance", "Footprint").
    Must be unique within the symbol."""
    
    default_value: str = ""
    """Default value when a part is instantiated."""
    
    editable: bool = True
    """Can the user edit this property on the part instance?"""
    
    visible: bool = True
    """Should this property be displayed on the schematic?"""
    
    required: bool = False
    """Is this property required for valid instantiation?
    Violations can be reported by DRC plugins."""
    
    property_type: str = "text"
    """One of: "text", "number", "enum", "footprint", "reference"
    Used for UI rendering and validation."""
    
    enum_values: List[str] = field(default_factory=list)
    """If property_type is "enum", list valid values."""
    
    display_order: int = 0
    """Sort order in property inspectors (lower = first)."""
    
    def copy(self) -> 'PropertyTemplate':
        """Create a deep copy of this template."""
        return PropertyTemplate(
            name=self.name,
            default_value=self.default_value,
            editable=self.editable,
            visible=self.visible,
            required=self.required,
            property_type=self.property_type,
            enum_values=list(self.enum_values),
            display_order=self.display_order
        )
    
    def toXml(self) -> etree._Element:
        """
        Serialize this template to an XML element.
        
        Returns:
            XML element representing this property template
        """
        prop = etree.Element("prop")
        prop.set("name", self.name)
        prop.text = self.default_value or ""
        
        if not self.editable:
            prop.set("editable", "0")
        if not self.visible:
            prop.set("visible", "0")
        if self.required:
            prop.set("required", "1")
        if self.property_type and self.property_type != "text":
            prop.set("type", self.property_type)
        if self.display_order != 0:
            prop.set("order", str(self.display_order))
        
        return prop
    
    @staticmethod
    def fromXml(elem: etree._Element) -> 'PropertyTemplate':
        """
        Create a PropertyTemplate from an XML element.
        
        Args:
            elem: XML element containing property template data
            
        Returns:
            PropertyTemplate instance
        """
        name = elem.attrib.get("name", "")
        default_value = elem.text or ""
        editable = elem.attrib.get("editable", "1") == "1"
        visible = elem.attrib.get("visible", "1") == "1"
        required = elem.attrib.get("required", "0") == "1"
        property_type = elem.attrib.get("type", "text")
        display_order = int(elem.attrib.get("order", "0"))
        
        return PropertyTemplate(
            name=name,
            default_value=default_value,
            editable=editable,
            visible=visible,
            required=required,
            property_type=property_type,
            enum_values=[],
            display_order=display_order
        )


class Property:
    """
    A single property value on a part instance.
    
    Properties are immutable; to change a value, create a new Property.
    """
    
    def __init__(self, template: PropertyTemplate, value: str = None):
        """
        Initialize a property.
        
        Args:
            template: The PropertyTemplate this property is based on
            value: The value (override). If None, uses template default.
        """
        self._template = template
        self._value = value if value is not None else template.default_value
        self._is_default = (value is None)
    
    @property
    def name(self) -> str:
        """Get the property name."""
        return self._template.name
    
    @property
    def value(self) -> str:
        """Get the effective value (override or default)."""
        return self._value
    
    @property
    def template(self) -> PropertyTemplate:
        """Get the associated template."""
        return self._template
    
    @property
    def is_default(self) -> bool:
        """True if this is the template default (not an override)."""
        return self._is_default
    
    def override(self, new_value: str) -> 'Property':
        """Create a new Property with an override value."""
        return Property(self._template, new_value)
    
    def reset(self) -> 'Property':
        """Create a new Property that uses the template default."""
        return Property(self._template, None)
    
    def __repr__(self) -> str:
        return f"Property(name={self.name!r}, value={self.value!r}, is_default={self._is_default})"


class PartPropertyStore:
    """
    Manages effective properties for a part instance.
    
    Combines template definitions with instance overrides.
    """
    
    def __init__(self, templates: List[PropertyTemplate]):
        """
        Initialize with property templates from the symbol master.
        
        Args:
            templates: List of PropertyTemplate objects from the symbol
        """
        self._templates: Dict[str, PropertyTemplate] = {}
        self._overrides: Dict[str, str] = {}
        
        for template in templates:
            self._templates[template.name] = template
    
    def get(self, name: str) -> str:
        """
        Get the effective value for a property.
        
        Args:
            name: The property name
            
        Returns:
            The override value if set, otherwise template default.
            
        Raises:
            KeyError: If property name is unknown
        """
        if name not in self._templates:
            raise KeyError(f"Property '{name}' not found in templates")
        
        if name in self._overrides:
            return self._overrides[name]
        return self._templates[name].default_value
    
    def set(self, name: str, value: str) -> None:
        """
        Set an override value for a property.
        
        Args:
            name: The property name
            value: The override value
            
        Raises:
            KeyError: If property name is unknown
        """
        if name not in self._templates:
            raise KeyError(f"Property '{name}' not found in templates")
        
        self._overrides[name] = value
    
    def unset(self, name: str) -> None:
        """
        Remove an override, reverting to template default.
        
        Args:
            name: The property name
            
        Raises:
            KeyError: If property name is unknown
        """
        if name not in self._templates:
            raise KeyError(f"Property '{name}' not found in templates")
        
        if name in self._overrides:
            del self._overrides[name]
    
    def reset_all(self) -> None:
        """Remove all overrides."""
        self._overrides.clear()
    
    def names(self) -> List[str]:
        """Get all property names (templates + any overrides)."""
        return list(self._templates.keys())
    
    def templates(self) -> List[PropertyTemplate]:
        """Get all property templates."""
        return list(self._templates.values())
    
    def has_override(self, name: str) -> bool:
        """Check if a property has an explicit override."""
        return name in self._overrides
    
    def get_overrides(self) -> Dict[str, str]:
        """Get all overrides as a dictionary."""
        return dict(self._overrides)
    
    def get_property(self, name: str) -> Property:
        """
        Get a Property object for a property name.
        
        Args:
            name: The property name
            
        Returns:
            Property object with template and effective value
        """
        if name not in self._templates:
            raise KeyError(f"Property '{name}' not found in templates")
        
        template = self._templates[name]
        value = self._overrides.get(name, None)
        return Property(template, value)
    
    def set_property(self, name: str, value: str) -> None:
        """
        Set a property override.
        
        Wrapper around set() for API compatibility with existing code.
        """
        self.set(name, value)
    
    def reset_property(self, name: str) -> None:
        """
        Reset a property to its template default.
        
        Wrapper around unset() for API compatibility with existing code.
        """
        self.unset(name)
    
    def get_template(self, name: str) -> PropertyTemplate:
        """
        Get the template for a property.
        
        Args:
            name: The property name
            
        Returns:
            The PropertyTemplate
            
        Raises:
            KeyError: If property name is unknown
        """
        if name not in self._templates:
            raise KeyError(f"Property '{name}' not found in templates")
        return self._templates[name]