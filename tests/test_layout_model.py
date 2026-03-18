import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.layout_model import LayoutModel
from inspector.property_registry import PropertyRegistry


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


def make_model():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    return LayoutModel(registry)


def create_node_applies_defaults():
    model = make_model()
    node = model.create_node("button", {})
    assert node.id == "button_1"
    assert node.properties["text"] == "Button"
    assert model.get_node(node.id) is node


def add_node_basic():
    model = make_model()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    button = model.create_node("button", {})
    model.add_node(document.id, button)

    assert document.parent_id == "root"
    assert button.parent_id == document.id
    assert model.get_children(document.id)[0].id == button.id


def remove_node_cascade():
    model = make_model()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    button = model.create_node("button", {})

    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    model.add_node(panel.id, button)

    deleted = model.remove_node(panel.id)
    assert deleted == [button.id, panel.id]
    assert model.get_node(panel.id) is None
    assert model.get_node(button.id) is None
    assert document.children == []


def move_node_basic():
    model = make_model()
    document = model.create_node("document", {})
    panel_a = model.create_node("panel", {})
    panel_b = model.create_node("panel", {})
    button = model.create_node("button", {})

    model.add_node(model.root_id, document)
    model.add_node(document.id, panel_a)
    model.add_node(document.id, panel_b)
    model.add_node(panel_a.id, button)

    model.move_node(button.id, panel_b.id)
    assert button.parent_id == panel_b.id
    assert panel_a.children == []
    assert panel_b.children == [button.id]


def prevent_cycle():
    model = make_model()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    button = model.create_node("button", {})

    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    model.add_node(panel.id, button)

    try:
        model.move_node(panel.id, button.id)
        raise AssertionError("Expected cycle prevention error")
    except ValueError:
        pass


def reorder_node():
    model = make_model()
    document = model.create_node("document", {})
    button = model.create_node("button", {})
    text = model.create_node("text", {})
    input_node = model.create_node("input", {})

    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    model.add_node(document.id, text)
    model.add_node(document.id, input_node)

    model.reorder_node(input_node.id, 0)
    assert document.children == [input_node.id, button.id, text.id]


def root_protection():
    model = make_model()
    try:
        model.remove_node(model.root_id)
        raise AssertionError("Expected root delete protection")
    except ValueError:
        pass

    try:
        model.move_node(model.root_id, model.root_id)
        raise AssertionError("Expected root move protection")
    except ValueError:
        pass


def id_generation_per_type():
    model = make_model()
    button_1 = model.create_node("button", {})
    button_2 = model.create_node("button", {})
    panel_1 = model.create_node("panel", {})

    assert button_1.id == "button_1"
    assert button_2.id == "button_2"
    assert panel_1.id == "panel_1"


def run_all_tests():
    tests = [
        create_node_applies_defaults,
        add_node_basic,
        remove_node_cascade,
        move_node_basic,
        prevent_cycle,
        reorder_node,
        root_protection,
        id_generation_per_type,
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
