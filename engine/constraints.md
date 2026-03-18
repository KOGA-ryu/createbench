# File: engine/constraints.py

## Purpose

Applies geometry rules to proposed rects. Acts as the deterministic enforcement layer for size limits and bounds containment before geometry is committed back to nodes.

## Responsibilities

* enforce min/max width and height
* clamp free-layout rects to parent bounds
* clamp top-level rects to canvas bounds
* resolve safe move outputs
* resolve safe resize outputs

## Inputs

* proposed rect dictionaries
* node objects or node-like property sources
* parent rects
* canvas rects

## Outputs

* corrected rect dictionaries
* validated move rects
* validated resize rects

## Public API

* `enforce_size_constraints(rect, node)`
* `clamp_to_parent(rect, parent_rect)`
* `clamp_to_canvas(rect, canvas_rect)`
* `validate_move(rect, node, parent_rect, canvas_rect)`
* `validate_resize(rect, node, parent_rect, canvas_rect)`

## Constraint Sources

Geometry constraints are read from node properties:

* `min_width`
* `min_height`
* `max_width`
* `max_height`
* `layout_mode`

This module assumes those properties already exist or have sane fallbacks.

## Internal Logic

### Size Enforcement

* min width always enforced
* min height always enforced
* max width enforced when not `None`
* max height enforced when not `None`

### Bounds Enforcement

* child free nodes must remain inside parent bounds
* top-level free nodes must remain inside canvas bounds
* overflow is not supported in MVP

### Move Validation

* preserve width and height
* clamp x and y into legal bounds
* return safe rect even when proposed move is illegal

### Resize Validation

* enforce min/max first
* clamp final rect into parent or canvas bounds
* return safe rect even when proposed resize is illegal

## Dependencies

* `engine/geometry.py`

## Constraints

* must NOT validate schema files
* must NOT do hit testing
* must NOT mutate nodes directly
* must remain deterministic

## Edge Cases

* parent smaller than node minimum size
* canvas smaller than node minimum size
* max values smaller than current size
* `None` max values
* root-level nodes with no parent rect
* resize attempts that would push a node outside bounds

## Tests

1. min size enforced
2. max size enforced
3. node stays inside parent
4. root-level node stays inside canvas
5. invalid resize resolves safely

## Decisions Locked

* constraints resolve to corrected geometry instead of rejecting with no result
* overflow is blocked in MVP
* size enforcement happens before snap-dependent higher layers
