# PySchem Architecture

This document records stable design decisions and responsibilities. It is not
an API reference or a copy of the XML schema. Implementation details belong in
the Python source, tests, and the authoritative files under `xml/`.

## Scope

PySchem is a local desktop schematic editor. The dependable core is responsible
for:

- editing schematic pages and symbol masters;
- placing parts, wires, lines, text, and sheet references;
- page-owned undo/redo;
- schema-validated XML persistence;
- project-scoped hierarchy resolution; and
- deterministic symbol-library lookup.

Netlist generation, DRC, BOM, simulation, export, and plugins remain future
extensions.

## Major components

The application has four cooperating layers:

1. **Document model** — `MasterDocument`, `DocPage`, and `SymbolPage` own
   persisted state and page-level undo stacks.
2. **Objects** — parts, nets, lines, text, property text, and sheet references
   provide drawing, hit testing, and XML serialization.
3. **Controller and tools** — controllers connect pages to the view; tools
   create and edit objects; editors submit undoable commands.
4. **Forms and project navigation** — the main window, inspector, tools dock,
   project dock, and page tabs expose the editing workflow.

The [source map](SOURCE_CODE_MAP.md) lists current modules when an
implementation lookup is necessary.

## Design decisions

### One document model

`SheetRefObj` is the canonical model for hierarchical sheet references. It is
not a library-backed symbol. A sheet reference stores its project-relative
target, display state, and port records directly.

### Derived connectivity

Connectivity is derived from normalized net geometry and port metadata. The
document does not maintain a second semantic graph, preventing stale graph
state after edits or undo/redo. Netlist and DRC features will extract their
graphs on demand.

### Template and instance separation

Symbol masters define property templates. Part instances store overrides only.
This allows defaults to remain associated with the master while instance edits
remain local and undoable.

### String property values

Property values are stored as strings. Property templates may describe display
or validation intent, but the core does not impose electrical or engineering
semantics on values.

### Generic properties

Parts, symbol-master pins, and net-label annotations expose a common property
interface. Standard properties are backed by model fields or registered
handlers, while user-defined properties are stored in a property bag. Stable
namespaced keys such as `part.reference`, `part.reference_prefix`,
`pin.number`, `pin.name`, and `net.name` are used internally; display labels
are separate from these keys.

Part custom-property definitions and defaults belong to the symbol master.
Placed parts store per-instance overrides. `part.reference_prefix` inherits
from the master by default but may be overridden on an individual part. A
reference designator is an annotation value, not an object identity or
primary key: duplicate values are allowed until a separate annotation step
resolves them. Newly placed parts may use placeholders such as `R?`.

Pin properties are owned by the symbol master and are shared by every placed
instance of that master. Per-instance pin overrides are intentionally not part
of the current model. Legacy pin fields remain compatibility aliases while
canonical properties are introduced.

### Attached property displays

`PropertyDisplay` is the common text child for rendering a property value. It
reuses text rendering, alignment, font, visibility, selection, and move/rotate
editing while storing only presentation state; the parent remains the source
of the value.

Pin displays are children of symbol-master pins and use pin-local coordinates.
They remain shared with every part instance and cannot be customized on an
instance. Symbol-master displays for part properties are cloned into each
`PartObj` in part-local coordinates, allowing an instance to move, rotate, or
hide its own reference/value/custom-field displays without changing the
master. Attached displays are indexed for selection but serialized by their
owner so they are drawn and persisted exactly once.

### Net labels and net semantics

`NetObj` represents immutable wire-segment geometry only. Properties must not
be attached directly to wire segments because normalization splits, merges,
deduplicates, and recreates them. A separate graphical `NetLabelObj` carries
net metadata at an anchored page position and exposes the generic property
interface. In the current model, net labels are semantics-neutral graphical
annotations: equal label text does not imply connectivity, and netlist
extraction will decide later how names, differential-pair metadata, and other
net properties are interpreted.

The label's attachment is geometric and local. Label anchor points participate
in wire normalization so a wire crossing an anchor is represented explicitly,
but moving geometry may leave a label unattached until the user moves it.

Reference designators and label text are never used as primary keys. Model
references use object identity or stable internal identifiers instead.

## Hierarchy

Sheet references are project-relative. The project root is the directory that
contains the root schematic, and every referenced schematic must resolve below
that directory. Absolute paths and paths that escape through `..` are rejected.

Child documents are loaded on demand and cached for the project. The cache is
shared by the hierarchy, so a cycle such as A → B → A reuses the existing
documents instead of recursively loading fresh copies. Traversals maintain
active-page guards and report cycles without recursion failures.

The project dock displays root documents, pages, sheet-reference children, and
unresolved/cyclic references. Double-clicking a page opens or activates its
page tab.

## Libraries

Library lookup has an explicit priority:

1. the project-local `schlib/` directory;
2. the user library directory; and
3. the default system library directories.

Within each root, files are traversed in sorted order. The first valid symbol
with a given name wins. Invalid library files are skipped and reported through
library diagnostics. Refreshing the library clears and rebuilds the cache.

Library paths and symbol identities are canonicalized before lookup so the same
file cannot appear under multiple path spellings.

## Persistence

`xml/schschema.rnc` and `xml/schschema.rng` are the format authority. Loading
validates the complete XML tree before parsing and commits the parsed document
only after all object parsers succeed. A failed load therefore cannot partially
replace an open document.

The current format is version 1 without a serialized root version attribute.
Before an incompatible change, the schema will add a root format version and
the loader will dispatch through explicit migrations. Unknown future versions
and unsupported migrations are errors.

For persistence examples and compatibility fixtures, use the schema and the
round-trip tests rather than duplicating XML in this document.

## Editing and undo/redo

Object creation, deletion, property edits, geometry edits, and normalized net
graph replacements are submitted to the owning page's `QUndoStack`. The main
window reflects the active page's undo and redo state. Inspector edits use the
same command path as direct object edits, including nested part-property
overrides.

## Testing and maintenance

The test runner is `run_tests.py`; setup and headless-testing guidance is in
`TESTING.md`. Tests cover persistence, normalization, undo/redo, hierarchy
cycles, project path safety, and library precedence.

This document should be updated only for stable behavior or design decisions.
Do not paste generated UI code, class signatures, schema definitions, or
speculative APIs here.
