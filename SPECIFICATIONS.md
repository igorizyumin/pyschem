# PySchem Schematic Capture - Technical Specifications

## 1. Overview

PySchem is a professional-grade, local Python/Qt-based electrical schematic capture application. It emphasizes simplicity, extensibility, and a plugin architecture that allows users to extend functionality without modifying the core product.

---

## 2. Application Architecture

### 2.1 Technology Stack
- **Language**: Python 3.x
- **GUI Framework**: PySide6 (Qt for Python)
- **XML Processing**: lxml (for schema validation and persistence)
- **Output Formats**: PDF (via reportlab or similar), SVG (via cairo or svgwrite)

### 2.2 Core Application Structure

```
pyschem/
├── sch/                    # Core application package
│   ├── __init__.py
│   ├── controller.py       # Application controller / event coordinator
│   ├── document.py         # Document structure (MasterDocument, DocPage, SymbolPage)
│   ├── library.py          # Library management system
│   ├── utils.py            # Shared utilities (LayerType, Layer, Geom)
│   ├── view.py             # View layer / event types
│   ├── forms/              # UI widgets
│   │   ├── main.py         # Main window
│   │   ├── inspector.py    # Property inspector
│   │   ├── projectdock.py  # Project/browser dock
│   │   └── treeutils.py    # Tree view utilities
│   ├── obj/                # Document object model
│   │   ├── part.py         # PartObj - instantiated components
│   │   ├── net.py          # NetObj - electrical connections
│   │   ├── line.py         # LineObj - drawing primitives
│   │   ├── text.py         # TextObj - annotations
│   │   └── proptext.py     # PropTextObj - property text
│   ├── tools/              # Interactive tools
│   │   ├── part.py         # Part placement tool
│   │   ├── net.py          # Wire/net drawing tool
│   │   ├── line.py         # Line drawing tool
│   │   ├── text.py         # Text tool
│   │   └── select.py       # Selection tool
│   └── uic/                # UI definitions (compiled from .ui files)
├── ui/                     # Qt Designer .ui files
├── xml/                    # XML schema definitions
│   ├── schschema.rnc      # RelaxNG Compact schema
│   └── schschema.rng      # RelaxNG schema
└── main.py                 # Application entry point
```

### 2.3 Design Principles

1. **Minimal Core**: The core application provides only essential schematic drawing capabilities
2. **Extensibility**: All advanced features (netlist generation, BOM, simulation) are implemented as plugins
3. **Unopinionated Flow**: Users can choose their workflow; the tool doesn't enforce a specific methodology
4. **File-Based Storage**: Libraries and components are stored as files in the filesystem with search paths

---

## 3. Library Management System

### 3.1 Hierarchy: Symbols → Parts

```
┌─────────────────────────────────────────────────────────────┐
│                    Library System                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐  │
│  │  Symbol File │───▶│   Symbol     │───▶│    Part      │  │
│  │  (*.xsch)    │    │   (Master)   │    │  (Instance)  │  │
│  └──────────────┘    └──────────────┘    └──────────────┘  │
│        │                   │                    │           │
│        │                   │                    │           │
│        ▼                   ▼                    ▼           │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Symbol: Generic schematic representation           │   │
│  │  - Contains drawing primitives (lines, arcs)        │   │
│  │  - Contains pin definitions with names              │   │
│  │  - Contains property templates                      │   │
│  │  - Stored as *.xsch file                            │   │
│  └─────────────────────────────────────────────────────┘   │
│                              │                               │
│                              ▼                               │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  Part: Instantiated component on schematic          │   │
│  │  - Reference to Symbol master                       │   │
│  │  - Position, rotation, mirror state                 │   │
│  │  - Component-specific property values               │   │
│  │  - PCB footprint association                        │   │
│  │  - Pin-to-symbol mapping (for complex parts)        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Symbol Definition

A **Symbol** is a generic schematic representation stored in a file:

**File Format**: `*.xsch` (XML-based, schema-validated)

**Symbol Contents**:
- **Drawing Objects**: Lines, arcs, rectangles, text
- **Pin Definitions**: Named connection points with:
  - Pin name/number
  - Electrical type (input, output, passive, etc.)
  - Position on symbol
- **Property Templates**: Default property values (e.g., "Resistor", "10k")
- **Metadata**: Author, version, description

### 3.3 Part Definition

A **Part** is an instantiated component on a schematic page:

**Part Properties**:
- Master symbol reference (path + name)
- Position (x, y coordinates)
- Rotation (0°, 90°, 180°, 270°)
- Mirror state (horizontal flip)
- Property values (overrides defaults)
- PCB footprint reference
- Instance identifier (R1, C2, U5, etc.)

**Complex Parts**: Parts may consist of multiple symbol instances with pin mappings:
```
Example: IC with multiple packages
┌────────────────────────────────────────┐
│  Part: "MCU_ATmega328P"                │
│  ├─ Symbol Instance 1: "MCU_Core"      │
│  │   Pin VCC → Part Pin 14             │
│  │   Pin GND → Part Pin 9              │
│  └─ Symbol Instance 2: "MCU_Ports"     │
│      Pin PORTA.0 → Part Pin 14          │
│      ...                               │
└────────────────────────────────────────┘
```

### 3.4 Library Search Paths

```python
class PartLibrary:
    paths = [
        '/usr/share/pyschem/symbols/',    # System-wide library
        '~/.pyschem/symbols/',            # User library
        './symbols/',                      # Project-local library
        '/custom/path/to/symbols/'         # Additional paths
    ]
```

**Search Behavior**:
- Libraries are scanned recursively
- Cache is built on initialization and refreshed when needed
- First match wins for symbol names (to allow overrides)

### 3.5 Library File Structure

```
pyschem-symbols/
├── logic/
│   ├── gates.xsch          # AND, OR, NAND, NOR, XOR
│   ├── flipflops.xsch      # D-FF, JK-FF, SR-FF
│   └── comparators.xsch    # Voltage comparator
├── analog/
│   ├── resistors.xsch
│   ├── capacitors.xsch
│   └── opamp.xsch
├── discrete/
│   ├── transistors.xsch
│   └── diodes.xsch
├── connectors/
│   ├── headers.xsch
│   └── terminals.xsch
└── ic/
    ├── microcontrollers/
    │   └── avr.xsch        # ATmega328P (complex multi-symbol part)
    └── memory/
        └── dram.xsch
```

---

## 4. Hierarchy Support

### 4.1 Hierarchical Schematics

The system supports multi-level schematic design:

```
┌─────────────────────────────────────────────────────────────┐
│                    Hierarchy Levels                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Level 0: Top-Level Sheet                                    │
│  ├─ Block: "Power Supply"                                    │
│  │   └─ References Level 1 sheet                            │
│  ├─ Block: "Microcontroller"                                 │
│  │   └─ References Level 1 sheet                            │
│  └─ Block: "I/O Interface"                                   │
│      └─ References Level 1 sheet                            │
│                                                              │
│  Level 1: Functional Blocks                                  │
│  ├─ "Power Supply" sheet                                     │
│  │   ├─ Part: LM317                                        │
│  │   ├─ Part: Capacitors                                   │
│  │   └─ Net connections                                     │
│  └─ "Microcontroller" sheet                                  │
│      ├─ Part: ATmega328P                                    │
│      └─ Net connections                                      │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 Sheet Reference Symbol

A **Sheet Reference** is a special symbol that represents another schematic page:

**Sheet Reference Properties**:
- Path to target document
- Sheet name within target document
- Port mappings (if any)
- Display options (label visibility, connection style)

**Implementation**: Sheet references are implemented using the existing symbol/part system:
- A special "sheet_ref" symbol in the library
- Properties define the target document and sheet
- When placed, it displays as a block with connection points

### 4.3 Unified Symbol/Library Concept

Sheet references unify with the library system:

```
Symbol File: "system/sheet_ref.xsch"
├─ Symbol: "sheet_ref"
│  ├─ Drawing: Rectangle with port pins
│  ├─ Pins: [port_name, direction]
│  └─ Props: [sheet_path, sheet_name, label_visible]
```

This allows sheet references to be:
- Stored in the library alongside other symbols
- Reused across projects
- Customized with different visual styles
- Extended with additional metadata

---

## 5. Document Model

### 5.1 Document Structure

```
MasterDocument
├─ _symbols: List[SymbolPage]      # Symbol definitions
└─ _pages: List[DocPage]           # Schematic pages
    └─ _objs: Set[Object]          # Objects on the page
        ├─ PartObj
        ├─ NetObj
        ├─ LineObj
        ├─ TextObj
        └─ PropTextObj
```

### 5.2 Undo/Redo System

- **QUndoStack**: Qt's built-in undo/redo framework
- **Command Objects**: Each operation is a command (ObjAddCmd, ObjDelCmd, ObjChangeCmd)
- **Memento Pattern**: Object state snapshots for change commands

### 5.3 Object Model

| Object Type | Description | Key Properties |
|-------------|-------------|----------------|
| PartObj | Component instance | position, rotation, mirror, master_ref, properties |
| NetObj | Electrical connection | segments, ports, name, class |
| LineObj | Drawing line | start, end, layer, style |
| TextObj | Annotation text | position, content, font, layer |
| PropTextObj | Property text | associated object, property name/value |

---

## 6. Tools and Interaction

### 6.1 Tool Architecture

```
BaseEditor
├─ PartTool       # Place component
├─ NetTool        # Draw wire
├─ LineTool       # Draw line
├─ TextTool       # Add text
└─ SelectTool     # Select/move objects
```

### 6.2 Tool Interface

```python
class BaseEditor(QObject):
    sigUpdate = Signal()           # Trigger view update
    
    def draw(self, painter):       # Preview drawing
    def handleEvent(self, event):  # Input handling
    def finish(self):              # Cleanup
```

### 6.3 Inspector Pattern

Each tool has an associated inspector widget:
- **PartInspector**: Select master symbol, view/edit properties
- **NetInspector**: Net name, class settings
- **TextInspector**: Font, size, alignment

---

## 7. Output and Extensions

### 7.1 Output Modules (Plugin Architecture)

Output generation is implemented as plugins:

```
outputs/
├── __init__.py
├── base.py              # Output plugin base class
├── pdf.py               # PDF output
├── svg.py               # SVG output
├── netlist.py           # Netlist generation
└── bom.py               # Bill of Materials
```

**Plugin Interface**:
```python
class OutputPlugin:
    def name(self) -> str:          # Plugin name
    def description(self) -> str:   # Plugin description
    def extensions(self) -> list:   # File extensions
    def generate(self, doc) -> bytes: # Generate output
```

### 7.2 Netlist Generation

Netlist plugin extracts connectivity information:

**Output Formats**:
- SPICE netlist (.cir, .net)
- Generic netlist (.net)
- Custom formats via plugin

**Netlist Content**:
```
* Netlist for project.xsch
* Generated by PySchem

R1 N001 N002 10k
C1 N002 GND 100u
U1 N001 N002 VCC GND NC1 NC2
```

### 7.3 Bill of Materials

BOM plugin generates component lists:

| RefDes | Value | Footprint | Qty | Description |
|--------|-------|-----------|-----|-------------|
| R1-R5  | 10k   | 0805      | 5   | Resistor 1/4W |
| C1     | 100u  | 1206      | 1   | Capacitor electrolytic |

### 7.4 Plugin Discovery

Plugins are discovered via:
- Filesystem search in `outputs/` directory
- Python entry points (for system-wide plugins)
- Configuration file for enabled plugins

---

## 8. XML Schema

### 8.1 Document Schema (schschema.rnc)

```
namespace obj = "http://pyschem.org/objects"

start = element xSchematic { props?, symbol?, pages? }

props = element props { uuid, props? }
uuid = element uuid { xsd:UUID }

symbol = element symbol { props, symPart+ }
symPart = element symPart { @name, props, objects }

pages = element pages { page+ }
page = element page { @name, objects }

objects = element objects { (line|net|text|part|proptext)+ }
```

### 8.2 Versioning

Schema includes version attribute:
```xml
<xSchematic version="1.0">
  ...
</xSchematic>
```

---

## 9. User Interface

### 9.1 Main Window Components

```
┌─────────────────────────────────────────────────────────────┐
│  Menu Bar: File, Edit, View, Insert, Tools, Help            │
├─────────────────────────────────────────────────────────────┤
│  Toolbar: [New] [Open] [Save] | [Undo] [Redo] | Tools...   │
├──────────────────┬──────────────────────────────────────────┤
│                  │                                          │
│  Project Dock    │      Canvas / Schematic Page             │
│  - Pages         │                                          │
│  - Symbols       │                                          │
│  - Parts         │                                          │
│                  │                                          │
├──────────────────┴──────────────────────────────────────────┤
│  Inspector Dock: Property editor for selected object        │
├─────────────────────────────────────────────────────────────┤
│  Status Bar: Coordinates, tool info, zoom level             │
└─────────────────────────────────────────────────────────────┘
```

### 9.2 Dock Widgets

| Dock | Purpose |
|------|---------|
| ProjectDock | Tree view of pages, symbols, parts |
| Inspector | Property editor for selected object |
| ToolsDock | Tool configuration and presets |

---

## 10. Extensibility Points

### 10.1 Plugin Types

1. **Output Plugins**: Generate PDF, SVG, netlists, BOMs
2. **Symbol Libraries**: Additional component libraries
3. **Validators**: Design rule checking
4. **Simulators**: SPICE integration, circuit simulation
5. **PCB Export**: Gerber, ODB++ output
6. **Custom Tools**: Additional editing tools

### 10.2 Extension API

```python
class PySchemPlugin:
    def register(self, api):
        # Register output formats
        api.register_output(self.output_plugin)
        # Register new tools
        api.register_tool(self.tool_class)
        # Register symbol library
        api.register_library(self.library_path)
```

---

## 11. Technical Requirements

### 11.1 Dependencies

| Package | Purpose |
|---------|---------|
| PySide6 | Qt bindings for Python |
| lxml | XML parsing and generation |
| reportlab | PDF generation |
| svgwrite | SVG generation |
| Pillow | Image handling (for footprints) |

### 11.2 Minimum Requirements

- Python 3.8+
- 64-bit OS (Windows, macOS, Linux)
- 2GB RAM minimum
- 100MB disk space

### 11.3 Performance Targets

- Open 100-page schematic in < 2 seconds
- Undo/redo operations < 100ms
- Symbol library with 1000+ symbols: < 5 second load

---

## 12. Future Considerations

### 12.1 Potential Enhancements

1. **Cloud Library**: Online component library repository
2. **Collaboration**: Multi-user editing with conflict resolution
3. **3D Visualization**: 3D preview of PCB layout
4. **Version Control**: Git integration for schematics
5. **Scripting**: Python API for automation

### 12.2 Known Limitations (Current Implementation)

- Complex multi-symbol parts have limited pin mapping support
- No automatic net naming
- Limited annotation automation
- No design rule checking (intentionally, as a plugin target)

---

## 13. Summary

PySchem is designed as a minimal, extensible schematic capture tool. The core provides:

1. **Document management** with undo/redo
2. **Basic drawing objects** (parts, nets, lines, text)
3. **Library system** with symbol/part hierarchy
4. **Hierarchical schematics** via sheet references
5. **Plugin architecture** for outputs and extensions

All advanced features (netlist, BOM, simulation) are implemented as plugins, keeping the core simple and allowing users to extend it according to their needs.