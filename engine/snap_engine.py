from __future__ import annotations

from engine.geometry import normalize_rect


Rect = dict[str, int]


def snap_value(value, grid_size):
    if not grid_size or grid_size <= 0:
        return int(round(value))
    return int(round(value / grid_size) * grid_size)


def snap_rect_to_grid(rect, grid_size) -> Rect:
    normalized = normalize_rect(rect["x"], rect["y"], rect["width"], rect["height"])
    return {
        "x": snap_value(normalized["x"], grid_size),
        "y": snap_value(normalized["y"], grid_size),
        "width": max(1, snap_value(normalized["width"], grid_size)),
        "height": max(1, snap_value(normalized["height"], grid_size)),
    }


def snap_rect_to_parent_edges(rect, parent_rect, threshold=8) -> Rect:
    normalized = normalize_rect(rect["x"], rect["y"], rect["width"], rect["height"])
    if parent_rect is None:
        return normalized

    parent = normalize_rect(
        parent_rect["x"], parent_rect["y"], parent_rect["width"], parent_rect["height"]
    )
    left = normalized["x"]
    right = normalized["x"] + normalized["width"]
    top = normalized["y"]
    bottom = normalized["y"] + normalized["height"]

    parent_left = parent["x"]
    parent_right = parent["x"] + parent["width"]
    parent_top = parent["y"]
    parent_bottom = parent["y"] + parent["height"]

    if abs(left - parent_left) <= threshold:
        normalized["x"] = parent_left
    elif abs(right - parent_right) <= threshold:
        normalized["x"] = parent_right - normalized["width"]

    if abs(top - parent_top) <= threshold:
        normalized["y"] = parent_top
    elif abs(bottom - parent_bottom) <= threshold:
        normalized["y"] = parent_bottom - normalized["height"]

    return normalized


def snap_rect_to_sibling_edges(rect, sibling_rects, threshold=8) -> Rect:
    normalized = normalize_rect(rect["x"], rect["y"], rect["width"], rect["height"])
    siblings = [
        normalize_rect(s["x"], s["y"], s["width"], s["height"])
        for s in (sibling_rects or [])
    ]

    if not siblings:
        return normalized

    best_x = _best_axis_snap(
        current_start=normalized["x"],
        current_end=normalized["x"] + normalized["width"],
        size=normalized["width"],
        candidate_rects=siblings,
        axis="x",
        threshold=threshold,
    )
    if best_x is not None:
        normalized["x"] = best_x

    best_y = _best_axis_snap(
        current_start=normalized["y"],
        current_end=normalized["y"] + normalized["height"],
        size=normalized["height"],
        candidate_rects=siblings,
        axis="y",
        threshold=threshold,
    )
    if best_y is not None:
        normalized["y"] = best_y

    return normalized


def resolve_snap(rect, parent_rect, sibling_rects, grid_size=8) -> Rect:
    snapped = snap_rect_to_grid(rect, grid_size)
    snapped = snap_rect_to_parent_edges(snapped, parent_rect)
    snapped = snap_rect_to_sibling_edges(snapped, sibling_rects)
    return snapped


def _best_axis_snap(current_start, current_end, size, candidate_rects, axis, threshold):
    best_distance = None
    best_value = None

    for sibling in candidate_rects:
        sibling_start = sibling[axis]
        sibling_end = sibling[axis] + sibling["width" if axis == "x" else "height"]
        candidates = (
            (abs(current_start - sibling_start), sibling_start),
            (abs(current_start - sibling_end), sibling_end),
            (abs(current_end - sibling_start), sibling_start - size),
            (abs(current_end - sibling_end), sibling_end - size),
        )
        for distance, snapped_start in candidates:
            if distance > threshold:
                continue
            if best_distance is None or distance < best_distance:
                best_distance = distance
                best_value = snapped_start
            elif distance == best_distance and best_value is not None:
                best_value = min(best_value, snapped_start)

    return best_value
