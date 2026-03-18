import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from state.app_state import AppState


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


def make_app_state():
    return AppState(str(CORE_SCHEMAS))


def app_state_initialization():
    state = make_app_state()
    assert state is not None


def subsystems_exist():
    state = make_app_state()
    assert state.property_registry is not None
    assert state.layout_model is not None
    assert state.selection_state is not None
    assert state.checklist_engine is not None


def get_selected_node_none():
    state = make_app_state()
    assert state.get_selected_node() is None


def get_node_lookup():
    state = make_app_state()
    document = state.layout_model.create_node("document", {})
    state.layout_model.add_node(state.layout_model.root_id, document)
    assert state.get_node(document.id) is document


def run_all_tests():
    tests = [
        app_state_initialization,
        subsystems_exist,
        get_selected_node_none,
        get_node_lookup,
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
