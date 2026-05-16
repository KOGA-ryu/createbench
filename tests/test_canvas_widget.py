import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from canvas.canvas_widget import CanvasWidget
from core.layout_model import LayoutModel
from core.node import Node
from inspector.property_registry import PropertyRegistry
from state.selection_state import SelectionState


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"
APP = QApplication.instance() or QApplication([])


def make_canvas():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    model = LayoutModel(registry)
    selection = SelectionState(model)
    canvas = CanvasWidget(model, selection)
    canvas.resize(800, 600)
    return canvas, model, selection


class RecordingCanvas(CanvasWidget):
    def __init__(self, layout_model, selection_state):
        super().__init__(layout_model, selection_state)
        self.draw_calls = []

    def _record(self, name, node, screen_rect, profile, painter):
        self.draw_calls.append((name, node.id))
        self._current_paint_node_id = node.id
        self.paint_rects[node.id] = screen_rect

    def _draw_button(self, node, screen_rect, profile, painter):
        self._record("button", node, screen_rect, profile, painter)

    def _draw_text(self, node, screen_rect, profile, painter):
        self._record("text", node, screen_rect, profile, painter)

    def _draw_input(self, node, screen_rect, profile, painter):
        self._record("input", node, screen_rect, profile, painter)

    def _draw_toolbar(self, node, screen_rect, profile, painter):
        self._record("toolbar", node, screen_rect, profile, painter)

    def _draw_sidebar(self, node, screen_rect, profile, painter):
        self._record("sidebar", node, screen_rect, profile, painter)

    def _draw_main(self, node, screen_rect, profile, painter):
        self._record("main", node, screen_rect, profile, painter)

    def _draw_panel(self, node, screen_rect, profile, painter):
        self._record("panel", node, screen_rect, profile, painter)

    def _draw_container(self, node, screen_rect, profile, painter):
        self._record("container", node, screen_rect, profile, painter)

    def _draw_tool_window(self, node, screen_rect, profile, painter):
        self._record("tool_window", node, screen_rect, profile, painter)

    def _draw_dialog(self, node, screen_rect, profile, painter):
        self._record("dialog", node, screen_rect, profile, painter)

    def _draw_generic_fallback(self, node, screen_rect, profile, painter):
        self._record("generic_fallback", node, screen_rect, profile, painter)


def _mouse_event(event_type, point, button=Qt.MouseButton.LeftButton, buttons=None):
    active_buttons = buttons if buttons is not None else button
    return QMouseEvent(
        event_type,
        QPointF(point),
        button,
        active_buttons,
        Qt.KeyboardModifier.NoModifier,
    )


def _wheel_event(point, angle_x=0, angle_y=0):
    return QWheelEvent(
        QPointF(point),
        QPointF(point),
        QPoint(angle_x, angle_y),
        QPoint(angle_x, angle_y),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.ScrollUpdate,
        False,
    )


def _source_metadata():
    return {
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter", "source_provider": "bluebench"},
    }


def world_rects_remain_engine_truth():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 120, "y": 120, "width": 200, "height": 96})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    engine_rect = canvas.engine_rects[button.id]
    world_rect = canvas.node_rects[button.id]
    assert engine_rect == {
        "x": world_rect.x(),
        "y": world_rect.y(),
        "width": world_rect.width(),
        "height": world_rect.height(),
    }
    assert canvas.authored_canvas_rect()["width"] == 8000
    assert canvas.authored_canvas_rect()["height"] == 8000


def screen_mapping_uses_camera_offset():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 300, "y": 220, "width": 200, "height": 96})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    before_world = canvas.node_rects[button.id]
    before_screen = canvas.screen_rects[button.id]
    canvas.camera_x = 80
    canvas.camera_y = 40
    canvas.repaint()
    APP.processEvents()

    after_world = canvas.node_rects[button.id]
    after_screen = canvas.screen_rects[button.id]
    assert after_world == before_world
    assert after_screen.x() == before_screen.x() - 80
    assert after_screen.y() == before_screen.y() - 40


def hit_test_uses_world_space():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 320, "y": 240, "width": 200, "height": 96})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    canvas.camera_x = 160
    canvas.camera_y = 80
    canvas.repaint()
    APP.processEvents()
    click_point = canvas.screen_rects[button.id].center()
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, click_point))
    assert selection.get_selection() == button.id


def drag_after_pan_updates_correct_world_position():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 320, "y": 240, "width": 200, "height": 96})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    canvas.camera_x = 160
    canvas.camera_y = 80
    canvas.repaint()
    APP.processEvents()
    start = canvas.screen_rects[button.id].center()
    moved = QPoint(start.x() + 40, start.y() + 24)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))

    assert button.properties["x"] > 320
    assert button.properties["y"] > 240


def focus_selected_recenters_camera_without_rescaling():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 900, "y": 700, "width": 200, "height": 96})
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
    button = model.create_node("button", {"layout_mode": "free", "x": 900, "y": 700, "width": 200, "height": 96})
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
    button = model.create_node("button", {"layout_mode": "free", "x": 320, "y": 240, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    canvas.show()
    canvas.repaint()
    APP.processEvents()
    selection.set_selection(button.id)
    canvas.camera_x = 160
    canvas.camera_y = 80
    canvas.repaint()
    APP.processEvents()

    handle = canvas.handle_rects[(button.id, "bottom_right")].center()
    moved = QPoint(handle.x() + 50, handle.y() + 40)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, handle))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))

    assert button.properties["width"] > 120
    assert button.properties["height"] > 64


def panning_does_not_change_node_geometry():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 320, "y": 240, "width": 200, "height": 96})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    before = dict(button.properties)

    canvas.show()
    canvas.repaint()
    APP.processEvents()
    start = QPoint(200, 200)
    moved = QPoint(140, 120)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start, button=Qt.MouseButton.MiddleButton))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved, button=Qt.MouseButton.NoButton, buttons=Qt.MouseButton.MiddleButton))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved, button=Qt.MouseButton.MiddleButton))

    assert button.properties == before


def drag_no_longer_requires_viewport_lock():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 120, "y": 120, "width": 200, "height": 96})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    canvas.show()
    canvas.repaint()
    APP.processEvents()
    start = canvas.screen_rects[button.id].center()
    moved = QPoint(start.x() + 30, start.y() + 30)
    before = dict(canvas.get_viewport_state()["camera"])
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
    start = QPoint(200, 200)
    moved = QPoint(140, 120)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start, button=Qt.MouseButton.MiddleButton))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved, button=Qt.MouseButton.NoButton, buttons=Qt.MouseButton.MiddleButton))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved, button=Qt.MouseButton.MiddleButton))
    assert canvas.camera_x > 0
    assert canvas.camera_y > 0


def wheel_pan_updates_camera():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)

    canvas.show()
    canvas.repaint()
    APP.processEvents()
    canvas.wheelEvent(_wheel_event(QPoint(200, 200), angle_y=-120))
    canvas.wheelEvent(_wheel_event(QPoint(200, 200), angle_x=-120))
    assert canvas.camera_x > 0
    assert canvas.camera_y > 0


def make_recording_canvas():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    model = LayoutModel(registry)
    selection = SelectionState(model)
    canvas = RecordingCanvas(model, selection)
    canvas.resize(800, 600)
    return canvas, model, selection


def _paint(canvas):
    canvas.show()
    canvas.repaint()
    APP.processEvents()


def button_resolves_to_button_draw_path():
    canvas, model, _selection = make_recording_canvas()
    button = model.create_node("button", {"layout_mode": "free", "x": 40, "y": 40, "width": 80, "height": 32})
    model.add_node(model.root_id, button)

    _paint(canvas)

    assert ("button", button.id) in canvas.draw_calls
    assert ("generic_fallback", button.id) not in canvas.draw_calls
    assert canvas.render_profiles[button.id]["render_kind"] == "button"


def toolbar_resolves_to_toolbar_draw_path():
    canvas, model, _selection = make_recording_canvas()
    toolbar = model.create_node("toolbar", {"layout_mode": "free", "x": 20, "y": 20, "width": 300, "height": 40})
    model.add_node(model.root_id, toolbar)

    _paint(canvas)

    assert ("toolbar", toolbar.id) in canvas.draw_calls
    assert ("generic_fallback", toolbar.id) not in canvas.draw_calls
    assert canvas.render_profiles[toolbar.id]["render_kind"] == "toolbar"


def sidebar_resolves_to_sidebar_draw_path():
    canvas, model, _selection = make_recording_canvas()
    sidebar = model.create_node("sidebar", {"layout_mode": "free", "x": 20, "y": 20, "width": 240, "height": 300})
    model.add_node(model.root_id, sidebar)

    _paint(canvas)

    assert ("sidebar", sidebar.id) in canvas.draw_calls
    assert ("generic_fallback", sidebar.id) not in canvas.draw_calls
    assert canvas.render_profiles[sidebar.id]["render_kind"] == "sidebar"


def panel_resolves_to_panel_draw_path():
    canvas, model, _selection = make_recording_canvas()
    panel = model.create_node("panel", {"layout_mode": "free", "x": 20, "y": 20, "width": 260, "height": 180})
    model.add_node(model.root_id, panel)

    _paint(canvas)

    assert ("panel", panel.id) in canvas.draw_calls
    assert ("generic_fallback", panel.id) not in canvas.draw_calls
    assert canvas.render_profiles[panel.id]["render_kind"] == "panel"


def container_resolves_to_container_draw_path():
    canvas, model, _selection = make_recording_canvas()
    container = model.create_node("container", {"layout_mode": "free", "x": 20, "y": 20, "width": 260, "height": 180})
    model.add_node(model.root_id, container)

    _paint(canvas)

    assert ("container", container.id) in canvas.draw_calls
    assert ("generic_fallback", container.id) not in canvas.draw_calls
    assert canvas.render_profiles[container.id]["render_kind"] == "container"


def tool_window_role_resolves_to_tool_window_draw_path():
    canvas, model, _selection = make_recording_canvas()
    window = model.create_node("panel", {"ui_role": "tool_window", "layout_mode": "free", "x": 20, "y": 20, "width": 260, "height": 180})
    model.add_node(model.root_id, window)

    _paint(canvas)

    assert ("tool_window", window.id) in canvas.draw_calls
    assert ("generic_fallback", window.id) not in canvas.draw_calls
    assert canvas.render_profiles[window.id]["render_kind"] == "tool_window"


def dialog_role_resolves_to_dialog_draw_path():
    canvas, model, _selection = make_recording_canvas()
    dialog = model.create_node("panel", {"ui_role": "dialog", "layout_mode": "free", "x": 20, "y": 20, "width": 260, "height": 180})
    model.add_node(model.root_id, dialog)

    _paint(canvas)

    assert ("dialog", dialog.id) in canvas.draw_calls
    assert ("generic_fallback", dialog.id) not in canvas.draw_calls
    assert canvas.render_profiles[dialog.id]["render_kind"] == "dialog"


def unsupported_role_type_uses_generic_fallback_draw_path():
    canvas, model, _selection = make_recording_canvas()
    unknown = Node(
        id="unknown_widget_1",
        type="unknown_widget",
        properties={"layout_mode": "free", "x": 20, "y": 20, "width": 180, "height": 120},
        parent_id=None,
    )
    model.add_node(model.root_id, unknown)

    _paint(canvas)

    assert ("generic_fallback", unknown.id) in canvas.draw_calls
    assert canvas.render_profiles[unknown.id]["render_kind"] == "generic_fallback"


def unsupported_ui_role_falls_back_to_supported_node_type_draw_path():
    canvas, model, _selection = make_recording_canvas()
    button = model.create_node(
        "button",
        {"ui_role": "mystery_role", "layout_mode": "free", "x": 20, "y": 20, "width": 80, "height": 32},
    )
    model.add_node(model.root_id, button)

    _paint(canvas)

    assert ("button", button.id) in canvas.draw_calls
    assert ("generic_fallback", button.id) not in canvas.draw_calls
    assert canvas.render_profiles[button.id]["render_kind"] == "button"


def selection_does_not_change_render_dispatch():
    canvas, model, selection = make_recording_canvas()
    button = model.create_node("button", {"layout_mode": "free", "x": 20, "y": 20, "width": 80, "height": 32})
    model.add_node(model.root_id, button)

    _paint(canvas)
    baseline_calls = list(canvas.draw_calls)
    canvas.draw_calls.clear()
    selection.set_selection(button.id)
    _paint(canvas)

    assert ("button", button.id) in baseline_calls
    assert ("button", button.id) in canvas.draw_calls
    assert ("generic_fallback", button.id) not in canvas.draw_calls


def source_node_resolves_source_badge():
    canvas, model, _selection = make_canvas()
    button = model.create_node("button", {"layout_mode": "free", "x": 20, "y": 20, "width": 120, "height": 40})
    button.metadata = {
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter"},
    }
    badge = canvas._resolve_node_badge(button)
    assert badge is not None
    assert badge["text"] == "SOURCE"


def forked_node_resolves_fork_badge():
    canvas, model, _selection = make_canvas()
    button = model.create_node("button", {"layout_mode": "free", "x": 20, "y": 20, "width": 120, "height": 40})
    button.metadata = {
        "origin_node_id": "button_1",
        "trust": {"trust_level": "partial", "representation_origin": "manual", "warnings": []},
        "provenance": {"representation_origin": "manual"},
    }
    badge = canvas._resolve_node_badge(button)
    assert badge is not None
    assert badge["text"] == "FORKED"


def bench_node_resolves_bench_badge():
    canvas, model, _selection = make_canvas()
    panel = model.create_node("panel", {"layout_mode": "free", "x": 20, "y": 20, "width": 180, "height": 120})
    panel.metadata = {
        "bench_session_id": "bench_panel_1",
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter", "fork_destination": "bench"},
    }
    badge = canvas._resolve_node_badge(panel)
    assert badge is not None
    assert badge["text"] == "BENCH"


def active_bench_session_filters_other_bench_nodes():
    canvas, model, _selection = make_canvas()
    workspace = model.create_node(
        "panel",
        {"title": model.BENCH_WORKSPACE_TITLE, "layout_mode": "free", "x": 920, "y": 72, "width": 420, "height": 680},
    )
    first = model.create_node("panel", {"layout_mode": "free", "x": 40, "y": 40, "width": 120, "height": 90})
    second = model.create_node("panel", {"layout_mode": "free", "x": 200, "y": 40, "width": 120, "height": 90})
    first.metadata = {
        "bench_session_id": "bench_first",
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter", "fork_destination": "bench"},
    }
    second.metadata = {
        "bench_session_id": "bench_second",
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter", "fork_destination": "bench"},
    }
    model.add_node(model.root_id, workspace)
    model.add_node(workspace.id, first)
    model.add_node(workspace.id, second)
    model.set_active_bench_session("bench_first")

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    assert first.id in canvas.screen_rects
    assert second.id not in canvas.screen_rects


def protected_source_click_sets_status_reason():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node(
        "button",
        {"layout_mode": "free", "x": 120, "y": 120, "width": 200, "height": 96, "text": "Save"},
    )
    button.metadata = _source_metadata()
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, canvas.screen_rects[button.id].center()))
    assert selection.get_selection() == button.id
    assert "Blocked: Source-backed or adapter-backed node requires fork/bench before editing" in canvas.get_status_text()


def protected_geometry_overlay_sets_status_reason():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node(
        "button",
        {"layout_mode": "free", "x": 120, "y": 120, "width": 200, "height": 96, "text": "Save"},
    )
    button.metadata = _source_metadata()
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    selection.set_selection(button.id)
    canvas.geometry_fields["x"].setText("200")
    canvas._apply_geometry_overlay_edits()
    assert "Blocked: Source-backed or adapter-backed node requires fork/bench before editing" in canvas.get_status_text()


def protected_selection_sets_status_guidance():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node(
        "button",
        {"layout_mode": "free", "x": 120, "y": 120, "width": 200, "height": 96, "text": "Save"},
    )
    button.metadata = _source_metadata()
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    assert "Inspect only: use Fork Here or Open In Bench to make an editable copy" in canvas.get_status_text()
    assert "WORKING: source truth" in canvas.get_status_text()


def forked_selection_sets_working_copy_guidance():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node(
        "button",
        {"layout_mode": "free", "x": 120, "y": 120, "width": 200, "height": 96, "text": "Save"},
    )
    button.metadata = {
        "origin_node_id": "source_button",
        "trust": {"trust_level": "partial", "representation_origin": "manual", "warnings": []},
        "provenance": {"representation_origin": "manual"},
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    status = canvas.get_status_text()
    assert "WORKING: forked copy" in status
    assert "Forked working copy: edits apply to the copy, not source truth" in status


def bench_selection_sets_working_copy_guidance():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    panel = model.create_node(
        "panel",
        {"layout_mode": "free", "x": 120, "y": 120, "width": 200, "height": 96, "title": "Bench"},
    )
    panel.metadata = {
        "bench_session_id": "bench_1",
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter", "fork_destination": "bench"},
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)

    selection.set_selection(panel.id)
    status = canvas.get_status_text()
    assert "WORKING: bench copy" in status
    assert "Bench copy: edits are isolated to the active bench session" in status


def run_all_tests():
    tests = [
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
        wheel_pan_updates_camera,
        button_resolves_to_button_draw_path,
        toolbar_resolves_to_toolbar_draw_path,
        sidebar_resolves_to_sidebar_draw_path,
        panel_resolves_to_panel_draw_path,
        container_resolves_to_container_draw_path,
        tool_window_role_resolves_to_tool_window_draw_path,
        dialog_role_resolves_to_dialog_draw_path,
        unsupported_role_type_uses_generic_fallback_draw_path,
        unsupported_ui_role_falls_back_to_supported_node_type_draw_path,
        selection_does_not_change_render_dispatch,
        source_node_resolves_source_badge,
        forked_node_resolves_fork_badge,
        bench_node_resolves_bench_badge,
        active_bench_session_filters_other_bench_nodes,
        protected_source_click_sets_status_reason,
        protected_geometry_overlay_sets_status_reason,
        protected_selection_sets_status_guidance,
        forked_selection_sets_working_copy_guidance,
        bench_selection_sets_working_copy_guidance,
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
