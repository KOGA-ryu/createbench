import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.placement_engine import place_new_node, place_template_subtree
from core.layout_model import LayoutModel
from inspector.property_registry import PropertyRegistry


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


class LayoutEngineStub:
    def __init__(self, rect_map=None):
        self.rect_map = rect_map or {}

    def get_node_rect(self, node_id):
        return self.rect_map.get(node_id)


def make_model():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    return LayoutModel(registry)


def free_parent_placement_gives_explicit_coordinates():
    model = make_model()
    parent = model.create_node("container", {"layout_mode": "free"})
    child = model.create_node("button", {})
    model.add_node(model.root_id, parent)

    props = place_new_node(
        child,
        parent,
        parent_rect={"x": 100, "y": 200, "width": 300, "height": 200},
        cursor_pos=(120, 240),
    )

    assert props["layout_mode"] == "free"
    assert props["x"] == 120
    assert props["y"] == 240


def auto_parent_placement_respects_order():
    model = make_model()
    parent = model.create_node("vertical", {"layout_mode": "auto"})
    first = model.create_node("text", {})
    second = model.create_node("button", {})
    model.add_node(model.root_id, parent)

    place_new_node(first, parent)
    model.add_node(parent.id, first)
    place_new_node(second, parent)
    model.add_node(parent.id, second)

    assert first.properties["layout_mode"] == "auto"
    assert second.properties["layout_mode"] == "auto"
    assert parent.children == [first.id, second.id]


def template_subtree_preserves_order():
    model = make_model()
    parent = model.create_node("container", {"layout_mode": "auto"})
    model.add_node(model.root_id, parent)

    template = {
        "type": "vertical",
        "children": [
            {"type": "text"},
            {"type": "button"},
        ],
    }

    first_created_id = place_template_subtree(template, parent.id, model, None)

    vertical = model.get_node(first_created_id)
    assert vertical is not None
    children = model.get_children(vertical.id)
    assert [child.type for child in children] == ["text", "button"]


def repeated_placement_uses_deterministic_offset():
    model = make_model()
    parent = model.create_node("container", {"layout_mode": "free"})
    model.add_node(model.root_id, parent)

    first = model.create_node("button", {})
    place_new_node(first, parent, parent_rect={"x": 10, "y": 20, "width": 200, "height": 100})
    model.add_node(parent.id, first)

    second = model.create_node("button", {})
    place_new_node(second, parent, parent_rect={"x": 10, "y": 20, "width": 200, "height": 100})

    assert (first.properties["x"], first.properties["y"]) == (10, 20)
    assert (second.properties["x"], second.properties["y"]) == (26, 36)


def run_all_tests():
    tests = [
        free_parent_placement_gives_explicit_coordinates,
        auto_parent_placement_respects_order,
        template_subtree_preserves_order,
        repeated_placement_uses_deterministic_offset,
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
