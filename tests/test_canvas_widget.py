import sys
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
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


def render_creates_node_rects():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {})
    button = model.create_node("button", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    assert document.id in canvas.node_rects
    assert button.id in canvas.node_rects


def click_selects_node():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {})
    button = model.create_node("button", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    rect = canvas.node_rects[button.id]
    point = rect.center()
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(point),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(event)
    assert selection.get_selection() == button.id


def layout_respects_children_count():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    top = model.create_node("button", {"layout_mode": "auto"})
    middle = model.create_node("text", {"layout_mode": "auto"})
    bottom = model.create_node("input", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, top)
    model.add_node(document.id, middle)
    model.add_node(document.id, bottom)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    top_rect = canvas.node_rects[top.id]
    middle_rect = canvas.node_rects[middle.id]
    bottom_rect = canvas.node_rects[bottom.id]
    assert top_rect.y() < middle_rect.y() < bottom_rect.y()


def selection_updates_on_click():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)

    updates = []
    selection.subscribe(updates.append)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    rect = canvas.node_rects[panel.id]
    point = rect.center()
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(point),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(event)
    assert updates[-1] == panel.id


def click_selects_topmost_overlapping_node():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    lower = model.create_node(
        "panel",
        {"layout_mode": "free", "x": 40, "y": 40, "width": 200, "height": 160},
    )
    upper = model.create_node(
        "button",
        {"layout_mode": "free", "x": 80, "y": 80, "width": 120, "height": 80},
    )
    model.add_node(model.root_id, document)
    model.add_node(document.id, lower)
    model.add_node(document.id, upper)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    point = canvas.node_rects[upper.id].center()
    event = QMouseEvent(
        QMouseEvent.Type.MouseButtonPress,
        QPointF(point),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    canvas.mousePressEvent(event)
    assert selection.get_selection() == upper.id


def run_all_tests():
    tests = [
        render_creates_node_rects,
        click_selects_node,
        layout_respects_children_count,
        selection_updates_on_click,
        click_selects_topmost_overlapping_node,
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
