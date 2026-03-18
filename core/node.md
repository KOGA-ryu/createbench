# File: core/node.py

## Purpose

Defines the fundamental unit of the UI layout system. Each node represents a UI element with type, properties, and hierarchical relationships.

## Responsibilities

* represent a single UI element
* store node identity and metadata
* store properties as key/value pairs
* maintain ordered list of children
* provide structured representation for layout_model
* track its parent by id

## Structure

Each node contains:

* id (unique identifier)
* type (base type or custom type)
* name (optional human-readable label)
* properties (dict of key/value pairs)
* parent_id (parent node id, top-level nodes use synthetic root id `root`)
* children (ordered list of child nodes)

## Inputs

* creation parameters (id, type, properties)
* property updates from inspector
* child node additions/removals

## Outputs

* structured node object
* serialized representation (dict/object form)

## Internal Logic

* stores properties without enforcing validation
* allows direct mutation of properties
* maintains strict ordering of children
* provides access to children and properties
* applies schema defaults at creation time
* may perform child checks only when schema/rule context is explicitly available

## Dependencies

* property_registry (external, defines schemas and defaults)
* used by layout_model

## Constraints

* must NOT enforce property validation (handled externally)
* must NOT contain UI logic
* must NOT handle rendering
* must NOT allow multiple parents
* must respect child-type restrictions (defined externally)
* must not exist in a truly uninitialized state with missing defaultable properties

## Child Rules

* allowed child types are defined externally (property_registry or rules)
* node enforces child-type restrictions only when schema/rule context is applied
* otherwise node remains structurally flexible during editing

## Custom Node Support

* supports plugin-style custom types via schema definitions
* schema defines:

  * allowed properties
  * default values
  * allowed children

## Edge Cases

* adding invalid child type
* missing required properties
* duplicate IDs (handled by layout_model)
* empty properties dict
* deeply nested structures
* parent_id mismatch with actual tree position

## Serialization Behavior

* outputs structured object:
  {
  "id": str,
  "type": str,
  "name": optional str,
  "parent_id": optional str,
  "properties": dict,
  "children": list
  }

* supports explicit-only serialization mode
* supports fully-expanded serialization mode
* fully-expanded mode includes schema defaults

## Ordering Rules

* child order is stable and significant
* child order determines visual layer order
* node must preserve append and indexed insertion order

## First-Class Node Types

* `document`
* `container`
* `vertical`
* `horizontal`
* `split`
* `sidebar`
* `toolbar`
* `main`
* `panel`
* `button`
* `text`
* `input`
* `list`

## Decisions Locked

* parent_id is stored on each node
* top-level nodes use synthetic root id `root` as parent
* defaults are applied immediately at creation
* child enforcement is schema-aware, not hard-coded
* custom node types are loaded through schema/template plugins
* node supports both explicit-only and fully-expanded serialization flows
