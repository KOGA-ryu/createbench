# File: checklist/checklist_engine.py

## Purpose

Evaluates the layout tree for completeness, validity, and structural correctness. Produces a structured set of issues with severity levels used by inspector and export systems.

## Responsibilities

* evaluate entire layout_model
* apply schema-driven and engine-level rules
* generate structured issue list
* provide summary counts
* support filtering by node

## Inputs

* layout_model (fully expanded state)
* property_registry (resolved schemas)

## Outputs

* checklist result:

  * summary (error/warning/info counts)
  * list of issues

## Issue Structure

Each issue includes:

* node_id
* property (optional)
* code (machine-readable)
* severity (error, warning, info)
* message (human-readable)

## Severity Model

* error:

  * blocks export
* warning:

  * non-blocking, should be addressed
* info:

  * optional guidance

## Rule Sources

### Schema-Driven Rules

* missing required properties
* invalid property types
* constraint violations:

  * min / max
  * allowed_values
  * regex
* invalid child types

### Engine-Level Rules

* unknown properties
* structural inconsistencies
* excessive nesting depth
* layout inconsistencies

## Evaluation Model

* full recomputation on:

  * property commit
  * structure change
* no incremental evaluation (MVP)

## Filtering

* supports:

  * full document issues
  * node-specific issues (by node_id)

## Unknown Properties

* always flagged
* default severity: warning

## Dependencies

* layout_model.py
* property_registry.py
* checklist_rules.py

## Constraints

* must NOT mutate nodes
* must NOT perform UI rendering
* must remain deterministic

## Edge Cases

* missing schema
* partially invalid node states
* deeply nested structures
* conflicting schema constraints

## Performance

* full scan of tree per evaluation (MVP)

## Open Questions

* when to introduce incremental evaluation
* when to introduce rule toggles or profiles
