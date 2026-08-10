"""Shared property definitions and storage for schematic objects.

Properties have two distinct parts: a definition (metadata such as the
display label, type, and default) and a value (a local override or a value
provided by a standard-property accessor).  The same small store is used by
parts, symbol-master pins, and net-label annotations.
"""

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Optional

from lxml import etree


@dataclass
class PropertyDefinition:
    """Describe a property exposed by a :class:`PropertyStore`.

    ``name`` is a stable internal key.  It is deliberately not the same thing
    as the label shown by an inspector.  Standard properties are marked with
    ``standard``; their values may be backed by an accessor instead of the
    store's override dictionary.
    """

    name: str
    default_value: str = ""
    editable: bool = True
    visible: bool = True
    required: bool = False
    property_type: str = "text"
    enum_values: List[str] = field(default_factory=list)
    display_order: int = 0
    standard: bool = False
    label: Optional[str] = None

    @property
    def key(self) -> str:
        """Canonical key used by APIs, property text, and persistence."""
        return self.name

    @property
    def display_name(self) -> str:
        """Human-readable label, falling back to the stable key."""
        return self.label or self.name

    def copy(self) -> "PropertyDefinition":
        return PropertyDefinition(
            name=self.name,
            default_value=self.default_value,
            editable=self.editable,
            visible=self.visible,
            required=self.required,
            property_type=self.property_type,
            enum_values=list(self.enum_values),
            display_order=self.display_order,
            standard=self.standard,
            label=self.label,
        )

    def toXml(self) -> etree._Element:
        prop = etree.Element("prop", name=self.name)
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
        if self.label and self.label != self.name:
            prop.set("label", self.label)
        return prop

    @staticmethod
    def fromXml(elem: etree._Element) -> "PropertyDefinition":
        return PropertyDefinition(
            name=elem.attrib.get("name", ""),
            default_value=elem.text or "",
            editable=elem.attrib.get("editable", "1") == "1",
            visible=elem.attrib.get("visible", "1") == "1",
            required=elem.attrib.get("required", "0") == "1",
            property_type=elem.attrib.get("type", "text"),
            display_order=int(elem.attrib.get("order", "0")),
            label=elem.attrib.get("label"),
        )


# Compatibility name used by the original part-template implementation.
PropertyTemplate = PropertyDefinition


class Property:
    """A resolved property value and its definition."""

    def __init__(
        self,
        template: PropertyDefinition,
        value: str = None,
        is_default: Optional[bool] = None,
    ):
        self._template = template
        self._value = value if value is not None else template.default_value
        self._is_default = (value is None) if is_default is None else is_default

    @property
    def name(self) -> str:
        return self._template.name

    @property
    def value(self) -> str:
        return self._value

    @property
    def template(self) -> PropertyDefinition:
        return self._template

    @property
    def definition(self) -> PropertyDefinition:
        return self._template

    @property
    def is_default(self) -> bool:
        return self._is_default

    def override(self, new_value: str) -> "Property":
        return Property(self._template, new_value, is_default=False)

    def reset(self) -> "Property":
        return Property(self._template, None, is_default=True)

    def __repr__(self) -> str:
        return f"Property(name={self.name!r}, value={self.value!r}, is_default={self._is_default})"


Getter = Callable[[], str]
Setter = Callable[[str], None]


class PropertyStore:
    """Store definitions, local overrides, and optional standard accessors."""

    def __init__(
        self,
        definitions: Iterable[PropertyDefinition] = None,
        getters: Dict[str, Getter] = None,
        setters: Dict[str, Setter] = None,
        aliases: Dict[str, str] = None,
        allow_unknown: bool = False,
    ):
        self._definitions: Dict[str, PropertyDefinition] = {}
        self._overrides: Dict[str, str] = {}
        self._getters = dict(getters or {})
        self._setters = dict(setters or {})
        self._aliases = dict(aliases or {})
        self._allow_unknown = allow_unknown
        for definition in definitions or ():
            self.add_definition(definition)

    def _canonical(self, name: str) -> str:
        current = name
        seen = set()
        while current in self._aliases and current not in seen:
            seen.add(current)
            current = self._aliases[current]
        return current

    def add_definition(self, definition: PropertyDefinition) -> None:
        self._definitions[definition.name] = definition

    define = add_definition

    def get(self, name: str) -> str:
        key = self._canonical(name)
        if key in self._overrides:
            return self._overrides[key]
        getter = self._getters.get(key)
        if getter is not None:
            return getter()
        if key in self._definitions:
            return self._definitions[key].default_value
        raise KeyError(f"Property '{name}' not found")

    def set(self, name: str, value: str) -> None:
        key = self._canonical(name)
        if key not in self._definitions and not self._allow_unknown:
            raise KeyError(f"Property '{name}' not found in definitions")
        setter = self._setters.get(key)
        if setter is not None:
            setter(value)
            self._overrides.pop(key, None)
            return
        self._overrides[key] = "" if value is None else str(value)

    def unset(self, name: str) -> None:
        key = self._canonical(name)
        if key not in self._definitions and key not in self._overrides:
            raise KeyError(f"Property '{name}' not found")
        self._overrides.pop(key, None)
        setter = self._setters.get(key)
        if setter is not None and key in self._definitions:
            setter(self._definitions[key].default_value)

    def reset_all(self) -> None:
        self._overrides.clear()
        for key, setter in self._setters.items():
            definition = self._definitions.get(key)
            if definition is not None:
                setter(definition.default_value)

    def apply_overrides(self, values: Dict[str, str]) -> None:
        """Apply persisted values, retaining unknown keys for round-tripping."""
        for name, value in values.items():
            key = self._canonical(name)
            if key in self._definitions or self._allow_unknown:
                setter = self._setters.get(key)
                if setter is not None:
                    setter(value)
                else:
                    self._overrides[key] = value

    def names(self) -> List[str]:
        return list(self._definitions.keys()) + [
            key for key in self._overrides if key not in self._definitions
        ]

    def templates(self) -> List[PropertyDefinition]:
        return list(self._definitions.values())

    definitions = templates

    def has_override(self, name: str) -> bool:
        return self._canonical(name) in self._overrides

    def get_overrides(self) -> Dict[str, str]:
        return dict(self._overrides)

    def restore_overrides(self, values: Dict[str, str]) -> None:
        """Restore an override snapshot without touching standard fields."""
        self._overrides.clear()
        self._overrides.update(values)

    def get_property(self, name: str) -> Property:
        key = self._canonical(name)
        definition = self._definitions.get(key)
        if definition is None:
            if key not in self._overrides:
                raise KeyError(f"Property '{name}' not found")
            definition = PropertyDefinition(name=key)
        value = self.get(key)
        return Property(definition, value, is_default=not self.has_override(key))

    def set_property(self, name: str, value: str) -> None:
        self.set(name, value)

    def reset_property(self, name: str) -> None:
        self.unset(name)

    def get_template(self, name: str) -> PropertyDefinition:
        key = self._canonical(name)
        if key not in self._definitions:
            raise KeyError(f"Property '{name}' not found in definitions")
        return self._definitions[key]


class PartPropertyStore(PropertyStore):
    """Part properties: standard definitions plus master and instance data."""

    STANDARD_DEFINITIONS = (
        PropertyDefinition(
            "part.reference",
            "?",
            property_type="reference",
            standard=True,
            label="Reference",
            display_order=-20,
        ),
        PropertyDefinition(
            "part.reference_prefix",
            "?",
            standard=True,
            label="Reference prefix",
            display_order=-10,
        ),
    )

    def __init__(self, templates: Iterable[PropertyDefinition] = None):
        # Unknown values are accepted so users can preserve or add custom
        # fields before a formal definition is introduced on the master.
        super().__init__(
            definitions=self.STANDARD_DEFINITIONS,
            allow_unknown=True,
        )
        master_templates = list(templates or ())
        for template in master_templates:
            self.add_definition(template)
        # A master normally supplies the prefix while the reference itself is
        # an instance annotation.  Derive the initial placeholder from that
        # prefix unless the master explicitly supplied a reference default.
        if not any(t.name == "part.reference" for t in master_templates):
            prefix = self.get("part.reference_prefix")
            if prefix and prefix != "?":
                reference = self.get_template("part.reference").copy()
                reference.default_value = f"{prefix}?"
                self.add_definition(reference)
