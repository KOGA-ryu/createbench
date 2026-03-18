import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent
from PySide6.QtWidgets import QApplication


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from canvas.canvas_widget import CanvasWidget
from core.layout_model import LayoutModel
from engine.constraints import clamp_to_parent
from engine.geometry import rect_contains_rect
from engine.layout_engine import LayoutEngine
from inspector.property_registry import PropertyRegistry
from state.selection_state import SelectionState


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"
CANVAS = {"x": 0, "y": 0, "width": 800, "height": 600}
APP = QApplication.instance() or QApplication([])


def make_model():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    return LayoutModel(registry)


def make_canvas():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    model = LayoutModel(registry)
    selection = SelectionState(model)
    canvas = CanvasWidget(model, selection)
    canvas.resize(800, 600)
    return canvas, model, selection


def _mouse_event(event_type, point):
    return QMouseEvent(
        event_type,
        QPointF(point),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )


def mixed_auto_and_free_layout():
    model = make_model()
    engine = LayoutEngine(model)
    document = model.create_node("document", {"layout_mode": "auto"})
    horizontal = model.create_node("horizontal", {"layout_mode": "auto"})
    sidebar = model.create_node("sidebar", {"layout_mode": "auto"})
    main = model.create_node("main", {"layout_mode": "auto"})
    panel = model.create_node(
        "panel",
        {"layout_mode": "free", "x": 320, "y": 120, "width": 160, "height": 120},
    )
    model.add_node(model.root_id, document)
    model.add_node(document.id, horizontal)
    model.add_node(horizontal.id, sidebar)
    model.add_node(horizontal.id, main)
    model.add_node(main.id, panel)

    rects = engine.compute_layout(model.root_id, CANVAS)
    for node in (document, horizontal, sidebar, main, panel):
        assert node.id in rects
    assert rects[panel.id] == {"x": 400, "y": 120, "width": 160, "height": 120}
    assert rects[sidebar.id]["width"] > 0
    assert rects[main.id]["width"] > 0
    assert rects[sidebar.id] != rects[panel.id]


def drag_auto_node_converts_to_free():
    model = make_model()
    engine = LayoutEngine(model)
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    engine.compute_layout(model.root_id, CANVAS)
    before = dict(button.properties)
    result = engine.move_node(button.id, 173, 117, CANVAS)

    assert before["layout_mode"] == "auto"
    assert result["layout_mode"] == "free"
    assert result["x"] % 8 == 0
    assert result["y"] % 8 == 0
    assert result["width"] > 0
    assert result["height"] > 0
    assert button.properties["layout_mode"] == "auto"


def locked_node_blocks_move_and_resize():
    model = make_model()
    engine = LayoutEngine(model)
    node = model.create_node(
        "button",
        {
            "layout_mode": "free",
            "locked": True,
            "x": 80,
            "y": 96,
            "width": 120,
            "height": 64,
            "title": "Save CTA",
        },
    )
    model.add_node(model.root_id, node)
    engine.compute_layout(model.root_id, CANVAS)
    before_props = dict(node.properties)
    before_rect = dict(engine.rect_map[node.id])

    moved = engine.move_node(node.id, 200, 220, CANVAS)
    resized = engine.resize_node(node.id, "bottom_right", 80, 80, CANVAS)

    assert moved["blocked"] is True
    assert resized["blocked"] is True
    assert moved["x"] == before_rect["x"]
    assert moved["y"] == before_rect["y"]
    assert resized["width"] == before_rect["width"]
    assert resized["height"] == before_rect["height"]
    assert node.properties == before_props


def overlapping_nodes_hit_test_topmost():
    model = make_model()
    engine = LayoutEngine(model)
    first = model.create_node("panel", {"layout_mode": "free", "x": 40, "y": 40, "width": 200, "height": 160})
    second = model.create_node("button", {"layout_mode": "free", "x": 80, "y": 80, "width": 120, "height": 80})
    model.add_node(model.root_id, first)
    model.add_node(model.root_id, second)

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert engine.hit_test((100, 100), rects, engine.draw_order) == second.id


def grid_snap_stability():
    model = make_model()
    engine = LayoutEngine(model)
    node = model.create_node("button", {"layout_mode": "free", "x": 13, "y": 19, "width": 99, "height": 42})
    model.add_node(model.root_id, node)

    results = [engine.move_node(node.id, 15, 18, CANVAS) for _ in range(5)]
    first = results[0]
    assert all(result == first for result in results[1:])


def resize_clamps_to_min():
    model = make_model()
    engine = LayoutEngine(model)
    node = model.create_node(
        "button",
        {"layout_mode": "free", "x": 100, "y": 100, "width": 120, "height": 64, "min_width": 50, "min_height": 30},
    )
    model.add_node(model.root_id, node)

    result = engine.resize_node(node.id, "bottom_right", -400, -400, CANVAS)
    assert result["width"] == 50
    assert result["height"] == 30


def parent_bounds_enforced():
    model = make_model()
    engine = LayoutEngine(model)
    document = model.create_node("document", {"layout_mode": "auto"})
    parent = model.create_node("panel", {"layout_mode": "auto"})
    child = model.create_node("button", {"layout_mode": "free", "x": 10, "y": 10, "width": 100, "height": 40})
    model.add_node(model.root_id, document)
    model.add_node(document.id, parent)
    model.add_node(parent.id, child)

    rects = engine.compute_layout(model.root_id, CANVAS)
    parent_rect = rects[parent.id]
    moved = engine.move_node(child.id, 999, 999, CANVAS)
    moved_rect = {
        "x": moved["x"],
        "y": moved["y"],
        "width": moved["width"],
        "height": moved["height"],
    }
    assert rect_contains_rect(parent_rect, moved_rect)
    assert moved_rect == clamp_to_parent(moved_rect, parent_rect)


def canvas_rect_map_matches_engine():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 96, "y": 88, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    canvas.show()
    canvas.repaint()
    APP.processEvents()

    engine_rect = canvas.layout_engine.get_node_rect(button.id)
    canvas_rect = canvas.node_rects[button.id]
    assert engine_rect == {
        "x": canvas_rect.x(),
        "y": canvas_rect.y(),
        "width": canvas_rect.width(),
        "height": canvas_rect.height(),
    }


def move_does_not_mutate_semantic_fields():
    model = make_model()
    engine = LayoutEngine(model)
    node = model.create_node(
        "button",
        {
            "layout_mode": "free",
            "x": 32,
            "y": 48,
            "width": 120,
            "height": 64,
            "title": "Primary",
            "description": "Save changes",
            "behavior": "submit",
            "interactions": "click",
        },
    )
    model.add_node(model.root_id, node)
    before = {
        "title": node.properties["title"],
        "description": node.properties["description"],
        "behavior": node.properties["behavior"],
        "interactions": node.properties["interactions"],
    }

    engine.move_node(node.id, 177, 141, CANVAS)

    after = {
        "title": node.properties["title"],
        "description": node.properties["description"],
        "behavior": node.properties["behavior"],
        "interactions": node.properties["interactions"],
    }
    assert before == after


def resize_does_not_mutate_semantic_fields():
    model = make_model()
    engine = LayoutEngine(model)
    node = model.create_node(
        "button",
        {
            "layout_mode": "free",
            "x": 32,
            "y": 48,
            "width": 120,
            "height": 64,
            "title": "Primary",
            "description": "Save changes",
            "behavior": "submit",
            "interactions": "click",
        },
    )
    model.add_node(model.root_id, node)
    before = {
        "title": node.properties["title"],
        "description": node.properties["description"],
        "behavior": node.properties["behavior"],
        "interactions": node.properties["interactions"],
    }

    engine.resize_node(node.id, "bottom_right", 40, 24, CANVAS)

    after = {
        "title": node.properties["title"],
        "description": node.properties["description"],
        "behavior": node.properties["behavior"],
        "interactions": node.properties["interactions"],
    }
    assert before == after


def rect_map_unique_per_node():
    model = make_model()
    engine = LayoutEngine(model)
    document = model.create_node("document", {"layout_mode": "auto"})
    model.add_node(model.root_id, document)
    for _ in range(5):
        model.add_node(document.id, model.create_node("button", {"layout_mode": "auto"}))

    rects = engine.compute_layout(model.root_id, CANVAS)
    assert len(rects) == len(set(rects))
    assert len(engine.draw_order) == len(set(engine.draw_order))


def no_negative_geometry_emitted():
    model = make_model()
    engine = LayoutEngine(model)
    node = model.create_node(
        "button",
        {"layout_mode": "free", "x": 10, "y": 10, "width": 1, "height": 1, "min_width": 50, "min_height": 30},
    )
    model.add_node(model.root_id, node)

    rects = engine.compute_layout(model.root_id, CANVAS)
    moved = engine.move_node(node.id, -100, -100, CANVAS)
    resized = engine.resize_node(node.id, "bottom_right", -1000, -1000, CANVAS)

    assert rects[node.id]["width"] >= 50
    assert rects[node.id]["height"] >= 30
    assert moved["width"] >= 50
    assert moved["height"] >= 30
    assert resized["width"] >= 50
    assert resized["height"] >= 30


def click_after_drag_selects_correct_node():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    first = model.create_node("button", {"layout_mode": "auto"})
    second = model.create_node("button", {"layout_mode": "free", "x": 300, "y": 200, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, first)
    model.add_node(document.id, second)
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    start = canvas.node_rects[first.id].center()
    moved = QPoint(start.x() + 80, start.y() + 56)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))
    APP.processEvents()

    click_point = canvas.node_rects[second.id].center()
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, click_point))
    assert selection.get_selection() == second.id


def locked_node_still_selectable():
    canvas, model, selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"locked": True})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    point = canvas.node_rects[button.id].center()
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, point))
    assert selection.get_selection() == button.id


def free_node_drag_updates_canvas_rects_after_repaint():
    canvas, model, _selection = make_canvas()
    document = model.create_node("document", {"layout_mode": "auto"})
    button = model.create_node("button", {"layout_mode": "free", "x": 120, "y": 120, "width": 120, "height": 64})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    canvas.show()
    canvas.repaint()
    APP.processEvents()

    before = canvas.node_rects[button.id]
    start = before.center()
    moved = QPoint(start.x() + 40, start.y() + 32)
    canvas.mousePressEvent(_mouse_event(QMouseEvent.Type.MouseButtonPress, start))
    canvas.mouseMoveEvent(_mouse_event(QMouseEvent.Type.MouseMove, moved))
    canvas.mouseReleaseEvent(_mouse_event(QMouseEvent.Type.MouseButtonRelease, moved))
    canvas.repaint()
    APP.processEvents()

    after = canvas.node_rects[button.id]
    assert after.topLeft() != before.topLeft()


def run_all_tests():
    tests = [
        mixed_auto_and_free_layout,
        drag_auto_node_converts_to_free,
        locked_node_blocks_move_and_resize,
        overlapping_nodes_hit_test_topmost,
        grid_snap_stability,
        resize_clamps_to_min,
        parent_bounds_enforced,
        canvas_rect_map_matches_engine,
        move_does_not_mutate_semantic_fields,
        resize_does_not_mutate_semantic_fields,
        rect_map_unique_per_node,
        no_negative_geometry_emitted,
        click_after_drag_selects_correct_node,
        locked_node_still_selectable,
        free_node_drag_updates_canvas_rects_after_repaint,
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
