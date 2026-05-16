from __future__ import annotations

from copy import deepcopy

from core.bench_workspace import ensure_bench_workspace, find_bench_workspace


def get_active_bench_session_id(api) -> str | None:
    active = api.get_scene_metadata().get("active_bench_session_id")
    return None if active is None else str(active)


def set_active_bench_session(api, bench_session_id: str | None) -> None:
    metadata = dict(api.get_scene_metadata())
    if bench_session_id is None:
        metadata.pop("active_bench_session_id", None)
    else:
        metadata["active_bench_session_id"] = str(bench_session_id)
    api.set_scene_metadata(metadata)


def clear_active_bench_session(api) -> None:
    set_active_bench_session(api, None)


def sync_active_bench_session(api) -> None:
    active_bench_session_id = get_active_bench_session_id(api)
    if active_bench_session_id is None:
        return
    if active_bench_session_id in get_bench_session_ids(api):
        return
    metadata = dict(api.get_scene_metadata())
    if "active_bench_session_id" not in metadata:
        return
    metadata.pop("active_bench_session_id", None)
    api.replace_scene_metadata_and_notify(metadata)


def get_bench_session_ids(api) -> list[str]:
    session_ids: set[str] = set()
    for node in api.iter_nodes():
        metadata = getattr(node, "metadata", {}) or {}
        bench_session_id = metadata.get("bench_session_id")
        if bench_session_id:
            session_ids.add(str(bench_session_id))
    return sorted(session_ids)


def get_recently_closed_bench_session_ids(api) -> list[str]:
    return [str(entry["bench_session_id"]) for entry in api.get_closed_bench_sessions()]


def close_bench_session(api, bench_session_id: str) -> list[str]:
    deleted: list[str] = []
    with api.batch_updates():
        roots_to_capture: list[str] = []
        for node in api.iter_nodes():
            if node.id == api.get_root_id():
                continue
            metadata = getattr(node, "metadata", {}) or {}
            if str(metadata.get("bench_session_id") or "") != str(bench_session_id):
                continue
            parent = api.get_parent(node.id)
            parent_session_id = None if parent is None else ((getattr(parent, "metadata", {}) or {}).get("bench_session_id"))
            if str(parent_session_id or "") != str(bench_session_id):
                roots_to_capture.append(node.id)
        if roots_to_capture:
            api.set_closed_bench_sessions([
                entry for entry in api.get_closed_bench_sessions()
                if str(entry["bench_session_id"]) != str(bench_session_id)
            ])
            api.get_closed_bench_sessions().insert(
                0,
                {
                    "bench_session_id": str(bench_session_id),
                    "roots": [api.serialize_subtree(node_id) for node_id in roots_to_capture if api.get_node(node_id) is not None],
                },
            )
        for node in api.iter_nodes():
            if node.id == api.get_root_id():
                continue
            metadata = getattr(node, "metadata", {}) or {}
            if str(metadata.get("bench_session_id") or "") != str(bench_session_id):
                continue
            if node.parent_id is None:
                continue
            if api.get_node(node.id) is None:
                continue
            deleted.extend(api.remove_node(node.id))

        if get_active_bench_session_id(api) == str(bench_session_id):
            clear_active_bench_session(api)

        workspace = find_bench_workspace(api)
        if workspace is not None and not workspace.children:
            deleted.extend(api.remove_node(workspace.id))

    return deleted


def reopen_closed_bench_session(api, bench_session_id: str) -> list[str]:
    restored_roots: list[str] = []
    entry = next(
        (entry for entry in api.get_closed_bench_sessions() if str(entry["bench_session_id"]) == str(bench_session_id)),
        None,
    )
    if entry is None:
        return restored_roots

    workspace = ensure_bench_workspace(api)

    def build(snapshot: dict[str, object], parent_id: str) -> str:
        node = api.create_node(
            str(snapshot["type"]),
            deepcopy(snapshot.get("properties", {})),
            name=snapshot.get("name"),
            metadata=deepcopy(snapshot.get("metadata", {})),
        )
        api.add_node(parent_id, node)
        for child_snapshot in snapshot.get("children", []):
            build(child_snapshot, node.id)
        return node.id

    with api.batch_updates():
        for root_snapshot in entry.get("roots", []):
            restored_roots.append(build(root_snapshot, workspace.id))
        set_active_bench_session(api, str(bench_session_id))
        api.set_closed_bench_sessions([
            existing for existing in api.get_closed_bench_sessions()
            if str(existing["bench_session_id"]) != str(bench_session_id)
        ])

    return restored_roots
