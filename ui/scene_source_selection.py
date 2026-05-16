from __future__ import annotations


def selected_scene_source(scene_source_selector) -> str:
    return str(scene_source_selector.currentData() or "project")


def scene_source_target_path(app_state, selected_source: str) -> str:
    return app_state.get_scene_source_target(selected_source)


def selected_scanner_probe_target(scanner_probe_target_selector) -> str:
    return str(scanner_probe_target_selector.currentData() or "main_window")


def selected_scanner_probe_label(probe_target: str) -> str:
    labels = {
        "main_window": "scanner main window",
        "profile_manager": "scanner profile manager",
    }
    return labels.get(probe_target, "scanner main window")


def selected_scene_source_label(selected_source: str, scanner_probe_label: str) -> str:
    labels = {
        "project": "project JSON",
        "extract_packet": "UI extract packet",
        "scanner_repo": scanner_probe_label,
    }
    return labels.get(selected_source, "project JSON")
