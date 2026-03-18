# File: engine/snap_engine.py

## Purpose

Resolves deterministic snapping for move and resize interactions. Acts as the engine layer that adjusts legal geometry to grid and nearby edges.

## Responsibilities

* snap scalar values to grid
* snap rects to grid
* snap rects to parent edges
* snap rects to sibling edges
* combine snapping stages into a stable output

## Inputs

* rect dictionaries
* parent rects
* sibling rect lists
* grid size
* snap thresholds

## Outputs

* snapped scalar values
* snapped rect dictionaries

## Public API

* `snap_value(value, grid_size)`
* `snap_rect_to_grid(rect, grid_size)`
* `snap_rect_to_parent_edges(rect, parent_rect, threshold=8)`
* `snap_rect_to_sibling_edges(rect, sibling_rects, threshold=8)`
* `resolve_snap(rect, parent_rect, sibling_rects, grid_size=8)`

## Snap Order

1. size constraints
2. parent bounds clamp
3. grid snap
4. parent edge snap
5. sibling edge snap

Higher layers must call this module in that order or provide already-constrained input.

## Grid Policy

* grid is enabled by default
* default grid size is 8
* move snaps to grid
* resize snaps to grid
* no snap bypass modifier in MVP

## Edge Snap Policy

### Parent edges

* snap when node edges fall within threshold distance
* preserve rect size while aligning position where applicable

### Sibling edges

* snap when node edges fall within threshold distance of sibling edges
* output must remain deterministic regardless of sibling list order policy used by caller

## Dependencies

* `engine/geometry.py`

## Constraints

* must NOT mutate nodes directly
* must NOT do hit testing
* must NOT import Qt
* must remain deterministic and stable across repeated calls

## Edge Cases

* zero or invalid grid size
* no parent rect
* empty sibling list
* multiple candidate sibling snaps
* repeated snapping of an already-snapped rect

## Tests

1. move snaps to grid
2. resize snaps to grid
3. parent edge snap works
4. sibling edge snap works
5. snap output deterministic

## Decisions Locked

* grid snapping is on by default
* snapping resolves to stable geometry, not advisory guides
* repeated snap calls must not jitter
