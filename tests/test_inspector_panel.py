import json
import sys
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication, QLabel, QLineEdit, QPushButton, QTabWidget


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


def inspector_has_truth_and_edit_tabs():
    panel, _model, _selection, _registry = make_panel()
    tabs = panel.findChild(QTabWidget, "inspector_tabs")
    assert tabs is not None
    assert tabs.tabText(0) == "Truth"
    assert tabs.tabText(1) == "Edit"


def source_selection_defaults_to_truth_tab():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save"})
    button.metadata = {
        "trust": {
            "trust_level": "partial",
            "representation_origin": "adapter",
            "warnings": [],
        },
        "provenance": {
            "representation_origin": "adapter",
        },
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    tabs = panel.findChild(QTabWidget, "inspector_tabs")
    assert tabs is not None
    assert tabs.currentIndex() == 0


def editable_design_selection_defaults_to_edit_tab():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    tabs = panel.findChild(QTabWidget, "inspector_tabs")
    assert tabs is not None
    assert tabs.currentIndex() == 1


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


def unknown_property_remove_is_disabled_when_not_editable():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {"custom_flag": True})
    button.metadata = {
        "trust": {
            "trust_level": "partial",
            "representation_origin": "adapter",
            "warnings": [],
        },
        "provenance": {
            "representation_origin": "adapter",
        },
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    remove_button = panel.findChild(QPushButton, "unknown_remove_custom_flag")
    assert remove_button is not None
    assert not remove_button.isEnabled()


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


def missing_schema_shows_editability_reason_and_disables_editor():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    custom = Node(id="custom_1", type="custom", properties={"foo": "bar"}, parent_id=document.id)
    custom.metadata = {
        "trust": {
            "trust_level": "partial",
            "representation_origin": "adapter",
            "warnings": [],
        },
        "provenance": {
            "representation_origin": "adapter",
        },
    }
    model.add_node(document.id, custom)

    selection.set_selection(custom.id)
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "Editing disabled: Source-backed or adapter-backed node requires fork/bench before editing" in labels
    editor = panel.findChild(QLineEdit, "field_editor_foo")
    assert editor is not None
    assert not editor.isEnabled()


def inspector_displays_trust_fields():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    model.scene_metadata = {
        "representation_origin": "adapter",
        "source_provider": "bluebench",
        "source_framework": "pyside6",
        "packet_trust_level": "partial",
    }
    button = model.create_node("button", {"text": "Save"})
    button.metadata = {
        "source": {
            "file": "ui/main_window.py",
            "symbol": "save_button",
            "line_start": 42,
            "line_end": 42,
            "source_id": "src_button_1",
        },
        "trust": {
            "trust_level": "partial",
            "representation_origin": "adapter",
            "warnings": ["text inferred"],
        },
        "provenance": {
            "representation_origin": "adapter",
            "source_framework": "pyside6",
            "source_provider": "bluebench",
            "packet_trust_level": "partial",
            "source_provider": "bluebench",
            "packet_warnings": ["packet partial"],
        },
        "relationships": {
            "communicates_to": ["dialog_1"],
            "depends_on": [],
            "updated_by": ["state_1"],
            "triggered_by": [],
        },
        "raw": {
            "provider_type": "button",
            "provider_data": {},
            "unresolved_fields": ["ui_role"],
        },
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "Truth" in labels
    assert "resolved_mode: source" in labels
    assert "editability: forkable" in labels
    assert "trust_level: partial" in labels
    assert "representation_origin: adapter" in labels
    assert "source_provider: bluebench" in labels
    assert "source_framework: pyside6" in labels
    assert "packet_trust_level: partial" in labels
    assert "source.file: ui/main_window.py" in labels
    assert "source.symbol: save_button" in labels
    assert "line_range: 42" in labels
    assert "Snapshot" in labels
    assert "snapshot.root_type: button" in labels
    assert "snapshot.child_count: 0" in labels
    assert "snapshot.node_count: 1" in labels
    assert "snapshot.children: -" in labels
    assert "Relationships" in labels
    assert "communicates_to: dialog_1" in labels
    assert "updated_by: state_1" in labels
    assert "Unresolved Fields" in labels
    assert "ui_role" in labels
    assert "Warnings" in labels
    assert "text inferred" in labels
    assert "edit_reason: Source-backed or adapter-backed node requires fork/bench before editing" in labels
    assert "Scene Truth" in labels
    assert "scene_mode: source" in labels
    assert "scene_origin: adapter" in labels
    assert "scene_source_provider: bluebench" in labels
    assert "scene_source_framework: pyside6" in labels
    assert "scene_packet_trust_level: partial" in labels


def inspector_snapshot_uses_serialize_subtree_contract():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    panel_node = model.create_node("panel", {"title": "Settings"})
    first = model.create_node("button", {"text": "Save"})
    second = model.create_node("text", {"text": "Status"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel_node)
    model.add_node(panel_node.id, first)
    model.add_node(panel_node.id, second)

    selection.set_selection(panel_node.id)
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "snapshot.root_type: panel" in labels
    assert "snapshot.child_count: 2" in labels
    assert "snapshot.node_count: 3" in labels
    assert "snapshot.children: button, text" in labels


def packet_protected_geometry_fields_are_disabled():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {"layout_mode": "free", "x": 12, "y": 24, "width": 80, "height": 32})
    button.metadata = {
        "source": {
            "file": "ui/main_window.py",
            "symbol": "save_button",
            "line_start": 42,
            "line_end": 42,
            "source_id": "src_button_1",
        },
        "trust": {
            "trust_level": "partial",
            "representation_origin": "adapter",
            "warnings": [],
        },
        "provenance": {
            "representation_origin": "adapter",
            "source_provider": "bluebench",
            "packet_warnings": [],
        },
        "relationships": {
            "communicates_to": [],
            "depends_on": [],
            "updated_by": [],
            "triggered_by": [],
        },
        "raw": {
            "provider_type": "button",
            "provider_data": {},
            "unresolved_fields": [],
        },
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    x_editor = panel.findChild(QLineEdit, "field_editor_x")
    width_editor = panel.findChild(QLineEdit, "field_editor_width")
    assert x_editor is not None
    assert width_editor is not None
    assert not x_editor.isEnabled()
    assert not width_editor.isEnabled()


def packet_protected_content_fields_are_disabled():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save"})
    button.metadata = {
        "source": {
            "file": "ui/main_window.py",
            "symbol": "save_button",
            "line_start": 42,
            "line_end": 42,
            "source_id": "src_button_1",
        },
        "trust": {
            "trust_level": "partial",
            "representation_origin": "adapter",
            "warnings": [],
        },
        "provenance": {
            "representation_origin": "adapter",
            "source_provider": "bluebench",
            "packet_warnings": [],
        },
        "relationships": {
            "communicates_to": [],
            "depends_on": [],
            "updated_by": [],
            "triggered_by": [],
        },
        "raw": {
            "provider_type": "button",
            "provider_data": {},
            "unresolved_fields": [],
        },
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    text_editor = panel.findChild(QLineEdit, "field_editor_text")
    title_editor = panel.findChild(QLineEdit, "field_editor_title")
    assert text_editor is not None
    assert title_editor is not None
    assert not text_editor.isEnabled()
    assert not title_editor.isEnabled()


def forkable_node_can_fork_to_design():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save"})
    button.metadata = {
        "source": {
            "file": "ui/main_window.py",
            "symbol": "save_button",
            "line_start": 42,
            "line_end": 42,
            "source_id": "src_button_1",
        },
        "trust": {
            "trust_level": "partial",
            "representation_origin": "adapter",
            "warnings": [],
        },
        "provenance": {
            "representation_origin": "adapter",
            "source_provider": "bluebench",
            "packet_warnings": [],
        },
        "relationships": {
            "communicates_to": [],
            "depends_on": [],
            "updated_by": [],
            "triggered_by": [],
        },
        "raw": {
            "provider_type": "button",
            "provider_data": {},
            "unresolved_fields": [],
        },
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    fork_button = panel.findChild(QPushButton, "truth_fork_to_design")
    assert fork_button is not None
    fork_button.clicked.emit()

    forked_id = selection.get_selection()
    assert forked_id is not None
    assert forked_id != button.id
    forked = model.get_node(forked_id)
    assert forked is not None
    assert forked.metadata["origin_node_id"] == button.id
    assert forked.metadata["trust"]["representation_origin"] == "manual"
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "fork_destination: here" in labels


def forkable_node_can_open_in_bench():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save"})
    button.metadata = {
        "source": {
            "file": "ui/main_window.py",
            "symbol": "save_button",
            "line_start": 42,
            "line_end": 42,
            "source_id": "src_button_1",
        },
        "trust": {
            "trust_level": "partial",
            "representation_origin": "adapter",
            "warnings": [],
        },
        "provenance": {
            "representation_origin": "adapter",
            "source_provider": "bluebench",
            "packet_warnings": [],
        },
        "relationships": {
            "communicates_to": [],
            "depends_on": [],
            "updated_by": [],
            "triggered_by": [],
        },
        "raw": {
            "provider_type": "button",
            "provider_data": {},
            "unresolved_fields": [],
        },
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    bench_button = panel.findChild(QPushButton, "truth_open_in_bench")
    assert bench_button is not None
    bench_button.clicked.emit()

    bench_id = selection.get_selection()
    assert bench_id is not None
    assert bench_id != button.id
    bench_node = model.get_node(bench_id)
    assert bench_node is not None
    assert bench_node.metadata["origin_node_id"] == button.id
    assert bench_node.metadata["bench_session_id"] == f"bench_{button.id}"
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "resolved_mode: bench" in labels
    assert "editability: editable" in labels
    assert f"bench_session_id: bench_{button.id}" in labels
    assert "fork_destination: bench" in labels
    assert f"scene_active_bench_session_id: bench_{button.id}" in labels


def bench_node_can_focus_and_clear_bench_session():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    bench_node = model.create_node("panel", {"layout_mode": "free", "x": 40, "y": 40, "width": 180, "height": 120})
    bench_node.metadata = {
        "origin_node_id": "panel_1",
        "bench_session_id": "bench_panel_1",
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter", "fork_destination": "bench"},
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, bench_node)

    selection.set_selection(bench_node.id)
    focus_button = panel.findChild(QPushButton, "truth_focus_bench_session")
    clear_button = panel.findChild(QPushButton, "truth_clear_bench_focus")
    assert focus_button is not None
    assert clear_button is not None

    focus_button.clicked.emit()
    assert model.get_active_bench_session_id() == "bench_panel_1"
    clear_button.clicked.emit()
    assert model.get_active_bench_session_id() is None


def scene_truth_lists_and_switches_bench_sessions():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    first = model.create_node("panel", {"layout_mode": "free", "x": 20, "y": 20, "width": 120, "height": 90})
    second = model.create_node("panel", {"layout_mode": "free", "x": 180, "y": 20, "width": 120, "height": 90})
    for node, session_id in ((first, "bench_first"), (second, "bench_second")):
        node.metadata = {
            "origin_node_id": f"origin_{session_id}",
            "bench_session_id": session_id,
            "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
            "provenance": {"representation_origin": "adapter", "fork_destination": "bench"},
        }
    model.add_node(model.root_id, document)
    model.add_node(document.id, first)
    model.add_node(document.id, second)
    model.set_active_bench_session("bench_first")

    selection.set_selection(first.id)
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "Bench Sessions" in labels
    assert "bench_first" in labels
    assert "bench_second" in labels

    buttons = {button.objectName(): button for button in panel.findChildren(QPushButton)}
    assert buttons["bench_session_focus_0"].text() == "Active"
    assert buttons["bench_session_focus_1"].text() == "Focus"
    buttons["bench_session_focus_1"].clicked.emit()
    assert model.get_active_bench_session_id() == "bench_second"
    buttons = {button.objectName(): button for button in panel.findChildren(QPushButton)}
    assert buttons["bench_session_focus_1"].text() == "Active"
    assert buttons["bench_session_clear_focus"].isEnabled()
    buttons["bench_session_clear_focus"].clicked.emit()
    assert model.get_active_bench_session_id() is None


def scene_truth_can_close_bench_session():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    source_node = model.create_node("panel", {"layout_mode": "free", "x": 20, "y": 20, "width": 120, "height": 90})
    source_node.metadata = {
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter"},
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, source_node)

    bench_id = model.open_subtree_in_bench(source_node.id)
    bench_node = model.get_node(bench_id)
    bench_session_id = bench_node.metadata["bench_session_id"]

    selection.set_selection(bench_node.id)
    buttons = {button.objectName(): button for button in panel.findChildren(QPushButton)}
    close_button = next(
        button for name, button in buttons.items()
        if name.startswith("bench_session_close_")
    )
    close_button.clicked.emit()
    APP.processEvents()

    assert model.get_node(bench_id) is None
    assert model.get_active_bench_session_id() is None
    assert selection.get_selection() is None


def recently_closed_bench_session_can_reopen():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    source_node = model.create_node("panel", {"layout_mode": "free", "x": 20, "y": 20, "width": 120, "height": 90})
    source_node.metadata = {
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter"},
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, source_node)

    bench_id = model.open_subtree_in_bench(source_node.id)
    bench_session_id = model.get_node(bench_id).metadata["bench_session_id"]
    model.close_bench_session(bench_session_id)

    selection.set_selection(source_node.id)
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "Recently Closed Bench Sessions" in labels
    assert bench_session_id in labels
    reopen_button = next(
        button for button in panel.findChildren(QPushButton)
        if button.objectName().startswith("closed_bench_session_reopen_")
    )
    reopen_button.clicked.emit()

    reopened_id = selection.get_selection()
    reopened = model.get_node(reopened_id)
    assert reopened is not None
    assert reopened.metadata["bench_session_id"] == bench_session_id
    assert model.get_active_bench_session_id() == bench_session_id
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "Recently Closed Bench Sessions" not in labels


def inspector_refreshes_from_model_notification():
    panel, model, selection, _registry = make_panel()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Old"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    selection.set_selection(button.id)
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "source.file: ui/main_window.py" not in labels

    button.metadata = {
        "source": {
            "file": "ui/main_window.py",
            "symbol": "save_button",
            "line_start": 10,
            "line_end": 12,
            "source_id": "src_button_1",
        },
        "trust": {
            "trust_level": "partial",
            "representation_origin": "adapter",
            "warnings": [],
        },
        "provenance": {
            "representation_origin": "adapter",
            "source_provider": "bluebench",
            "source_framework": "pyside6",
            "packet_trust_level": "partial",
            "packet_warnings": [],
        },
        "relationships": {
            "communicates_to": [],
            "depends_on": [],
            "updated_by": [],
            "triggered_by": [],
        },
        "raw": {
            "provider_type": "button",
            "provider_data": {},
            "unresolved_fields": [],
        },
    }
    model.notify_subscribers()

    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "source.file: ui/main_window.py" in labels


def source_scene_shows_scene_level_fork_actions():
    panel, model, selection, _registry = make_panel()
    model.scene_metadata = {
        "representation_origin": "adapter",
        "source_provider": "scanner_qt_runtime_probe",
        "packet_trust_level": "partial",
    }
    document = model.create_node("document", {"layout_mode": "free", "x": 10, "y": 10, "width": 200, "height": 120})
    document.metadata = {
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter"},
    }
    model.add_node(model.root_id, document)

    selection.set_selection(document.id)
    buttons = {button.objectName(): button for button in panel.findChildren(QPushButton)}
    assert "scene_truth_fork_scene_here" in buttons
    assert "scene_truth_open_scene_in_bench" in buttons


def scene_level_bench_action_selects_bench_clone():
    panel, model, selection, _registry = make_panel()
    model.scene_metadata = {
        "representation_origin": "adapter",
        "source_provider": "scanner_qt_runtime_probe",
        "packet_trust_level": "partial",
    }
    document = model.create_node("document", {"layout_mode": "free", "x": 10, "y": 10, "width": 200, "height": 120})
    document.metadata = {
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter"},
    }
    model.add_node(model.root_id, document)

    selection.set_selection(document.id)
    bench_button = panel.findChild(QPushButton, "scene_truth_open_scene_in_bench")
    assert bench_button is not None
    bench_button.clicked.emit()

    selected_id = selection.get_selection()
    selected = model.get_node(selected_id)
    assert selected is not None
    assert selected.parent_id == model.ensure_bench_workspace().id
    assert selected.metadata["bench_session_id"] == model.get_active_bench_session_id()


def run_all_tests():
    tests = [
        no_selection_shows_placeholder,
        inspector_has_truth_and_edit_tabs,
        source_selection_defaults_to_truth_tab,
        editable_design_selection_defaults_to_edit_tab,
        selection_renders_fields,
        property_commit_updates_node,
        invalid_number_does_not_commit,
        unknown_properties_section,
        unknown_property_remove_is_disabled_when_not_editable,
        reset_to_default,
        missing_schema_fallback,
        missing_schema_shows_editability_reason_and_disables_editor,
        inspector_displays_trust_fields,
        inspector_snapshot_uses_serialize_subtree_contract,
        packet_protected_geometry_fields_are_disabled,
        packet_protected_content_fields_are_disabled,
        forkable_node_can_fork_to_design,
        forkable_node_can_open_in_bench,
        bench_node_can_focus_and_clear_bench_session,
        scene_truth_lists_and_switches_bench_sessions,
        scene_truth_can_close_bench_session,
        recently_closed_bench_session_can_reopen,
        inspector_refreshes_from_model_notification,
        source_scene_shows_scene_level_fork_actions,
        scene_level_bench_action_selects_bench_clone,
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
