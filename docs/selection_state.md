# File: state/selection_state.py

## Purpose

Manages the currently selected node in the layout. Acts as a single source of truth for selection and notifies dependent systems of changes.

## Responsibilities

* store current selection (node_id)
* validate selection against layout_model
* update selection on user interaction or structural changes
* emit selection change events

## Inputs

* node_id (from canvas or system actions)

## Outputs

* current selection
* change notifications to subscribers

## Internal Logic

### Selection Storage

* stores selected node_id only
* resolves node via layout_model when needed

### Selection Updates

* set_selection(node_id):

  * validate node exists
  * update internal state
  * emit change event

* clear_selection():

  * clear selected node
  * emit change event

### Deletion Handling

* if selected node is deleted:

  * attempt to select parent
  * fallback to clearing selection

### Reselect Behavior

* selecting the same node triggers change event

### Event System

* supports simple subscription model:

  * subscribe(callback)
* emits on every selection change

## Dependencies

* layout_model.py (for validation)

## Constraints

* must NOT store node references
* must NOT contain UI logic
* must NOT know about inspector, canvas, or checklist

## Edge Cases

* selecting non-existent node
* node deleted during selection
* rapid selection changes

## Initial State

* no selection on startup

## Performance

* minimal, event-driven updates only

## Open Questions

* when to add selection history (undo/redo)
