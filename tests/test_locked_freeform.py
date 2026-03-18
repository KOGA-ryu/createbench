import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication, QCheckBox, QLineEdit


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from canvas.canvas_widget import CanvasWidget
from core.layout_model import LayoutModel
from inspector.inspector_panel import InspectorPanel
from inspector.property_registry import PropertyRegistry
from state.selection_state import SelectionState


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"
APP = QApplication.instance() or QApplication([])


def make_system():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    model = LayoutModel(registry)
    selection = SelectionState(model)
    canvas = CanvasWidget(model, selection)
    canvas.resize(800, 600)
    inspector = InspectorPanel(model, selection, registry)
    return canvas, inspector, model, selection


def _mouse_event(event_type, point):
    return QMouseEvent(
        event_type,
        QPointF(point),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def locked_node_cannot_move():
    canvas, _inspector, model, selection = make_system()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save"})
    button.properties["locked"] = True
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    start = canvas.node_rects[button.id].center()
    moved = QPoint(start.x() + 40, start.y() + 20)
    selection.set_selection(button.id)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))

    assert button.properties["x"] == 0
    assert button.properties["y"] == 0


def locked_node_cannot_resize():
    canvas, _inspector, model, selection = make_system()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save"})
    button.properties["locked"] = True
    button.properties["layout_mode"] = "free"
    button.properties["x"] = 100
    button.properties["y"] = 100
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    selection.set_selection(button.id)
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    original_width = button.properties["width"]
    original_height = button.properties["height"]
    handle = canvas.handle_rects.get((button.id, "bottom_right"))
    assert handle is None
    assert button.properties["width"] == original_width
    assert button.properties["height"] == original_height


def unlocked_node_moves():
    canvas, _inspector, model, _selection = make_system()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save"})
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

    assert button.properties["x"] != 0 or button.properties["y"] != 0


def semantic_fields_persist():
    _canvas, inspector, model, selection = make_system()
    document = model.create_node("document", {})
    button = model.create_node(
        "button",
        {
            "title": "Save CTA",
            "description": "Primary action",
            "behavior": "submit",
            "interactions": "click",
            "text": "Save",
        },
    )
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    APP.processEvents()

    assert button.properties["title"] == "Save CTA"
    assert button.properties["description"] == "Primary action"
    assert button.properties["behavior"] == "submit"
    assert button.properties["interactions"] == "click"
    assert inspector.findChild(QLineEdit, "field_editor_title") is not None


def lock_toggle_behavior():
    _canvas, inspector, model, selection = make_system()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    APP.processEvents()

    lock_checkbox = inspector.findChild(QCheckBox, "field_editor_locked")
    assert lock_checkbox is not None
    lock_checkbox.setChecked(True)
    APP.processEvents()

    x_editor = inspector.findChild(QLineEdit, "field_editor_x")
    title_editor = inspector.findChild(QLineEdit, "field_editor_title")
    assert not x_editor.isEnabled()
    assert title_editor.isEnabled()


def run_all_tests():
    tests = [
        locked_node_cannot_move,
        locked_node_cannot_resize,
        unlocked_node_moves,
        semantic_fields_persist,
        lock_toggle_behavior,
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
