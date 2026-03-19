import io
import sys
from contextlib import redirect_stdout
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from checklist.checklist_panel import ChecklistPanel
from state.app_state import AppState
from ui.main_window import MainWindow


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"
APP = QApplication.instance() or QApplication([])


def make_panel():
    state = AppState(str(CORE_SCHEMAS))
    panel = ChecklistPanel(
        state.layout_model, state.checklist_engine, state.selection_state
    )
    return panel, state


def checklist_updates_on_selection():
    panel, state = make_panel()
    document = state.layout_model.create_node("document", {})
    button = state.layout_model.create_node("button", {})
    button.properties.pop("text", None)
    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, button)

    state.selection_state.set_selection(button.id)
    APP.processEvents()

    assert panel.selected_list.count() == 1


def summary_counts_displayed():
    panel, state = make_panel()
    document = state.layout_model.create_node("document", {})
    button = state.layout_model.create_node("button", {})
    button.properties.pop("text", None)
    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, button)

    panel.update_checklist()
    assert "Errors: 1" in panel.summary_label.text()


def selected_node_highlight():
    panel, state = make_panel()
    document = state.layout_model.create_node("document", {})
    button = state.layout_model.create_node("button", {"custom_flag": True})
    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, button)

    state.selection_state.set_selection(button.id)
    panel.update_checklist()
    assert panel.selected_list.count() >= 1
    assert button.id in panel.selected_list.item(0).text()


def severity_tags_colored():
    panel, state = make_panel()
    document = state.layout_model.create_node("document", {})
    button = state.layout_model.create_node("button", {})
    button.properties.pop("text", None)
    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, button)

    panel.update_checklist()
    item = panel.other_list.item(0)
    color = item.foreground().color().name()
    assert color == "#dc2626"


def export_blocked_when_errors():
    state = AppState(str(CORE_SCHEMAS))
    document = state.layout_model.create_node("document", {})
    button = state.layout_model.create_node("button", {})
    button.properties.pop("text", None)
    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, button)

    window = MainWindow(state)
    out = io.StringIO()
    with redirect_stdout(out):
        window.export_button.clicked.emit()
    assert out.getvalue().strip() == "Export blocked: fix errors in checklist"


def export_succeeds_when_valid():
    state = AppState(str(CORE_SCHEMAS))
    document = state.layout_model.create_node("document", {})
    button = state.layout_model.create_node("button", {"text": "Save"})
    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, button)

    window = MainWindow(state)
    out = io.StringIO()
    with redirect_stdout(out):
        window.export_button.clicked.emit()
    value = out.getvalue()
    assert "@create_bench v1" in value
    assert "node document" in value
    assert "Export successful" in value


def handoff_export_contains_visual_state():
    state = AppState(str(CORE_SCHEMAS))
    document = state.layout_model.create_node("document", {"layout_mode": "auto"})
    button = state.layout_model.create_node("button", {"text": "Save", "layout_mode": "free", "x": 96, "y": 88})
    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, button)
    state.selection_state.set_selection(button.id)

    window = MainWindow(state)
    out = io.StringIO()
    with redirect_stdout(out):
        window.handoff_button.clicked.emit()
    value = out.getvalue()
    assert '"selection": "button_1"' in value
    assert '"rect_map"' in value
    assert '"viewport"' in value
    assert '"draw_order"' in value
    assert '"checklist"' in value


def tool_sections_start_closed():
    state = AppState(str(CORE_SCHEMAS))
    window = MainWindow(state)
    assert window.active_tool_sections == []
    assert all(not button.isChecked() for button in window.section_toggle_buttons.values())
    assert window.left_toolbar is not None
    assert window.tool_workspace_window is not None


def tool_sections_open_in_click_order():
    state = AppState(str(CORE_SCHEMAS))
    window = MainWindow(state)

    window.section_toggle_buttons["Geometry"].click()
    window.section_toggle_buttons["Components"].click()
    window.section_toggle_buttons["Inspector"].click()
    window.section_toggle_buttons["Project"].click()

    assert window.active_tool_sections == ["Geometry", "Components", "Inspector", "Project"]
    assert window.section_cards["Geometry"].parent() is not None
    assert window.section_cards["Components"].parent() is not None
    assert window.section_cards["Inspector"].parent() is not None
    assert window.section_cards["Project"].parent() is not None
    assert window.tool_workspace_window.isVisible()


def tool_workspace_is_floating_tool_window():
    state = AppState(str(CORE_SCHEMAS))
    window = MainWindow(state)
    assert bool(window.tool_workspace_window.windowFlags() & Qt.WindowType.Tool)


def run_all_tests():
    tests = [
        checklist_updates_on_selection,
        summary_counts_displayed,
        selected_node_highlight,
        severity_tags_colored,
        export_blocked_when_errors,
        export_succeeds_when_valid,
        handoff_export_contains_visual_state,
        tool_sections_start_closed,
        tool_sections_open_in_click_order,
        tool_workspace_is_floating_tool_window,
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
