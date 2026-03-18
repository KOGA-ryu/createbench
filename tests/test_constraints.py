import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.constraints import (
    clamp_to_canvas,
    clamp_to_parent,
    enforce_size_constraints,
    validate_resize,
)


class StubNode:
    def __init__(self, **properties):
        self.properties = dict(properties)


def min_size_enforced():
    node = StubNode(min_width=50, min_height=30, max_width=None, max_height=None)
    rect = {"x": 10, "y": 20, "width": 10, "height": 5}
    constrained = enforce_size_constraints(rect, node)
    assert constrained == {"x": 10, "y": 20, "width": 50, "height": 30}


def max_size_enforced():
    node = StubNode(min_width=50, min_height=30, max_width=120, max_height=80)
    rect = {"x": 10, "y": 20, "width": 200, "height": 100}
    constrained = enforce_size_constraints(rect, node)
    assert constrained == {"x": 10, "y": 20, "width": 120, "height": 80}


def node_stays_inside_parent():
    rect = {"x": 180, "y": 140, "width": 80, "height": 60}
    parent_rect = {"x": 100, "y": 100, "width": 120, "height": 100}
    constrained = clamp_to_parent(rect, parent_rect)
    assert constrained == {"x": 140, "y": 140, "width": 80, "height": 60}


def root_level_node_stays_inside_canvas():
    rect = {"x": -20, "y": 190, "width": 80, "height": 40}
    canvas_rect = {"x": 0, "y": 0, "width": 200, "height": 200}
    constrained = clamp_to_canvas(rect, canvas_rect)
    assert constrained == {"x": 0, "y": 160, "width": 80, "height": 40}


def invalid_resize_resolves_safely():
    node = StubNode(
        min_width=50,
        min_height=30,
        max_width=None,
        max_height=None,
        layout_mode="free",
    )
    rect = {"x": 80, "y": 90, "width": 200, "height": 120}
    parent_rect = {"x": 100, "y": 100, "width": 60, "height": 40}
    constrained = validate_resize(rect, node, parent_rect, None)
    assert constrained == {"x": 100, "y": 100, "width": 60, "height": 40}


def run_all_tests():
    tests = [
        min_size_enforced,
        max_size_enforced,
        node_stays_inside_parent,
        root_level_node_stays_inside_canvas,
        invalid_resize_resolves_safely,
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
