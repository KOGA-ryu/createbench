import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.scene_resolution import resolve_scene_state


def design_scene_defaults():
    resolved = resolve_scene_state({})
    assert resolved["resolved_mode"] == "design"
    assert resolved["origin"] == "manual"
    assert resolved["trust_level"] == "mock"


def source_scene_from_adapter_metadata():
    resolved = resolve_scene_state(
        {
            "representation_origin": "adapter",
            "source_provider": "bluebench",
            "source_framework": "pyside6",
            "packet_trust_level": "partial",
            "packet_version": "1",
        }
    )
    assert resolved["resolved_mode"] == "source"
    assert resolved["origin"] == "adapter"
    assert resolved["trust_level"] == "partial"
    assert resolved["source_provider"] == "bluebench"
    assert resolved["source_framework"] == "pyside6"
    assert resolved["packet_version"] == "1"


def bench_scene_wins_mode():
    resolved = resolve_scene_state(
        {
            "representation_origin": "adapter",
            "packet_trust_level": "partial",
            "bench_session_id": "bench_1",
            "active_bench_session_id": "bench_1",
        }
    )
    assert resolved["resolved_mode"] == "bench"
    assert resolved["active_bench_session_id"] == "bench_1"


def run_all_tests():
    tests = [
        design_scene_defaults,
        source_scene_from_adapter_metadata,
        bench_scene_wins_mode,
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
