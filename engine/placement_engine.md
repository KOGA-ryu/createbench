# File: engine/placement_engine.py

## Purpose

Provides deterministic initial placement rules for new nodes and templates. Acts as the engine layer that decides where geometry begins before direct manipulation occurs.

## Responsibilities

* choose initial placement for new nodes
* choose initial placement for template subtrees
* preserve template child order
* support free-layout and auto-layout parent behaviors

## Inputs

* new node objects
* parent nodes
* optional parent rects
* optional cursor positions
* template dictionaries
* layout model references for subtree creation
* layout engine references when computed geometry is needed

## Outputs

* placement-ready node properties
* deterministically inserted template subtrees

## Public API

* `place_new_node(node, parent, parent_rect=None, cursor_pos=None)`
* `place_template_subtree(template_dict, parent_id, model, layout_engine)`

## Placement Rules

### Auto-layout parent

* new child placement follows parent layout order
* explicit x/y placement is not authoritative
* sibling order remains the source of visual order

### Free-layout parent

* place near cursor when cursor position is available
* otherwise place at a deterministic offset from parent origin
* resulting node must have explicit geometry properties

### Template placement

* preserve template child order exactly
* preserve subtree shape exactly
* apply placement deterministically

## Offset Policy

* repeated placement may use a stable offset progression
* if offset progression exists, it must be deterministic
* repeated inserts must not land on identical geometry by accident when avoidable

## Dependencies

* `engine/layout_engine.py` for computed geometry context when needed
* layout model for subtree insertion

## Constraints

* must NOT paint UI
* must NOT perform snapping
* must NOT validate schemas
* must remain deterministic

## Edge Cases

* free parent without parent rect
* root placement without cursor position
* empty template children
* nested template placement under mixed auto/free parents

## Tests

1. free parent placement gives explicit coordinates
2. auto parent placement respects order
3. template subtree preserves order
4. repeated placement does not overlap identically if offset policy exists

## Decisions Locked

* placement is engine-owned, not canvas-owned
* template order is preserved exactly
* free parents produce explicit geometry at creation time
