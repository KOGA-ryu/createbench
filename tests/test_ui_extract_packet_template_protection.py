import json
import sys
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from canvas.canvas_widget import CanvasWidget
from state.app_state import AppState
from ui_extract_packet import load_packet


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"
APP = QApplication.instance() or QApplication([])


def protected_packet():
    return {
        "packet_version": "1",
        "source_framework": "pyside6",
        "source_provider": "manual_adapter",
        "trust_level": "partial",
        "roots": ["window_1"],
        "nodes": [
            {
                "id": "window_1",
                "type": "panel",
                "ui_role": "tool_window",
                "parent": None,
                "children": [],
                "source": {
                    "file": "ui/main_window.py",
                    "symbol": "MainWindow",
                    "line_start": 10,
                    "line_end": 120,
                    "source_id": "src_window_1",
                },
                "layout_hints": {
                    "layout_mode": "free",
                    "layout_direction": None,
                    "preferred_width": None,
                    "preferred_height": None,
                    "min_width": None,
                    "min_height": None,
                    "max_width": None,
                    "max_height": None,
                    "x": 40,
                    "y": 60,
                    "width": 320,
                    "height": 240,
                },
                "render_hints": {
                    "title": "Main Window",
                    "text": None,
                    "placeholder": None,
                    "icon": None,
                    "visible": True,
                    "enabled": True,
                    "window_mode": "window",
                },
                "relationships": {
                    "communicates_to": [],
                    "depends_on": [],
                    "updated_by": [],
                    "triggered_by": [],
                },
                "trust": {
                    "trust_level": "partial",
                    "representation_origin": "adapter",
                    "warnings": [],
                },
                "raw": {
                    "provider_type": "widget",
                    "provider_data": {},
                    "unresolved_fields": [],
                },
            },
        ],
        "warnings": [],
    }


def template_node():
    return {
        "type": "button",
        "properties": {"text": "Injected"},
        "children": [],
    }


def make_state():
    return AppState(str(CORE_SCHEMAS))


def template_not_applied_into_protected_selected_parent():
    state = make_state()
    canvas = CanvasWidget(state.layout_model, state.selection_state)
    with tempfile.TemporaryDirectory() as tmp:
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_text(json.dumps(protected_packet(), indent=2), encoding="utf-8")
        load_packet(state.layout_model, packet_path)

    state.selection_state.set_selection("window_1")
    canvas.apply_template(template_node(), replace_root=False)
    window = state.layout_model.get_node("window_1")
    assert window is not None
    assert window.children == []


def template_not_applied_when_replacing_protected_root():
    state = make_state()
    canvas = CanvasWidget(state.layout_model, state.selection_state)
    with tempfile.TemporaryDirectory() as tmp:
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_text(json.dumps(protected_packet(), indent=2), encoding="utf-8")
        load_packet(state.layout_model, packet_path)

    root_children_before = [child.id for child in state.layout_model.get_children(state.layout_model.root_id)]
    canvas.apply_template(template_node(), replace_root=True)
    root_children_after = [child.id for child in state.layout_model.get_children(state.layout_model.root_id)]
    assert root_children_after == root_children_before


def clear_root_children_blocked_for_protected_root():
    state = make_state()
    canvas = CanvasWidget(state.layout_model, state.selection_state)
    with tempfile.TemporaryDirectory() as tmp:
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_text(json.dumps(protected_packet(), indent=2), encoding="utf-8")
        load_packet(state.layout_model, packet_path)

    root_children_before = [child.id for child in state.layout_model.get_children(state.layout_model.root_id)]
    canvas.clear_root_children()
    root_children_after = [child.id for child in state.layout_model.get_children(state.layout_model.root_id)]

    assert root_children_after == root_children_before


def template_not_applied_into_source_scene_root_when_nothing_selected():
    state = make_state()
    canvas = CanvasWidget(state.layout_model, state.selection_state)
    with tempfile.TemporaryDirectory() as tmp:
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_text(json.dumps(protected_packet(), indent=2), encoding="utf-8")
        load_packet(state.layout_model, packet_path)

    root_children_before = [child.id for child in state.layout_model.get_children(state.layout_model.root_id)]
    state.selection_state.clear_selection()
    canvas.apply_template(template_node(), replace_root=False)
    root_children_after = [child.id for child in state.layout_model.get_children(state.layout_model.root_id)]

    assert root_children_after == root_children_before


def add_child_blocked_at_source_scene_root():
    state = make_state()
    canvas = CanvasWidget(state.layout_model, state.selection_state)
    with tempfile.TemporaryDirectory() as tmp:
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_text(json.dumps(protected_packet(), indent=2), encoding="utf-8")
        load_packet(state.layout_model, packet_path)

    root_children_before = [child.id for child in state.layout_model.get_children(state.layout_model.root_id)]
    state.selection_state.clear_selection()
    canvas.add_child_to_selected()
    root_children_after = [child.id for child in state.layout_model.get_children(state.layout_model.root_id)]

    assert root_children_after == root_children_before


def create_component_blocked_at_source_scene_root():
    state = make_state()
    canvas = CanvasWidget(state.layout_model, state.selection_state)
    with tempfile.TemporaryDirectory() as tmp:
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_text(json.dumps(protected_packet(), indent=2), encoding="utf-8")
        load_packet(state.layout_model, packet_path)

    root_children_before = [child.id for child in state.layout_model.get_children(state.layout_model.root_id)]
    state.selection_state.clear_selection()
    created = canvas.create_component_node("button", {"text": "Injected"})
    root_children_after = [child.id for child in state.layout_model.get_children(state.layout_model.root_id)]

    assert created is None
    assert root_children_after == root_children_before


def run_all_tests():
    tests = [
        template_not_applied_into_protected_selected_parent,
        template_not_applied_when_replacing_protected_root,
        clear_root_children_blocked_for_protected_root,
        template_not_applied_into_source_scene_root_when_nothing_selected,
        add_child_blocked_at_source_scene_root,
        create_component_blocked_at_source_scene_root,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            APP.processEvents()
            passed += 1
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")

    print(f"\nResult: {passed} passed, {failed} failed")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    run_all_tests()
