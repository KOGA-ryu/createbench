import sys
from pathlib import Path

from PySide6.QtCore import QPointF, Qt
from PySide6.QtGui import QKeyEvent
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


def add_child_creates_node():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    selection.set_selection(document.id)

    canvas.add_child_to_selected()

    children = model.get_children(document.id)
    assert len(children) == 1
    assert children[0].type == "panel"


def add_child_sets_selection():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    selection.set_selection(document.id)

    canvas.add_child_to_selected()

    child = model.get_children(document.id)[0]
    assert selection.get_selection() == child.id


def delete_selected_removes_node():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    selection.set_selection(panel.id)

    canvas.delete_selected()

    assert model.get_node(panel.id) is None
    assert model.get_children(document.id) == []


def delete_selects_parent():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    selection.set_selection(panel.id)

    canvas.delete_selected()

    assert selection.get_selection() == document.id


def delete_root_blocked():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    selection.set_selection(model.root_id)

    canvas.delete_selected()

    assert model.get_node(model.root_id) is not None
    assert model.get_node(document.id) is not None
    assert selection.get_selection() == model.root_id


def delete_with_no_selection_safe():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    selection.clear_selection()

    canvas.delete_selected()

    assert model.get_node(panel.id) is not None
    assert selection.get_selection() is None


def keyboard_delete_triggers():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    selection.set_selection(panel.id)
    canvas.show()
    canvas.setFocus()
    APP.processEvents()

    event = QKeyEvent(QKeyEvent.Type.KeyPress, Qt.Key.Key_Delete, Qt.KeyboardModifier.NoModifier)
    canvas.keyPressEvent(event)

    assert model.get_node(panel.id) is None
    assert selection.get_selection() == document.id


def run_all_tests():
    tests = [
        add_child_creates_node,
        add_child_sets_selection,
        delete_selected_removes_node,
        delete_selects_parent,
        delete_root_blocked,
        delete_with_no_selection_safe,
        keyboard_delete_triggers,
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
