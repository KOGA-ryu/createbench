from __future__ import annotations

import json
from pathlib import Path

from core.scene_resolution import resolve_scene_state
from export.dsl_builder import DSL_VERSION


def default_scene_source_target_path(selected_source: str) -> str:
    defaults = {
        "project": "project.json",
        "extract_packet": "ui_extract_packet.json",
        "scanner_repo": "/Users/kogaryu/dev/scanner",
    }
    return defaults.get(selected_source, "")


def scene_action_target_suffix(target_path: str, default_target_path: str) -> str:
    if not target_path:
        return ""
    if target_path == default_target_path:
        return ""
    return f" at {target_path}"


def scene_source_preflight_text(
    *,
    selected_source: str,
    target_path: str,
    scanner_probe_target: str,
    validate_scanner_repo_root,
    validate_scanner_probe_target,
    validate_ui_extract_packet,
) -> str:
    path = Path(target_path)
    if not path.exists():
        return "Preflight: missing target"
    if selected_source == "scanner_repo":
        try:
            validate_scanner_repo_root(path)
        except Exception:
            return "Preflight: invalid scanner repo"
        try:
            validate_scanner_probe_target(scanner_probe_target)
        except Exception:
            return "Preflight: invalid scanner probe target"
        return "Preflight: valid scanner repo"
    try:
        with open(path, "r", encoding="utf-8") as handle:
            payload = json.load(handle)
    except Exception:
        return "Preflight: unreadable file"

    if selected_source == "extract_packet":
        try:
            validate_ui_extract_packet(payload)
        except Exception:
            return "Preflight: invalid extract packet"
        return "Preflight: valid extract packet"

    if not isinstance(payload, dict):
        return "Preflight: invalid project file"
    if payload.get("version") != DSL_VERSION:
        return "Preflight: invalid project version"
    if "data" not in payload:
        return "Preflight: invalid project file"
    return "Preflight: valid project file"


def scene_action_hint_text(action: str) -> str:
    hints = {
        "replace": "Replace: clears the current scene and loads the selected source into it",
        "alongside": "Alongside: preserves the current scene and adds the selected source beside it",
        "bench": "Recommended: Bench preserves the current scene and opens the selected source in an isolated bench session",
    }
    return hints[action]


def recommended_scene_action(scene_metadata: dict[str, object]) -> str:
    resolved_scene = resolve_scene_state(scene_metadata)
    if resolved_scene["resolved_mode"] in {"source", "bench"}:
        return "bench"
    return "alongside"


def scene_action_context_text(
    *,
    actionable: bool,
    scene_metadata: dict[str, object],
    source_label: str,
    target_suffix: str,
) -> str:
    if not actionable:
        return "Scene actions are unavailable until the selected source passes preflight."
    resolved_scene = resolve_scene_state(scene_metadata)
    if resolved_scene["resolved_mode"] == "source":
        return f"Current scene is source-backed, so bench is the safest isolated path for incoming {source_label}{target_suffix}."
    if resolved_scene["resolved_mode"] == "bench":
        return f"Current scene is bench-focused, so bench keeps incoming {source_label}{target_suffix} isolated."
    return f"Current scene is design-only, so alongside keeps existing work visible while adding incoming {source_label}{target_suffix}."
