"""Deterministic symbol-library discovery and caching."""

from pathlib import Path
from typing import Dict, List, Optional, Tuple
import os

from PySide6.QtCore import QObject, QStandardPaths

from sch.document import MasterDocument


class PartLibrary(QObject):
    """Search project, user, and system libraries in fixed priority order.

    A symbol name is claimed by the first valid library file encountered.
    Files and directories are traversed in sorted order, making duplicate
    precedence deterministic across platforms.
    """

    def __init__(self, project_root=None, user_paths=None, system_paths=None):
        super().__init__()
        self.project_root = self._canonical_dir(project_root) if project_root else None
        self.user_paths = [self._canonical_dir(p) for p in (user_paths or self._default_user_paths())]
        self.system_paths = [self._canonical_dir(p) for p in (system_paths or self._default_system_paths())]
        # Kept as a compatibility surface for callers that used ``paths``.
        self.paths = []
        self._docs: Dict[str, MasterDocument] = {}
        self._symbols: Dict[str, Tuple[str, object]] = {}
        self.diagnostics: List[str] = []
        self.refresh()

    @staticmethod
    def _canonical_dir(path) -> Optional[str]:
        if not path:
            return None
        return str(Path(path).expanduser().resolve(strict=False))
    @staticmethod
    def _default_user_paths() -> List[str]:
        root = QStandardPaths.writableLocation(QStandardPaths.AppDataLocation)
        return [str(Path(root) / "schlib")] if root else []

    @staticmethod
    def _default_system_paths() -> List[str]:
        bundled = Path(__file__).resolve().parent.parent / "schlib"
        data_root = QStandardPaths.locate(QStandardPaths.GenericDataLocation,
                                          "pyschem", QStandardPaths.LocateDirectory)
        paths = [str(bundled)]
        if data_root:
            paths.append(str(Path(data_root) / "schlib"))
        return paths

    def set_project_root(self, project_root) -> None:
        self.project_root = self._canonical_dir(project_root) if project_root else None
        self.refresh()

    def configure(self, project_root=None, user_paths=None, system_paths=None) -> None:
        """Set search roots and rebuild the cache."""
        self.project_root = self._canonical_dir(project_root) if project_root else None
        if user_paths is not None:
            self.user_paths = [self._canonical_dir(p) for p in user_paths]
        if system_paths is not None:
            self.system_paths = [self._canonical_dir(p) for p in system_paths]
        self.refresh()

    def search_roots(self) -> List[Tuple[str, str]]:
        roots = []
        if self.project_root:
            roots.append(("project", str(Path(self.project_root) / "schlib"))
            )
        roots.extend(("user", path) for path in self.user_paths if path)
        roots.extend(("system", path) for path in self.system_paths if path)
        return roots

    def refresh(self) -> None:
        """Clear and rebuild the library cache, retaining diagnostics."""
        self._docs.clear()
        self._symbols.clear()
        self.diagnostics.clear()
        claimed_names = set()

        for scope, root_text in self.search_roots():
            root = Path(root_text)
            if not root.is_dir():
                continue
            for file_path in sorted(root.rglob("*.xsch"), key=lambda p: str(p).casefold()):
                canonical = str(file_path.resolve())
                try:
                    document = MasterDocument(self, project_root=root.parent)
                    document.loadFromFile(canonical)
                except Exception as error:
                    self.diagnostics.append(
                        f"{scope} library: could not load {canonical}: {error}"
                    )
                    continue
                self._docs[canonical] = document
                for symbol in document.symbols:
                    if symbol.name in claimed_names:
                        continue
                    claimed_names.add(symbol.name)
                    self._symbols[symbol.name] = (canonical, symbol)

    # Backward-compatible name used by older callers.
    _rebuildCache = refresh

    def getSymList(self):
        return [(path, [symbol.name]) for path, symbol in self._symbols.values()]

    def getSym(self, path, name):
        canonical = self._canonical_file(path)
        entry = self._symbols.get(name)
        if entry and entry[0] == canonical:
            return entry[1]
        # Preserve direct lookup for callers holding a non-winning file path.
        document = self._docs.get(canonical)
        if document:
            return next((symbol for symbol in document.symbols if symbol.name == name), None)
        return None

    def _canonical_file(self, path) -> Optional[str]:
        if not path:
            return None
        return str(Path(path).expanduser().resolve(strict=False))
