import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.snap_engine import (
    resolve_snap,
    snap_rect_to_grid,
    snap_rect_to_parent_edges,
    snap_rect_to_sibling_edges,
)


def move_snaps_to_grid():
    rect = {"x": 13, "y": 19, "width": 100, "height": 40}
    snapped = snap_rect_to_grid(rect, 8)
    assert snapped == {"x": 16, "y": 16, "width": 96, "height": 40}


def resize_snaps_to_grid():
    rect = {"x": 0, "y": 0, "width": 103, "height": 41}
    snapped = snap_rect_to_grid(rect, 8)
    assert snapped == {"x": 0, "y": 0, "width": 104, "height": 40}


def parent_edge_snap_works():
    rect = {"x": 5, "y": 6, "width": 96, "height": 40}
    parent = {"x": 0, "y": 0, "width": 200, "height": 120}
    snapped = snap_rect_to_parent_edges(rect, parent, threshold=8)
    assert snapped == {"x": 0, "y": 0, "width": 96, "height": 40}


def sibling_edge_snap_works():
    rect = {"x": 58, "y": 67, "width": 100, "height": 40}
    siblings = [
        {"x": 0, "y": 64, "width": 60, "height": 40},
        {"x": 200, "y": 0, "width": 50, "height": 50},
    ]
    snapped = snap_rect_to_sibling_edges(rect, siblings, threshold=8)
    assert snapped == {"x": 60, "y": 64, "width": 100, "height": 40}


def snap_output_deterministic():
    rect = {"x": 15, "y": 18, "width": 99, "height": 42}
    parent = {"x": 0, "y": 0, "width": 200, "height": 200}
    siblings = [{"x": 104, "y": 16, "width": 40, "height": 40}]

    first = resolve_snap(rect, parent, siblings, grid_size=8)
    second = resolve_snap(first, parent, siblings, grid_size=8)

    assert first == second


def run_all_tests():
    tests = [
        move_snaps_to_grid,
        resize_snaps_to_grid,
        parent_edge_snap_works,
        sibling_edge_snap_works,
        snap_output_deterministic,
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
