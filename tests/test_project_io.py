import json
import sys
import tempfile
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from project_io import (
    load_project,
    load_project_alongside,
    load_project_in_bench,
    save_project,
)
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


def save_load_preserves_ids():
    state = make_state()
    document, container, button = build_sample_layout(state)
    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)

        loaded_state = make_state()
        load_project(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath,
        )

        assert loaded_state.layout_model.get_node(document.id) is not None
        assert loaded_state.layout_model.get_node(container.id) is not None
        assert loaded_state.layout_model.get_node(button.id) is not None


def save_load_preserves_parent_child_structure():
    state = make_state()
    document, container, button = build_sample_layout(state)
    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)

        loaded_state = make_state()
        load_project(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath,
        )

        loaded_document = loaded_state.layout_model.get_node(document.id)
        loaded_container = loaded_state.layout_model.get_node(container.id)
        loaded_button = loaded_state.layout_model.get_node(button.id)
        assert loaded_document is not None
        assert loaded_container is not None
        assert loaded_button is not None
        assert loaded_container.parent_id == loaded_document.id
        assert loaded_button.parent_id == loaded_container.id
        assert loaded_document.children == [loaded_container.id]
        assert loaded_container.children == [loaded_button.id]


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


def next_created_id_advances_after_restored_ids():
    state = make_state()
    document = state.layout_model.create_node("document", {})
    state.layout_model.add_node(state.layout_model.root_id, document)
    for index in range(7):
        button = state.layout_model.create_node("button", {"text": f"Button {index}"})
        state.layout_model.add_node(document.id, button)

    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)

        loaded_state = make_state()
        load_project(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath,
        )

        next_button = loaded_state.layout_model.create_node("button", {"text": "Next"})
        assert next_button.id == "button_8"


def export_after_reload_preserves_ids():
    state = make_state()
    document, container, button = build_sample_layout(state)
    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)

        loaded_state = make_state()
        load_project(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath,
        )
        save_project(loaded_state.layout_model, filepath)

        payload = json.loads(filepath.read_text(encoding="utf-8"))
        exported = payload["data"]
        assert exported["id"] == document.id
        assert exported["children"][0]["id"] == container.id
        assert exported["children"][0]["children"][0]["id"] == button.id


def duplicate_restored_id_raises():
    state = make_state()
    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        payload = {
            "version": "v1",
            "data": {
                "id": "document_1",
                "type": "document",
                "properties": {},
                "children": [
                    {
                        "id": "button_1",
                        "type": "button",
                        "properties": {"text": "A"},
                        "children": [],
                    },
                    {
                        "id": "button_1",
                        "type": "button",
                        "properties": {"text": "B"},
                        "children": [],
                    },
                ],
            },
        }
        filepath.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        try:
            load_project(state.layout_model, state.property_registry, filepath)
            raise AssertionError("Expected duplicate restored ID error")
        except ValueError as exc:
            assert str(exc) == "Duplicate node id: button_1"


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


def save_load_preserves_metadata():
    state = make_state()
    document, _container, button = build_sample_layout(state)
    document.metadata = {
        "source": {
            "file": "ui/main_window.py",
            "symbol": "MainWindow",
            "line_start": 10,
            "line_end": 120,
            "source_id": "src_document_1",
        },
        "trust": {
            "trust_level": "partial",
            "representation_origin": "adapter",
            "warnings": ["geometry inferred"],
        },
        "provenance": {
            "representation_origin": "adapter",
            "source_provider": "manual_adapter",
            "source_framework": "pyside6",
            "packet_version": "1",
            "packet_trust_level": "partial",
            "packet_warnings": ["packet partial"],
        },
        "relationships": {
            "communicates_to": [],
            "depends_on": [],
            "updated_by": [],
            "triggered_by": [],
        },
        "raw": {
            "provider_type": "widget",
            "provider_data": {"class_name": "QMainWindow"},
            "unresolved_fields": ["ui_role"],
        },
    }
    button.metadata = {
        "source": {
            "file": "ui/main_window.py",
            "symbol": "save_button",
            "line_start": 42,
            "line_end": 42,
            "source_id": "src_button_1",
        },
        "trust": {
            "trust_level": "source",
            "representation_origin": "source",
            "warnings": [],
        },
        "provenance": {
            "representation_origin": "source",
            "source_provider": "runtime_probe",
            "source_framework": "pyside6",
            "packet_version": "1",
            "packet_trust_level": "source",
            "packet_warnings": [],
        },
        "relationships": {
            "communicates_to": ["dialog_1"],
            "depends_on": [],
            "updated_by": [],
            "triggered_by": [],
        },
        "raw": {
            "provider_type": "button",
            "provider_data": {},
            "unresolved_fields": [],
        },
    }

    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)

        loaded_state = make_state()
        load_project(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath,
        )

        loaded_document = loaded_state.layout_model.get_node(document.id)
        loaded_button = loaded_state.layout_model.get_node(button.id)
        assert loaded_document is not None
        assert loaded_button is not None
        assert loaded_document.metadata["source"]["file"] == "ui/main_window.py"
        assert loaded_document.metadata["trust"]["trust_level"] == "partial"
        assert loaded_button.metadata["source"]["symbol"] == "save_button"
        assert loaded_button.metadata["relationships"]["communicates_to"] == ["dialog_1"]


def save_load_preserves_scene_metadata():
    state = make_state()
    build_sample_layout(state)
    state.layout_model.scene_metadata = {
        "packet_version": "1",
        "source_framework": "pyside6",
        "source_provider": "manual_adapter",
        "packet_trust_level": "partial",
        "packet_warnings": ["packet partial"],
        "representation_origin": "adapter",
    }
    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)

        loaded_state = make_state()
        load_project(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath,
        )

        assert loaded_state.layout_model.scene_metadata["source_provider"] == "manual_adapter"
        assert loaded_state.layout_model.scene_metadata["packet_trust_level"] == "partial"
        assert loaded_state.layout_model.scene_metadata["packet_warnings"] == ["packet partial"]


def save_load_preserves_closed_bench_sessions():
    state = make_state()
    document, _container, button = build_sample_layout(state)
    state.layout_model.scene_metadata = {
        "representation_origin": "adapter",
        "packet_trust_level": "partial",
    }
    state.layout_model.closed_bench_sessions = [
        {
            "bench_session_id": "bench_button_1",
            "roots": [
                {
                    "type": "button",
                    "name": button.name,
                    "properties": {"text": "Bench Save", "layout_mode": "free", "x": 48, "y": 64},
                    "metadata": {
                        "origin_node_id": button.id,
                        "bench_session_id": "bench_button_1",
                        "trust": {
                            "trust_level": "partial",
                            "representation_origin": "adapter",
                            "warnings": [],
                        },
                        "provenance": {
                            "representation_origin": "adapter",
                            "forked_from_origin": button.id,
                            "fork_destination": "bench",
                        },
                    },
                    "children": [],
                }
            ],
        }
    ]

    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)

        loaded_state = make_state()
        load_project(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath,
        )

        assert loaded_state.layout_model.closed_bench_sessions == state.layout_model.closed_bench_sessions
        assert loaded_state.layout_model.get_recently_closed_bench_session_ids() == [
            "bench_button_1"
        ]


def load_clears_stale_active_bench_session():
    state = make_state()
    build_sample_layout(state)
    state.layout_model.scene_metadata = {
        "representation_origin": "adapter",
        "packet_trust_level": "partial",
        "active_bench_session_id": "bench_missing",
    }
    state.layout_model.closed_bench_sessions = [
        {
            "bench_session_id": "bench_missing",
            "roots": [],
        }
    ]

    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(state.layout_model, filepath)

        loaded_state = make_state()
        load_project(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath,
        )

        assert loaded_state.layout_model.get_active_bench_session_id() is None
        assert loaded_state.layout_model.get_recently_closed_bench_session_ids() == [
            "bench_missing"
        ]


def load_project_alongside_preserves_existing_scene():
    source_state = make_state()
    document, _container, _button = build_sample_layout(source_state)
    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(source_state.layout_model, filepath)

        loaded_state = make_state()
        existing_document = loaded_state.layout_model.create_node("document", {})
        existing = loaded_state.layout_model.create_node("panel", {"layout_mode": "free"})
        loaded_state.layout_model.add_node(loaded_state.layout_model.root_id, existing_document)
        loaded_state.layout_model.add_node(loaded_state.layout_model.root_id, existing)

        created_root_ids = load_project_alongside(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath,
        )

        assert loaded_state.layout_model.get_node(existing.id) is not None
        assert created_root_ids
        imported_root = loaded_state.layout_model.get_node(created_root_ids[0])
        assert imported_root is not None
        assert imported_root.id != document.id
        assert imported_root.metadata["provenance"]["project_node_id"] == document.id


def load_project_in_bench_creates_bench_projection():
    source_state = make_state()
    document, _container, _button = build_sample_layout(source_state)
    with tempfile.TemporaryDirectory() as tmp:
        filepath = Path(tmp) / "project.json"
        save_project(source_state.layout_model, filepath)

        loaded_state = make_state()
        created_root_ids = load_project_in_bench(
            loaded_state.layout_model,
            loaded_state.property_registry,
            filepath,
        )

        assert created_root_ids
        bench_root = loaded_state.layout_model.get_node(created_root_ids[0])
        assert bench_root is not None
        assert bench_root.metadata["provenance"]["project_node_id"] == document.id
        assert bench_root.metadata["bench_session_id"].startswith(
            loaded_state.layout_model.BENCH_SESSION_PREFIX
        )
        assert (
            loaded_state.layout_model.get_active_bench_session_id()
            == bench_root.metadata["bench_session_id"]
        )
        workspace = loaded_state.layout_model.ensure_bench_workspace()
        assert bench_root.parent_id == workspace.id


def run_all_tests():
    tests = [
        save_creates_file,
        load_recreates_structure,
        save_load_preserves_ids,
        save_load_preserves_parent_child_structure,
        roundtrip_consistency,
        next_created_id_advances_after_restored_ids,
        export_after_reload_preserves_ids,
        duplicate_restored_id_raises,
        version_written,
        version_respected_on_load,
        save_load_preserves_metadata,
        save_load_preserves_scene_metadata,
        save_load_preserves_closed_bench_sessions,
        load_clears_stale_active_bench_session,
        load_project_alongside_preserves_existing_scene,
        load_project_in_bench_creates_bench_projection,
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
