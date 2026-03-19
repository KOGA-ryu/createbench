from __future__ import annotations

import importlib.util
from pathlib import Path


_MODULE_PATH = Path(__file__).resolve().parent / "io" / "ui_extract_packet.py"
_SPEC = importlib.util.spec_from_file_location("_createbench_ui_extract_packet", _MODULE_PATH)
_MODULE = importlib.util.module_from_spec(_SPEC)
assert _SPEC is not None and _SPEC.loader is not None
_SPEC.loader.exec_module(_MODULE)

validate_packet = _MODULE.validate_packet
normalize_packet = _MODULE.normalize_packet
import_packet_into_layout = _MODULE.import_packet_into_layout
load_packet = _MODULE.load_packet
load_packet_alongside = _MODULE.load_packet_alongside
load_packet_in_bench = _MODULE.load_packet_in_bench
