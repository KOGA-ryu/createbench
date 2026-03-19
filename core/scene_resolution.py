from __future__ import annotations


def resolve_scene_state(scene_metadata: dict | None = None) -> dict[str, object]:
    scene_metadata = scene_metadata or {}
    origin = (
        scene_metadata.get("representation_origin")
        or scene_metadata.get("source_provider")
        or "manual"
    )
    trust_level = (
        scene_metadata.get("packet_trust_level")
        or scene_metadata.get("trust_level")
        or "mock"
    )
    source_provider = scene_metadata.get("source_provider") or "-"
    source_framework = scene_metadata.get("source_framework") or "-"
    packet_version = scene_metadata.get("packet_version") or "-"
    active_bench_session_id = scene_metadata.get("active_bench_session_id")

    if scene_metadata.get("bench_session_id"):
        resolved_mode = "bench"
    elif origin in {"source", "adapter"}:
        resolved_mode = "source"
    else:
        resolved_mode = "design"

    return {
        "resolved_mode": resolved_mode,
        "origin": origin,
        "trust_level": trust_level,
        "source_provider": source_provider,
        "source_framework": source_framework,
        "packet_version": packet_version,
        "active_bench_session_id": active_bench_session_id,
    }
