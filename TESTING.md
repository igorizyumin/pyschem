# Testing

Tests live in the `tests/` directory and use Python's standard-library
`unittest` framework. The top-level runner makes test discovery independent of
the current working directory and returns a non-zero exit code on failure.

From the project root:

```powershell
python run_tests.py
python run_tests.py -v
```

To run one module or test case:

```powershell
python run_tests.py tests.test_regressions
python run_tests.py tests.test_regressions.TestNetRegression
```

Create a clean Windows environment from the repository root with:

```powershell
.\setup.ps1
```

The script creates `.venv` and installs the dependencies from
`requirements.txt`. Use the resulting interpreter with:

```powershell
.\.venv\Scripts\python.exe run_tests.py
```

## Current environment notes

The dependency manifest is `requirements.txt`. The test environment requires at least:

- Python 3.10+
- PySide6
- lxml

The system interpreter may fail with `ModuleNotFoundError: No module named 'PySide6'`; use `.venv` after running the setup script. The current suite is primarily unit/regression coverage for document persistence, immutable net geometry, normalization, and undo/redo. GUI behavior, library discovery, external hierarchy loading, and export are not comprehensively tested.

Library tests use the documented priority order: project `schlib/`, then the
user library, then the default system library. Hierarchy tests use only
project-relative document paths and verify external loading, path escapes,
duplicate page names, and cycles.

## GUI smoke tests

The intended smoke workflow creates a `QApplication` in Qt's `offscreen` mode,
opens a new page, performs an edit, and checks the Undo/Redo state transitions.
It is intended for automated environments and does not require a display or
manual interaction. The current bundled Qt runtime can hang when this window
lifecycle is run through `unittest`, so the workflow is documented but not yet
registered in the default suite until that runtime issue is isolated.

```powershell
.\venv\Scripts\python.exe run_tests.py tests.test_gui_smoke
```
