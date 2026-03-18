# File: ui/main_window.py

## Purpose

Assembles the main application window and arranges core UI components: canvas, inspector, and checklist.

## Responsibilities

* construct main window layout
* instantiate UI components
* wire components to required subsystems
* define layout structure using splitters

## Layout Structure

### Primary Layout

* horizontal splitter:

  * left: canvas
  * right: right_panel

### Right Panel

* vertical splitter:

  * top: inspector
  * bottom: checklist

## Components

* canvas_widget
* inspector_panel
* checklist_panel

## Inputs

* core subsystems (passed from app_state or setup layer):

  * layout_model
  * selection_state
  * property_registry
  * checklist_engine

## Outputs

* fully constructed UI window

## Splitter Behavior

* horizontal splitter:

  * resizable canvas vs right panel
* vertical splitter:

  * resizable inspector vs checklist

## Default Sizes

* canvas: ~70%
* right panel: ~30%
* inspector: ~60% of right panel
* checklist: ~40% of right panel

## Constraints

* must NOT contain business logic
* must NOT manage state transitions
* must NOT perform validation
* must only wire components together

## Dependencies

* canvas_widget.py
* inspector_panel.py
* checklist_panel.py

## Edge Cases

* window resizing
* minimum sizes of panels

## Performance

* static layout, no dynamic restructuring

## Future Extensions

* persistent layout (save splitter positions)
* detachable panels
* multi-window support

## Open Questions

* when to introduce layout persistence
