from __future__ import annotations

import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parent / "io" / "project_io.py"
_SPEC = importlib.util.spec_from_file_location("_createbench_project_io", _MODULE_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC is not None and _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)

save_project = _MODULE.save_project
load_project = _MODULE.load_project
