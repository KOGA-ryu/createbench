import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from engine.lock_manager import can_move, can_resize


class StubNode:
    def __init__(self, **properties):
        self.properties = dict(properties)


def locked_node_cannot_move():
    node = StubNode(locked=True)
    assert can_move(node) is False


def locked_node_cannot_resize():
    node = StubNode(locked=True)
    assert can_resize(node) is False


def unlocked_node_can_move():
    node = StubNode(locked=False)
    assert can_move(node) is True


def unlocked_node_can_resize():
    node = StubNode(locked=False)
    assert can_resize(node) is True


def run_all_tests():
    tests = [
        locked_node_cannot_move,
        locked_node_cannot_resize,
        unlocked_node_can_move,
        unlocked_node_can_resize,
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
