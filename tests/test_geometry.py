import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.geometry import (
    apply_resize,
    clamp,
    detect_resize_handle,
    normalize_rect,
    point_in_rect,
)


def point_hit_works():
    rect = {"x": 10, "y": 20, "width": 100, "height": 40}
    assert point_in_rect(10, 20, rect) is True
    assert point_in_rect(110, 60, rect) is True
    assert point_in_rect(9, 20, rect) is False
    assert point_in_rect(111, 61, rect) is False


def clamp_works():
    assert clamp(5, 0, 10) == 5
    assert clamp(-1, 0, 10) == 0
    assert clamp(11, 0, 10) == 10
    assert clamp(11, 0, None) == 11


def resize_handle_detection_works():
    rect = {"x": 10, "y": 20, "width": 100, "height": 40}
    assert detect_resize_handle((110, 60), rect) == "bottom_right"
    assert detect_resize_handle((110, 30), rect) == "right"
    assert detect_resize_handle((50, 60), rect) == "bottom"
    assert detect_resize_handle((20, 30), rect) is None


def resize_math_respects_min_sizes():
    rect = {"x": 10, "y": 20, "width": 100, "height": 40}

    resized_width = apply_resize(
        rect,
        "right",
        dx=-200,
        dy=0,
        min_width=50,
        min_height=30,
    )
    assert resized_width == {"x": 10, "y": 20, "width": 50, "height": 40}

    resized_height = apply_resize(
        rect,
        "bottom",
        dx=0,
        dy=-200,
        min_width=50,
        min_height=30,
    )
    assert resized_height == {"x": 10, "y": 20, "width": 100, "height": 30}

    resized_both = apply_resize(
        rect,
        "bottom_right",
        dx=-200,
        dy=-200,
        min_width=50,
        min_height=30,
        max_width=120,
        max_height=80,
    )
    assert resized_both == {"x": 10, "y": 20, "width": 50, "height": 30}


def normalized_rect_never_negative():
    rect = normalize_rect(100, 50, -25, -10)
    assert rect == {"x": 75, "y": 40, "width": 25, "height": 10}
    assert rect["width"] >= 0
    assert rect["height"] >= 0


def run_all_tests():
    tests = [
        point_hit_works,
        clamp_works,
        resize_handle_detection_works,
        resize_math_respects_min_sizes,
        normalized_rect_never_negative,
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
