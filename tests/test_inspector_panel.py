import json
import sys
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.layout_model import LayoutModel
from core.node import Node
from inspector.inspector_panel import InspectorPanel
from inspector.property_registry import PropertyRegistry
from state.selection_state import SelectionState


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"
APP = QApplication.instance() or QApplication([])


def write_schema(directory: Path, name: str, schema: dict) -> None:
    (directory / name).write_text(json.dumps(schema, indent=2), encoding="utf-8")


def make_panel(user_dir: Path | None = None):
    registry = PropertyRegistry(str(CORE_SCHEMAS), str(user_dir) if user_dir else None)
    model = LayoutModel(registry)
    selection = SelectionState(model)
    panel = InspectorPanel(model, selection, registry)
    return panel, model, selection, registry


def no_selection_shows_placeholder():
    panel, _model, _selection, _registry = make_panel()
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "No selection" in labels


def selection_renders_fields():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "Content" in labels
    assert any(text.startswith("text *") for text in labels)
    assert any("(default)" in text for text in labels)


def property_commit_updates_node():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    editor = panel.findChild(QLineEdit, "field_editor_text")
    editor.setText("Apply")
    editor.editingFinished.emit()
    assert button.properties["text"] == "Apply"


def invalid_number_does_not_commit():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    panel_node = model.create_node("panel", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel_node)

    selection.set_selection(panel_node.id)
    editor = panel.findChild(QLineEdit, "field_editor_width")
    original = panel_node.properties["width"]
    editor.setText("abc")
    editor.editingFinished.emit()
    assert panel_node.properties["width"] == original
    assert "border: 1px solid #dc2626;" not in editor.styleSheet()


def unknown_properties_section():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {"custom_flag": True})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "Unknown Properties" in labels


def reset_to_default():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Changed"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    reset = panel.findChild(QPushButton, "field_reset_text")
    reset.clicked.emit()
    assert button.properties["text"] == "Button"


def missing_schema_fallback():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    custom = Node(id="custom_1", type="custom", properties={"foo": "bar"}, parent_id=document.id)
    model.add_node(document.id, custom)

    selection.set_selection(custom.id)
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "No schema found" in labels
    editor = panel.findChild(QLineEdit, "field_editor_foo")
    assert editor is not None


def run_all_tests():
    tests = [
        no_selection_shows_placeholder,
        selection_renders_fields,
        property_commit_updates_node,
        invalid_number_does_not_commit,
        unknown_properties_section,
        reset_to_default,
        missing_schema_fallback,
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
