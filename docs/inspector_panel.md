# File: inspector/inspector_panel.py

## Purpose

Provides a docked panel for inspecting and editing properties of the currently selected node using schema-driven UI generation.

## Responsibilities

* subscribe to selection state
* rebuild UI when selection changes
* render property fields based on resolved schema
* group properties by schema-defined groups
* handle user input and update node properties
* display validation and completeness indicators
* expose unknown properties separately

## Inputs

* selected node (via selection state)
* resolved schema (via property_registry)

## Outputs

* UI representation of node properties
* property updates applied to node
* change signals (optional, for state systems)

## Internal Logic

### Selection Handling

* subscribes to selection changes
* on change -> rebuild entire inspector UI

### Property Rendering

* fields generated dynamically from schema
* grouped by property group:

  * layout
  * appearance
  * content
  * behavior
  * data
* order follows schema declaration

### Field Behavior

* text/number inputs:

  * store local value while editing
  * commit on blur/enter
* bool/enum:

  * commit immediately

### Validation

* invalid input:

  * not committed to node
  * field shows strong error indicator

### Required Properties

* missing required fields:

  * visually highlighted
  * flagged for checklist system

### Unknown Properties

* shown in separate "Unknown Properties" section
* editable and removable
* flagged visually

### Default Handling

* default values already applied at node creation
* inspector shows distinction between:

  * default values
  * user-modified values

### Reset to Default

* each property supports reset action
* resets value to schema default

### Inheritance Indicators

* inherited properties marked subtly

### Reference Properties

* MVP:

  * text input + validation
* future:

  * constrained node picker

### Empty State

* if no node selected:

  * show instruction panel

### Missing Schema

* if node has no schema:

  * show raw properties
  * display error banner

## Dependencies

* property_registry.py
* layout_model.py
* selection_state.py

## Checklist Interaction

* inspector commits trigger checklist recomputation
* checklist updates live on committed changes
* structural changes also trigger checklist recomputation
* selection changes update selected-node issue highlighting
* inspector highlights issues for selected node based on checklist results

## Constraints

* must NOT contain business logic
* must NOT validate schema correctness
* must NOT manage layout structure
* must rebuild UI simply (no diffing)

## Edge Cases

* rapid selection changes
* partially invalid user input
* unknown property keys
* missing schema definitions

## Performance

* full rebuild on selection change
* no optimization in MVP

## Open Questions

* when to introduce collapsible groups
* when to introduce reference pickers
