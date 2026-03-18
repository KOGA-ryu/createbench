# File: engine/geometry.py

## Purpose

Provides pure geometry and rect math helpers for the layout engine. Acts as the lowest-level deterministic utility layer for hit testing, normalization, and resize calculations.

## Responsibilities

* normalize rect values
* clamp scalar values into legal ranges
* detect point hits inside rects
* check whether a child rect fits inside a parent rect
* detect active resize handles from a point
* apply resize math for supported handles

## Inputs

* numeric coordinates
* rect dictionaries with:

  * x
  * y
  * width
  * height
* resize handle identifiers
* min/max size constraints

## Outputs

* normalized rect dictionaries
* bool hit results
* resolved handle identifiers
* resized rect dictionaries

## Public API

* `point_in_rect(x, y, rect)`
* `clamp(value, low, high)`
* `normalize_rect(x, y, width, height)`
* `rect_contains_rect(parent, child)`
* `detect_resize_handle(point, rect, handle_size=8)`
* `apply_resize(rect, handle, dx, dy, min_width, min_height, max_width=None, max_height=None)`

## Rect Definition

All rects use:

* `x`
* `y`
* `width`
* `height`

All returned rects must preserve this shape.

## Handle Policy

Supported MVP handles:

* `right`
* `bottom`
* `bottom_right`

`detect_resize_handle(...)` returns:

* one of the supported handle ids
* `None` when no handle is active

## Internal Logic

### Normalization

* rect width must never be negative
* rect height must never be negative
* normalization must produce stable numeric output

### Hit Testing

* point hit includes the rect boundary
* point hit uses only numeric geometry

### Resize Math

* `right` changes width only
* `bottom` changes height only
* `bottom_right` changes width and height
* resize math must apply min/max limits deterministically
* resize math must never return negative width or height

## Dependencies

* none

## Constraints

* must NOT import Qt
* must NOT access layout_model
* must NOT inspect node schema
* must remain pure and deterministic

## Edge Cases

* negative width input
* negative height input
* resize deltas that would shrink below minimum size
* resize deltas that would exceed maximum size
* point hits exactly on edges
* zero-sized rects

## Tests

1. point hit works
2. clamp works
3. resize handle detection works
4. resize math respects min sizes
5. normalized rect never returns negative width/height

## Decisions Locked

* geometry helpers are pure functions only
* rects use dict shape, not Qt objects
* resize handles are limited to right, bottom, and bottom_right in MVP
* boundary-inclusive hit testing is required
