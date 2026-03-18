import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.layout_model import LayoutModel
from inspector.property_registry import PropertyRegistry
from state.selection_state import SelectionState


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


def make_selection_state():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    model = LayoutModel(registry)
    return SelectionState(model), model


def set_and_get_selection():
    selection, model = make_selection_state()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)

    selection.set_selection(document.id)
    assert selection.get_selection() == document.id


def clear_selection():
    selection, model = make_selection_state()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)

    selection.set_selection(document.id)
    selection.clear_selection()
    assert selection.get_selection() is None


def invalid_selection_clears():
    selection, _model = make_selection_state()
    selection.set_selection("missing_node")
    assert selection.get_selection() is None


def reselect_triggers_event():
    selection, model = make_selection_state()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)

    events = []
    selection.subscribe(events.append)

    selection.set_selection(document.id)
    selection.set_selection(document.id)

    assert events == [document.id, document.id]


def deletion_selects_parent():
    selection, model = make_selection_state()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    button = model.create_node("button", {})

    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    model.add_node(panel.id, button)

    selection.set_selection(button.id)
    selection.handle_node_deleted(button.id)

    assert selection.get_selection() == panel.id


def deletion_clears_if_no_parent():
    selection, model = make_selection_state()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)

    selection.set_selection(document.id)
    model.remove_node(document.id)
    selection.handle_node_deleted(document.id)

    assert selection.get_selection() is None


def subscriber_called_on_change():
    selection, model = make_selection_state()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)

    calls = []

    def callback(selected_id):
        calls.append(selected_id)

    selection.subscribe(callback)
    selection.set_selection(document.id)
    selection.clear_selection()

    assert calls == [document.id, None]


def run_all_tests():
    tests = [
        set_and_get_selection,
        clear_selection,
        invalid_selection_clears,
        reselect_triggers_event,
        deletion_selects_parent,
        deletion_clears_if_no_parent,
        subscriber_called_on_change,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
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
