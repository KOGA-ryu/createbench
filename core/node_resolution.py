from __future__ import annotations


def resolve_node_state(node, scene_metadata: dict | None = None) -> dict[str, object]:
    scene_metadata = scene_metadata or {}
    metadata = getattr(node, "metadata", {}) or {}
    trust = metadata.get("trust", {}) or {}
    provenance = metadata.get("provenance", {}) or {}

    trust_level = (
        trust.get("trust_level")
        or scene_metadata.get("packet_trust_level")
        or scene_metadata.get("trust_level")
        or "mock"
    )
    origin = (
        provenance.get("representation_origin")
        or trust.get("representation_origin")
        or scene_metadata.get("representation_origin")
        or scene_metadata.get("source_provider")
        or "manual"
    )
    bench_session_id = metadata.get("bench_session_id") or scene_metadata.get("bench_session_id")
    origin_node_id = metadata.get("origin_node_id") or scene_metadata.get("origin_node_id")

    if bench_session_id:
        resolved_mode = "bench"
    elif origin in {"source", "adapter"}:
        resolved_mode = "source"
    else:
        resolved_mode = "design"

    if bool(node.properties.get("locked")):
        editability = "locked"
        reason = "Node is locked"
    elif resolved_mode == "bench":
        editability = "editable"
        reason = ""
    elif resolved_mode == "source":
        editability = "forkable"
        reason = "Source-backed or adapter-backed node requires fork/bench before editing"
    elif resolved_mode == "design":
        editability = "editable"
        reason = ""
    else:
        editability = "inspect_only"
        reason = "Node mode could not be resolved safely"

    return {
        "resolved_mode": resolved_mode,
        "editability": editability,
        "trust_level": trust_level,
        "origin": origin,
        "reason": reason,
        "origin_node_id": origin_node_id,
        "bench_session_id": bench_session_id,
    }
