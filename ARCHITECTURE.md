# PySchem Architecture Documentation

**Version**: 1.0  
**Last Updated**: March 2026  
**Status**: Proposed Architecture

---

## Table of Contents

1. [Overview](#overview)
2. [Design Principles](#design-principles)
3. [Property System](#property-system)
4. [Hierarchical Sheet References](#hierarchical-sheet-references)
5. [Integration Points](#integration-points)
6. [Implementation Roadmap](#implementation-roadmap)
7. [File Format Extensions](#file-format-extensions)

---

## Overview

This document describes the core architecture for PySchem, a schematic capture application. The focus is on two foundational systems that enable extensibility while keeping the core clean:

1. **Part Property System** - How component properties are defined, stored, and managed
2. **Hierarchical Sheet References** - How multi-level schematic design is structured

The architecture prioritizes:
- **Clean separation** between the symbol, the implementation (schematic, SPICE model, etc), and the instance (the instantiation of the symbol on a schematic page)
- **Explicit hierarchy** for multi-level schematic design. Hierarchical instances are treated similarly to parts.
- **Extensibility** via plugins to support diverse use cases (simulator front-end, PCB layout, custom IC design...)
- **Simplicity** in the core, pushing complexity to optional features (plugins)

---

## Design Principles

### 1. Minimal Core
The core application provides only essential schematic drawing capabilities. Advanced features (netlist generation, BOM, simulation, DRC) are implemented as plugins.

### 2. Template/Instance Separation
Symbol masters define templates; part instances store only overrides and may add additional properties. This enables:
- Reset to defaults
- Easy symbol library updates
- Clear data ownership

### 3. Deferred Connectivity
Net connectivity is extracted on-demand (for netlist export or DRC), not maintained during editing. This avoids premature commitments to net names or topologies. Connectivity is established by placing graphical symbols (net names, power rails, ports, etc.), and the actual netlist must be defined by the graphical representation.

### 4. Explicit Hierarchy
Sheet references are first-class objects with explicit port definitions. This enables:
- Clear port-to-port connections
- Direction-based analysis
- Bus support with per-bit net names
- Graphical port representation connected to nets

### 5. String-Based Values
All property values are stored as strings. This provides:
- XML-friendly serialization
- No type definition complexity
- Flexibility and extensibility.  The tool does not need to be concerned with the semantics of a given property.

### 6. Port Rendering
Ports on sheet references have graphical representation:
- Port objects (PortObj) are drawn at connection points
- Port labels are positioned relative to port pins (default ~500 units)
- Port labels are draggable when editing
- Ports connect to nets by name
- All ports are visible (no visibility toggle)

---

## Property System

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Symbol Master                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  PropertyTemplate                                             │   │
│  │  - name: "Resistance"                                        │   │
│  │  - default_value: "10k"                                      │   │
│  │  - editable: true                                            │   │
│  │  - visible: true                                             │   │
│  │  - required: false                                           │   │
│  │  - property_type: "text"                                     │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ defines
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         Part Instance                               │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  PartPropertyStore                                          │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  _templates: {name -> PropertyTemplate}             │   │   │
│  │  │  _overrides: {name -> value}                        │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  │                                                             │   │
│  │  get("Resistance") → "10k" (from override)                 │   │
│  │  get("Footprint") → "0805" (from template default)         │   │
│  │  get("Power") → "1/4W" (from template default)             │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Class Specifications

#### PropertyTemplate

```python
class PropertyTemplate:
    """
    Defines a property on a symbol master.
    
    Templates are inherited by part instances, which can override values.
    """
    
    name: str
        """Unique name of the property (e.g., "Resistance", "Footprint").
        Must be unique within the symbol."""
    
    default_value: str
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
    
    enum_values: List[str] = []
        """If property_type is "enum", list valid values."""
    
    display_order: int = 0
        """Sort order in property inspectors (lower = first)."""
```

#### Property

```python
class Property:
    """
    A single property value on a part instance.
    
    Properties are immutable; to change a value, create a new Property.
    """
    
    name: str
    value: str
    is_default: bool
        """True if this is the template default (not an override)."""
    
    def override(self, new_value: str) -> 'Property':
        """Create a new Property with an override value."""
    
    def reset(self) -> 'Property':
        """Create a new Property that uses the template default."""
```

#### PartPropertyStore

```python
class PartPropertyStore:
    """
    Manages effective properties for a part instance.
    
    Combines template definitions with instance overrides.
    """
    
    def __init__(self, templates: List[PropertyTemplate]):
        """Initialize with property templates from the symbol master."""
    
    def get(self, name: str) -> str
        """
        Get the effective value for a property.
        
        Returns override value if set, otherwise template default.
        Raises KeyError if property name is unknown.
        """
    
    def set(self, name: str, value: str)
        """
        Set an override value for a property.
        
        Creates an override if none exists, updates existing override.
        """
    
    def unset(self, name: str)
        """
        Remove an override, reverting to template default.
        
        No-op if no override existed.
        """
    
    def reset_all()
        """Remove all overrides."""
    
    def names(self) -> List[str]
        """Get all property names (templates + any overrides)."""
    
    def templates(self) -> List[PropertyTemplate]
        """Get all property templates."""
    
    def has_override(self, name: str) -> bool
        """Check if a property has an explicit override."""
    
    def get_overrides(self) -> Dict[str, str]
        """Get all overrides as a dictionary."""
```

### PartObj Integration

```python
class PartObj:
    """
    Represents an instantiated component on a schematic page.
    """
    
    def __init__(self, lib, path=None, name=None, pos=QPoint(0, 0), 
                 rot=0, mirror=False):
        """
        Initialize a part instance.
        
        Args:
            lib: PartLibrary instance for symbol lookup
            path: Path to symbol file (relative to library paths)
            name: Name of symbol within the file
            pos: Position on page
            rot: Rotation (0, 90, 180, 270 degrees)
            mirror: Horizontal flip flag
        """
        self._lib = lib
        self._master_ref = (path, name)
        self._properties = None  # Lazy-initialized PartPropertyStore
        self._pos = pos
        self._rot = rot
        self._mirror = mirror
    
    @property
    def master(self) -> SymbolPage:
        """
        Get the master symbol this part is based on.
        
        Returns None if the master cannot be found.
        """
    
    @property
    def properties(self) -> PartPropertyStore:
        """
        Get the property store for this part.
        
        Initializes from master templates on first access.
        """
    
    def getProp(self, name: str) -> str
        """Get a property value (wrapper around properties.get())."""
    
    def setProp(self, name: str, value: str)
        """Set a property override (wrapper around properties.set())."""
    
    def getPropertyTemplates(self) -> List[PropertyTemplate]
        """Get all property templates from the master symbol."""
    
    def resetProperty(self, name: str)
        """Reset a property to its template default."""
    
    def resetAllProperties()
        """Reset all properties to template defaults."""
    
    def hasUnsavedChanges(self) -> bool
        """Check if any properties have unsaved overrides."""
```

### UI Integration

#### Property Inspector Widget

```python
class PropertyInspector(QDockWidget):
    """
    Displays and edits properties of selected objects.
    """
    
    def updateForObject(self, obj: Object)
        """
        Update inspector to show properties of the given object.
        
        For PartObj:
        - Shows all property templates from master
        - Shows instance-specific properties (e.g., RefDes)
        - Each property has editable value field
        - Reset button for each override
        
        For SheetRefObj:
        - Shows sheet path, page name
        - Shows port configuration
        """
    
    def _createPropertyWidget(self, template: PropertyTemplate, 
                              part: PartObj) -> QWidget
        """Create an editor widget for a property."""
```

---

## Hierarchical Sheet References

### Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────┐
│                      Top-Level Schematic                            │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Part: U1 (MCU_ATmega328P)                                  │   │
│  │  Part: R1 (Resistor)                                        │   │
│  │                                                             │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  Sheet Reference: "PowerSupply"                     │   │   │
│  │  │  ├─ docPath: "../power/power_supply.xsch"          │   │   │
│  │  │  ├─ pageName: "PowerSupply"                        │   │   │
│  │  │  ├─ Ports:                                          │   │   │
│  │  │  │  ├─ VCC (input) ────┐                            │   │   │
│  │  │  │  ├─ GND (passive) ───┼─── Net: GND_NET          │   │   │
│  │  │  │  └─ OUTPUT (output)──┘                            │   │   │
│  │  │  └─ Label: "Power Supply"                           │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
                              │
                              │ references
                              ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   Child Document: power_supply.xsch                 │
│  ┌─────────────────────────────────────────────────────────────┐   │
│  │  Page: "PowerSupply"                                        │   │
│  │  ┌─────────────────────────────────────────────────────┐   │   │
│  │  │  Part: U2 (LM317)                                   │   │   │
│  │  │  Part: C1 (Capacitor)                               │   │   │
│  │  │                                                     │   │   │
│  │  │  ┌─────────────────────────────────────────────┐   │   │   │
│  │  │  │  Port: VCC (input)  ← connected from top   │   │   │   │
│  │  │  │  Port: GND (passive)                       │   │   │   │
│  │  │  │  Port: OUTPUT (output) → connected to top  │   │   │   │
│  │  │  └─────────────────────────────────────────────┘   │   │   │
│  │  └─────────────────────────────────────────────────────┘   │   │
│  └─────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

### Class Specifications

#### PortDirection

```python
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
```

#### Port

```python
class Port:
    """
    A connection point on a sheet reference.
    
    Ports enable communication between hierarchical levels.
    """
    
    name: str
        """Port name (e.g., "CLK", "VCC", "DATA[0..15]").
        Must be unique within the sheet reference.
        Supports bus syntax: DATA[0..15] or heterogeneous: DATA[0..7],CLK,SDI,SDO."""
    
    direction: PortDirection
        """Electrical direction of the port."""
    
    label_position: QPoint = QPoint(0, 0)
        """Position of port label relative to port pin.
        Default is aligned some distance (e.g., 500 units) from port.
        User can adjust position when editing the schematic."""
    
    bus_nets: List[str] = []
        """Per-bit net names for bus ports.
        Parsed from port name using bus syntax.
        Examples:
          - "DATA[0..15]" → ["DATA[0]", "DATA[1]", ..., "DATA[15]"]
          - "ADDR[8:0]" → ["ADDR[8]", "ADDR[7]", ..., "ADDR[0]"]
          - "DATA[0..7],CLK,SDI,SDO" → ["DATA[0]", ..., "DATA[7]", "CLK", "SDI", "SDO"]
        For single-bit ports, this list contains just the port name."""
    
    net_names: List[str] = []
        """Names of nets connected to this port (for netlist generation).
        Populated when ports are connected in parent scope."""
    
    def __str__(self) -> str:
        """String representation for display."""
    
    @staticmethod
    def parse_bus_syntax(port_name: str) -> Tuple[str, List[str]]:
        """
        Parse port name and return (base_name, per_bit_nets).
        
        Examples:
          - "DATA[0..15]" → ("DATA", ["DATA[0]", ..., "DATA[15]"])
          - "DATA[8:0]" → ("DATA", ["DATA[8]", ..., "DATA[0]"])
          - "DATA[0..7],CLK,SDI,SDO" → ("DATA", ["DATA[0]", ..., "DATA[7]", "CLK", "SDI", "SDO"])
          - "CLK" → ("CLK", ["CLK"])
        """
    
    def is_single_bit(self) -> bool:
        """Check if this is a single-bit port (not a bus)."""
    
    def get_bus_range(self) -> Tuple[int, int]:
        """Get (start, end) indices for bus ports. Returns None for non-bus ports."""
```

#### SheetRefObj

```python
class SheetRefObj:
    """
    Represents a sheet reference on a schematic page.
    
    Sheet refs enable hierarchical schematic design by referencing
    other pages (in the same or different documents).
    """
    
    def __init__(self, doc_path: str, page_name: str, pos=QPoint(0, 0)):
        """
        Initialize a sheet reference.
        
        Args:
            doc_path: Path to child document (relative or absolute)
            page_name: Name of page within child document
            pos: Position on parent page
        """
        self.path = doc_path
        self.page_name = page_name
        self.pos = pos
        self._rot = 0
        self._mirror = False
        self._ports: List[Port] = []
        self._label_visible = True
        self._port_label_style = PortLabelStyle.FULL
    
    @property
    def rot(self) -> int
        """Rotation (0, 90, 180, 270 degrees)."""
    
    @rot.setter
    def rot(self, value: int)
    
    @property
    def mirror(self) -> bool
        """Horizontal flip flag."""
    
    @mirror.setter
    def mirror(self, value: bool)
    
    @property
    def ports(self) -> List[Port]:
        """Get list of ports defined on this sheet reference.
        Port names must be unique."""
    
    @property
    def portObjs(self) -> List['PortObj']:
        """Get graphical port objects for rendering.
        One PortObj per port (or per bit for bus ports)."""
    
    def addPort(self, port: Port)
        """Add a port to this sheet reference."""
    
    def removePort(self, port_name: str)
        """Remove a port by name."""
    
    def getPort(self, name: str) -> Port
        """Get a port by name, or None if not found."""
    
    def get_effective_path(self, parent_doc_path: str = None) -> str
        """
        Resolve relative path to absolute path.
        
        Args:
            parent_doc_path: Path to parent document (for resolving relative paths)
        
        Returns:
            Absolute path to child document.
        """
    
    def resolve_target(self) -> Tuple[MasterDocument, DocPage]
        """
        Resolve to actual document and page objects.
        
        Returns:
            Tuple of (MasterDocument, DocPage) if found, (None, None) otherwise.
        """
    
    def getPortConnections(self) -> Dict[str, List[str]]
        """
        Get port-to-net mappings.
        
        Returns:
            Dictionary mapping port names to list of connected net names.
            Used by netlist plugins.
            For bus ports, keys include per-bit names (e.g., "DATA[0]", "DATA[1]").
        """
    
    def draw(self, painter: QPainter)
        """Draw the sheet reference and all port objects."""
    
    def portAt(self, pos: QPoint) -> Optional[Port]:
        """Find port at given position (for hit testing)."""
```

### DocPage Integration

```python
class DocPage:
    """
    Represents a schematic page.
    """
    
    def __init__(self, parent: MasterDocument):
        self._objs: Set[Object] = set()
        self._sheet_refs: List[SheetRefObj] = []
        self._parent = parent
        self._name = "Page1"
    
    def sheetReferences(self) -> List[SheetRefObj]:
        """Get all sheet references on this page."""
    
    def addSheetReference(self, ref: SheetRefObj)
        """Add a sheet reference to this page."""
    
    def removeSheetReference(self, ref: SheetRefObj)
        """Remove a sheet reference from this page."""
    
    def objects(self, objType=None, exclude=None) -> Set[Object]:
        """
        Get objects on this page.
        
        Args:
            objType: Filter by object type (optional)
            exclude: Exclude these types (optional)
        """
```

### HierarchyResolver

```python
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
    
    def get_child_pages(self, parent_page: DocPage) -> List[Tuple[SheetRefObj, DocPage]]:
        """
        Get all child pages referenced from this page.
        
        Returns:
            List of (sheet_ref, child_page) tuples.
        """
    
    def get_ancestors(self, page: DocPage) -> List[DocPage]:
        """
        Get ancestor pages from top-level down to this page.
        
        Returns:
            List of ancestor pages, starting from top-level.
        """
    
    def get_full_path(self, page: DocPage) -> List[Tuple[MasterDocument, DocPage]]:
        """
        Get the full hierarchical path to a page.
        
        Returns:
            List of (document, page) tuples from top to current.
        """
    
    def find_page(self, doc_path: str, page_name: str) -> DocPage
        """
        Find a page by document path and name.
        
        Returns:
            DocPage if found, None otherwise.
        """
    
    def validate_hierarchy(self) -> List[str]:
        """
        Validate the hierarchy for errors.
        
        Returns:
            List of error messages (empty if valid).
        """
```

### UI Integration

#### SheetRefDialog

```python
class SheetRefDialog(QDialog):
    """
    Dialog for placing and editing sheet references.
    
    Provides UI for:
    - Entering child document path
    - Selecting page name
    - Defining/editing ports (name, direction, bus syntax)
    - Configuring port label visibility and style
    """
    
    doc_path: str
    page_name: str
    ports: List[Port]
    label_visible: bool
    port_label_style: PortLabelStyle
    
    def __init__(self, parent=None, existing_ref: SheetRefObj = None):
        """
        Initialize dialog.
        
        Args:
            parent: Parent widget
            existing_ref: Existing sheet reference for editing (optional)
        """
    
    def get_sheet_ref(self) -> SheetRefObj:
        """Create/update SheetRefObj from dialog inputs."""
```

#### Project Dock (Page Tree)

```python
class ProjectDock(QDockWidget):
    """
    Displays hierarchical tree of pages and sheet references.
    """
    
    def buildPageTree(self)
        """
        Build tree view showing document hierarchy.
        
        Structure:
        - Top-level pages
          - Sheet references (expandable)
            - Child pages
              - Sheet references...
        """
    
    def _buildPageNode(self, parent_item: QTreeWidgetItem, 
                       pages: List[DocPage], 
                       depth: int = 0)
        """Recursively build page tree nodes."""
    
    def selectPage(self, page: DocPage)
        """Select and scroll to a page in the tree."""
```

---

## Integration Points

### 1. Document Loading/Saving

#### Loading Flow

```
loadFromFile(file)
  ├─ Parse XML
  ├─ Create MasterDocument
  ├─ Load symbols (with PropertyTemplates)
  │   └─ For each symPart:
  │       ├─ Create SymbolPage
  │       ├─ Parse <props> as PropertyTemplates
  │       └─ Store templates in SymbolPage
  ├─ Load pages
  │   ├─ Create DocPage
  │   ├─ Load objects
  │   │   ├─ For parts:
  │   │   │   ├─ Create PartObj
  │   │   │   ├─ Load <props> as overrides
  │   │   │   └─ Initialize PartPropertyStore
  │   │   └─ For sheet refs:
  │   │       ├─ Create SheetRefObj
  │   │       ├─ Load <ports> as Port objects
  │   │       └─ Add to page._sheet_refs
  └─ Emit sigChanged
```

#### Saving Flow

```
saveToFile(file)
  ├─ Create XML root
  ├─ Write <props> with document UUID
  ├─ Write <symbol> section
  │   └─ For each symbol:
  │       ├─ Write <symPart> with name
  │       ├─ Write <props> with templates (default values)
  │       └─ Write <objects>
  ├─ Write <pages> section
  │   └─ For each page:
  │       ├─ Write <page> with name
  │       ├─ Write <objects>
  │       │   ├─ For parts:
  │       │   │   ├─ Write <part> with attributes
  │       │   │   └─ Write <props> with OVERRIDES only
  │       │   └─ For sheet refs:
  │       │       ├─ Write <sheetRef> with attributes
  │       │       └─ Write <ports>
  └─ Write to file
```

### 2. Property Editor Workflow

```
User selects PartObj on canvas
  ├─ Controller receives selection event
  ├─ Calls PropertyInspector.updateForObject(part)
  ├─ Inspector creates widgets:
  │   ├─ For each PropertyTemplate:
  │   │   ├─ Create QLineEdit for value
  │   │   ├─ Connect to part.setProp()
  │   │   └─ Add reset button
  │   └─ For instance properties (RefDes, etc.):
  │       └─ Create editable widget
  └─ Inspector displays widgets

User edits property value
  ├─ Widget emits textChanged(value)
  ├─ Inspector calls part.setProp(name, value)
  ├─ PartPropertyStore sets override
  ├─ Part emits sigPropertyChanged(name, value)
  ├─ Controller updates document modified state
  └─ UI reflects change (e.g., title bar "*")
```

### 3. Sheet Reference Placement Workflow

```
User selects "Place Sheet Reference" tool
  ├─ Controller activates SheetRefTool
  ├─ User clicks on canvas
  ├─ SheetRefDialog appears:
  │   ├─ User enters:
  │   │   ├─ Child document path
  │   │   ├─ Page name
  │   │   └─ Port definitions (name, direction, bus syntax)
  │   └─ User confirms
  ├─ Controller creates SheetRefObj
  ├─ Creates PortObj instances for each port
  ├─ Adds to page._sheet_refs
  ├─ Adds to page._objs (including PortObjs)
  ├─ Triggers net normalization (if connected to nets)
  └─ UI refreshes
```

### 4. Port Editing Workflow

```
User selects sheet reference with ports
  ├─ Controller selects SheetRefObj
  ├─ Inspector shows port configuration
  ├─ User can drag port labels to reposition
  ├─ PortObj objects update position
  └─ Document state updated via undo command
```

### 5. Port-to-Network Connection Workflow

```
User draws net to sheet reference port
  ├─ NetTool draws net segment
  ├─ Net endpoint snaps to port connection point
  ├─ NetObj created/modified
  ├─ PortObj connected to NetObj
  ├─ Net normalization triggered
  └─ Port net_names updated for netlist generation
```

---

## Implementation Roadmap

### Phase 1: Property System Foundation (Week 1-2)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 1.1 | Create `PropertyTemplate` class | None |
| 1.2 | Create `PartPropertyStore` class | None |
| 1.3 | Update `SymbolPage.fromXml()` to parse templates | 1.1 |
| 1.4 | Update `PartObj` to use `PartPropertyStore` | 1.2 |
| 1.5 | Add XML serialization for templates | 1.3 |
| 1.6 | Add XML serialization for overrides | 1.4 |
| 1.7 | Update `PartInspector` to display properties | 1.4 |
| 1.8 | Update `PartInspector` to edit properties | 1.7 |
| 1.9 | Add property reset functionality | 1.7 |
| 1.10 | Add property validation (required fields) | 1.8 |

### Phase 2: Sheet Reference Foundation (Week 2-3)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 2.1 | Create `PortDirection` enum | None |
| 2.2 | Create `Port` class | None |
| 2.3 | Create `SheetRefObj` class | None |
| 2.4 | Update `DocPage` to track sheet refs | 2.3 |
| 2.5 | Add XML serialization for sheet refs | 2.4 |
| 2.6 | Add XML serialization for ports | 2.2 |
| 2.7 | Create `SheetRefDialog` for placement | 2.3 |
| 2.8 | Create `PortObj` class for graphical ports | 2.7 |
| 2.9 | Update UI to place sheet references | 2.7 |
| 2.10 | Implement port label positioning | 2.8 |
| 2.11 | Implement port label dragging | 2.10 |
| 2.12 | Implement path resolution | 2.3 |
| 2.13 | Implement target resolution | 2.12 |

### Phase 3: Hierarchy Navigation (Week 3-4)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 3.1 | Create `HierarchyResolver` class | 2.13 |
| 3.2 | Implement `get_child_pages()` | 3.1 |
| 3.3 | Implement `get_ancestors()` | 3.1 |
| 3.4 | Implement `validate_hierarchy()` | 3.1 |
| 3.5 | Update `ProjectDock` to show hierarchy | 3.2 |
| 3.6 | Add page navigation commands | 3.5 |
| 3.7 | Add "Go to parent" command | 3.3 |

### Phase 4: Integration & Polish (Week 4-5)

| Task | Description | Dependencies |
|------|-------------|--------------|
| 4.1 | Add port-to-net connection highlighting | 2.8 |
| 4.2 | Implement bus port per-bit netlist generation | 2.6 |
| 4.3 | Add port label drag editing | 2.10 |
| 4.4 | Add property copy/paste | 1.8 |
| 4.5 | Add property apply-to-selection | 4.4 |
| 4.6 | Add property export/import | 4.4 |
| 4.7 | Update documentation | All |
| 4.8 | Write unit tests | All |
| 4.9 | Performance optimization | All |

---

## File Format Extensions

### Current Format (Before Changes)

```xml
<xSchematic version="1.0">
  <props><uuid>...</uuid></props>
  
  <symbol>
    <symPart name="Resistor">
      <objects>
        <line x1="0" y1="0" x2="100" y2="0" .../>
        <!-- No property templates -->
      </objects>
    </symPart>
  </symbol>
  
  <pages>
    <page name="Page1">
      <objects>
        <part schPath="resistors.xsch" partId="Resistor" x="100" y="200" rot="0" mirror="0">
          <!-- No property storage -->
        </part>
      </objects>
    </page>
  </pages>
</xSchematic>
```

### Extended Format (After Changes - Bus Support)

```xml
<xSchematic version="1.0">
  <props><uuid>...</uuid></props>
  
  <symbol>
    <symPart name="Resistor" schPath="analog/resistors.xsch">
      <props>
        <prop name="Resistance" default="10k" editable="1" visible="1" 
              required="0" type="text" order="1"/>
        <prop name="Footprint" default="0805" editable="1" visible="1" 
              required="0" type="footprint" order="2"/>
        <prop name="Power" default="1/4W" editable="0" visible="1" 
              required="0" type="text" order="3"/>
      </props>
      <objects>
        <line x1="0" y1="0" x2="100" y2="0" .../>
        <proptext x="10" y="-10" prop="Resistance" .../>
        <proptext x="10" y="10" prop="Footprint" .../>
      </objects>
    </symPart>
  </symbol>
  
  <pages>
    <page name="Page1">
      <objects>
        <part schPath="analog/resistors.xsch" partId="Resistor" 
              x="100" y="200" rot="0" mirror="0">
          <props>
            <prop name="Resistance" value="10k"/>      <!-- Override -->
            <prop name="Footprint" value="0603"/>      <!-- Override -->
            <!-- Power uses template default (1/4W) -->
          </props>
        </part>
        
        <sheetRef docPath="../power/power_supply.xsch" 
                  pageName="PowerSupply"
                  x="500" y="100" rot="0" mirror="0">
          <props>
            <prop name="LabelVisible" value="1"/>
            <prop name="PortLabelStyle" value="full"/>
          </props>
          <ports>
            <!-- Single-bit ports -->
            <port name="VCC" direction="input"/>
            <port name="GND" direction="passive"/>
            <port name="OUTPUT" direction="output"/>
            <!-- Bus port with range syntax -->
            <port name="DATA[0..15]" direction="bidirectional"/>
            <!-- Bus port with colon syntax (descending) -->
            <port name="ADDR[8:0]" direction="input"/>
            <!-- Heterogeneous bus -->
            <port name="DATA[0..7],CLK,SDI,SDO" direction="bidirectional"/>
          </ports>
        </sheetRef>
      </objects>
    </page>
  </pages>
</xSchematic>
```

### Schema Updates (RelaxNG Compact)

```rng
namespace obj = "http://pyschem.org/objects"

start = element xSchematic { 
  @version?,
  props?, 
  (symbol+)?, 
  pages? 
}

# Property templates in symbols
symbol = element symbol {
  symPart+
}

symPart = element symPart {
  @name,
  @schPath?,
  props,                    # NEW: Property templates
  objects
}

props = element props {
  uuid?,
  prop*
}

prop = element prop {
  @name,
  @default?,                # NEW: Template default value
  @editable { "0" | "1" }?,
  @visible { "0" | "1" }?,
  @required { "0" | "1" }?,
  @type { "text" | "number" | "enum" | "footprint" | "reference" }?,
  @order?,
  text?                     # Value (override) or default
}

# Part instances with overrides
part = element part {
  @schPath,
  @partId,
  @x,
  @y,
  @rot,
  @mirror { "0" | "1" }?,
  props?,                   # NEW: Property overrides
  proptext*
}

# Sheet references
sheetRef = element sheetRef {
  @docPath,
  @pageName,
  @x,
  @y,
  @rot,
  @mirror { "0" | "1" }?,
  props?,
  port*
}

port = element port {
  @name,
  @direction { "input" | "output" | "bidirectional" | "passive" | "uncertain" },
  @x?,
  @y?
}
# Port name includes bus syntax if applicable (e.g., DATA[0..15])
# Port position is relative to sheet reference position
```

---

## Appendix: Design Rationale

### Why String-Based Properties?

**Option 1: Strongly Typed Values**
- Pros: Type safety, built-in validation
- Cons: Complex XML schema, type coercion issues, limited extensibility

**Option 2: String-Based Values** (chosen)
- Pros: Simple XML, flexible, easy to extend, no coercion needed
- Cons: Validation must be explicit

**Decision**: String-based because the core is a drawing tool, not a circuit simulator. Type validation can be added in plugins.

### Why Separate Template/Instance Storage?

**Option 1: Inline Overrides in Symbol**
- Pros: Simpler data model
- Cons: Hard to update symbols, unclear ownership

**Option 2: Separate Template/Instance** (chosen)
- Pros: Clean separation, easy symbol updates, reset to defaults
- Cons: Slightly more complex lookup

**Decision**: Separate storage enables symbol library updates without breaking existing schematics.

### Why Deferred Connectivity?

**Option 1: Maintain Connectivity During Editing**
- Pros: Instant netlist generation
- Cons: Complex state management, premature commitments

**Option 2: Extract Connectivity On-Demand** (chosen)
- Pros: Simpler core, flexible export formats
- Cons: Netlist generation has latency

**Decision**: The core is a drawing tool. Connectivity extraction is an export concern, handled by plugins.

### Why Graphical Port Objects?

**Option 1: Port as Metadata Only**
- Pros: Simpler data model
- Cons: No visual representation, unclear connections

**Option 2: Graphical Port Objects** (chosen)
- Pros: Clear visual representation, explicit connections to nets
- Cons: Slightly more complex rendering

**Decision**: Graphical ports make the schematic clearer and enable proper netlist generation.

### Why Bus Syntax in Port Name?

**Option 1: Separate Bus Definition**
- Pros: Explicit bus structure
- Cons: More complex schema, more XML elements

**Option 2: Bus Syntax in Name** (chosen)
- Pros: Simple, compact, easy to parse
- Cons: Parsing logic required

**Decision**: Bus syntax in the name keeps the schema simple and is familiar to engineers.

---

## Appendix: Glossary

| Term | Definition |
|------|------------|
| **Symbol** | Master definition of a component (stored in library) |
| **Part** | Instantiated component on a schematic page |
| **Template** | Property definition on a symbol master |
| **Override** | Instance-specific property value |
| **Sheet Reference** | Symbol representing a child page in hierarchy |
| **Port** | Connection point on a sheet reference |
| **Net** | Electrical connection between objects |
| **Hierarchy** | Multi-level schematic design structure |
| **Bus Port** | A port that represents multiple signals (e.g., DATA[0..15]) |
| **PortObj** | Graphical object representing a port on the schematic |

---

*End of Document*