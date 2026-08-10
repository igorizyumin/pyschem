# PySchem Source Code Map

This document provides a current map of the implemented classes, their locations, and their responsibilities. It is not a plugin/API specification; planned features are tracked in `PLAN.md` and `TODO.md`.

---

## Table of Contents

1. [Core Modules](#core-modules)
2. [Object Model (sch/obj/)](#object-model-schobj)
3. [Tools (sch/tools/)](#tools-schtools)
4. [Forms (sch/forms/)](#forms-schforms)
5. [UI Classes (sch/uic/)](#ui-classes-schuic)
6. [Architecture Overview](#architecture-overview)

---

## Core Modules

### sch/controller.py

| Class | Description |
|-------|-------------|
| `Controller` | Main application controller that coordinates the view, document, tools, and library. Manages tool switching, event handling, and the overall application state. |

### sch/document.py

| Class | Description |
|-------|-------------|
| `MasterDocument` | Top-level document container that holds all pages, manages the part library, and handles file I/O operations. |
| `DocPage` | Represents a single schematic page within a document. Contains objects (parts, nets, text, etc.) and sheet references for hierarchical design. |
| `BaseUndoCmd` | Base class for undo/redo commands. |
| `ObjAddCmd` | Command to add an object to a document. |
| `ObjDelCmd` | Command to delete an object from a document. |
| `ObjChangeCmd` | Command to modify an object's properties. |
| `AbstractPage` | Page-owned object collection and `QUndoStack` lifecycle. |
| `SymbolPage` | Symbol master page with property templates and symbol objects. |

### sch/library.py

| Class | Description |
|-------|-------------|
| `PartLibrary` | Stores part symbols and manages their loading from external files. Provides lookup by symbol name. |

### sch/utils.py

| Class | Description |
|-------|-------------|
| `Layer` | Provides access to layer colors and properties for rendering. |
| `LayerType` | Enumerates available drawing layers (wire, annotate, selection, etc.). |

### sch/obj/property.py

| Class | Description |
|-------|-------------|
| `PropertyDefinition` / `PropertyTemplate` | Stable property metadata, including defaults, type, visibility, editability, and standard-property markers. `PropertyTemplate` remains the compatibility name. |
| `Property` | A resolved property value, either default or overridden. |
| `PropertyStore` | Generic definitions, standard accessors, and local property overrides. |
| `PartPropertyStore` | Part-specific standard definitions plus master and instance values. |

### sch/obj/sheetref.py and sch/obj/port.py

| Class | Description |
|-------|-------------|
| `SheetRefObj` | First-class hierarchical child-sheet reference with XML persistence and target resolution. |
| `Port` | Port record attached to a sheet reference, including direction and bus metadata. |
| `PortDirection` | Enumerated port direction values. |
| `Geom` | Geometric utility functions (norm, dotProd, isParallel, etc.). |
| `Point` | Point type utilities. |

### sch/view.py

| Class | Description |
|-------|-------------|
| `View` | Main graphics view widget using Qt Graphics View Framework. Handles rendering and mouse/keyboard events. |
| `Event` | Event type definitions for the graphics view. |

---

## Object Model (sch/obj/)

These classes represent the fundamental elements in a schematic diagram.

### sch/obj/line.py

| Class | Description |
|-------|-------------|
| `LineObj` | Represents a line object in the schematic. Has two endpoints (pt1, pt2) and supports XML serialization. |

### sch/obj/net.py

| Class | Description |
|-------|-------------|
| `NetObj` | Represents an electrical connection (wire) between pins/ports. Supports automatic net normalization when lines intersect or connect. Has endpoints (pt1, pt2) and methods for collision detection. |

### sch/obj/netlabel.py

| Class | Description |
|-------|-------------|
| `NetLabelObj` | Graphical, semantics-neutral net annotation anchored to a page position. Carries generic net properties without modifying immutable wire-segment geometry. |

### sch/obj/part.py

| Class | Description |
|-------|-------------|
| `PartObj` | Represents a part/symbol in the schematic. Contains ports, properties, and references to a master symbol definition. Supports rotation, mirroring, and hierarchical sheet references. |

### sch/obj/port.py

| Class | Description |
|-------|-------------|
| `Port` | Represents a connection point on a part. Has a name, direction (input/output/bidirectional), and can be connected to nets. |
| `PortDirection` | Enum defining port directions (input, output, bidirectional, etc.). |

### sch/obj/property.py

| Class | Description |
|-------|-------------|
| `Property` | Represents a property/attribute of a part (e.g., value, manufacturer, etc.). |

### sch/obj/proptext.py

| Class | Description |
|-------|-------------|
| `PropTextObj` | Represents a property text display on the schematic. Shows property values dynamically and can display property names. |

### sch/obj/sheetref.py

| Class | Description |
|-------|-------------|
| `SheetRefObj` | Represents a sheet reference for hierarchical schematics. Links to child pages (in the same or different documents) and defines ports for interface. Supports path resolution and port management. |

### sch/obj/text.py

| Class | Description |
|-------|-------------|
| `TextBase` | Base class for text rendering with support for alignment, rotation, font family, and size. Uses QStaticText for efficient rendering. |
| `TextObj` | Represents a static text annotation in the schematic. |

---

## Tools (sch/tools/)

These classes implement the interactive tools for creating and editing schematic elements.

### sch/tools/base.py

| Class | Description |
|-------|-------------|
| `EditHandle` | Editable handle for dragging object endpoints. Emits signals when dragged or moved. |
| `BaseEditor` | Base class for object editors. Manages edit handles, provides common editing functionality, and handles commit/delete operations. |
| `TextHandle` | Specialized handle for dragging text objects. |

### sch/tools/hierarchy.py

| Class | Description |
|-------|-------------|
| `HierarchyResolver` | Resolves hierarchical references between pages. Provides utilities for navigation (child pages, ancestors), path resolution, and hierarchy validation (cycle detection, missing files). |

### sch/tools/line.py

| Class | Description |
|-------|-------------|
| `LineTool` | Tool for drawing line objects. Handles mouse events for line creation. |
| `LineEditor` | Editor for modifying line endpoints after creation. |

### sch/tools/net.py

| Class | Description |
|-------|-------------|
| `NetTool` | Tool for drawing electrical connections (nets). Implements automatic net normalization - splits existing nets when new nets intersect or connect at non-parallel angles. |
| `NetEditor` | Editor for modifying net endpoints. Handles connected segment movement and junction dragging with automatic normalization. |

### sch/tools/part.py

| Class | Description |
|-------|-------------|
| `PartTool` | Tool for placing parts from the library. Includes an inspector for selecting symbols. |
| `PartEditor` | Editor for modifying part properties after placement. Supports rotation (R), flip horizontal (H), and flip vertical (V) keyboard shortcuts. |
| `PartInspector` | Widget for selecting part symbols and editing effective part properties. |

### sch/tools/proptext.py

| Class | Description |
|-------|-------------|
| `PropTextTool` | Tool for adding property text displays. |
| `PropTextEditor` | Editor for modifying property text position. |
| `PropTextInspector` | Widget for editing property text properties (property name, value, visibility, alignment, font). |

### sch/tools/select.py

| Class | Description |
|-------|-------------|
| `SelectTool` | Selection tool for picking and editing objects. Manages selection state and delegates to appropriate editors based on object type. |

### sch/tools/text.py

| Class | Description |
|-------|-------------|
| `TextTool` | Tool for adding text annotations. |
| `TextEditor` | Editor for modifying text position and properties. |
| `TextInspector` | Widget for editing text properties (text content, alignment, font family, font size). |

### sch/tools/netlabel.py

| Class | Description |
|-------|-------------|
| `NetLabelTool` | Tool for placing semantics-neutral graphical net labels. |
| `NetLabelEditor` | Editor for moving, rotating, and editing net-label text. |

---

## Forms (sch/forms/)

These classes implement dockable form widgets in the application.

### sch/forms/inspector.py

| Class | Description |
|-------|-------------|
| `InspectorDock` | Dockable widget for displaying property inspectors for selected objects. |

### sch/forms/main.py

| Class | Description |
|-------|-------------|
| `Main` | Main application form/window class. |

### sch/forms/projectdock.py

| Class | Description |
|-------|-------------|
| `ProjectDock` | Dockable widget for displaying the project hierarchy/tree. |

### sch/forms/treeutils.py

| Class | Description |
|-------|-------------|
| `TreeItem` | Tree item representation for hierarchical data. |
| `TreeWidget` | Custom tree widget implementation. |

---

## UI Classes (sch/uic/)

These classes are auto-generated from Qt Designer `.ui` files. They provide the UI structure for various widgets.

| File | Class | Description |
|------|-------|-------------|
| `ui_inspectordock.py` | `Ui_InspectorDock` | UI for inspector dock widget |
| `ui_mainwindow.py` | `Ui_MainWindow` | UI for main application window |
| `ui_partinspector.py` | `Ui_PartInspector` | UI for part inspector widget |
| `ui_projectdock.py` | `Ui_ProjectDock` | UI for project dock widget |
| `ui_proptextinspector.py` | `Ui_PropTextInspector` | UI for property text inspector widget |
| `ui_textinspector.py` | `Ui_TextInspector` | UI for text inspector widget |
| `ui_toolsdock.py` | `Ui_ToolsDock` | UI for tools dock widget |

---

## Architecture Overview

### Component Relationships

```
┌─────────────────────────────────────────────────────────────────┐
│                         Controller                               │
│  (Coordinates View, Document, Tools, Library)                    │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────┐
        │                       │                       │
        ▼                       ▼                       ▼
┌───────────────┐      ┌───────────────┐      ┌───────────────┐
│     View      │      │  Document     │      │   Library     │
│ (Graphics     │      │ (MasterDoc,   │      │ (PartLibrary, │
│  View Widget) │      │  DocPage)     │      │  Documents)   │
└───────────────┘      └───────────────┘      └───────────────┘
        │                       │
        │                       │
        ▼                       ▼
┌─────────────────────────────────────────────────────────┐
│                      Tools                               │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────────┐   │
│  │ Select  │ │  Net    │ │  Part   │ │  Text/Line  │   │
│  │  Tool   │ │  Tool   │ │  Tool   │ │   Tools     │   │
│  └────┬────┘ └────┬────┘ └────┬────┘ └──────┬──────┘   │
│       │           │           │             │           │
│       ▼           ▼           ▼             ▼           │
│  ┌─────────────────────────────────────────────────┐   │
│  │              Editors                             │   │
│  │  (NetEditor, PartEditor, TextEditor, etc.)      │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────┐
│                   Object Model                           │
│  ┌────────┐ ┌──────┐ ┌─────┐ ┌──────┐ ┌─────────────┐  │
│  │  Net   │ │ Part │ │Port │ │Text  │ │ SheetRef    │  │
│  └────────┘ └──────┘ └─────┘ └──────┘ └─────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Data Flow

1. **User Input** → View → Controller → Event Handling
2. **Tool Activation** → Controller switches active tool
3. **Object Creation** → Tool creates Object → Document.add()
4. **Object Editing** → Select Tool → Editor → Object modification
5. **Rendering** → View renders Document objects
6. **Undo/Redo** → Page-owned commands, including `NetGraphCmd` for normalized net graphs.

### Key Design Patterns

- **MVC-like Pattern**: Model (Document/Objects), View (`SchView`), Controller (`Controller`)
- **Command Pattern**: Undo/redo via command objects
- **Tool Pattern**: Different tools for different operations
- **Editor Pattern**: Object-specific editors for modification
- **Strategy Pattern**: Different editors based on selected object type

---

## File Summary

| Directory | Files | Primary Purpose |
|-----------|-------|-----------------|
| `sch/` | controller.py, document.py, library.py, utils.py, view.py | Core application components |
| `sch/obj/` | 10 files | Object model classes |
| `sch/tools/` | 8 files | Interactive tools and editors |
| `sch/forms/` | 4 files | Dockable form widgets |
| `sch/uic/` | 7 files | Auto-generated Qt UI classes |
| `ui/` | 7 .ui files | Qt Designer UI files |
| `xml/` | 2 files | XML schema definitions |

---

*Decision: this map is maintained manually. Structural changes should update it
in the same change; it is intentionally not generated because the descriptions
include architectural roles that cannot be inferred reliably from module names.*
