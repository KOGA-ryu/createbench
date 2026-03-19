from __future__ import annotations

from copy import deepcopy
import json

from checklist.checklist_engine import ChecklistEngine
from export.dsl_builder import DSLBuilder
from export.dsl_builder import DSL_VERSION


def save_project(layout_model, filepath):
    builder = DSLBuilder(
        layout_model,
        layout_model.registry,
        ChecklistEngine(layout_model, layout_model.registry),
    )
    data = builder.build_json(mode="expanded")
    with open(filepath, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "version": DSL_VERSION,
                "scene_metadata": dict(getattr(layout_model, "scene_metadata", {})),
                "closed_bench_sessions": deepcopy(
                    getattr(layout_model, "closed_bench_sessions", [])
                ),
                "data": data,
            },
            handle,
            indent=2,
        )


def _next_bench_session_id(layout_model, seed: str) -> str:
    base = f"{layout_model.BENCH_SESSION_PREFIX}{seed}"
    existing = set(layout_model.get_bench_session_ids()) | set(
        layout_model.get_recently_closed_bench_session_ids()
    )
    if base not in existing:
        return base
    index = 2
    while f"{base}_{index}" in existing:
        index += 1
    return f"{base}_{index}"


def _load_project_payload(layout_model, payload: dict, destination: str) -> list[str]:
    if payload.get("version") != DSL_VERSION:
        raise ValueError(f"Unsupported project version: {payload.get('version')}")
    data = payload["data"]
    created_root_ids: list[str] = []

    def build(node_dict, parent_id, *, restore_ids: bool, bench_session_id: str | None = None):
        node = layout_model.create_node(
            node_dict["type"],
            node_dict.get("properties", {}),
            restored_id=node_dict.get("id") if restore_ids else None,
            metadata=deepcopy(node_dict.get("metadata")),
        )
        if not restore_ids:
            metadata = deepcopy(getattr(node, "metadata", {}) or {})
            provenance = dict(metadata.get("provenance", {}) or {})
            provenance["project_node_id"] = node_dict.get("id")
            if bench_session_id is not None:
                metadata["bench_session_id"] = bench_session_id
                provenance["fork_destination"] = "bench"
            metadata["provenance"] = provenance
            node.metadata = metadata
        layout_model.add_node(parent_id, node)
        for child in node_dict.get("children", []):
            build(
                child,
                node.id,
                restore_ids=restore_ids,
                bench_session_id=bench_session_id,
            )
        return node.id

    with layout_model.batch_updates():
        if destination == "replace":
            layout_model.set_scene_metadata(dict(payload.get("scene_metadata", {})))
            layout_model.closed_bench_sessions = deepcopy(
                payload.get("closed_bench_sessions", [])
            )
            for child in list(layout_model.get_children(layout_model.root_id)):
                layout_model.remove_node(child.id)
            layout_model.type_counters = {}
            if "type" in data:
                created_root_ids.append(build(data, layout_model.root_id, restore_ids=True))
            else:
                for child in data.get("children", []):
                    created_root_ids.append(build(child, layout_model.root_id, restore_ids=True))
            layout_model.sync_active_bench_session()
        elif destination == "alongside":
            if "type" in data:
                created_root_ids.append(build(data, layout_model.root_id, restore_ids=False))
            else:
                for child in data.get("children", []):
                    created_root_ids.append(build(child, layout_model.root_id, restore_ids=False))
        elif destination == "bench":
            workspace = layout_model.ensure_bench_workspace()
            seed = data.get("id") if isinstance(data, dict) and data.get("id") else "project"
            bench_session_id = _next_bench_session_id(layout_model, f"project_{seed}")
            if "type" in data:
                created_root_ids.append(
                    build(
                        data,
                        workspace.id,
                        restore_ids=False,
                        bench_session_id=bench_session_id,
                    )
                )
            else:
                for child in data.get("children", []):
                    created_root_ids.append(
                        build(
                            child,
                            workspace.id,
                            restore_ids=False,
                            bench_session_id=bench_session_id,
                        )
                    )
            layout_model.set_active_bench_session(bench_session_id)
        else:
            raise ValueError(f"Unsupported project load destination: {destination}")

        layout_model.validate_integrity()

    return created_root_ids


def load_project(layout_model, property_registry, filepath):
    del property_registry
    with open(filepath, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    _load_project_payload(layout_model, payload, destination="replace")


def load_project_alongside(layout_model, property_registry, filepath):
    del property_registry
    with open(filepath, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return _load_project_payload(layout_model, payload, destination="alongside")


def load_project_in_bench(layout_model, property_registry, filepath):
    del property_registry
    with open(filepath, "r", encoding="utf-8") as handle:
        payload = json.load(handle)
    return _load_project_payload(layout_model, payload, destination="bench")
