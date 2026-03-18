import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QCheckBox, QComboBox, QLineEdit, QPushButton


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from canvas.canvas_widget import CanvasWidget
from checklist.checklist_engine import ChecklistEngine
from core.layout_model import LayoutModel
from export.dsl_builder import DSLBuilder
from forms.component_form_builder import ComponentFormBuilder
from inspector.property_registry import PropertyRegistry
from state.selection_state import SelectionState


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"
COMPONENT_TEMPLATES = PROJECT_ROOT / "component_templates"
APP = QApplication.instance() or QApplication([])


def make_builder():
    return ComponentFormBuilder(COMPONENT_TEMPLATES)


def make_canvas():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    model = LayoutModel(registry)
    selection = SelectionState(model)
    canvas = CanvasWidget(model, selection)
    canvas.resize(800, 600)
    return canvas, model, selection, registry


def component_templates_load():
    builder = make_builder()
    components = builder.list_components()
    assert {"sidebar", "main", "toolbar", "panel", "button"} == set(components)


def build_sidebar_form():
    builder = make_builder()
    form = builder.build_form("sidebar", lambda payload: payload)
    assert form.findChild(QLineEdit, "component_trait_input_sidebar_title") is not None
    assert form.findChild(QLineEdit, "component_trait_input_sidebar_width") is not None
    assert form.findChild(QComboBox, "component_trait_input_sidebar_layout_mode") is not None
    assert form.findChild(QCheckBox, "component_trait_input_sidebar_locked") is not None


def submit_form_creates_node():
    canvas, model, selection, _registry = make_canvas()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    selection.set_selection(document.id)
    builder = make_builder()
    created = []

    def on_submit(payload):
        created.append(canvas.create_component_node(payload["type"], payload["properties"]))

    form = builder.build_form("sidebar", on_submit)
    form.findChild(QLineEdit, "component_trait_input_sidebar_title").setText("Nav")
    form.findChild(QLineEdit, "component_trait_input_sidebar_width").setText("280")
    form.findChild(QComboBox, "component_trait_input_sidebar_layout_mode").setCurrentText("free")
    form.findChild(QCheckBox, "component_trait_input_sidebar_locked").setChecked(True)
    form.findChild(QLineEdit, "component_trait_input_sidebar_description").setText("Navigation")
    form.findChild(QPushButton, "component_form_submit").click()

    node = created[0]
    assert node.type == "sidebar"
    assert node.properties["title"] == "Nav"
    assert node.properties["width"] == 280
    assert node.properties["layout_mode"] == "free"
    assert node.properties["locked"] is True
    assert node.properties["description"] == "Navigation"


def custom_trait_persists():
    canvas, model, selection, _registry = make_canvas()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    selection.set_selection(document.id)
    builder = make_builder()
    created = []

    def on_submit(payload):
        created.append(canvas.create_component_node(payload["type"], payload["properties"]))

    form = builder.build_form("panel", on_submit)
    form.findChild(QLineEdit, "component_custom_trait_name").setText("custom_trait")
    form.findChild(QLineEdit, "component_custom_trait_value").setText("hello")
    form.findChild(QPushButton, "component_custom_trait_add").click()
    form.findChild(QPushButton, "component_form_submit").click()

    node = created[0]
    assert node.properties["custom_trait"] == "hello"


def selected_parent_receives_new_component():
    canvas, model, selection, _registry = make_canvas()
    document = model.create_node("document", {})
    parent = model.create_node("panel", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, parent)
    selection.set_selection(parent.id)
    builder = make_builder()

    form = builder.build_form(
        "button",
        lambda payload: canvas.create_component_node(payload["type"], payload["properties"]),
    )
    form.findChild(QPushButton, "component_form_submit").click()

    children = model.get_children(parent.id)
    assert len(children) == 1
    assert children[0].type == "button"


def fallback_to_root_when_no_selection():
    canvas, model, selection, _registry = make_canvas()
    selection.clear_selection()
    builder = make_builder()

    form = builder.build_form(
        "panel",
        lambda payload: canvas.create_component_node(payload["type"], payload["properties"]),
    )
    form.findChild(QPushButton, "component_form_submit").click()

    root_children = model.get_children(model.root_id)
    assert len(root_children) == 1
    assert root_children[0].type == "panel"


def new_node_selected_after_create():
    canvas, model, selection, _registry = make_canvas()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    selection.set_selection(document.id)
    builder = make_builder()

    form = builder.build_form(
        "panel",
        lambda payload: canvas.create_component_node(payload["type"], payload["properties"]),
    )
    form.findChild(QPushButton, "component_form_submit").click()

    child = model.get_children(document.id)[0]
    assert selection.get_selection() == child.id


def preferred_size_applied():
    canvas, model, selection, _registry = make_canvas()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    selection.set_selection(document.id)
    builder = make_builder()
    created = []

    def on_submit(payload):
        created.append(canvas.create_component_node(payload["type"], payload["properties"]))

    form = builder.build_form("panel", on_submit)
    form.findChild(QPushButton, "component_form_submit").click()

    node = created[0]
    assert node.properties["width"] == 320
    assert node.properties["height"] == 240


def export_preserves_custom_traits():
    canvas, model, selection, registry = make_canvas()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    selection.set_selection(document.id)
    builder = make_builder()

    form = builder.build_form(
        "button",
        lambda payload: canvas.create_component_node(payload["type"], payload["properties"]),
    )
    form.findChild(QLineEdit, "component_custom_trait_name").setText("analytics_tag")
    form.findChild(QLineEdit, "component_custom_trait_value").setText("save-cta")
    form.findChild(QPushButton, "component_custom_trait_add").click()
    form.findChild(QPushButton, "component_form_submit").click()

    checklist = ChecklistEngine(model, registry)
    dsl_builder = DSLBuilder(model, registry, checklist)
    dsl = dsl_builder.build_dsl()
    exported_json = dsl_builder.build_json()

    assert "analytics_tag = \"save-cta\"" in dsl
    button_json = exported_json["children"][0]
    assert button_json["properties"]["unknown"]["analytics_tag"] == "save-cta"


def run_all_tests():
    tests = [
        component_templates_load,
        build_sidebar_form,
        submit_form_creates_node,
        custom_trait_persists,
        selected_parent_receives_new_component,
        fallback_to_root_when_no_selection,
        new_node_selected_after_create,
        preferred_size_applied,
        export_preserves_custom_traits,
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
