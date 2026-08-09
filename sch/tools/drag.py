"""Immutable preview transactions used by interactive editors.

DragController deliberately never writes to a document.  Editors provide a
preview builder which receives the original objects and the current cursor;
the resulting objects are rendered temporarily and committed once, through
DragCommand, when the drag completes.
"""

import copy

from sch.document import BaseUndoCmd


class DragController:
    def __init__(self, source, selected, preview_builder):
        self._source = tuple(source)
        self._selected = tuple(selected)
        self._baseline = tuple(self._snapshot(obj) for obj in self._selected)
        self._preview_builder = preview_builder
        self._preview = list(self._baseline)

    @staticmethod
    def _snapshot(obj):
        try:
            return copy.copy(obj)
        except (AttributeError, TypeError):
            # Immutable geometry objects can expose a value-copy constructor
            # without supporting Python's copy protocol.
            if hasattr(obj, "with_endpoints"):
                return obj.with_endpoints(obj.pt1, obj.pt2)
            raise

    @property
    def source(self):
        return list(self._source)

    @property
    def selected(self):
        return list(self._selected)

    @property
    def baseline(self):
        return list(self._baseline)

    @property
    def preview(self):
        return list(self._preview)

    def update(self, cursor):
        self._preview = list(self._preview_builder(self.baseline, cursor))
        return self.preview


class DragCommand(BaseUndoCmd):
    """Atomically swap the objects participating in one drag transaction."""

    def __init__(self, doc, before, after, obj_type=None, name="drag objects"):
        super().__init__(name, doc=doc)
        self._before = list(before)
        self._after = list(after)
        self._obj_type = obj_type

    def _replace(self, remove, add):
        self.doc.replaceObjects(remove, add, objType=self._obj_type)

    def redo(self):
        self._replace(self._before, self._after)

    def undo(self):
        self._replace(self._after, self._before)
