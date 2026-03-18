import json
import io
import sys
import tempfile
from contextlib import redirect_stdout
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from inspector.property_registry import PropertyRegistry, SchemaError


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


def write_schema(directory: Path, name: str, schema: dict) -> None:
    (directory / name).write_text(json.dumps(schema, indent=2), encoding="utf-8")


def make_registry(user_dir: Path | None = None) -> PropertyRegistry:
    return PropertyRegistry(str(CORE_SCHEMAS), str(user_dir) if user_dir else None)


def capture_output(func):
    buf = io.StringIO()
    with redirect_stdout(buf):
        func()
    return buf.getvalue()


def test_load_core_schemas():
    registry = make_registry()
    expected = {"document", "container", "vertical", "horizontal", "button", "text", "input"}
    assert expected.issubset(set(registry.resolved_schemas))


def test_inheritance_merge():
    registry = make_registry()
    vertical = registry.get_schema("vertical")
    horizontal = registry.get_schema("horizontal")

    for schema in (vertical, horizontal):
        assert schema["extends"] == "container"
        assert "width" in schema["properties"]
        assert "height" in schema["properties"]


def test_property_removal():
    with tempfile.TemporaryDirectory() as tmp:
        user_dir = Path(tmp)
        write_schema(
            user_dir,
            "compact_panel.json",
            {
                "type": "compact_panel",
                "version": 1,
                "display_name": "Compact Panel",
                "category": "region",
                "extends": "container",
                "layout": True,
                "allowed_children": ["@component"],
                "remove": {"properties": ["height"]},
                "properties": {
                    "title": {
                        "type": "string",
                        "default": "Compact",
                        "group": "content",
                    }
                },
            },
        )

        registry = make_registry(user_dir)
        schema = registry.get_schema("compact_panel")
        assert "width" in schema["properties"]
        assert "height" not in schema["properties"]


def test_category_expansion():
    registry = make_registry()
    resolved = registry.get_schema("container")["allowed_children_resolved"]

    assert "button" in resolved
    assert "vertical" in resolved
    assert resolved == sorted(resolved)
    assert len(resolved) == len(set(resolved))


def test_reference_target_expansion():
    with tempfile.TemporaryDirectory() as tmp:
        user_dir = Path(tmp)
        write_schema(
            user_dir,
            "link_button.json",
            {
                "type": "link_button",
                "version": 1,
                "display_name": "Link Button",
                "category": "component",
                "extends": "button",
                "layout": False,
                "allowed_children": [],
                "properties": {
                    "target": {
                        "type": "reference",
                        "required": False,
                        "group": "data",
                        "reference_targets": ["@region", "button"],
                    }
                },
            },
        )

        registry = make_registry(user_dir)
        targets = registry.get_schema("link_button")["properties"]["target"][
            "reference_targets_resolved"
        ]
        assert targets == sorted(targets)
        assert "button" in targets
        assert "panel" in targets
        assert "main" in targets


def test_enum_validation_failure():
    with tempfile.TemporaryDirectory() as tmp:
        user_dir = Path(tmp)
        write_schema(
            user_dir,
            "bad_enum.json",
            {
                "type": "bad_enum",
                "version": 1,
                "display_name": "Bad Enum",
                "category": "component",
                "layout": False,
                "allowed_children": [],
                "properties": {
                    "mode": {
                        "type": "enum",
                        "group": "behavior",
                    }
                },
            },
        )

        registry = make_registry(user_dir)
        assert not registry.has_schema("bad_enum")
        assert "bad_enum.json" in registry.user_schema_errors
        assert "enum requires 'allowed_values'" in registry.user_schema_errors["bad_enum.json"]


def test_regex_and_allowed_values_conflict():
    with tempfile.TemporaryDirectory() as tmp:
        user_dir = Path(tmp)
        write_schema(
            user_dir,
            "bad_conflict.json",
            {
                "type": "bad_conflict",
                "version": 1,
                "display_name": "Bad Conflict",
                "category": "component",
                "layout": False,
                "allowed_children": [],
                "properties": {
                    "mode": {
                        "type": "string",
                        "group": "behavior",
                        "allowed_values": ["a", "b"],
                        "regex": "^[ab]$",
                    }
                },
            },
        )

        registry = make_registry(user_dir)
        assert not registry.has_schema("bad_conflict")
        assert "bad_conflict.json" in registry.user_schema_errors
        assert (
            "cannot define both 'allowed_values' and 'regex'"
            in registry.user_schema_errors["bad_conflict.json"]
        )


def test_default_injection():
    registry = make_registry()
    props = registry.apply_defaults("button", {})
    assert props["text"] == "Button"


def test_unknown_property_preserved():
    registry = make_registry()
    props = registry.apply_defaults("button", {"custom_flag": True})
    assert props["text"] == "Button"
    assert props["custom_flag"] is True


def test_duplicate_schema_without_override():
    with tempfile.TemporaryDirectory() as tmp:
        user_dir = Path(tmp)
        write_schema(
            user_dir,
            "button.json",
            {
                "type": "button",
                "version": 1,
                "display_name": "Button Override",
                "category": "component",
                "layout": False,
                "allowed_children": [],
                "properties": {},
            },
        )

        registry = make_registry(user_dir)
        assert registry.has_schema("button")
        assert "button.json" in registry.user_schema_errors
        assert (
            "duplicate schema 'button' without override=true"
            in registry.user_schema_errors["button.json"]
        )


def test_core_schema_failure_hard():
    with tempfile.TemporaryDirectory() as tmp:
        core_dir = Path(tmp)
        write_schema(
            core_dir,
            "bad_core.json",
            {
                "type": "bad_core",
                "version": 1,
                "display_name": "Bad Core",
                "category": "component",
                "layout": False,
                "allowed_children": [],
                "properties": {
                    "mode": {
                        "type": "enum",
                        "group": "behavior",
                    }
                },
            },
        )

        try:
            PropertyRegistry(str(core_dir))
            raise AssertionError("Expected SchemaError")
        except SchemaError:
            pass


def run_all_tests():
    tests = [
        test_load_core_schemas,
        test_inheritance_merge,
        test_property_removal,
        test_category_expansion,
        test_reference_target_expansion,
        test_enum_validation_failure,
        test_regex_and_allowed_values_conflict,
        test_default_injection,
        test_unknown_property_preserved,
        test_duplicate_schema_without_override,
        test_core_schema_failure_hard,
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
