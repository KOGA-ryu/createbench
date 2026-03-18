# File: export/dsl_builder.py

## Purpose

Generates deterministic, human-readable DSL and JSON representations of the layout tree for external use (e.g., AI interaction, tooling).

## Responsibilities

* build DSL output from layout_model
* build JSON output from layout_model
* enforce deterministic formatting
* support export modes (explicit vs expanded)
* integrate with checklist validation

## Outputs

* DSL string (nested format)
* JSON object

## Export Modes

* explicit:

  * only user-set properties
* expanded:

  * all resolved properties (including defaults)

## DSL Structure

### Header

* includes:

  * version
  * export mode

Example:
@create_bench v1
@mode expanded

### Node Format

* uses nested structure:

node <type> id=<id>
prop <key> = <value>
node <child> ...

### Unknown Properties

* emitted under:
  unknown:
  key = value

### Value Formatting

* string -> "text"
* number -> 42, 3.14
* bool -> true/false
* reference -> node_id

## JSON Structure

* explicit object representation:

  * id
  * type
  * properties
  * children

## Determinism Rules

* child order preserved
* property keys sorted
* output stable across runs

## Validation Behavior

* export blocked if checklist contains errors
* builder raises on invalid state

## Scope

* exports full document only (MVP)
* synthetic root excluded

## Dependencies

* layout_model.py
* property_registry.py
* checklist_engine.py

## Constraints

* must NOT mutate nodes
* must NOT include UI logic
* must remain deterministic

## Edge Cases

* missing schema
* unknown properties
* partially invalid nodes

## Future Extensions

* subtree export
* metadata flags in JSON
* export bundles (DSL + JSON + checklist)

## Open Questions

* when to support alternative DSL formats
