import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.layout_engine import LayoutEngine
from inspector.property_registry import PropertyRegistry
from core.layout_model import LayoutModel


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"
CANVAS = {"x": 0, "y": 0, "width": 400, "height": 300}


def make_model():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    return LayoutModel(registry)


def free_node_uses_explicit_rect():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "free", "x": 20, "y": 30, "width": 120, "height": 80})
    model.add_node(model.root_id, document)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[document.id] == {"x": 20, "y": 30, "width": 120, "height": 80}


def auto_vertical_layout_distributes_children():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    top = model.create_node("panel", {"layout_mode": "auto"})
    bottom = model.create_node("panel", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, top)
    model.add_node(document.id, bottom)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[top.id] == {"x": 0, "y": 0, "width": 400, "height": 150}
    assert rects[bottom.id] == {"x": 0, "y": 150, "width": 400, "height": 150}


def auto_horizontal_layout_distributes_children():
    model = make_model()
    horizontal = model.create_node("horizontal", {"layout_mode": "auto"})
    left = model.create_node("panel", {"layout_mode": "auto"})
    right = model.create_node("panel", {"layout_mode": "auto"})
    model.add_node(model.root_id, horizontal)
    model.add_node(horizontal.id, left)
    model.add_node(horizontal.id, right)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[left.id] == {"x": 0, "y": 0, "width": 200, "height": 300}
    assert rects[right.id] == {"x": 200, "y": 0, "width": 200, "height": 300}


def mixed_free_and_auto_layout_works():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    free_child = model.create_node("button", {"layout_mode": "free", "x": 40, "y": 50, "width": 90, "height": 40})
    auto_child = model.create_node("panel", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, free_child)
    model.add_node(document.id, auto_child)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[free_child.id] == {"x": 40, "y": 50, "width": 90, "height": 40}
    assert rects[auto_child.id] == {"x": 0, "y": 0, "width": 400, "height": 300}


def hit_test_selects_topmost_node():
    model = make_model()
    bottom = model.create_node("panel", {"layout_mode": "free", "x": 0, "y": 0, "width": 200, "height": 200})
    top = model.create_node("button", {"layout_mode": "free", "x": 40, "y": 40, "width": 120, "height": 80})
    model.add_node(model.root_id, bottom)
    model.add_node(model.root_id, top)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    hit = engine.hit_test((50, 50), rects, engine.draw_order)
    assert hit == top.id


def drag_converts_auto_node_to_free():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    child = model.create_node("button", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, child)
    engine = LayoutEngine(model)

    engine.compute_layout(model.root_id, CANVAS)
    result = engine.move_node(child.id, 23, 37, CANVAS)

    assert result["layout_mode"] == "free"
    assert result["x"] == 24
    assert result["y"] == 40
    assert result["blocked"] is False


def locked_node_does_not_move():
    model = make_model()
    node = model.create_node(
        "button",
        {"layout_mode": "free", "x": 16, "y": 24, "width": 96, "height": 40, "locked": True},
    )
    model.add_node(model.root_id, node)
    engine = LayoutEngine(model)

    engine.compute_layout(model.root_id, CANVAS)
    result = engine.move_node(node.id, 80, 90, CANVAS)

    assert result["blocked"] is True
    assert result["x"] == 16
    assert result["y"] == 24


def resize_respects_min_sizes():
    model = make_model()
    node = model.create_node(
        "button",
        {"layout_mode": "free", "x": 10, "y": 20, "width": 96, "height": 40, "min_width": 50, "min_height": 30},
    )
    model.add_node(model.root_id, node)
    engine = LayoutEngine(model)

    engine.compute_layout(model.root_id, CANVAS)
    result = engine.resize_node(node.id, "bottom_right", -200, -200, CANVAS)

    assert result["x"] == 10
    assert result["y"] == 20
    assert result["width"] == 50
    assert result["height"] == 30
    assert result["layout_mode"] == "free"


def grid_snap_deterministic():
    model = make_model()
    node = model.create_node(
        "button",
        {"layout_mode": "free", "x": 15, "y": 18, "width": 99, "height": 42},
    )
    model.add_node(model.root_id, node)
    engine = LayoutEngine(model)

    first = engine.move_node(node.id, 15, 18, CANVAS)
    second = engine.move_node(node.id, first["x"], first["y"], CANVAS)

    assert first["x"] == second["x"]
    assert first["y"] == second["y"]
    assert first["width"] == second["width"]
    assert first["height"] == second["height"]


def sibling_order_preserved():
    model = make_model()
    first = model.create_node("button", {"layout_mode": "free", "x": 0, "y": 0, "width": 80, "height": 40})
    second = model.create_node("button", {"layout_mode": "free", "x": 20, "y": 20, "width": 80, "height": 40})
    third = model.create_node("button", {"layout_mode": "free", "x": 40, "y": 40, "width": 80, "height": 40})
    model.add_node(model.root_id, first)
    model.add_node(model.root_id, second)
    model.add_node(model.root_id, third)
    engine = LayoutEngine(model)

    engine.compute_layout(model.root_id, CANVAS)
    assert engine.draw_order == [first.id, second.id, third.id]


def run_all_tests():
    tests = [
        free_node_uses_explicit_rect,
        auto_vertical_layout_distributes_children,
        auto_horizontal_layout_distributes_children,
        mixed_free_and_auto_layout_works,
        hit_test_selects_topmost_node,
        drag_converts_auto_node_to_free,
        locked_node_does_not_move,
        resize_respects_min_sizes,
        grid_snap_deterministic,
        sibling_order_preserved,
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
