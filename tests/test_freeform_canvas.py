import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from canvas.canvas_widget import CanvasWidget
from core.layout_model import LayoutModel
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


def _mouse_event(event_type, point):
    return QMouseEvent(
        event_type,
        QPointF(point),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def drag_sets_free_mode():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    start = canvas.node_rects[button.id].center()
    moved = QPoint(start.x() + 20, start.y() + 20)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))

    assert button.properties["layout_mode"] == "free"


def position_updates_on_drag():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node(
        "button",
        {"text": "Save", "layout_mode": "free", "x": 120, "y": 120, "width": 200, "height": 96},
    )
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    start = canvas.node_rects[button.id].center()
    moved = QPoint(start.x() + 40, start.y() + 30)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))

    assert button.properties["x"] > 120
    assert button.properties["y"] > 120


def drag_auto_node_snaps_to_grid():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"text": "Save", "layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    start = canvas.node_rects[button.id].center()
    moved = QPoint(start.x() + 21, start.y() + 19)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))

    assert button.properties["layout_mode"] == "free"
    assert button.properties["x"] % 8 == 0
    assert button.properties["y"] % 8 == 0


def resize_updates_dimensions():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"text": "Save"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    selection.set_selection(button.id)
    button.properties["layout_mode"] = "free"
    button.properties["x"] = 100
    button.properties["y"] = 100
    button.properties["width"] = 120
    button.properties["height"] = 60
    original_width = button.properties["width"]
    original_height = button.properties["height"]
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    handle = canvas.handle_rects[(button.id, "bottom_right")].center()
    moved = QPoint(handle.x() + 50, handle.y() + 40)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, handle))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))

    assert button.properties["width"] > original_width
    assert button.properties["height"] > original_height
    assert (button.properties["x"] + button.properties["width"]) % 8 == 0
    assert (button.properties["y"] + button.properties["height"]) % 8 == 0


def auto_mode_ignored_when_free():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"text": "Save"})
    button.properties["layout_mode"] = "free"
    button.properties["x"] = 50
    button.properties["y"] = 70
    button.properties["width"] = 180
    button.properties["height"] = 90
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    rect = canvas.engine_rects[button.id]
    assert rect["x"] == 50
    assert rect["y"] == 70


def multiple_nodes_independent_positions():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    first = model.create_node("button", {"text": "A"})
    second = model.create_node("button", {"text": "B"})
    first.properties["layout_mode"] = "free"
    first.properties["x"] = 40
    first.properties["y"] = 40
    second.properties["layout_mode"] = "free"
    second.properties["x"] = 220
    second.properties["y"] = 180
    model.add_node(model.root_id, document)
    model.add_node(document.id, first)
    model.add_node(document.id, second)
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    first_rect = canvas.node_rects[first.id]
    second_rect = canvas.node_rects[second.id]
    assert first_rect.topLeft() != second_rect.topLeft()


def screen_rects_follow_camera_without_changing_world_rects():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node(
        "button",
        {"layout_mode": "free", "x": 720, "y": 400, "width": 240, "height": 96},
    )
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    engine_rect = canvas.engine_rects[button.id]
    world_rect = canvas.node_rects[button.id]
    display_rect = canvas.screen_rects[button.id]
    assert engine_rect["width"] == 240
    assert display_rect.width() == engine_rect["width"]
    canvas.camera_x = 120
    canvas.camera_y = 60
    canvas.repaint()
    APP.processEvents()
    shifted_display_rect = canvas.screen_rects[button.id]
    assert canvas.node_rects[button.id] == world_rect
    assert shifted_display_rect.x() == display_rect.x() - 120
    assert shifted_display_rect.y() == display_rect.y() - 60


def run_all_tests():
    tests = [
        drag_sets_free_mode,
        position_updates_on_drag,
        drag_auto_node_snaps_to_grid,
        resize_updates_dimensions,
        auto_mode_ignored_when_free,
        multiple_nodes_independent_positions,
        screen_rects_follow_camera_without_changing_world_rects,
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
