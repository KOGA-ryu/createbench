import json
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_io import load_project, save_project
from state.app_state import AppState


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


def make_state():
    return AppState(str(CORE_SCHEMAS))


def build_sample_layout(state):
    document = state.layout_model.create_node("document", {})
    container = state.layout_model.create_node("container", {})
    button = state.layout_model.create_node("button", {"text": "Save"})
    state.layout_model.add_node(state.layout_model.root_id, document)
    state.layout_model.add_node(document.id, container)
    state.layout_model.add_node(container.id, button)
    return document, container, button


def save_creates_file():
    state = make_state()
    build_sample_layout(state)
    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)
        assert filepath.exists()
        assert filepath.read_text(encoding="utf-8")


def load_recreates_structure():
    state = make_state()
    build_sample_layout(state)
    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)

        loaded_state = make_state()
        load_project(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath,
        )

        root_children = loaded_state.layout_model.get_children(
            loaded_state.layout_model.root_id
        )
        assert len(root_children) == 1
        assert root_children[0].type == "document"
        document_children = loaded_state.layout_model.get_children(root_children[0].id)
        assert [child.type for child in document_children] == ["container"]
        container_children = loaded_state.layout_model.get_children(document_children[0].id)
        assert [child.type for child in container_children] == ["button"]


def roundtrip_consistency():
    state = make_state()
    build_sample_layout(state)
    with tempfile.TemporaryDirectory() as tmp:
        filepath_a = Path(tmp) / "project_a.json"
        filepath_b = Path(tmp) / "project_b.json"
        save_project(state.layout_model, filepath_a)

        loaded_state = make_state()
        load_project(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath_a,
        )
        save_project(loaded_state.layout_model, filepath_b)

        data_a = json.loads(filepath_a.read_text(encoding="utf-8"))
        data_b = json.loads(filepath_b.read_text(encoding="utf-8"))
        assert data_a == data_b


def version_written():
    state = make_state()
    build_sample_layout(state)
    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)
        payload = json.loads(filepath.read_text(encoding="utf-8"))
        assert payload["version"] == "v1"
        assert "data" in payload


def version_respected_on_load():
    state = make_state()
    build_sample_layout(state)
    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)
        payload = json.loads(filepath.read_text(encoding="utf-8"))
        payload["version"] = "v999"
        filepath.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            load_project(state.layout_model, state.property_registry, filepath)
            raise AssertionError("Expected version error")
        except ValueError as exc:
            assert str(exc) == "Unsupported project version: v999"


def run_all_tests():
    tests = [
        save_creates_file,
        load_recreates_structure,
        roundtrip_consistency,
        version_written,
        version_respected_on_load,
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
