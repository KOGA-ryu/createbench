# File: canvas/canvas_widget.py

## Purpose

Provides a visual representation of the layout tree and allows direct manipulation of nodes through drag, drop, and resize interactions.

## Responsibilities

* render nodes based on layout_model
* handle node selection
* support drag-and-drop reordering and reparenting
* support resizing of layout elements
* translate user interactions into layout_model mutations

## Inputs

* layout_model (tree structure)
* selection_state
* property_registry (for node type context)

## Outputs

* user interactions translated into:

  * add_node
  * move_node
  * reorder_node
  * property updates
* selection updates

## Rendering

### Style

* lightweight semantic previews
* containers/regions:

  * wireframe blocks with labels
* components:

  * minimal recognizable visuals (button, text, input)

### Layout

* respects node layout type:

  * vertical
  * horizontal
  * split

* tree order determines visual order

## Interaction Model

### Selection

* single selection only
* click selects node
* selection updates selection_state

### Drag & Drop

* drag node to:

  * reorder within parent
  * reparent to another node
* drop zones are explicit and computed

### Resize

* resize handles on applicable nodes
* updates:

  * width / height
  * split ratios

## Node Creation

* initiated from palette/actions (not gestures)
* inserted into layout_model immediately

## Data Flow

* all edits apply directly to layout_model
* no staging/draft layer

## Validation Behavior

### Blocked Actions

* creating cycles
* reparenting into own subtree
* invalid structural operations

### Allowed but Flagged

* schema-invalid placements
* incorrect child types

## Dependencies

* layout_model.py
* tree_manager.py
* selection_state.py

## Constraints

* must NOT own layout state
* must NOT validate schema rules
* must NOT contain business logic
* must remain deterministic

## Edge Cases

* dragging over deeply nested structures
* rapid drag events
* resizing conflicting with layout constraints
* invalid drop zones

## Performance

* full redraw on change (MVP)

## Open Questions

* when to introduce gesture-based creation
* when to optimize rendering
