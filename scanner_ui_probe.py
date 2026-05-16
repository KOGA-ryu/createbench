from __future__ import annotations

import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parent / "io" / "scanner_ui_probe.py"
_SPEC = importlib.util.spec_from_file_location("_createbench_scanner_ui_probe", _MODULE_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC is not None and _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)

validate_scanner_repo_root = _MODULE.validate_scanner_repo_root
validate_scanner_probe_target = _MODULE.validate_scanner_probe_target
build_scanner_packet = _MODULE.build_scanner_packet
build_scanner_main_window_packet = _MODULE.build_scanner_main_window_packet
build_scanner_profile_manager_packet = _MODULE.build_scanner_profile_manager_packet
load_scanner_probe = _MODULE.load_scanner_probe
load_scanner_main_window = _MODULE.load_scanner_main_window
load_scanner_profile_manager = _MODULE.load_scanner_profile_manager
load_scanner_main_window_replace = _MODULE.load_scanner_main_window_replace
load_scanner_main_window_alongside = _MODULE.load_scanner_main_window_alongside
load_scanner_main_window_in_bench = _MODULE.load_scanner_main_window_in_bench
load_scanner_profile_manager_replace = _MODULE.load_scanner_profile_manager_replace
load_scanner_profile_manager_alongside = _MODULE.load_scanner_profile_manager_alongside
load_scanner_profile_manager_in_bench = _MODULE.load_scanner_profile_manager_in_bench
