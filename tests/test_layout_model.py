import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from core.layout_model import LayoutModel
from inspector.property_registry import PropertyRegistry


CORE_SCHEMAS = PROJECT_ROOT / "schemas" / "core"


def make_model():
    registry = PropertyRegistry(str(CORE_SCHEMAS))
    return LayoutModel(registry)


def create_node_applies_defaults():
    model = make_model()
    node = model.create_node("button", {})
    assert node.id == "button_1"
    assert node.properties["text"] == "Button"
    assert model.get_node(node.id) is node


def add_node_basic():
    model = make_model()
    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    button = model.create_node("button", {})
    model.add_node(document.id, button)

    assert document.parent_id == "root"
    assert button.parent_id == document.id
    assert model.get_children(document.id)[0].id == button.id


def remove_node_cascade():
    model = make_model()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    button = model.create_node("button", {})

    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    model.add_node(panel.id, button)

    deleted = model.remove_node(panel.id)
    assert deleted == [button.id, panel.id]
    assert model.get_node(panel.id) is None
    assert model.get_node(button.id) is None
    assert document.children == []


def move_node_basic():
    model = make_model()
    document = model.create_node("document", {})
    panel_a = model.create_node("panel", {})
    panel_b = model.create_node("panel", {})
    button = model.create_node("button", {})

    model.add_node(model.root_id, document)
    model.add_node(document.id, panel_a)
    model.add_node(document.id, panel_b)
    model.add_node(panel_a.id, button)

    model.move_node(button.id, panel_b.id)
    assert button.parent_id == panel_b.id
    assert panel_a.children == []
    assert panel_b.children == [button.id]


def prevent_cycle():
    model = make_model()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    button = model.create_node("button", {})

    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    model.add_node(panel.id, button)

    try:
        model.move_node(panel.id, button.id)
        raise AssertionError("Expected cycle prevention error")
    except ValueError:
        pass


def reorder_node():
    model = make_model()
    document = model.create_node("document", {})
    button = model.create_node("button", {})
    text = model.create_node("text", {})
    input_node = model.create_node("input", {})

    model.add_node(model.root_id, document)
    model.add_node(document.id, button)
    model.add_node(document.id, text)
    model.add_node(document.id, input_node)

    model.reorder_node(input_node.id, 0)
    assert document.children == [input_node.id, button.id, text.id]


def root_protection():
    model = make_model()
    try:
        model.remove_node(model.root_id)
        raise AssertionError("Expected root delete protection")
    except ValueError:
        pass

    try:
        model.move_node(model.root_id, model.root_id)
        raise AssertionError("Expected root move protection")
    except ValueError:
        pass


def id_generation_per_type():
    model = make_model()
    button_1 = model.create_node("button", {})
    button_2 = model.create_node("button", {})
    panel_1 = model.create_node("panel", {})

    assert button_1.id == "button_1"
    assert button_2.id == "button_2"
    assert panel_1.id == "panel_1"


def fork_subtree_to_design():
    model = make_model()
    document = model.create_node("document", {})
    panel = model.create_node(
        "panel",
        {"title": "Source Panel", "layout_mode": "free", "x": 100, "y": 140, "width": 240, "height": 180},
    )
    button = model.create_node("button", {"text": "Save", "layout_mode": "free", "x": 124, "y": 176, "width": 80, "height": 32})
    panel.metadata = {
        "source": {"file": "ui/main_window.py", "symbol": "Panel", "line_start": 10, "line_end": 20, "source_id": "src_panel"},
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter", "source_provider": "bluebench"},
        "relationships": {"communicates_to": [], "depends_on": [], "updated_by": [], "triggered_by": []},
        "raw": {"provider_type": "panel", "provider_data": {}, "unresolved_fields": []},
    }
    button.metadata = {
        "source": {"file": "ui/main_window.py", "symbol": "save_button", "line_start": 21, "line_end": 21, "source_id": "src_button"},
        "trust": {"trust_level": "source", "representation_origin": "source", "warnings": []},
        "provenance": {"representation_origin": "source", "source_provider": "runtime_probe"},
        "relationships": {"communicates_to": [], "depends_on": [], "updated_by": [], "triggered_by": []},
        "raw": {"provider_type": "button", "provider_data": {}, "unresolved_fields": []},
    }

    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)
    model.add_node(panel.id, button)

    forked_id = model.fork_subtree_to_design(panel.id)
    assert forked_id is not None
    forked_panel = model.get_node(forked_id)
    assert forked_panel is not None
    assert forked_panel.id != panel.id
    assert forked_panel.parent_id == document.id
    assert document.children == [panel.id, forked_panel.id]
    assert forked_panel.metadata["origin_node_id"] == panel.id
    assert forked_panel.metadata["trust"]["trust_level"] == "partial"
    assert forked_panel.metadata["trust"]["representation_origin"] == "manual"
    assert forked_panel.metadata["provenance"]["representation_origin"] == "manual"
    assert forked_panel.metadata["provenance"]["fork_destination"] == "here"
    assert forked_panel.properties["x"] == panel.properties["x"] + model.FORK_OFFSET
    assert forked_panel.properties["y"] == panel.properties["y"] + model.FORK_OFFSET
    assert len(forked_panel.children) == 1
    forked_button = model.get_node(forked_panel.children[0])
    assert forked_button is not None
    assert forked_button.metadata["origin_node_id"] == button.id
    assert forked_button.properties["text"] == "Save"
    assert forked_button.metadata["provenance"]["fork_destination"] == "here"
    assert forked_button.properties["x"] == button.properties["x"] + model.FORK_OFFSET
    assert forked_button.properties["y"] == button.properties["y"] + model.FORK_OFFSET


def unsupported_fork_destination_fails():
    model = make_model()
    document = model.create_node("document", {})
    panel = model.create_node("panel", {})
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)

    try:
        model.fork_subtree(panel.id, destination="workspace")
        raise AssertionError("Expected unsupported destination failure")
    except ValueError:
        pass


def open_subtree_in_bench_creates_bench_projection():
    model = make_model()
    document = model.create_node("document", {})
    panel = model.create_node(
        "panel",
        {"title": "Source Panel", "layout_mode": "free", "x": 40, "y": 60, "width": 180, "height": 140},
    )
    panel.metadata = {
        "source": {"file": "ui/main_window.py", "symbol": "Panel", "line_start": 10, "line_end": 20, "source_id": "src_panel"},
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter", "source_provider": "bluebench"},
        "relationships": {"communicates_to": [], "depends_on": [], "updated_by": [], "triggered_by": []},
        "raw": {"provider_type": "panel", "provider_data": {}, "unresolved_fields": []},
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, panel)

    bench_id = model.open_subtree_in_bench(panel.id)
    workspace = next(
        child for child in model.get_children(model.root_id)
        if child.type == "panel" and child.properties.get("title") == model.BENCH_WORKSPACE_TITLE
    )
    bench_node = model.get_node(bench_id)
    assert bench_node is not None
    assert bench_node.parent_id == workspace.id
    assert bench_node.metadata["origin_node_id"] == panel.id
    assert bench_node.metadata["bench_session_id"] == f"{model.BENCH_SESSION_PREFIX}{panel.id}"
    assert bench_node.metadata["provenance"]["fork_destination"] == "bench"
    assert bench_node.metadata["provenance"]["representation_origin"] == "adapter"
    assert bench_node.metadata["trust"]["trust_level"] == "partial"
    assert bench_node.properties["x"] == panel.properties["x"] + model.FORK_OFFSET
    assert bench_node.properties["y"] == panel.properties["y"] + model.FORK_OFFSET
    assert model.get_active_bench_session_id() == f"{model.BENCH_SESSION_PREFIX}{panel.id}"


def bench_workspace_is_reused():
    model = make_model()
    document = model.create_node("document", {})
    first = model.create_node("panel", {"layout_mode": "free", "x": 20, "y": 20, "width": 120, "height": 90})
    second = model.create_node("panel", {"layout_mode": "free", "x": 60, "y": 60, "width": 120, "height": 90})
    first.metadata = {
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter"},
    }
    second.metadata = {
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter"},
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, first)
    model.add_node(document.id, second)

    first_bench = model.open_subtree_in_bench(first.id)
    second_bench = model.open_subtree_in_bench(second.id)

    workspaces = [
        child for child in model.get_children(model.root_id)
        if child.type == "panel" and child.properties.get("title") == model.BENCH_WORKSPACE_TITLE
    ]
    assert len(workspaces) == 1
    workspace = workspaces[0]
    assert model.get_node(first_bench).parent_id == workspace.id
    assert model.get_node(second_bench).parent_id == workspace.id
    assert model.get_active_bench_session_id() == f"{model.BENCH_SESSION_PREFIX}{second.id}"


def active_bench_session_can_be_cleared():
    model = make_model()
    model.set_active_bench_session("bench_panel_1")
    assert model.get_active_bench_session_id() == "bench_panel_1"
    model.clear_active_bench_session()
    assert model.get_active_bench_session_id() is None


def bench_session_ids_are_listed_once():
    model = make_model()
    document = model.create_node("document", {})
    first = model.create_node("panel", {})
    second = model.create_node("panel", {})
    first.metadata = {"bench_session_id": "bench_a"}
    second.metadata = {"bench_session_id": "bench_a"}
    model.add_node(model.root_id, document)
    model.add_node(document.id, first)
    model.add_node(document.id, second)

    assert model.get_bench_session_ids() == ["bench_a"]


def close_bench_session_removes_only_that_session_and_empty_workspace():
    model = make_model()
    document = model.create_node("document", {})
    source_panel = model.create_node("panel", {"layout_mode": "free", "x": 20, "y": 20, "width": 120, "height": 90})
    source_panel.metadata = {
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter"},
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, source_panel)

    bench_id = model.open_subtree_in_bench(source_panel.id)
    bench_session_id = model.get_node(bench_id).metadata["bench_session_id"]
    workspace = next(
        child for child in model.get_children(model.root_id)
        if child.type == "panel" and child.properties.get("title") == model.BENCH_WORKSPACE_TITLE
    )

    deleted = model.close_bench_session(bench_session_id)
    assert bench_id in deleted
    assert workspace.id in deleted
    assert model.get_node(bench_id) is None
    assert model.get_node(workspace.id) is None
    assert model.get_node(source_panel.id) is not None
    assert model.get_active_bench_session_id() is None


def close_one_bench_session_keeps_other_session_and_workspace():
    model = make_model()
    document = model.create_node("document", {})
    first = model.create_node("panel", {"layout_mode": "free", "x": 20, "y": 20, "width": 120, "height": 90})
    second = model.create_node("panel", {"layout_mode": "free", "x": 60, "y": 60, "width": 120, "height": 90})
    for node in (first, second):
        node.metadata = {
            "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
            "provenance": {"representation_origin": "adapter"},
        }
    model.add_node(model.root_id, document)
    model.add_node(document.id, first)
    model.add_node(document.id, second)

    first_bench = model.open_subtree_in_bench(first.id)
    second_bench = model.open_subtree_in_bench(second.id)
    first_session = model.get_node(first_bench).metadata["bench_session_id"]

    deleted = model.close_bench_session(first_session)
    assert first_bench in deleted
    assert model.get_node(first_bench) is None
    assert model.get_node(second_bench) is not None
    workspaces = [
        child for child in model.get_children(model.root_id)
        if child.type == "panel" and child.properties.get("title") == model.BENCH_WORKSPACE_TITLE
    ]
    assert len(workspaces) == 1


def closed_bench_session_can_reopen():
    model = make_model()
    document = model.create_node("document", {})
    source_panel = model.create_node("panel", {"layout_mode": "free", "x": 20, "y": 20, "width": 120, "height": 90})
    source_panel.metadata = {
        "trust": {"trust_level": "partial", "representation_origin": "adapter", "warnings": []},
        "provenance": {"representation_origin": "adapter"},
    }
    model.add_node(model.root_id, document)
    model.add_node(document.id, source_panel)

    bench_id = model.open_subtree_in_bench(source_panel.id)
    bench_session_id = model.get_node(bench_id).metadata["bench_session_id"]
    model.close_bench_session(bench_session_id)

    assert model.get_recently_closed_bench_session_ids() == [bench_session_id]
    restored_roots = model.reopen_closed_bench_session(bench_session_id)
    assert len(restored_roots) == 1
    restored = model.get_node(restored_roots[0])
    assert restored is not None
    assert restored.metadata["bench_session_id"] == bench_session_id
    assert restored.metadata["origin_node_id"] == source_panel.id
    assert model.get_active_bench_session_id() == bench_session_id
    assert model.get_recently_closed_bench_session_ids() == []


def model_notifies_subscribers_on_mutation():
    model = make_model()
    notifications: list[str] = []

    model.subscribe(lambda: notifications.append("changed"))

    document = model.create_node("document", {})
    model.add_node(model.root_id, document)
    model.reorder_node(document.id, 0)
    model.set_scene_metadata({"representation_origin": "template"})

    assert len(notifications) >= 3


def batch_updates_coalesce_notifications():
    model = make_model()
    notifications: list[str] = []
    model.subscribe(lambda: notifications.append("changed"))

    with model.batch_updates():
        document = model.create_node("document", {})
        model.add_node(model.root_id, document)
        model.set_scene_metadata({"representation_origin": "template"})

    assert notifications == ["changed"]


def run_all_tests():
    tests = [
        create_node_applies_defaults,
        add_node_basic,
        remove_node_cascade,
        move_node_basic,
        prevent_cycle,
        reorder_node,
        root_protection,
        id_generation_per_type,
        fork_subtree_to_design,
        unsupported_fork_destination_fails,
        open_subtree_in_bench_creates_bench_projection,
        bench_workspace_is_reused,
        active_bench_session_can_be_cleared,
        bench_session_ids_are_listed_once,
        close_bench_session_removes_only_that_session_and_empty_workspace,
        close_one_bench_session_keeps_other_session_and_workspace,
        closed_bench_session_can_reopen,
        model_notifies_subscribers_on_mutation,
        batch_updates_coalesce_notifications,
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
