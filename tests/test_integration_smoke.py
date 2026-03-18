import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from export.dsl_builder import DSLBuilder
from core.tree_manager import TreeManager
from state.app_state import AppState


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


def make_state():
    return AppState(str(CORE_SCHEMAS))


def app_state_wires_all_systems():
    state = make_state()
    assert state.property_registry is not None
    assert state.layout_model is not None
    assert state.selection_state is not None
    assert state.checklist_engine is not None


def full_flow_no_errors():
    state = make_state()
    document = state.layout_model.create_node("document", {})
    container = state.layout_model.create_node("container", {})
    button = state.layout_model.create_node("button", {"text": "Save"})

    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, container)
    state.layout_model.add_node(container.id, button)

    result = state.checklist_engine.run()
    assert result["summary"]["errors"] == 0


def export_roundtrip_smoke():
    state = make_state()
    document = state.layout_model.create_node("document", {})
    container = state.layout_model.create_node("container", {})
    button = state.layout_model.create_node("button", {"text": "Save"})

    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, container)
    state.layout_model.add_node(container.id, button)

    builder = DSLBuilder(
        state.layout_model, state.property_registry, state.checklist_engine
    )
    dsl = builder.build_dsl()
    exported_json = builder.build_json()

    assert dsl
    assert exported_json


def integrity_check_passes():
    state = make_state()
    document = state.layout_model.create_node("document", {})
    container = state.layout_model.create_node("container", {})
    button = state.layout_model.create_node("button", {"text": "Save"})

    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, container)
    state.layout_model.add_node(container.id, button)

    state.layout_model.validate_integrity()


def invalid_move_raises_clear_error():
    state = make_state()
    manager = TreeManager(state.layout_model)
    document = state.layout_model.create_node("document", {})
    container = state.layout_model.create_node("container", {})
    button = state.layout_model.create_node("button", {"text": "Save"})

    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, container)
    state.layout_model.add_node(container.id, button)

    try:
        manager.move_node(container.id, button.id)
        raise AssertionError("Expected invalid move")
    except ValueError as exc:
        assert str(exc) == "Invalid move: cannot reparent into descendant"


def export_error_message():
    state = make_state()
    document = state.layout_model.create_node("document", {})
    button = state.layout_model.create_node("button", {})
    button.properties.pop("text", None)
    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, button)

    builder = DSLBuilder(
        state.layout_model, state.property_registry, state.checklist_engine
    )
    try:
        builder.build_dsl()
        raise AssertionError("Expected export block")
    except Exception as exc:
        assert str(exc) == "Export blocked: checklist errors present"


def run_all_tests():
    tests = [
        app_state_wires_all_systems,
        full_flow_no_errors,
        export_roundtrip_smoke,
        integrity_check_passes,
        invalid_move_raises_clear_error,
        export_error_message,
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
