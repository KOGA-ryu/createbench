from __future__ import annotations


def route_scene_action(selected_source: str, action: str) -> str:
    routes = {
        ("project", "replace"): "project_replace",
        ("project", "alongside"): "project_alongside",
        ("project", "bench"): "project_bench",
        ("extract_packet", "replace"): "extract_packet_replace",
        ("extract_packet", "alongside"): "extract_packet_alongside",
        ("extract_packet", "bench"): "extract_packet_bench",
        ("scanner_repo", "replace"): "scanner_replace",
        ("scanner_repo", "alongside"): "scanner_alongside",
        ("scanner_repo", "bench"): "scanner_bench",
    }
    return routes[(selected_source, action)]
