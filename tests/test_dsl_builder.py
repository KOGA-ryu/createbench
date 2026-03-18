import json
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from checklist.checklist_engine import ChecklistEngine
from core.layout_model import LayoutModel
from export.dsl_builder import DSLBuilder
from inspector.property_registry import PropertyRegistry


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


def make_builder():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    model = LayoutModel(registry)
    checklist = ChecklistEngine(model, registry)
    builder = DSLBuilder(model, registry, checklist)
    return builder, model


def make_builder_with_user_schema(schema_name: str, schema: dict):
    with tempfile.TemporaryDirectory() as tmp:
        user_dir = Path(tmp)
        (user_dir / schema_name).write_text(json.dumps(schema, indent=2), encoding="utf-8")
        registry = PropertyRegistry(str(CORE_SCHEMAS), str(user_dir))
        model = LayoutModel(registry)
        checklist = ChecklistEngine(model, registry)
        builder = DSLBuilder(model, registry, checklist)
        return builder, model


def setup_basic_document():
    builder, model = make_builder()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save"})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    return builder, model, document, button


def export_blocked_on_error():
    builder, model = make_builder()
    document = model.create_node("document", {})
    button = model.create_node("button", {})
    button.properties.pop("text", None)
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    try:
        builder.build_json()
        raise AssertionError("Expected export to be blocked")
    except Exception as exc:
        assert str(exc) == "Export blocked: checklist errors present"


def json_export_structure():
    builder, _model, document, button = setup_basic_document()
    exported = builder.build_json()
    assert exported["id"] == document.id
    assert exported["type"] == "document"
    assert exported["children"][0]["id"] == button.id
    assert exported["children"][0]["type"] == "button"


def json_expanded_vs_explicit():
    builder, model = make_builder()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)

    expanded = builder.build_json(mode="expanded")
    explicit = builder.build_json(mode="explicit")
    expanded_props = expanded["children"][0]["properties"]
    explicit_props = explicit["children"][0]["properties"]

    assert "title" in expanded_props
    assert "width" in expanded_props
    assert explicit_props == {}


def dsl_format_structure():
    builder, _model, document, button = setup_basic_document()
    dsl = builder.build_dsl()
    assert f"node document id={document.id}" in dsl
    assert f"  node button id={button.id}" in dsl
    assert '    prop text = "Save"' in dsl


def dsl_unknown_block():
    builder, model = make_builder()
    document = model.create_node("document", {})
    button = model.create_node("button", {"text": "Save", "custom_flag": True})
    model.add_node(model.root_id, document)
    model.add_node(document.id, button)

    dsl = builder.build_dsl()
    assert "unknown:" in dsl
    assert "custom_flag = true" in dsl


def property_sorting():
    builder, model = make_builder()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {"title": "A", "height": 111, "width": 222})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)

    dsl = builder.build_dsl()
    height_index = dsl.index("prop height")
    title_index = dsl.index("prop title")
    width_index = dsl.index("prop width")
    assert height_index < title_index < width_index


def deterministic_output():
    builder, _model, _document, _button = setup_basic_document()
    first = builder.build_dsl()
    second = builder.build_dsl()
    assert first == second


def reference_format():
    builder, model = make_builder_with_user_schema(
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
                    "group": "data",
                    "reference_targets": ["panel"],
                }
            },
        },
    )
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    button = model.create_node("link_button", {"text": "Go", "target": panel.id})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    model.add_node(panel.id, button)

    dsl = builder.build_dsl()
    assert f'prop target = "{panel.id}"' in dsl


def header_present():
    builder, _model, _document, _button = setup_basic_document()
    dsl = builder.build_dsl(mode="explicit")
    assert dsl.startswith("@create_bench v1\n@mode explicit")


def run_all_tests():
    tests = [
        export_blocked_on_error,
        json_export_structure,
        json_expanded_vs_explicit,
        dsl_format_structure,
        dsl_unknown_block,
        property_sorting,
        deterministic_output,
        reference_format,
        header_present,
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
