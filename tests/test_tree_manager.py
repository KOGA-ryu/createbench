import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.layout_model import LayoutModel
from core.tree_manager import TreeManager
from inspector.property_registry import PropertyRegistry


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


def make_tree_manager():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    model = LayoutModel(registry)
    return TreeManager(model), model


def add_node_returns_action():
    manager, model = make_tree_manager()
    document = model.create_node("document", {})
    result = manager.add_node(model.root_id, document)
    assert result == {"action": "add", "node_id": document.id, "parent_id": model.root_id}


def remove_node_returns_deleted_ids():
    manager, model = make_tree_manager()
    document = model.create_node("document", {})
    button = model.create_node("button", {})
    manager.add_node(model.root_id, document)
    manager.add_node(document.id, button)

    result = manager.remove_node(document.id)
    assert result["action"] == "remove"
    assert result["deleted_ids"] == [button.id, document.id]


def move_node_updates_parent():
    manager, model = make_tree_manager()
    document = model.create_node("document", {})
    panel_a = model.create_node("panel", {})
    panel_b = model.create_node("panel", {})
    button = model.create_node("button", {})

    manager.add_node(model.root_id, document)
    manager.add_node(document.id, panel_a)
    manager.add_node(document.id, panel_b)
    manager.add_node(panel_a.id, button)

    result = manager.move_node(button.id, panel_b.id)
    assert result == {"action": "move", "node_id": button.id, "new_parent_id": panel_b.id}
    assert model.get_parent(button.id).id == panel_b.id


def reorder_node_changes_order():
    manager, model = make_tree_manager()
    document = model.create_node("document", {})
    button = model.create_node("button", {})
    text = model.create_node("text", {})
    input_node = model.create_node("input", {})

    manager.add_node(model.root_id, document)
    manager.add_node(document.id, button)
    manager.add_node(document.id, text)
    manager.add_node(document.id, input_node)

    result = manager.reorder_node(input_node.id, 0)
    assert result == {"action": "reorder", "node_id": input_node.id, "new_index": 0}
    assert document.children == [input_node.id, button.id, text.id]


def invalid_move_raises():
    manager, model = make_tree_manager()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    button = model.create_node("button", {})

    manager.add_node(model.root_id, document)
    manager.add_node(document.id, panel)
    manager.add_node(panel.id, button)

    try:
        manager.move_node(panel.id, button.id)
        raise AssertionError("Expected invalid move to raise")
    except ValueError:
        pass


def get_parent_and_children():
    manager, model = make_tree_manager()
    document = model.create_node("document", {})
    button = model.create_node("button", {})
    text = model.create_node("text", {})

    manager.add_node(model.root_id, document)
    manager.add_node(document.id, button)
    manager.add_node(document.id, text)

    parent = manager.get_parent(button.id)
    children = manager.get_children(document.id)

    assert parent is not None
    assert parent.id == document.id
    assert [child.id for child in children] == [button.id, text.id]


def run_all_tests():
    tests = [
        add_node_returns_action,
        remove_node_returns_deleted_ids,
        move_node_updates_parent,
        reorder_node_changes_order,
        invalid_move_raises,
        get_parent_and_children,
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
