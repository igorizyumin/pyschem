# PySchem Technical Specification

This document describes supported behavior and intentional boundaries of the
current local schematic editor. It avoids duplicating implementation details;
the Python source, tests, and XML schema are authoritative where applicable.

## Product scope

PySchem provides a local PySide6 desktop editor for schematic documents. The
core workflow is:

1. create or open a project schematic;
2. edit pages and symbol masters;
3. place and edit schematic objects;
4. save, undo, and redo changes; and
5. navigate project hierarchy through sheet references.

Export, simulation, DRC, BOM generation, cloud collaboration, and a general
plugin marketplace are outside the near-term core release.

## Supported model

### Documents and pages

A master document contains zero or more symbol masters and schematic pages.
Each page owns its objects and its undo stack. Symbol masters provide reusable
geometry and property templates; parts refer to masters through the library.

### Schematic objects

The current editor supports:

- immutable, integer-coordinate net segments with normalization for splits,
  merges, deduplication, and T-junctions;
- graphical lines;
- static text and property text;
- library-backed part instances with property overrides; and
- project-scoped sheet references with ports, labels, rotation, and mirroring.

The model and tools expose drawing, selection, hit testing, persistence, and
undoable edits for these objects.

### Properties

Symbol masters define property templates. Part instances store only explicit
overrides. Inspector changes participate in undo/redo, including edits made
through property-text displays.

Property values are strings. Validation and electrical interpretation are
future extension responsibilities.

## Hierarchy requirements

All schematic files in a hierarchy belong to one project directory. A sheet
reference uses a relative path from its containing schematic; absolute paths and
paths escaping the project directory are invalid.

Child documents load on demand and are cached. Missing files, missing pages,
malformed child documents, duplicate page names, and cycles are reported or
resolved deterministically without unbounded recursion.

Sheet-reference behavior currently includes placement, selection/editing,
rendering, rotation, mirroring, and project-dock navigation. Semantic
port-to-net connectivity is not yet implemented.

## Library requirements

Library search priority is fixed:

1. project-local `schlib/`;
2. user library; and
3. default system library.

The first valid symbol found wins. Files are traversed in deterministic sorted
order. Cache refresh is explicit, and malformed library files are retained in
diagnostics rather than silently treated as valid symbols.

## Persistence contract

The XML format is defined exclusively by:

- [`xml/schschema.rnc`](xml/schschema.rnc); and
- [`xml/schschema.rng`](xml/schschema.rng).

The loader validates before replacing document state and commits only after
successful parsing. The current format is version 1 and has no root version
attribute. Incompatible future changes require an explicit root version and
migration functions; unknown versions are load errors.

Do not add copied schema definitions or hand-maintained XML examples here.
Use schema validation and round-trip tests for format compatibility.

## User interface

The main window provides document tabs, a schematic canvas, a project dock, an
inspector dock, and a tools dock. The tools include selection, line, net, text,
part, and sheet-reference tools.

The project dock shows documents, symbol masters, pages, and resolved or
unresolved child-sheet references. Double-clicking a page opens it in a tab.

## Dependencies and testing

The runtime requires Python 3.10+, PySide6, and lxml. Installation and test
commands are documented in `TESTING.md`; the dependency manifest is
`requirements.txt`.

The automated suite covers persistence round trips, load safety, undo/redo,
net normalization, hierarchy cycles and path safety, library precedence, and
malformed-library diagnostics. GUI smoke-test guidance is documented for
headless environments.

## Intentional limitations

The following are not current core capabilities:

- semantic netlist or DRC analysis;
- SVG/PDF export;
- BOM generation;
- SPICE simulation;
- cloud or multi-user collaboration; and
- a general plugin marketplace or entry-point ecosystem.
