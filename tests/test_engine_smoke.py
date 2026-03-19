import json
import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from canvas.canvas_widget import CanvasWidget
from core.layout_model import LayoutModel
from engine.constraints import clamp_to_parent
from engine.geometry import rect_contains_rect
from engine.layout_engine import LayoutEngine
from inspector.property_registry import PropertyRegistry
from state.app_state import AppState
from state.selection_state import SelectionState
from ui.main_window import MainWindow


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"
CANVAS = {"x": 0, "y": 0, "width": 1440, "height": 900}
APP = QApplication.instance() or QApplication([])


def make_model():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    return LayoutModel(registry)


def make_canvas():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    model = LayoutModel(registry)
    selection = SelectionState(model)
    canvas = CanvasWidget(model, selection)
    canvas.resize(800, 600)
    return canvas, model, selection


def _mouse_event(event_type, point, button=Qt.MouseButton.LeftButton, buttons=None):
    active_buttons = buttons if buttons is not None else button
    return QMouseEvent(
        event_type,
        QPointF(point),
        button,
        active_buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def mixed_auto_and_free_layout():
    model = make_model()
    engine = LayoutEngine(model)
    document = model.create_node("document", {"layout_mode": "auto"})
    horizontal = model.create_node("horizontal", {"layout_mode": "auto"})
    sidebar = model.create_node("sidebar", {"layout_mode": "auto"})
    main = model.create_node("main", {"layout_mode": "auto"})
    panel = model.create_node(
        "panel",
        {"layout_mode": "free", "x": 320, "y": 120, "width": 160, "height": 120},
    )
    model.add_node(model.root_id, document)
    model.add_node(document.id, horizontal)
    model.add_node(horizontal.id, sidebar)
    model.add_node(horizontal.id, main)
    model.add_node(main.id, panel)

    rects = engine.compute_layout(model.root_id, CANVAS)
    for node in (document, horizontal, sidebar, main, panel):
        assert node.id in rects
    assert rects[panel.id]["width"] == 160
    assert rects[sidebar.id]["width"] > 0


def parent_bounds_enforced():
    model = make_model()
    engine = LayoutEngine(model)
    document = model.create_node("document", {"layout_mode": "auto"})
    parent = model.create_node("panel", {"layout_mode": "auto"})
    child = model.create_node("button", {"layout_mode": "free", "x": 10, "y": 10, "width": 100, "height": 40})
    model.add_node(model.root_id, document)
    model.add_node(document.id, parent)
    model.add_node(parent.id, child)

    rects = engine.compute_layout(model.root_id, CANVAS)
    parent_rect = rects[parent.id]
    moved = engine.move_node(child.id, 999, 999, CANVAS)
    moved_rect = {"x": moved["x"], "y": moved["y"], "width": moved["width"], "height": moved["height"]}
    assert rect_contains_rect(parent_rect, moved_rect)
    assert moved_rect == clamp_to_parent(moved_rect, parent_rect)


def rect_map_unique_per_node():
    model = make_model()
    engine = LayoutEngine(model)
    document = model.create_node("document", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    for _ in range(5):
        model.add_node(document.id, model.create_node("button", {"layout_mode": "auto"}))
    rects = engine.compute_layout(model.root_id, CANVAS)
    assert len(rects) == len(set(rects))
    assert len(engine.draw_order) == len(set(engine.draw_order))


def no_negative_geometry_emitted():
    model = make_model()
    engine = LayoutEngine(model)
    node = model.create_node(
        "button",
        {"layout_mode": "free", "x": 10, "y": 10, "width": 1, "height": 1, "min_width": 50, "min_height": 30},
    )
    model.add_node(model.root_id, node)
    rects = engine.compute_layout(model.root_id, CANVAS)
    moved = engine.move_node(node.id, -100, -100, CANVAS)
    resized = engine.resize_node(node.id, "bottom_right", -1000, -1000, CANVAS)
    assert rects[node.id]["width"] >= 50
    assert moved["width"] >= 50
    assert resized["height"] >= 30


def world_rects_remain_engine_truth():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 96, "y": 88, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()
    assert canvas.engine_rects[button.id] == {
        "x": canvas.node_rects[button.id].x(),
        "y": canvas.node_rects[button.id].y(),
        "width": canvas.node_rects[button.id].width(),
        "height": canvas.node_rects[button.id].height(),
    }


def screen_mapping_uses_camera_offset():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 300, "y": 220, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()
    before = canvas.screen_rects[button.id]
    canvas.camera_x = 100
    canvas.camera_y = 60
    canvas.repaint()
    APP.processEvents()
    after = canvas.screen_rects[button.id]
    assert after.x() == before.x() - 100
    assert after.y() == before.y() - 60
    assert canvas.node_rects[button.id].x() == 300


def hit_test_uses_world_space():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 300, "y": 220, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()
    canvas.camera_x = 120
    canvas.camera_y = 80
    canvas.repaint()
    APP.processEvents()
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, canvas.screen_rects[button.id].center()))
    assert selection.get_selection() == button.id


def drag_after_pan_updates_correct_world_position():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 300, "y": 220, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()
    canvas.camera_x = 120
    canvas.camera_y = 80
    canvas.repaint()
    APP.processEvents()
    start = canvas.screen_rects[button.id].center()
    moved = QPoint(start.x() + 40, start.y() + 24)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))
    assert button.properties["x"] > 300
    assert button.properties["y"] > 220


def focus_selected_recenters_camera_without_rescaling():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 1000, "y": 760, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()
    selection.set_selection(button.id)
    before = dict(canvas.get_viewport_state()["camera"])
    canvas.focus_selected_node()
    after = dict(canvas.get_viewport_state()["camera"])
    assert after != before
    assert "scale" not in canvas.get_viewport_state()


def show_all_resets_camera():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 1000, "y": 760, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()
    selection.set_selection(button.id)
    canvas.focus_selected_node()
    canvas.clear_focus()
    assert canvas.camera_x == 0
    assert canvas.camera_y == 0


def resize_after_pan_uses_world_delta():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 300, "y": 220, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()
    selection.set_selection(button.id)
    canvas.camera_x = 120
    canvas.camera_y = 80
    canvas.repaint()
    APP.processEvents()
    handle = canvas.handle_rects[(button.id, "bottom_right")].center()
    moved = QPoint(handle.x() + 48, handle.y() + 40)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, handle))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))
    assert button.properties["width"] > 120
    assert button.properties["height"] > 64


def panning_does_not_change_node_geometry():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 300, "y": 220, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    before = dict(button.properties)
    canvas.show()
    canvas.repaint()
    APP.processEvents()
    start = QPoint(200, 200)
    moved = QPoint(150, 120)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start, button=Qt.MouseButton.MiddleButton))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved, button=Qt.MouseButton.NoButton, buttons=Qt.MouseButton.MiddleButton))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved, button=Qt.MouseButton.MiddleButton))
    assert button.properties == before


def drag_no_longer_requires_viewport_lock():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 300, "y": 220, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()
    before = dict(canvas.get_viewport_state()["camera"])
    start = canvas.screen_rects[button.id].center()
    moved = QPoint(start.x() + 20, start.y() + 20)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    during = dict(canvas.get_viewport_state()["camera"])
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))
    assert during == before


def middle_mouse_pan_updates_camera():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    canvas.show()
    canvas.repaint()
    APP.processEvents()
    start = QPoint(240, 220)
    moved = QPoint(160, 140)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start, button=Qt.MouseButton.MiddleButton))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved, button=Qt.MouseButton.NoButton, buttons=Qt.MouseButton.MiddleButton))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved, button=Qt.MouseButton.MiddleButton))
    assert canvas.camera_x > 0
    assert canvas.camera_y > 0


def status_strip_updates_focus_label():
    state = AppState(str(CORE_SCHEMAS))
    state.layout_model.set_scene_metadata(
        {
            "representation_origin": "adapter",
            "packet_trust_level": "partial",
        }
    )
    document = state.layout_model.create_node("document", {"layout_mode": "auto"})
    button = state.layout_model.create_node("button", {"layout_mode": "free", "x": 900, "y": 700, "width": 120, "height": 64})
    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, button)
    window = MainWindow(state)
    state.selection_state.set_selection(button.id)
    window.canvas_panel.focus_selected_node()
    APP.processEvents()
    assert "SCENE: adapter/partial" in window.canvas_status_label.text()
    assert "MODE: source" in window.canvas_status_label.text()
    assert f"FOCUS: {button.id}" in window.canvas_status_label.text()


def unified_scene_actions_exist():
    state = AppState(str(CORE_SCHEMAS))
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project_path = tmp_path / "project.json"
        packet_path = tmp_path / "ui_extract_packet.json"
        project_path.write_text(
            json.dumps({"version": "v1", "data": {"id": "root", "type": "root", "properties": {}, "children": []}}, indent=2),
            encoding="utf-8",
        )
        packet_path.write_text(
            json.dumps(
                {
                    "packet_version": "1",
                    "source_framework": "pyside6",
                    "source_provider": "manual_adapter",
                    "trust_level": "partial",
                    "roots": [],
                    "nodes": [],
                    "warnings": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        state.set_scene_source_target("project", str(project_path))
        state.set_scene_source_target("extract_packet", str(packet_path))
        window = MainWindow(state)
        project_section = window.section_contents["Project"]
        save_group = project_section.findChild(QWidget, "project_save_group")
        source_group = project_section.findChild(QWidget, "project_source_group")
        actions_group = project_section.findChild(QWidget, "project_scene_actions_group")
        export_group = project_section.findChild(QWidget, "project_export_group")
        save_group_title = project_section.findChild(QLabel, "project_save_group_title")
        source_group_title = project_section.findChild(QLabel, "project_source_group_title")
        actions_group_title = project_section.findChild(QLabel, "project_scene_actions_group_title")
        export_group_title = project_section.findChild(QLabel, "project_export_group_title")
        save_target_label = project_section.findChild(QLabel, "save_target_label")
        selector = project_section.findChild(QComboBox, "scene_source_selector")
        target_field = project_section.findChild(QLineEdit, "scene_source_target_field")
        hint_label = project_section.findChild(QLabel, "scene_action_hint_label")
        preflight_label = project_section.findChild(QLabel, "scene_source_preflight_label")
        context_label = project_section.findChild(QLabel, "scene_action_context_label")
        replace_button = project_section.findChild(QPushButton, "scene_replace_button")
        alongside_button = project_section.findChild(QPushButton, "scene_alongside_button")
        bench_button = project_section.findChild(QPushButton, "scene_bench_button")

        assert save_group is not None
        assert source_group is not None
        assert actions_group is not None
        assert export_group is not None
        assert save_group_title is not None
        assert save_group_title.text() == "Save & Persist"
        assert source_group_title is not None
        assert source_group_title.text() == "Source Target"
        assert actions_group_title is not None
        assert actions_group_title.text() == "Scene Actions"
        assert export_group_title is not None
        assert export_group_title.text() == "Export"
        assert save_target_label is not None
        assert save_target_label.text() == f"Save Target: {project_path}"
        assert selector is not None
        assert selector.count() == 2
        assert selector.itemText(0) == "Project JSON"
        assert selector.itemText(1) == "UI Extract Packet"
        assert target_field is not None
        assert target_field.text() == str(project_path)
        assert preflight_label is not None
        assert preflight_label.text() == "Preflight: valid project file"
        assert hint_label is not None
        assert context_label is not None
        assert "Current scene is design-only" in context_label.text()
        assert "incoming project JSON" in context_label.text()
        assert str(project_path) in context_label.text()
        assert "Alongside: preserves the current scene" in hint_label.text()
        selector.setCurrentIndex(1)
        APP.processEvents()
        assert target_field.text() == str(packet_path)
        assert save_target_label.text() == f"Save Target: {project_path}"
        assert preflight_label.text() == "Preflight: valid extract packet"
        assert replace_button is not None
        assert replace_button.text() == "Replace Current Scene"
        assert alongside_button is not None
        assert alongside_button.text() == "Import Alongside (Recommended)"
        assert bench_button is not None
        assert bench_button.text() == "Open In Bench"
        window.eventFilter(alongside_button, QEvent(QEvent.Type.FocusIn))
        assert "Alongside: preserves the current scene" in hint_label.text()
        window.eventFilter(bench_button, QEvent(QEvent.Type.FocusIn))
        assert "Recommended: Bench preserves the current scene" in hint_label.text()


def source_scene_defaults_to_bench_recommendation():
    state = AppState(str(CORE_SCHEMAS))
    state.layout_model.set_scene_metadata(
        {
            "representation_origin": "adapter",
            "packet_trust_level": "partial",
        }
    )
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project_path = tmp_path / "project.json"
        project_path.write_text(
            json.dumps({"version": "v1", "data": {"id": "root", "type": "root", "properties": {}, "children": []}}, indent=2),
            encoding="utf-8",
        )
        state.set_scene_source_target("project", str(project_path))
        window = MainWindow(state)
        project_section = window.section_contents["Project"]
        hint_label = project_section.findChild(QLabel, "scene_action_hint_label")
        context_label = project_section.findChild(QLabel, "scene_action_context_label")
        alongside_button = project_section.findChild(QPushButton, "scene_alongside_button")
        bench_button = project_section.findChild(QPushButton, "scene_bench_button")

        assert hint_label is not None
        assert context_label is not None
        assert alongside_button is not None
        assert bench_button is not None
        assert "Current scene is source-backed" in context_label.text()
        assert "incoming project JSON" in context_label.text()
        assert str(project_path) in context_label.text()
        assert "Recommended: Bench preserves the current scene" in hint_label.text()
        assert alongside_button.text() == "Import Alongside"
        assert bench_button.text() == "Open In Bench (Recommended)"


def scene_source_target_field_updates_app_state():
    state = AppState(str(CORE_SCHEMAS))
    window = MainWindow(state)
    project_section = window.section_contents["Project"]
    selector = project_section.findChild(QComboBox, "scene_source_selector")
    save_target_label = project_section.findChild(QLabel, "save_target_label")
    target_field = project_section.findChild(QLineEdit, "scene_source_target_field")
    preflight_label = project_section.findChild(QLabel, "scene_source_preflight_label")
    context_label = project_section.findChild(QLabel, "scene_action_context_label")
    hint_label = project_section.findChild(QLabel, "scene_action_hint_label")
    replace_button = project_section.findChild(QPushButton, "scene_replace_button")
    alongside_button = project_section.findChild(QPushButton, "scene_alongside_button")
    bench_button = project_section.findChild(QPushButton, "scene_bench_button")

    assert selector is not None
    assert save_target_label is not None
    assert target_field is not None
    assert preflight_label is not None
    assert context_label is not None
    assert hint_label is not None
    assert replace_button is not None
    assert alongside_button is not None
    assert bench_button is not None
    selector.setCurrentIndex(1)
    APP.processEvents()
    target_field.setText("packets/custom_packet.json")
    target_field.editingFinished.emit()
    assert state.get_scene_source_target("extract_packet") == "packets/custom_packet.json"
    assert preflight_label.text() == "Preflight: missing target"
    assert (
        context_label.text()
        == "Scene actions are unavailable until the selected source passes preflight."
    )
    assert hint_label.text() == ""
    assert not replace_button.isEnabled()
    assert not alongside_button.isEnabled()
    assert not bench_button.isEnabled()
    selector.setCurrentIndex(0)
    APP.processEvents()
    assert target_field.text() == "project.json"
    target_field.setText("projects/custom_project.json")
    target_field.editingFinished.emit()
    assert save_target_label.text() == "Save Target: projects/custom_project.json"
    assert (
        context_label.text()
        == "Scene actions are unavailable until the selected source passes preflight."
    )
    selector.setCurrentIndex(1)
    APP.processEvents()
    assert target_field.text() == "packets/custom_packet.json"
    assert save_target_label.text() == "Save Target: projects/custom_project.json"


def scene_source_preflight_reflects_target_validity():
    state = AppState(str(CORE_SCHEMAS))
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        project_path = tmp_path / "scene_project.json"
        packet_path = tmp_path / "scene_packet.json"
        project_path.write_text(
            json.dumps({"version": "v1", "data": {"id": "root", "type": "root", "properties": {}, "children": []}}, indent=2),
            encoding="utf-8",
        )
        packet_path.write_text(
            json.dumps(
                {
                    "packet_version": "1",
                    "source_framework": "pyside6",
                    "source_provider": "manual_adapter",
                    "trust_level": "partial",
                    "roots": ["button_1"],
                    "nodes": [
                        {
                            "id": "button_1",
                            "type": "button",
                            "ui_role": None,
                            "parent": None,
                            "children": [],
                            "source": {
                                "file": "ui/main_window.py",
                                "symbol": "save_button",
                                "line_start": 10,
                                "line_end": 10,
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
                                "x": 20,
                                "y": 20,
                                "width": 120,
                                "height": 40,
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
                        }
                    ],
                    "warnings": [],
                },
                indent=2,
            ),
            encoding="utf-8",
        )
        state.set_scene_source_target("project", str(project_path))
        state.set_scene_source_target("extract_packet", str(packet_path))
        window = MainWindow(state)
        project_section = window.section_contents["Project"]
        selector = project_section.findChild(QComboBox, "scene_source_selector")
        preflight_label = project_section.findChild(QLabel, "scene_source_preflight_label")
        target_field = project_section.findChild(QLineEdit, "scene_source_target_field")

        assert selector is not None
        assert preflight_label is not None
        assert target_field is not None
        assert preflight_label.text() == "Preflight: valid project file"
        selector.setCurrentIndex(1)
        APP.processEvents()
        assert preflight_label.text() == "Preflight: valid extract packet"
        target_field.setText(str(tmp_path / "missing.json"))
        target_field.editingFinished.emit()
        assert preflight_label.text() == "Preflight: missing target"


def no_auto_reframe_on_interaction():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 300, "y": 220, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()
    selection.set_selection(button.id)
    canvas.repaint()
    APP.processEvents()
    before_camera = dict(canvas.get_viewport_state()["camera"])
    handle = canvas.handle_rects[(button.id, "bottom_right")].center()
    moved = QPoint(handle.x() + 24, handle.y() + 24)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, handle))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    during_camera = dict(canvas.get_viewport_state()["camera"])
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))
    assert during_camera == before_camera


def run_all_tests():
    tests = [
        mixed_auto_and_free_layout,
        parent_bounds_enforced,
        rect_map_unique_per_node,
        no_negative_geometry_emitted,
        world_rects_remain_engine_truth,
        screen_mapping_uses_camera_offset,
        hit_test_uses_world_space,
        drag_after_pan_updates_correct_world_position,
        focus_selected_recenters_camera_without_rescaling,
        show_all_resets_camera,
        resize_after_pan_uses_world_delta,
        panning_does_not_change_node_geometry,
        drag_no_longer_requires_viewport_lock,
        middle_mouse_pan_updates_camera,
        status_strip_updates_focus_label,
        unified_scene_actions_exist,
        source_scene_defaults_to_bench_recommendation,
        scene_source_target_field_updates_app_state,
        scene_source_preflight_reflects_target_validity,
        no_auto_reframe_on_interaction,
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
