from __future__ import annotations

from core.node import Node


BENCH_WORKSPACE_TITLE = "Bench Workspace"
BENCH_WORKSPACE_X = 1800
BENCH_WORKSPACE_Y = 72
BENCH_WORKSPACE_WIDTH = 1280
BENCH_WORKSPACE_HEIGHT = 860


def find_bench_workspace(api) -> Node | None:
    for child in api.get_children(api.get_root_id()):
        if (
            child.type == "panel"
            and child.properties.get("title") == BENCH_WORKSPACE_TITLE
            and child.properties.get("layout_mode") == "free"
        ):
            return child
    return None


def ensure_bench_workspace(api) -> Node:
    existing = find_bench_workspace(api)
    if existing is not None:
        existing.properties = dict(existing.properties)
        existing.properties["layout_mode"] = "free"
        existing.properties["x"] = BENCH_WORKSPACE_X
        existing.properties["y"] = BENCH_WORKSPACE_Y
        existing.properties["width"] = BENCH_WORKSPACE_WIDTH
        existing.properties["height"] = BENCH_WORKSPACE_HEIGHT
        return existing

    workspace = api.create_node(
        "panel",
        {
            "title": BENCH_WORKSPACE_TITLE,
            "layout_mode": "free",
            "x": BENCH_WORKSPACE_X,
            "y": BENCH_WORKSPACE_Y,
            "width": BENCH_WORKSPACE_WIDTH,
            "height": BENCH_WORKSPACE_HEIGHT,
        },
        metadata={
            "trust": {
                "trust_level": "mock",
                "representation_origin": "manual",
                "warnings": [],
            },
            "provenance": {
                "representation_origin": "manual",
                "internal_role": "bench_workspace",
            },
        },
    )
    api.add_node(api.get_root_id(), workspace)
    return workspace
