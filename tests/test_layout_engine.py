import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.layout_model import LayoutModel
from engine.intrinsic_size import get_intrinsic_size
from engine.layout_engine import LayoutEngine
from inspector.property_registry import PropertyRegistry


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


def button_intrinsic_size_uses_text():
    model = make_model()
    node = model.create_node("button", {"text": "Open Dashboard"})
    size = get_intrinsic_size(node)
    assert size == {"width": 136, "height": 32}


def text_intrinsic_height_uses_line_count():
    model = make_model()
    single = model.create_node("text", {"text": "One line"})
    multi = model.create_node("text", {"text": "Line 1\nLine 2\nLine 3"})
    assert get_intrinsic_size(single)["height"] == 26
    assert get_intrinsic_size(multi)["height"] == 62


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
    assert rects[top.id] == {"x": 0, "y": 0, "width": 260, "height": 180}
    assert rects[bottom.id] == {"x": 0, "y": 180, "width": 260, "height": 180}


def vertical_layout_respects_intrinsic_children():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "auto", "text": "Run"})
    text = model.create_node("text", {"layout_mode": "auto", "text": "Line 1\nLine 2"})
    panel = model.create_node("panel", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    model.add_node(document.id, text)
    model.add_node(document.id, panel)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[button.id] == {"x": 0, "y": 0, "width": 80, "height": 32}
    assert rects[text.id] == {"x": 0, "y": 32, "width": 200, "height": 44}
    assert rects[panel.id] == {"x": 0, "y": 76, "width": 260, "height": 180}


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
    assert rects[left.id] == {"x": 0, "y": 0, "width": 260, "height": 180}
    assert rects[right.id] == {"x": 260, "y": 0, "width": 260, "height": 180}


def horizontal_layout_respects_sidebar_width():
    model = make_model()
    horizontal = model.create_node("horizontal", {"layout_mode": "auto"})
    sidebar = model.create_node("sidebar", {"layout_mode": "auto"})
    main = model.create_node("main", {"layout_mode": "auto"})
    model.add_node(model.root_id, horizontal)
    model.add_node(horizontal.id, sidebar)
    model.add_node(horizontal.id, main)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[sidebar.id] == {"x": 0, "y": 0, "width": 240, "height": 300}
    assert rects[main.id] == {"x": 240, "y": 0, "width": 400, "height": 300}


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
    assert rects[auto_child.id] == {"x": 0, "y": 0, "width": 260, "height": 180}


def free_layout_ignores_intrinsic_override():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node(
        "button",
        {"layout_mode": "free", "x": 24, "y": 32, "width": 260, "height": 88, "text": "Tiny"},
    )
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[button.id] == {"x": 24, "y": 32, "width": 260, "height": 88}


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


def resize_from_left_and_top_handles_moves_origin_correctly():
    model = make_model()
    node = model.create_node(
        "button",
        {"layout_mode": "free", "x": 40, "y": 50, "width": 120, "height": 60, "min_width": 50, "min_height": 30},
    )
    model.add_node(model.root_id, node)
    engine = LayoutEngine(model)

    engine.compute_layout(model.root_id, CANVAS)
    left_result = engine.resize_node(node.id, "left", 20, 0, CANVAS, base_rect={"x": 40, "y": 50, "width": 120, "height": 60})
    top_left_result = engine.resize_node(node.id, "top_left", 20, 10, CANVAS, base_rect={"x": 40, "y": 50, "width": 120, "height": 60})

    assert left_result["x"] == 64
    assert left_result["y"] == 48
    assert left_result["width"] == 96
    assert top_left_result["x"] == 64
    assert top_left_result["y"] == 62
    assert top_left_result["width"] == 96
    assert top_left_result["height"] == 48


def no_negative_geometry_after_measure_layout():
    cramped_canvas = {"x": 0, "y": 0, "width": 160, "height": 60}
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    toolbar = model.create_node("toolbar", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "auto", "text": "Confirm"})
    input_node = model.create_node("input", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, toolbar)
    model.add_node(document.id, button)
    model.add_node(document.id, input_node)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, cramped_canvas)
    assert all(rect["width"] > 0 and rect["height"] > 0 for rect in rects.values())
    assert rects[toolbar.id]["height"] == 40
    assert rects[button.id]["height"] == 32
    assert rects[input_node.id]["height"] == 32


def deterministic_intrinsic_layout():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    toolbar = model.create_node("toolbar", {"layout_mode": "auto"})
    horizontal = model.create_node("horizontal", {"layout_mode": "auto"})
    sidebar = model.create_node("sidebar", {"layout_mode": "auto"})
    main = model.create_node("main", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "auto", "text": "Run build"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, toolbar)
    model.add_node(document.id, horizontal)
    model.add_node(horizontal.id, sidebar)
    model.add_node(horizontal.id, main)
    model.add_node(main.id, button)
    engine = LayoutEngine(model)

    first = engine.compute_layout(model.root_id, CANVAS)
    second = engine.compute_layout(model.root_id, CANVAS)
    assert first == second


def button_no_longer_equal_split_giant():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "auto", "text": "Save"})
    panel = model.create_node("panel", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    model.add_node(document.id, panel)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[button.id]["height"] == 32
    assert rects[button.id]["height"] < rects[panel.id]["height"]


def input_intrinsic_height_fixed():
    model = make_model()
    horizontal = model.create_node("horizontal", {"layout_mode": "auto"})
    input_node = model.create_node("input", {"layout_mode": "auto"})
    main = model.create_node("main", {"layout_mode": "auto"})
    model.add_node(model.root_id, horizontal)
    model.add_node(horizontal.id, input_node)
    model.add_node(horizontal.id, main)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[input_node.id]["height"] == 32
    assert rects[input_node.id]["width"] == 220
    assert rects[input_node.id]["y"] == 0
    assert rects[main.id]["x"] == 220
    assert rects[main.id]["width"] == 400


def toolbar_prefers_fixed_height():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    toolbar = model.create_node("toolbar", {"layout_mode": "auto"})
    main = model.create_node("main", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, toolbar)
    model.add_node(document.id, main)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[toolbar.id]["height"] == 40
    assert rects[main.id]["height"] == 300


def unsupported_ui_role_falls_back_to_supported_node_type():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node(
        "button",
        {"layout_mode": "auto", "text": "Save", "ui_role": "not_supported"},
    )
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[button.id] == {"x": 0, "y": 0, "width": 80, "height": 32}


def unsupported_ui_role_has_zero_effect_on_supported_type():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "auto", "text": "Save", "ui_role": "mystery_role"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[button.id] == {"x": 0, "y": 0, "width": 80, "height": 32}


def preferred_children_do_not_fill_cross_axis_by_default():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "auto", "text": "Save"})
    input_node = model.create_node("input", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    model.add_node(document.id, input_node)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[button.id]["width"] == 80
    assert rects[input_node.id]["width"] == 220


def only_fill_capable_children_absorb_primary_axis_remainder():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    toolbar = model.create_node("toolbar", {"layout_mode": "auto"})
    main = model.create_node("main", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, toolbar)
    model.add_node(document.id, main)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[toolbar.id] == {"x": 0, "y": 0, "width": 400, "height": 40}
    assert rects[main.id] == {"x": 0, "y": 40, "width": 400, "height": 300}


def panel_does_not_become_fill_just_because_it_is_last_child():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "auto", "text": "Save"})
    panel = model.create_node("panel", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    model.add_node(document.id, panel)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[panel.id] == {"x": 0, "y": 32, "width": 260, "height": 180}


def window_roles_do_not_fill_canvas():
    model = make_model()
    document = model.create_node("document", {"layout_mode": "auto"})
    window = model.create_node(
        "main",
        {"layout_mode": "auto", "ui_role": "tool_window", "width": 320, "height": 220},
    )
    model.add_node(model.root_id, document)
    model.add_node(document.id, window)
    engine = LayoutEngine(model)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert rects[window.id] == {"x": 0, "y": 0, "width": 320, "height": 220}


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


def run_all_tests():
    tests = [
        free_node_uses_explicit_rect,
        button_intrinsic_size_uses_text,
        text_intrinsic_height_uses_line_count,
        auto_vertical_layout_distributes_children,
        vertical_layout_respects_intrinsic_children,
        auto_horizontal_layout_distributes_children,
        horizontal_layout_respects_sidebar_width,
        mixed_free_and_auto_layout_works,
        free_layout_ignores_intrinsic_override,
        hit_test_selects_topmost_node,
        drag_converts_auto_node_to_free,
        locked_node_does_not_move,
        resize_respects_min_sizes,
        resize_from_left_and_top_handles_moves_origin_correctly,
        no_negative_geometry_after_measure_layout,
        deterministic_intrinsic_layout,
        button_no_longer_equal_split_giant,
        input_intrinsic_height_fixed,
        toolbar_prefers_fixed_height,
        unsupported_ui_role_falls_back_to_supported_node_type,
        unsupported_ui_role_has_zero_effect_on_supported_type,
        preferred_children_do_not_fill_cross_axis_by_default,
        only_fill_capable_children_absorb_primary_axis_remainder,
        panel_does_not_become_fill_just_because_it_is_last_child,
        window_roles_do_not_fill_canvas,
        sibling_order_preserved,
        grid_snap_deterministic,
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
