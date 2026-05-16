import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from state.app_state import AppState
from ui_extract_packet import import_packet_into_layout, validate_packet


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


def make_state():
    return AppState(str(CORE_SCHEMAS))


def sample_packet():
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
                "children": ["button_1", "button_2"],
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
                    "warnings": ["geometry inferred"],
                },
                "raw": {
                    "provider_type": "widget",
                    "provider_data": {"class_name": "QMainWindow"},
                    "unresolved_fields": ["ui_role"],
                },
            },
            {
                "id": "button_1",
                "type": "button",
                "ui_role": None,
                "parent": "window_1",
                "children": [],
                "source": {
                    "file": "ui/main_window.py",
                    "symbol": "save_button",
                    "line_start": 40,
                    "line_end": 40,
                    "source_id": "src_button_1",
                },
                "layout_hints": {
                    "layout_mode": "auto",
                    "layout_direction": None,
                    "preferred_width": None,
                    "preferred_height": None,
                    "min_width": None,
                    "min_height": None,
                    "max_width": None,
                    "max_height": None,
                    "x": None,
                    "y": None,
                    "width": None,
                    "height": None,
                },
                "render_hints": {
                    "title": None,
                    "text": "Save",
                    "placeholder": None,
                    "icon": None,
                    "visible": True,
                    "enabled": True,
                    "window_mode": None,
                },
                "relationships": {
                    "communicates_to": [],
                    "depends_on": [],
                    "updated_by": [],
                    "triggered_by": [],
                },
                "trust": {
                    "trust_level": "source",
                    "representation_origin": "source",
                    "warnings": [],
                },
                "raw": {
                    "provider_type": "button",
                    "provider_data": {},
                    "unresolved_fields": [],
                },
            },
            {
                "id": "button_2",
                "type": "button",
                "ui_role": None,
                "parent": "window_1",
                "children": [],
                "source": {
                    "file": "ui/main_window.py",
                    "symbol": "cancel_button",
                    "line_start": 41,
                    "line_end": 41,
                    "source_id": "src_button_2",
                },
                "layout_hints": {
                    "layout_mode": "auto",
                    "layout_direction": None,
                    "preferred_width": None,
                    "preferred_height": None,
                    "min_width": None,
                    "min_height": None,
                    "max_width": None,
                    "max_height": None,
                    "x": None,
                    "y": None,
                    "width": None,
                    "height": None,
                },
                "render_hints": {
                    "title": None,
                    "text": "Cancel",
                    "placeholder": None,
                    "icon": None,
                    "visible": True,
                    "enabled": True,
                    "window_mode": None,
                },
                "relationships": {
                    "communicates_to": [],
                    "depends_on": [],
                    "updated_by": [],
                    "triggered_by": [],
                },
                "trust": {
                    "trust_level": "source",
                    "representation_origin": "source",
                    "warnings": [],
                },
                "raw": {
                    "provider_type": "button",
                    "provider_data": {},
                    "unresolved_fields": [],
                },
            },
        ],
        "warnings": ["packet has inferred geometry"],
    }


def valid_packet_passes_validation():
    validate_packet(sample_packet())


def invalid_packet_missing_fields_fails():
    packet = sample_packet()
    del packet["nodes"][0]["source"]
    try:
        validate_packet(packet)
        raise AssertionError("Expected missing field validation error")
    except ValueError as exc:
        assert "missing required fields" in str(exc)


def parent_child_mismatch_fails():
    packet = sample_packet()
    packet["nodes"][0]["children"] = ["button_1"]
    try:
        validate_packet(packet)
        raise AssertionError("Expected parent/child mismatch error")
    except ValueError as exc:
        assert "parent/child mismatch" in str(exc)


def import_preserves_child_order():
    state = make_state()
    import_packet_into_layout(state.layout_model, sample_packet())
    window = state.layout_model.get_node("window_1")
    assert window is not None
    assert window.children == ["button_1", "button_2"]


def import_maps_ui_role_correctly():
    state = make_state()
    import_packet_into_layout(state.layout_model, sample_packet())
    window = state.layout_model.get_node("window_1")
    assert window is not None
    assert window.properties["ui_role"] == "tool_window"


def import_preserves_metadata():
    state = make_state()
    import_packet_into_layout(state.layout_model, sample_packet())
    window = state.layout_model.get_node("window_1")
    assert window is not None
    assert window.metadata["source"]["file"] == "ui/main_window.py"
    assert window.metadata["layout_hints"]["width"] == 320
    assert window.metadata["render_hints"]["title"] == "Main Window"
    assert window.metadata["raw"]["unresolved_fields"] == ["ui_role"]
    assert window.metadata["provenance"]["source_provider"] == "manual_adapter"
    assert state.layout_model.scene_metadata["source_provider"] == "manual_adapter"
    assert state.layout_model.scene_metadata["packet_trust_level"] == "partial"


def trust_level_not_lost_on_import():
    state = make_state()
    import_packet_into_layout(state.layout_model, sample_packet())
    window = state.layout_model.get_node("window_1")
    assert window is not None
    assert window.metadata["trust"]["trust_level"] == "partial"


def run_all_tests():
    tests = [
        valid_packet_passes_validation,
        invalid_packet_missing_fields_fails,
        parent_child_mismatch_fails,
        import_preserves_child_order,
        import_maps_ui_role_correctly,
        import_preserves_metadata,
        trust_level_not_lost_on_import,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
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
