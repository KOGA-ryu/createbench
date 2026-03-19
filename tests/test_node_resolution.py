import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.node import Node
from core.node_resolution import resolve_node_state


def design_node_defaults_to_editable():
    node = Node(id="button_1", type="button", properties={"text": "Save"})
    resolved = resolve_node_state(node)
    assert resolved["resolved_mode"] == "design"
    assert resolved["editability"] == "editable"
    assert resolved["trust_level"] == "mock"
    assert resolved["origin"] == "manual"


def source_node_resolves_forkable():
    node = Node(
        id="button_1",
        type="button",
        properties={"text": "Save"},
        metadata={
            "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
            "provenance": {"representation_origin": "adapter"},
        },
    )
    resolved = resolve_node_state(node)
    assert resolved["resolved_mode"] == "source"
    assert resolved["editability"] == "forkable"
    assert resolved["reason"] == "Source-backed or adapter-backed node requires fork/bench before editing"


def locked_node_resolves_locked():
    node = Node(id="button_1", type="button", properties={"locked": True})
    resolved = resolve_node_state(node)
    assert resolved["editability"] == "locked"
    assert resolved["reason"] == "Node is locked"


def bench_session_resolves_bench_mode():
    node = Node(
        id="button_1",
        type="button",
        properties={},
        metadata={"bench_session_id": "bench_1", "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []}},
    )
    resolved = resolve_node_state(node)
    assert resolved["resolved_mode"] == "bench"
    assert resolved["editability"] == "editable"
    assert resolved["bench_session_id"] == "bench_1"


def scene_metadata_backfills_origin_and_trust():
    node = Node(id="panel_1", type="panel", properties={})
    resolved = resolve_node_state(
        node,
        {
            "representation_origin": "adapter",
            "source_provider": "manual_adapter",
            "packet_trust_level": "partial",
        },
    )
    assert resolved["resolved_mode"] == "source"
    assert resolved["editability"] == "forkable"
    assert resolved["trust_level"] == "partial"
    assert resolved["origin"] == "adapter"


def run_all_tests():
    tests = [
        design_node_defaults_to_editable,
        source_node_resolves_forkable,
        locked_node_resolves_locked,
        bench_session_resolves_bench_mode,
        scene_metadata_backfills_origin_and_trust,
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
