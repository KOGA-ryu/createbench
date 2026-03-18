# File: core/tree_manager.py

## Purpose

Handles structural operations on the layout tree, including adding, removing, reordering, and reparenting nodes while maintaining hierarchy integrity.

## Responsibilities

* manage parent-child relationships
* handle node insertion and removal
* support reparenting of nodes
* support child reordering operations
* maintain structural integrity of the tree
* operate on the lookup index owned by `layout_model`

## Inputs

* node operations (add, remove, move, reorder)
* node references or node IDs
* optional insertion index or sibling placement targets

## Outputs

* updated tree structure
* updated parent-child relationships
* change information suitable for higher-level state systems

## Internal Logic

### Node Addition

* insert node under a specified parent
* update parent's children list while preserving order
* assign `parent_id` on inserted node
* register node through the index owned by `layout_model`

### Node Removal

* cascade delete
* remove node and all descendants
* remove from parent's children list
* remove all deleted nodes from the lookup index
* return deleted node IDs and a lightweight change record

### Reparenting

* move node from old parent to new parent
* entire subtree moves with node
* update `parent_id` on moved node
* preserve requested placement order in new parent
* same-parent moves are treated as reordering, not reparenting

### Reordering

* reorder within the same parent
* supports optional target index
* is the only operation used for same-parent movement

### Lookup

* operate on shared lookup index:

  * id -> node reference
* enables O(1) lookup

## Dependencies

* node.py
* layout_model.py (for index ownership, ID assignment, and overall control)

## Constraints

* must NOT contain UI logic
* must NOT handle validation rules
* must NOT enforce business logic beyond structure
* must preserve ordering of children
* must keep the tree deterministic and free of structural corruption
* must raise hard exceptions on invalid structural operations

## Root Rules

* tree uses a synthetic internal root with `root_id = "root"`
* root is an implicit container for all top-level nodes
* root cannot be deleted
* all top-level nodes use the synthetic root as parent
* all non-root nodes must resolve to the synthetic root through parent links

## Structural Guarantees

* each node has exactly one parent except the synthetic root
* no circular references allowed
* no orphan nodes allowed
* duplicate IDs must be rejected
* tree order is visual order

## Temporary Invalid States

* tree may enter temporary invalid states during editing only with respect to product rules
* structural integrity must still be preserved at all times
* checklist handles semantic validation, not `tree_manager`

## Validation Boundary

* `tree_manager` must always reject structural impossibilities
* must reject cycles and self-parenting
* may allow schema-invalid parent-child combinations temporarily
* checklist system reports business-rule violations later

## Edge Cases

* reparenting node to its own descendant must be prevented
* deleting node during iteration is unsupported; callers must not mutate during iteration
* adding node with duplicate ID must be rejected
* moving node to invalid parent type may be allowed temporarily if structurally valid
* attempts to delete the root must be rejected
* same-parent movement must route through reorder logic

## API Direction

* `add_node(parent_id, node, index=None)`
* `remove_node(node_id)`
* `move_node(node_id, new_parent_id, index=None)`
* `reorder_node(node_id, new_index)`
* `get_parent(node_id)`
* `get_children(node_id)`

## Index Ownership

* `layout_model` owns the node index and remains the source of truth
* `tree_manager` receives references to the model and shared index
* `tree_manager` mutates structure through that shared state

## Return Values

* mutating operations return lightweight change records
* delete operations return deleted node IDs
* example change record:
  {
  "action": "delete",
  "affected_ids": ["panel_2", "button_4"]
  }

## Failure Model

* invalid structural operations raise exceptions
* duplicate IDs raise hard exceptions
* higher-level systems may wrap exceptions later if needed

## Scope Boundaries

* position and layout preservation are out of scope
* selection cleanup is out of scope
* batch operations are planned but not implemented
* subtree cloning is planned but not implemented

## Decisions Locked

* `layout_model` owns the index and `tree_manager` operates on it
* root is a synthetic implicit container with id `root`
* deletion is cascade delete
* moved nodes carry their full subtree
* lookup is index-based by node id
* insertion supports optional index placement
* same-parent movement is reordering, not reparenting
* mutating operations return lightweight change records
* structural failures raise exceptions
* `tree_manager` owns structural integrity, not UI validation

## Open Questions

* none currently locked out at the tree-manager level
