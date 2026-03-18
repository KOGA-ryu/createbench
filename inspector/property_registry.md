# File: inspector/property_registry.py

## Purpose

Defines and manages node schemas, including properties, defaults, inheritance, and validation rules. Acts as the central authority for node definitions and inspector generation.

## Responsibilities

* load and validate schemas (built-in and external)
* provide schema lookup by node type
* apply inheritance and property merging
* supply default values for node creation
* define allowed child types
* provide metadata for inspector generation
* flag unknown or invalid properties

## Schema Structure

Each node schema includes:

* version
* display_name
* category (layout, region, component, etc.)
* extends (optional parent type)
* layout (bool)
* allowed_children (list of types or category tokens like "@component")
* properties (dict)

Each property includes:

* type (int, float, string, bool, enum, color, reference)
* default (optional)
* required (bool)
* group (layout, appearance, content, behavior, data)
* ui (optional override)
* constraints:

  * min
  * max
  * allowed_values
  * regex
* reference targets (for reference type)

## Inheritance Rules

* child schema extends a single parent
* properties are merged:

  * parent properties first
  * child overrides by key
* explicit removal supported via:

  * "remove": [property_keys]

## Inputs

* built-in schema files
* external schema files (user-defined)

## Outputs

* resolved schema objects
* property definitions with defaults
* inspector metadata

## Internal Logic

### Schema Loading

* load all schema files from:

  * core schemas directory
  * external schemas directory
* validate structure strictly
* fail on invalid schema

### Property Resolution

* apply inheritance
* merge properties
* apply removals
* produce final schema

### Default Injection

* provide defaults for node creation
* ensure nodes are initialized with valid baseline properties

### Allowed Children

* supports:

  * explicit types
  * category tokens (e.g., "@component")

### Unknown Properties

* allowed but flagged
* preserved during serialization

## Dependencies

* node.py
* layout_model.py
* used by inspector and checklist systems

## Constraints

* must NOT contain UI rendering logic
* must NOT mutate nodes directly
* must remain deterministic

## Edge Cases

* circular inheritance (must reject)
* missing parent schema
* invalid property definitions
* conflicting property overrides
* unknown property types

## External Schema Support

* schemas loaded from folder
* one node type per file
* identical format to built-in schemas

## Serialization Behavior

* does NOT serialize nodes directly
* provides schema context for export system

## Open Questions

* how to cache resolved schemas for performance
* whether to support schema hot-reload in editor
