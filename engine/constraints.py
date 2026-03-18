from __future__ import annotations

from typing import Any

from engine.geometry import clamp, normalize_rect


Rect = dict[str, int]


def enforce_size_constraints(rect: dict[str, Any], node) -> Rect:
    normalized = normalize_rect(rect["x"], rect["y"], rect["width"], rect["height"])

    min_width = _get_node_property(node, "min_width", 50)
    min_height = _get_node_property(node, "min_height", 30)
    max_width = _get_node_property(node, "max_width", None)
    max_height = _get_node_property(node, "max_height", None)

    return normalize_rect(
        normalized["x"],
        normalized["y"],
        clamp(normalized["width"], min_width, max_width),
        clamp(normalized["height"], min_height, max_height),
    )


def clamp_to_parent(rect: dict[str, Any], parent_rect: dict[str, Any] | None) -> Rect:
    if parent_rect is None:
        return normalize_rect(rect["x"], rect["y"], rect["width"], rect["height"])
    return _clamp_rect_to_bounds(rect, parent_rect)


def clamp_to_canvas(rect: dict[str, Any], canvas_rect: dict[str, Any] | None) -> Rect:
    if canvas_rect is None:
        return normalize_rect(rect["x"], rect["y"], rect["width"], rect["height"])
    return _clamp_rect_to_bounds(rect, canvas_rect)


def validate_move(
    rect: dict[str, Any],
    node,
    parent_rect: dict[str, Any] | None,
    canvas_rect: dict[str, Any] | None,
) -> Rect:
    constrained = enforce_size_constraints(rect, node)
    return _clamp_for_node(constrained, node, parent_rect, canvas_rect)


def validate_resize(
    rect: dict[str, Any],
    node,
    parent_rect: dict[str, Any] | None,
    canvas_rect: dict[str, Any] | None,
) -> Rect:
    constrained = enforce_size_constraints(rect, node)
    return _clamp_for_node(constrained, node, parent_rect, canvas_rect)


def _clamp_for_node(
    rect: dict[str, Any],
    node,
    parent_rect: dict[str, Any] | None,
    canvas_rect: dict[str, Any] | None,
) -> Rect:
    layout_mode = _get_node_property(node, "layout_mode", "free")
    if layout_mode != "free":
        return normalize_rect(rect["x"], rect["y"], rect["width"], rect["height"])
    if parent_rect is not None:
        return clamp_to_parent(rect, parent_rect)
    return clamp_to_canvas(rect, canvas_rect)


def _clamp_rect_to_bounds(rect: dict[str, Any], bounds: dict[str, Any]) -> Rect:
    normalized = normalize_rect(rect["x"], rect["y"], rect["width"], rect["height"])
    container = normalize_rect(bounds["x"], bounds["y"], bounds["width"], bounds["height"])

    width = min(normalized["width"], container["width"])
    height = min(normalized["height"], container["height"])

    min_x = container["x"]
    max_x = container["x"] + container["width"] - width
    min_y = container["y"]
    max_y = container["y"] + container["height"] - height

    return {
        "x": int(clamp(normalized["x"], min_x, max_x)),
        "y": int(clamp(normalized["y"], min_y, max_y)),
        "width": int(width),
        "height": int(height),
    }


def _get_node_property(node, key: str, default):
    if hasattr(node, "properties") and isinstance(node.properties, dict):
        return node.properties.get(key, default)
    if isinstance(node, dict):
        return node.get(key, default)
    return default
