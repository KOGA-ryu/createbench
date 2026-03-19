from __future__ import annotations

from typing import Any


Rect = dict[str, int]


def clamp(value: int | float, low: int | float, high: int | float | None):
    if high is not None and high < low:
        high = low
    if value < low:
        return low
    if high is not None and value > high:
        return high
    return value


def normalize_rect(x: int | float, y: int | float, width: int | float, height: int | float) -> Rect:
    normalized_x = x
    normalized_y = y
    normalized_width = width
    normalized_height = height

    if normalized_width < 0:
        normalized_x = x + normalized_width
        normalized_width = abs(normalized_width)
    if normalized_height < 0:
        normalized_y = y + normalized_height
        normalized_height = abs(normalized_height)

    return {
        "x": int(round(normalized_x)),
        "y": int(round(normalized_y)),
        "width": int(round(normalized_width)),
        "height": int(round(normalized_height)),
    }


def point_in_rect(x: int | float, y: int | float, rect: dict[str, Any]) -> bool:
    normalized = normalize_rect(rect["x"], rect["y"], rect["width"], rect["height"])
    return (
        normalized["x"] <= x <= normalized["x"] + normalized["width"]
        and normalized["y"] <= y <= normalized["y"] + normalized["height"]
    )


def rect_contains_rect(parent: dict[str, Any], child: dict[str, Any]) -> bool:
    outer = normalize_rect(parent["x"], parent["y"], parent["width"], parent["height"])
    inner = normalize_rect(child["x"], child["y"], child["width"], child["height"])
    return (
        outer["x"] <= inner["x"]
        and outer["y"] <= inner["y"]
        and inner["x"] + inner["width"] <= outer["x"] + outer["width"]
        and inner["y"] + inner["height"] <= outer["y"] + outer["height"]
    )


def detect_resize_handle(
    point: tuple[int | float, int | float],
    rect: dict[str, Any],
    handle_size: int = 8,
) -> str | None:
    normalized = normalize_rect(rect["x"], rect["y"], rect["width"], rect["height"])
    px, py = point
    left = normalized["x"]
    right = normalized["x"] + normalized["width"]
    top = normalized["y"]
    bottom = normalized["y"] + normalized["height"]

    if left <= px <= left + handle_size and top <= py <= top + handle_size:
        return "top_left"
    if right - handle_size <= px <= right and top <= py <= top + handle_size:
        return "top_right"
    if left <= px <= left + handle_size and bottom - handle_size <= py <= bottom:
        return "bottom_left"
    if right - handle_size <= px <= right and bottom - handle_size <= py <= bottom:
        return "bottom_right"
    if left <= px <= left + handle_size and top <= py <= bottom:
        return "left"
    if right - handle_size <= px <= right and top <= py <= bottom:
        return "right"
    if left <= px <= right and top <= py <= top + handle_size:
        return "top"
    if left <= px <= right and bottom - handle_size <= py <= bottom:
        return "bottom"
    return None


def apply_resize(
    rect: dict[str, Any],
    handle: str,
    dx: int | float,
    dy: int | float,
    min_width: int | float,
    min_height: int | float,
    max_width: int | float | None = None,
    max_height: int | float | None = None,
) -> Rect:
    normalized = normalize_rect(rect["x"], rect["y"], rect["width"], rect["height"])
    x = normalized["x"]
    y = normalized["y"]
    width = normalized["width"]
    height = normalized["height"]
    right = x + width
    bottom = y + height

    if handle == "left":
        width = clamp(right - (x + dx), min_width, max_width)
        x = right - width
    elif handle == "right":
        width = clamp(width + dx, min_width, max_width)
    elif handle == "top":
        height = clamp(bottom - (y + dy), min_height, max_height)
        y = bottom - height
    elif handle == "bottom":
        height = clamp(height + dy, min_height, max_height)
    elif handle == "top_left":
        width = clamp(right - (x + dx), min_width, max_width)
        x = right - width
        height = clamp(bottom - (y + dy), min_height, max_height)
        y = bottom - height
    elif handle == "top_right":
        width = clamp(width + dx, min_width, max_width)
        height = clamp(bottom - (y + dy), min_height, max_height)
        y = bottom - height
    elif handle == "bottom_left":
        width = clamp(right - (x + dx), min_width, max_width)
        x = right - width
        height = clamp(height + dy, min_height, max_height)
    elif handle == "bottom_right":
        width = clamp(width + dx, min_width, max_width)
        height = clamp(height + dy, min_height, max_height)
    else:
        raise ValueError(f"Invalid resize handle: {handle}")

    return normalize_rect(x, y, width, height)
