# Engine Execution Plan

## Goal

Build a real layout/interaction engine under Create Bench so the app can express UI intent with minimal ambiguity.

This engine must become the geometry and interaction truth for:
- freeform placement
- resize
- locking
- grid snap
- parent bounds
- hit testing
- deterministic rect generation

The canvas must stop inventing layout behavior and become a rendering/input layer only.

---

## Core Principle

**The engine owns geometry truth. The canvas only visualizes and forwards interaction.**

---

## Execution Order

1. `engine/layout_engine.md`
2. `engine/geometry.md`
3. `engine/constraints.md`
4. `engine/snap_engine.md`
5. `engine/placement_engine.md`
6. `engine/lock_manager.md`
7. implement `geometry.py`
8. implement `constraints.py`
9. implement `lock_manager.py`
10. implement `placement_engine.py`
11. implement `snap_engine.py`
12. implement `layout_engine.py`
13. refactor `canvas_widget.py` to consume `layout_engine`
14. add move
15. add resize
16. add locking enforcement
17. add grid + snap
18. test end-to-end before structural editing

---

## Files To Add

```text
createbench/engine/
  geometry.py
  constraints.py
  lock_manager.py
  placement_engine.py
  snap_engine.py
  layout_engine.py
```

---

## Files To Update

```text
createbench/canvas/canvas_widget.py
createbench/core/node.py
createbench/schemas/core/*.json
createbench/tests/
```

---

## Engine Property Requirements

These properties must be standardized and schema-backed on relevant node types:
- `x`
- `y`
- `width`
- `height`
- `min_width`
- `min_height`
- `max_width`
- `max_height`
- `layout_mode`
- `locked`

Recommended defaults:
- `x = 0`
- `y = 0`
- `width = 200`
- `height = 100`
- `min_width = 50`
- `min_height = 30`
- `max_width = null`
- `max_height = null`
- `layout_mode = "free"` for expression-first design work
- `locked = false`

---

## Locked Engine Policies

### Layout modes

- `auto`
- `free`

### auto

- node follows parent layout rules
- parent controls geometry

### free

- node uses explicit `x`, `y`, `width`, `height`
- still subject to min/max and parent/canvas bounds

---

## Locking

- locked node can be selected
- locked node cannot move
- locked node cannot resize
- locked node semantic fields remain editable
- no lock inheritance in MVP

---

## Grid

- grid enabled by default
- default grid size: 8
- move snaps to grid
- resize snaps to grid
- no snap bypass modifier yet

---

## Parent bounds

- free nodes stay inside parent by default
- root-level free nodes stay inside canvas
- overflow is not supported in MVP

---

## Z-order

- draw order = sibling order
- last drawn = topmost
- hit testing checks reverse draw order

---

## Resize handles

MVP handles:
- right
- bottom
- bottom-right

---

## Drag policy

Dragging a node on canvas:
- if node is locked: blocked
- if node is free: move directly
- if node is auto:
- switch to free
- preserve current computed rect as starting explicit rect
- then move

This supports expression-first editing without tool friction.

---

## Subsystem Responsibilities

---

## `geometry.py`

### Purpose

Pure geometry/math helpers. No node logic. No model access.

### Responsibilities

- rect normalization
- point-in-rect
- clamp
- overlap tests
- edge distance
- corner/edge handle detection
- resize math helpers

### Public functions

- `point_in_rect(x, y, rect)`
- `clamp(value, low, high)`
- `normalize_rect(x, y, width, height)`
- `rect_contains_rect(parent, child)`
- `detect_resize_handle(point, rect, handle_size=8)`
- `apply_resize(rect, handle, dx, dy, min_width, min_height, max_width=None, max_height=None)`

### Constraints

- no `layout_model`
- no Qt imports
- deterministic only

### Tests

1. point hit works
2. clamp works
3. resize handle detection works
4. resize math respects min sizes
5. normalized rect never returns negative width/height

---

## `constraints.py`

### Purpose

Geometry rule enforcement.

### Responsibilities

- min/max width/height enforcement
- parent bounds clamping
- canvas bounds clamping
- legal resize filtering
- legal move filtering

### Public functions

- `enforce_size_constraints(rect, node)`
- `clamp_to_parent(rect, parent_rect)`
- `clamp_to_canvas(rect, canvas_rect)`
- `validate_move(rect, node, parent_rect, canvas_rect)`
- `validate_resize(rect, node, parent_rect, canvas_rect)`

### Constraints

- no schema validation
- no hit testing
- deterministic only

### Tests

1. min size enforced
2. max size enforced
3. node stays inside parent
4. root-level node stays inside canvas
5. invalid resize resolves safely

---

## `lock_manager.py`

### Purpose

Central lock rules.

### Responsibilities

- decide whether node can move
- decide whether node can resize

### Public functions

- `can_move(node) -> bool`
- `can_resize(node) -> bool`

### Rules

- `locked = true` blocks move and resize
- selection remains allowed

### Tests

1. locked node cannot move
2. locked node cannot resize
3. unlocked node can move
4. unlocked node can resize

---

## `placement_engine.py`

### Purpose

Initial placement rules for new nodes/templates.

### Responsibilities

- choose initial placement for new node
- preserve template child order
- support free and auto parent placement

### Public functions

- `place_new_node(node, parent, parent_rect=None, cursor_pos=None)`
- `place_template_subtree(template_dict, parent_id, model, layout_engine)`

### Rules

- auto-layout parent:
- placement follows parent layout order
- free-layout parent:
- place near cursor if available
- else place at parent origin offset
- preserve template order exactly

### Tests

1. free parent placement gives explicit coordinates
2. auto parent placement respects order
3. template subtree preserves order
4. repeated placement does not overlap identically if offset policy exists

---

## `snap_engine.py`

### Purpose

Resolve snapping for move/resize.

### Responsibilities

- grid snap
- parent edge snap
- sibling edge snap

### Public functions

- `snap_value(value, grid_size)`
- `snap_rect_to_grid(rect, grid_size)`
- `snap_rect_to_parent_edges(rect, parent_rect, threshold=8)`
- `snap_rect_to_sibling_edges(rect, sibling_rects, threshold=8)`
- `resolve_snap(rect, parent_rect, sibling_rects, grid_size=8)`

### Snap order

1. size constraints
2. parent bounds clamp
3. grid snap
4. parent edge snap
5. sibling edge snap

### Tests

1. move snaps to grid
2. resize snaps to grid
3. parent edge snap works
4. sibling edge snap works
5. snap output deterministic

---

## `layout_engine.py`

### Purpose

Main geometry orchestrator.

### Responsibilities

- compute all node rects
- resolve free vs auto layout
- provide hit-testing metadata
- resolve move/resize outcomes
- preserve deterministic draw order

### Dependencies

- `geometry.py`
- `constraints.py`
- `snap_engine.py`
- `lock_manager.py`
- `placement_engine.py`

### Public API

- `compute_layout(root_id, canvas_rect) -> dict[node_id, rect]`
- `hit_test(point, rect_map, draw_order) -> node_id | None`
- `get_resize_handle(point, node_id, rect_map) -> str | None`
- `move_node(node_id, proposed_x, proposed_y, canvas_rect) -> dict`
- `resize_node(node_id, handle, dx, dy, canvas_rect) -> dict`

### Output shape

```python
{
    "button_1": {"x": 10, "y": 20, "width": 200, "height": 40},
    "main_1": {"x": 220, "y": 0, "width": 900, "height": 700}
}
```

### Internal behavior

#### `compute_layout`

- start from synthetic root children
- compute DFS
- preserve sibling order
- support:
- vertical
- horizontal
- container as vertical default
- free
- fallback for leaf nodes

#### auto layout policy

- vertical:
- equal height distribution by child count
- horizontal:
- equal width distribution by child count
- container:
- vertical by default unless later overridden

#### free layout policy

- use explicit `x`, `y`, `width`, `height`

#### `move_node`

- resolve current rect
- if auto node dragged:
- convert to free
- seed explicit geometry from computed rect
- enforce:
- lock policy
- bounds
- snap
- min/max

#### `resize_node`

- detect handle
- resolve new rect
- enforce:
- lock policy
- bounds
- snap
- min/max

#### Hit testing

- use reverse draw order
- topmost wins

### Constraints

- no UI rendering
- no direct Qt painting
- no checklist logic
- no schema validation beyond geometry assumptions

### Tests

1. free node uses explicit rect
2. auto vertical layout distributes children
3. auto horizontal layout distributes children
4. mixed free + auto layout works
5. hit test selects topmost node
6. drag converts auto node to free
7. locked node does not move
8. resize respects min sizes
9. grid snap deterministic
10. sibling order preserved

---

## Canvas Refactor Plan

### Goal

Canvas stops computing geometry.

### New responsibility split

#### Canvas owns

- painting from rect map
- mouse events
- interaction state
- selected node visuals

#### Engine owns

- geometry
- hit testing data
- move/resize resolution

### Canvas changes

- request rect map from `layout_engine.compute_layout(...)`
- store returned `node_rects`
- use `layout_engine.hit_test(...)` on click
- on drag:
- call `layout_engine.move_node(...)`
- write resolved values back to node
- on resize:
- call `layout_engine.resize_node(...)`
- write resolved values back to node

---

## Implementation Sequence In Detail

---

## Step 1 - Write engine docs

Create:
- `engine/layout_engine.md`
- `engine/geometry.md`
- `engine/constraints.md`
- `engine/snap_engine.md`
- `engine/placement_engine.md`
- `engine/lock_manager.md`

Do not code before these are locked.

---

## Step 2 - Add geometry properties to schemas

Update relevant node schemas with:
- position
- size
- lock
- layout mode
- min/max constraints

Also update any default application behavior if needed through registry-backed defaults.

---

## Step 3 - Implement `geometry.py`

Write pure helpers first.

Success checkpoint:
- geometry tests all pass
- no model dependencies exist

---

## Step 4 - Implement `constraints.py`

Write size/bounds enforcement.

Success checkpoint:
- constraints tests all pass
- parent/canvas clamping works deterministically

---

## Step 5 - Implement `lock_manager.py`

Keep it tiny and correct.

Success checkpoint:
- lock tests pass
- no hidden behavior

---

## Step 6 - Implement `placement_engine.py`

Initial placement only.

Success checkpoint:
- template/new-node placement behaves predictably

---

## Step 7 - Implement `snap_engine.py`

Grid first, then edges.

Success checkpoint:
- snapping is deterministic
- no jitter loop in repeated snap calls

---

## Step 8 - Implement `layout_engine.py`

Compute-only first.
No canvas changes yet.

Success checkpoint:
- stable rect map generation
- hit testing works
- move/resize APIs return correct rects

---

## Step 9 - Refactor `canvas_widget.py`

Remove canvas-owned geometry logic.
Use engine rect map only.

Success checkpoint:
- app still renders
- selection still works
- no behavior regressions

---

## Step 10 - Add drag

Use engine move API.

Success checkpoint:
- free nodes move
- auto nodes convert to free on drag
- locked nodes do not move

---

## Step 11 - Add resize

Use engine resize API.

Success checkpoint:
- selected node shows handles
- resize updates width/height
- min sizes enforced

---

## Step 12 - Add snapping and grid visuals

Engine already snaps. Canvas can optionally draw:
- grid background
- maybe guides later

Success checkpoint:
- move and resize visibly snap
- no weird oscillation

---

## Step 13 - Full engine smoke pass

Manual test:
- add nodes
- drag
- resize
- lock
- drag locked node
- mixed free/auto
- repeated template adds

Must confirm:
- no crashes
- no geometry drift
- no duplicate rect ownership
- no hidden mutations

---

## Test Plan Summary

### Unit tests

- geometry
- constraints
- lock_manager
- placement_engine
- snap_engine
- layout_engine

### Integration tests

- canvas renders engine rects
- click selects topmost node
- drag updates node geometry
- resize updates node geometry
- locked node blocked
- auto-to-free transition works

### Manual smoke tests

1. drag a node
2. resize a node
3. lock node and confirm frozen
4. drag overlapping nodes and confirm topmost selection
5. add template and confirm stable placement
6. export after geometry edits and confirm stability

---

## Non-Goals For This Engine Phase

Do NOT add:
- import pipeline
- semantic behavior compilation
- advanced snapping guides
- full structural editing menus
- style/theming system
- persistence of grid settings
- plugin architecture

This phase is geometry and interaction truth only.

---

## Exit Criteria For Engine Phase

The engine phase is complete only when:
- nodes can be placed freely
- nodes can be resized
- locking works
- auto/free modes both work
- grid snap works
- hit testing is reliable
- canvas depends on engine for geometry
- tests pass
- manual smoke use feels expressive instead of clunky

---

## Next Phase After Engine

Only after the engine is stable:
1. structural editing actions
2. component form system
3. improved template behavior
4. import adapter contract
5. semantic compilation later

---

## Key Reminder

The current bottleneck is not code generation.

The bottleneck is expression bandwidth.

Every engine decision should answer this:

Can Ace place, size, lock, and describe the thing fast enough to show exact intent?

If not, keep working on the engine.
