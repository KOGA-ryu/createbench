# File: engine/layout_engine.py

## Purpose

Owns geometry truth for Create Bench. Computes rects, resolves free vs auto layout behavior, provides hit testing data, and returns deterministic move and resize outcomes for the canvas to apply.

## Responsibilities

* compute rects for all visible nodes
* resolve free-layout and auto-layout geometry
* preserve sibling order as draw order
* provide hit testing against computed rects
* provide resize handle lookup
* resolve move outcomes
* resolve resize outcomes

## Inputs

* layout_model tree
* node properties
* canvas rect
* proposed interaction deltas
* parent and sibling geometry context

## Outputs

* `rect_map` keyed by node id
* deterministic draw order
* hit-tested node ids
* resolved move results
* resolved resize results

## Dependencies

* `engine/geometry.py`
* `engine/constraints.py`
* `engine/snap_engine.py`
* `engine/lock_manager.py`
* `engine/placement_engine.py`

## Public API

* `compute_layout(root_id, canvas_rect) -> dict[node_id, rect]`
* `hit_test(point, rect_map, draw_order) -> node_id | None`
* `get_resize_handle(point, node_id, rect_map) -> str | None`
* `move_node(node_id, proposed_x, proposed_y, canvas_rect) -> dict`
* `resize_node(node_id, handle, dx, dy, canvas_rect) -> dict`

## Output Shape

```python
{
    "button_1": {"x": 10, "y": 20, "width": 200, "height": 40},
    "main_1": {"x": 220, "y": 0, "width": 900, "height": 700}
}
```

## Layout Modes

* `auto`
* `free`

### Auto mode

* node follows parent layout rules
* parent owns computed geometry

### Free mode

* node uses explicit:

  * x
  * y
  * width
  * height
* node remains subject to constraints and snapping

## Internal Logic

### `compute_layout(...)`

* starts at synthetic root children
* computes geometry with deterministic DFS traversal
* preserves sibling order
* returns stable rect output for the same input tree

### Supported auto layout policies

* `vertical`:

  * equal height distribution by child count
* `horizontal`:

  * equal width distribution by child count
* `container`:

  * behaves as vertical by default in MVP
* leaf fallback:

  * uses existing computed slot or explicit rect as applicable

### Free layout policy

* explicit x/y/width/height are authoritative
* final rect still runs through constraints and snapping layers when interaction occurs

### `move_node(...)`

* resolves current computed rect
* blocks when lock policy disallows movement
* if dragged node is `auto`:

  * convert node to `free`
  * seed explicit geometry from current computed rect
  * then resolve move
* enforce:

  * lock policy
  * size/bounds constraints
  * snapping

### `resize_node(...)`

* blocks when lock policy disallows resize
* resolves current computed rect
* applies resize math using handle and deltas
* enforce:

  * lock policy
  * size/bounds constraints
  * snapping

### Hit testing

* uses reverse draw order
* topmost node wins
* relies only on computed rects

### Resize handle lookup

* delegated to geometry handle detection
* based on current computed rect

## Draw Order

* draw order equals sibling order
* last drawn is topmost
* hit testing checks reverse draw order

## Canvas Relationship

Canvas is a rendering and input layer only.

Canvas may:

* ask for rects
* paint rects
* request hit testing
* forward move and resize intents

Canvas must NOT:

* invent geometry
* invent hit testing rules
* own snapping decisions

## Constraints

* must NOT paint UI
* must NOT import Qt drawing APIs
* must NOT contain checklist logic
* must NOT validate schema files beyond geometry assumptions
* must remain deterministic

## Edge Cases

* mixed free and auto siblings
* empty containers
* zero-sized canvas
* root-level free nodes
* overlapping siblings in free mode
* drag of locked node
* resize beyond min/max or parent bounds

## Tests

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

## Decisions Locked

* geometry truth lives in the engine
* canvas is not allowed to compute layout behavior
* sibling order is authoritative for draw order
* auto-to-free conversion on drag is required in MVP
* container defaults to vertical auto layout in MVP
