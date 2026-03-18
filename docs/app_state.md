# File: state/app_state.py

## Purpose

Provides a centralized container for core application subsystems. Acts as a stable access point for domain state without coordinating behavior.

## Responsibilities

* initialize and store core subsystems
* expose subsystem references
* provide minimal convenience accessors

## Owned Subsystems

* layout_model
* selection_state
* property_registry
* checklist_engine

## Initialization Order

1. property_registry
2. layout_model
3. selection_state
4. checklist_engine

## Inputs

* configuration (future)
* schema sources (via property_registry)

## Outputs

* access to core subsystems

## Access Pattern

* direct access:

  * state.layout_model
  * state.selection_state
  * state.property_registry
  * state.checklist_engine

* convenience methods:

  * get_selected_node()
  * get_node(node_id)

## Constraints

* must NOT contain UI logic
* must NOT coordinate interactions between systems
* must NOT trigger side effects automatically
* must remain stable after initialization

## Dependencies

* layout_model.py
* selection_state.py
* property_registry.py
* checklist_engine.py

## Mutability

* app_state is fixed after initialization
* internal subsystems are mutable

## Separation of Concerns

* UI components receive only the subsystems they need
* app_state is not globally injected into all components

## Edge Cases

* missing schema on startup
* initialization failure in core subsystems

## Future Extensions

* app settings (separate module)
* dependency injection patterns (if needed)

## Open Questions

* whether to introduce lightweight service locators later
