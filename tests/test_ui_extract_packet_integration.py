import json
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from canvas.canvas_widget import CanvasWidget
from state.app_state import AppState
from ui_extract_packet import load_packet
from ui_extract_packet import load_packet_alongside
from ui_extract_packet import load_packet_in_bench


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"
APP = QApplication.instance() or QApplication([])


def _mouse_event(event_type, point):
    return QMouseEvent(
        event_type,
        QPointF(point),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


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
                "children": ["button_1"],
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
                    "layout_mode": "free",
                    "layout_direction": None,
                    "preferred_width": None,
                    "preferred_height": None,
                    "min_width": None,
                    "min_height": None,
                    "max_width": None,
                    "max_height": None,
                    "x": 72,
                    "y": 96,
                    "width": 80,
                    "height": 32,
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
                    "trust_level": "partial",
                    "representation_origin": "adapter",
                    "warnings": [],
                },
                "raw": {
                    "provider_type": "button",
                    "provider_data": {},
                    "unresolved_fields": [],
                },
            },
        ],
        "warnings": [],
    }


def make_state():
    return AppState(str(CORE_SCHEMAS))


def load_packet_entrypoint_imports_nodes():
    state = make_state()
    with tempfile.TemporaryDirectory() as tmp:
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_text(json.dumps(protected_packet(), indent=2), encoding="utf-8")
        load_packet(state.layout_model, packet_path)

    assert state.layout_model.get_node("window_1") is not None
    assert state.layout_model.get_node("button_1") is not None


def imported_partial_node_cannot_move():
    state = make_state()
    canvas = CanvasWidget(state.layout_model, state.selection_state)
    canvas.resize(800, 600)
    with tempfile.TemporaryDirectory() as tmp:
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_text(json.dumps(protected_packet(), indent=2), encoding="utf-8")
        load_packet(state.layout_model, packet_path)

    button = state.layout_model.get_node("button_1")
    assert button is not None
    original_x = button.properties["x"]
    original_y = button.properties["y"]

    canvas.show()
    canvas.repaint()
    APP.processEvents()
    center = canvas.node_rects[button.id].center()
    moved = QPoint(center.x() + 32, center.y() + 24)
    state.selection_state.set_selection(button.id)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, center))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))

    assert button.properties["x"] == original_x
    assert button.properties["y"] == original_y


def load_packet_alongside_preserves_existing_scene():
    state = make_state()
    document = state.layout_model.create_node("document", {"layout_mode": "auto"})
    existing = state.layout_model.create_node("panel", {"layout_mode": "free", "x": 10, "y": 10, "width": 100, "height": 80})
    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, existing)

    with tempfile.TemporaryDirectory() as tmp:
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_text(json.dumps(protected_packet(), indent=2), encoding="utf-8")
        created_root_ids = load_packet_alongside(state.layout_model, packet_path)

    assert state.layout_model.get_node(document.id) is not None
    assert created_root_ids
    imported_root = state.layout_model.get_node(created_root_ids[0])
    assert imported_root is not None
    assert imported_root.id != "window_1"
    assert imported_root.metadata["provenance"]["packet_node_id"] == "window_1"


def load_packet_in_bench_creates_bench_projection():
    state = make_state()
    with tempfile.TemporaryDirectory() as tmp:
        packet_path = Path(tmp) / "packet.json"
        packet_path.write_text(json.dumps(protected_packet(), indent=2), encoding="utf-8")
        created_root_ids = load_packet_in_bench(state.layout_model, packet_path)

    assert created_root_ids
    bench_root = state.layout_model.get_node(created_root_ids[0])
    assert bench_root is not None
    assert bench_root.metadata["bench_session_id"].startswith(state.layout_model.BENCH_SESSION_PREFIX)
    assert state.layout_model.get_active_bench_session_id() == bench_root.metadata["bench_session_id"]
    workspace = state.layout_model.ensure_bench_workspace()
    assert bench_root.parent_id == workspace.id


def run_all_tests():
    tests = [
        load_packet_entrypoint_imports_nodes,
        imported_partial_node_cannot_move,
        load_packet_alongside_preserves_existing_scene,
        load_packet_in_bench_creates_bench_projection,
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
