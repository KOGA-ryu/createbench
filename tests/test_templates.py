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


def apply_basic_template_to_empty_canvas():
    canvas, model, _selection = make_canvas()
    templates = load_templates()
    canvas.apply_template(templates["app_shell"])

    root_children = model.get_children(model.root_id)
    assert len(root_children) == 1
    document = root_children[0]
    assert document.type == "document"
    assert [child.type for child in model.get_children(document.id)] == ["toolbar", "horizontal"]


def replace_root_with_template():
    canvas, model, selection = make_canvas()
    templates = load_templates()
    old_document = model.create_node("document", {})
    old_panel = model.create_node("panel", {})
    model.add_node(model.root_id, old_document)
    model.add_node(old_document.id, old_panel)
    selection.set_selection(old_panel.id)
    canvas.apply_template(templates["dashboard"], replace_root=True)

    root_children = model.get_children(model.root_id)
    assert len(root_children) == 1
    assert root_children[0].type == "document"
    assert model.get_node(old_document.id) is None
    assert model.get_node(old_panel.id) is None


def apply_template_to_selected_parent():
    canvas, model, selection = make_canvas()
    templates = load_templates()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    selection.set_selection(panel.id)
    canvas.apply_template(templates["form_layout"])

    children = model.get_children(panel.id)
    assert len(children) == 1
    assert children[0].type == "vertical"


def document_template_flattens_when_inserting_into_nonempty_project():
    canvas, model, selection = make_canvas()
    templates = load_templates()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    selection.set_selection(document.id)
    canvas.apply_template(templates["app_shell"])

    root_children = model.get_children(model.root_id)
    assert len(root_children) == 1
    assert root_children[0].id == document.id
    assert [child.type for child in model.get_children(document.id)[:2]] == ["toolbar", "horizontal"]


def selection_after_template_application():
    canvas, model, selection = make_canvas()
    templates = load_templates()
    canvas.apply_template(templates["app_shell"])

    first = model.get_children(model.root_id)[0]
    assert selection.get_selection() == first.id


def template_properties_seed_node():
    canvas, model, _selection = make_canvas()
    templates = load_templates()
    canvas.apply_template(templates["app_shell"])

    document = model.get_children(model.root_id)[0]
    toolbar, horizontal = model.get_children(document.id)
    sidebar, main = model.get_children(horizontal.id)
    assert toolbar.properties["title"] == "Toolbar"
    assert sidebar.properties["title"] == "Sidebar"
    assert main.properties["title"] == "Main"


def preserve_template_order():
    canvas, model, _selection = make_canvas()
    templates = load_templates()
    canvas.apply_template(templates["dashboard"])

    document = model.get_children(model.root_id)[0]
    assert [child.type for child in model.get_children(document.id)] == ["toolbar", "horizontal"]
    horizontal = model.get_children(document.id)[1]
    assert [child.type for child in model.get_children(horizontal.id)] == ["sidebar", "vertical"]


def replace_root_clears_previous_content():
    canvas, model, _selection = make_canvas()
    templates = load_templates()
    old_document = model.create_node("document", {})
    old_button = model.create_node("button", {})
    model.add_node(model.root_id, old_document)
    model.add_node(old_document.id, old_button)

    canvas.apply_template(templates["app_shell"], replace_root=True)

    assert model.get_node(old_document.id) is None
    assert model.get_node(old_button.id) is None


def apply_template_without_selection_falls_back_to_root():
    canvas, model, selection = make_canvas()
    templates = load_templates()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    selection.clear_selection()
    canvas.apply_template(templates["app_shell"])

    root_children = model.get_children(model.root_id)
    assert [child.type for child in root_children] == ["document", "toolbar", "horizontal"]


def run_all_tests():
    tests = [
        apply_basic_template_to_empty_canvas,
        replace_root_with_template,
        apply_template_to_selected_parent,
        document_template_flattens_when_inserting_into_nonempty_project,
        selection_after_template_application,
        template_properties_seed_node,
        preserve_template_order,
        replace_root_clears_previous_content,
        apply_template_without_selection_falls_back_to_root,
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
