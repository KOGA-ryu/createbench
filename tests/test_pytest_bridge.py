from __future__ import annotations

import importlib
import importlib.util
import os
from pathlib import Path

import pytest


# Qt-backed tests in this repo already assume headless execution in automation.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


TESTS_DIR = Path(__file__).resolve().parent


TEST_MODULES = [
    "test_app_state.py",
    "test_checklist_engine.py",
    "test_layout_model.py",
    "test_inspector_panel.py",
    "test_canvas_widget.py",
    "test_engine_smoke.py",
    "test_checklist_panel.py",
    "test_component_form_system.py",
    "test_constraints.py",
    "test_dsl_builder.py",
    "test_freeform_canvas.py",
    "test_geometry.py",
    "test_integration_smoke.py",
    "test_layout_engine.py",
    "test_lock_manager.py",
    "test_locked_freeform.py",
    "test_node.py",
    "test_project_io.py",
    "test_placement_engine.py",
    "test_property_registry.py",
    "test_selection_state.py",
    "test_snap_engine.py",
    "test_structural_editing.py",
    "test_templates.py",
    "test_tree_manager.py",
    "test_ui_extract_packet.py",
    "test_ui_extract_packet_integration.py",
    "test_ui_extract_packet_template_protection.py",
    "test_scanner_ui_probe.py",
    "test_node_resolution.py",
    "test_scene_resolution.py",
]



@pytest.mark.parametrize("module_name", TEST_MODULES)
def test_run_all_bridge(module_name: str):
    module_path = TESTS_DIR / module_name
    spec = importlib.util.spec_from_file_location(module_path.stem, module_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.run_all_tests()
