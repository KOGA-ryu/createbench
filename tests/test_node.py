import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.node import Node


def create_node_basic():
    node = Node(id="button_1", type="button", properties={"text": "Save"}, parent_id="root")
    assert node.id == "button_1"
    assert node.type == "button"
    assert node.name is None
    assert node.properties == {"text": "Save"}
    assert node.children == []
    assert node.parent_id == "root"


def add_child_append():
    node = Node(id="container_1", type="container", properties={})
    node.add_child("button_1")
    node.add_child("text_1")
    assert node.children == ["button_1", "text_1"]


def add_child_insert():
    node = Node(id="container_1", type="container", properties={})
    node.add_child("button_1")
    node.add_child("input_1")
    node.add_child("text_1", index=1)
    assert node.children == ["button_1", "text_1", "input_1"]


def remove_child():
    node = Node(id="container_1", type="container", properties={})
    node.add_child("button_1")
    node.add_child("text_1")
    node.remove_child("button_1")
    node.remove_child("missing")
    assert node.children == ["text_1"]


def reorder_child():
    node = Node(id="container_1", type="container", properties={})
    node.add_child("button_1")
    node.add_child("text_1")
    node.add_child("input_1")
    node.reorder_child("input_1", 0)
    node.reorder_child("missing", 1)
    assert node.children == ["input_1", "button_1", "text_1"]


def to_dict_structure():
    node = Node(
        id="button_1",
        type="button",
        properties={"text": "Save"},
        parent_id="main_1",
        name="Primary Save",
    )
    node.add_child("ignored_child")
    data = node.to_dict()
    assert data == {
        "id": "button_1",
        "type": "button",
        "name": "Primary Save",
        "properties": {"text": "Save"},
        "children": ["ignored_child"],
    }


def run_all_tests():
    tests = [
        create_node_basic,
        add_child_append,
        add_child_insert,
        remove_child,
        reorder_child,
        to_dict_structure,
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
