import json
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from canvas.canvas_widget import CanvasWidget
from core.layout_model import LayoutModel
from inspector.property_registry import PropertyRegistry
from state.selection_state import SelectionState


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"
TEMPLATES_PATH = PROJECT_ROOT / "templates" / "templates.json"
APP = QApplication.instance() or QApplication([])


def load_templates():
    return json.loads(TEMPLATES_PATH.read_text(encoding="utf-8"))


def make_canvas():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    model = LayoutModel(registry)
    selection = SelectionState(model)
    canvas = CanvasWidget(model, selection)
    return canvas, model, selection


def apply_basic_template():
    canvas, model, _selection = make_canvas()
    templates = load_templates()
    canvas.apply_template(templates["basic_layout"], model.root_id)

    root_children = model.get_children(model.root_id)
    assert len(root_children) == 1
    container = root_children[0]
    assert container.type == "container"
    children = model.get_children(container.id)
    assert [child.type for child in children] == ["sidebar", "main"]


def nested_template_creation():
    canvas, model, _selection = make_canvas()
    templates = load_templates()
    canvas.apply_template(templates["vertical_stack"], model.root_id)

    root_children = model.get_children(model.root_id)
    vertical = root_children[0]
    children = model.get_children(vertical.id)
    assert [child.type for child in children] == ["text", "button"]


def selection_after_template():
    canvas, model, selection = make_canvas()
    templates = load_templates()
    canvas.apply_template(templates["basic_layout"], model.root_id)

    first = model.get_children(model.root_id)[0]
    assert selection.get_selection() == first.id


def run_all_tests():
    tests = [
        apply_basic_template,
        nested_template_creation,
        selection_after_template,
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
