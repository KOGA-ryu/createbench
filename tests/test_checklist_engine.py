import json
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from checklist.checklist_engine import ChecklistEngine
from core.layout_model import LayoutModel
from core.node import Node
from inspector.property_registry import PropertyRegistry


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


def write_schema(directory: Path, name: str, schema: dict) -> None:
    (directory / name).write_text(json.dumps(schema, indent=2), encoding="utf-8")


def make_engine(user_dir: Path | None = None):
    registry = PropertyRegistry(str(CORE_SCHEMAS), str(user_dir) if user_dir else None)
    model = LayoutModel(registry)
    return ChecklistEngine(model, registry), model


def issue_codes(result):
    return [issue["code"] for issue in result["issues"]]


def missing_required_property_detected():
    engine, model = make_engine()
    document = model.create_node("document", {})
    button = model.create_node("button", {})
    button.properties.pop("text", None)
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    result = engine.run()
    assert "missing_required_property" in issue_codes(result)


def invalid_type_detected():
    engine, model = make_engine()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": 123})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    result = engine.run()
    assert "invalid_property_type" in issue_codes(result)


def constraint_violation_detected():
    with tempfile.TemporaryDirectory() as tmp:
        user_dir = Path(tmp)
        write_schema(
            user_dir,
            "limited_panel.json",
            {
                "type": "limited_panel",
                "version": 1,
                "display_name": "Limited Panel",
                "category": "region",
                "extends": "panel",
                "layout": True,
                "allowed_children": ["@component"],
                "properties": {
                    "width": {"type": "int", "default": 50, "group": "layout", "min": 100}
                },
            },
        )
        engine, model = make_engine(user_dir)
        document = model.create_node("document", {})
        panel = model.create_node("limited_panel", {"width": 50})
        model.add_node(model.root_id, document)
        model.add_node(document.id, panel)

        result = engine.run()
        assert "constraint_min" in issue_codes(result)


def invalid_child_detected():
    with tempfile.TemporaryDirectory() as tmp:
        user_dir = Path(tmp)
        write_schema(
            user_dir,
            "strict_panel.json",
            {
                "type": "strict_panel",
                "version": 1,
                "display_name": "Strict Panel",
                "category": "region",
                "extends": "panel",
                "layout": True,
                "allowed_children": ["button"],
                "properties": {},
            },
        )
        engine, model = make_engine(user_dir)
        document = model.create_node("document", {})
        panel = model.create_node("strict_panel", {})
        text = model.create_node("text", {})
        model.add_node(model.root_id, document)
        model.add_node(document.id, panel)
        model.add_node(panel.id, text)

        result = engine.run()
        assert "invalid_child_type" in issue_codes(result)


def unknown_property_warning():
    engine, model = make_engine()
    document = model.create_node("document", {})
    button = model.create_node("button", {"custom_flag": True})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    result = engine.run()
    assert "unknown_property" in issue_codes(result)


def excessive_depth_warning():
    engine, model = make_engine()
    current_parent = model.create_node("document", {})
    model.add_node(model.root_id, current_parent)
    deepest = current_parent

    for _ in range(11):
        child = model.create_node("container", {})
        model.add_node(deepest.id, child)
        deepest = child

    result = engine.run()
    assert "excessive_nesting" in issue_codes(result)


def missing_schema_warning():
    engine, model = make_engine()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)

    unknown = Node(id="custom_1", type="custom", properties={}, parent_id=document.id)
    model.add_node(document.id, unknown)

    result = engine.run()
    assert "missing_schema" in issue_codes(result)


def summary_counts_correct():
    engine, model = make_engine()
    document = model.create_node("document", {})
    button = model.create_node("button", {"custom_flag": True})
    button.properties.pop("text", None)
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    result = engine.run()
    assert result["summary"]["errors"] == 1
    assert result["summary"]["warnings"] == 1
    assert result["summary"]["info"] == 0


def filter_by_node():
    engine, model = make_engine()
    document = model.create_node("document", {})
    button = model.create_node("button", {"custom_flag": True})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    engine.run()
    issues = engine.filter_by_node(button.id)
    assert issues
    assert all(issue["node_id"] == button.id for issue in issues)


def run_all_tests():
    tests = [
        missing_required_property_detected,
        invalid_type_detected,
        constraint_violation_detected,
        invalid_child_detected,
        unknown_property_warning,
        excessive_depth_warning,
        missing_schema_warning,
        summary_counts_correct,
        filter_by_node,
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
