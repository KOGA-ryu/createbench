# Mode Model Contract

## Purpose

This document defines the operational modes of Create Bench and the rules that govern:

- how nodes are interpreted
- how layout and render behave
- how trust is enforced
- what the user is allowed to modify

This prevents mixing:

- source-backed UI
- design/mock UI
- isolated editing work

This contract is implementation law for mode resolution and edit gating.

## Core Principle

Every node must be viewed in exactly one mode at a time.

Modes are not visual styles.
Modes are interpretation layers over the same node data.

If the system cannot resolve a node into exactly one mode, the node is not safe to edit.

## Supported Modes

### 1. Source Mode

#### Purpose

Inspect and represent real UI from code or runtime.

#### Rules

- source truth outranks all other representations
- layout and structure must reflect source-backed information when available
- Create Bench must not override:
  - structure
  - layout, if source-backed
  - role, if source-backed
- missing data is allowed but must be explicit
- inferred data must be marked

#### Allowed Behavior

- selection
- inspection
- navigation
- highlighting relationships

#### Disallowed Behavior

- arbitrary geometry edits
- silent layout overrides
- role reassignment without explicit conversion

#### Trust Requirements

- must expose `trust_level`
- must expose `representation_origin`
- must not present inferred or mock data as source

### 2. Design Mode

#### Purpose

Create and shape UI without requiring source backing.

#### Rules

- nodes are treated as mock or inferred
- layout follows `LAYOUT_POLICY_CONTRACT.md`
- render follows `RENDER_PROFILE_CONTRACT.md`

#### Allowed Behavior

- add/remove nodes
- change layout policy
- change roles
- edit geometry in auto or free layout
- apply templates

#### Trust Requirements

- nodes default to `mock` or `inferred`
- source fields may be null
- must not imply source linkage

### 3. Bench Mode

#### Purpose

Isolate a subtree or component for focused editing.

#### Definition

A bench session is a projection of one or more nodes into a separate working surface.

#### Rules

- bench nodes maintain linkage to original node ids
- bench nodes may diverge in:
  - geometry
  - layout
  - role
- bench does not mutate source or design nodes unless explicitly committed

#### Allowed Behavior

- clone subtree
- reposition freely
- edit layout and role
- test variations

#### Required Behavior

- lineage must be preserved
- origin node must be traceable
- trust must reflect divergence

#### Trust Rules

- cloned from source -> `partial`
- cloned from design -> `mock`
- edited beyond source -> trust must downgrade

## Mode Resolution

Mode is determined by:

```text
node context + view context
```

Resolved mode must be explicit.
It must not be inferred ad hoc during render or edit handling.

### Resolution Order

1. If the current view is a bench projection, the node resolves as `bench`
2. Else if the node is source-backed and opened in a source-faithful view, the node resolves as `source`
3. Else the node resolves as `design`

### Required Mode Fields

Each inspected or rendered node must be able to resolve:

```json
{
  "resolved_mode": "source|design|bench",
  "representation_origin": "source|adapter|template|manual|unknown",
  "trust_level": "source|inferred|mock|partial",
  "origin_node_id": "string|null",
  "bench_session_id": "string|null"
}
```

### Mode Precedence

If multiple truths exist, precedence is:

1. `bench`
2. `source`
3. `design`

Meaning:

- a bench projection linked to source is still operationally `bench`
- a source-backed node opened in normal inspection remains `source`
- a mock/template/manual node remains `design`

## Mode Behavior Matrix

### Source Mode

- layout authority:
  - source-backed layout if available
  - otherwise explicit inferred layout, marked as inferred
- render authority:
  - source-backed role if available
  - otherwise resolved role with trust downgrade
- geometry edits:
  - disallowed by default
- role edits:
  - disallowed by default
- structural edits:
  - disallowed by default
- templates:
  - disallowed
- inspector:
  - full source and provenance visibility required

### Design Mode

- layout authority:
  - Create Bench layout policy contract
- render authority:
  - Create Bench render profile contract
- geometry edits:
  - allowed
- role edits:
  - allowed
- structural edits:
  - allowed
- templates:
  - allowed
- inspector:
  - must show mock or inferred provenance honestly

### Bench Mode

- layout authority:
  - Create Bench layout policy on the bench projection
- render authority:
  - Create Bench render profile contract
- geometry edits:
  - allowed
- role edits:
  - allowed
- structural edits:
  - allowed inside bench
- commit back:
  - explicit only
- inspector:
  - must show origin id, bench session id, and divergence state

## Edit Gating Rules

### Source Mode

Must block:

- drag/move that changes committed geometry
- resize that changes committed geometry
- role reassignment
- structural add/remove
- silent conversion to free layout

May allow later through explicit action:

- convert to design
- send to bench
- create editable fork

### Design Mode

Must allow:

- free and auto layout edits
- role reassignment
- geometry edits
- template application
- structural edits

### Bench Mode

Must allow:

- isolated edits without mutating origin
- free rearrangement
- role experiments
- subtree restructuring

Must require explicit action for:

- commit back
- replace origin
- merge selected changes

## Trust Enforcement

### Global Rule

Mode does not replace trust.

A node in any mode must still expose:

- `trust_level`
- `representation_origin`

### Required Combinations

#### Source Mode

Allowed trust:

- `source`
- `inferred`
- `partial`

Disallowed default:

- `mock`

#### Design Mode

Allowed trust:

- `mock`
- `inferred`

Disallowed default:

- `source`

#### Bench Mode

Allowed trust:

- `partial`
- `mock`
- `inferred`

Special rule:

- bench cloned from source starts as `partial`
- bench cloned from design starts as `mock`

## Conversion Rules

### Source -> Design

Allowed only through explicit conversion.

Effect:

- breaks source-authoritative edit restrictions
- preserves provenance
- downgrades trust to `partial` or `mock` depending on retained linkage

### Source -> Bench

Allowed explicitly.

Effect:

- creates bench projection
- preserves origin id
- mode becomes `bench`
- trust becomes at least `partial`

### Design -> Bench

Allowed explicitly.

Effect:

- creates bench projection
- preserves origin id if applicable
- trust remains `mock` unless external source linkage exists

### Bench -> Design

Allowed on detach or save-as-design.

Effect:

- removes bench-only session context
- preserves lineage in provenance if desired
- resulting node is `design`

### Bench -> Source

Not automatic.

Requires explicit merge or commit workflow.
Must validate what can legally flow back.

## Layout And Render Interpretation By Mode

### Source Mode

- source-backed layout must win over local heuristics
- source-backed role must win over local role guesses
- inferred missing values may be filled for display only
- inferred values must not become authoritative edits

### Design Mode

- layout policy contract governs geometry
- render profile contract governs appearance
- role changes are local design truth

### Bench Mode

- same layout and render behavior as design for editing
- but with preserved lineage and divergence markers

## Inspector Requirements By Mode

### Source Mode Inspector Must Show

- source file
- source symbol
- source range
- trust level
- representation origin
- whether geometry is source-backed or inferred
- whether role is source-backed or inferred

### Design Mode Inspector Must Show

- node id
- node type
- ui_role
- geometry
- layout policy
- render profile
- trust level
- representation origin of `template`, `manual`, or `unknown`

### Bench Mode Inspector Must Show

- origin node id
- bench session id
- divergence summary
- current local geometry, layout, and role
- trust downgrade reason

## Non-Goals

This mode model does not define:

- bench merge mechanics
- runtime extraction protocol
- source parser format
- render implementation details
- exact UI chrome for mode badges

## Minimal Implementation Order

1. add explicit `resolved_mode` to inspector payload
2. gate editing by mode
3. surface trust and origin everywhere in inspector
4. add explicit source-to-design and source-to-bench conversion actions
5. add bench lineage fields before bench editing ships

## Blunt Rule

If the system cannot say whether a node is `source`, `design`, or `bench`, then it is not safe to edit.

## Source of Truth

If code and this document diverge, this document is the intended contract law and the implementation should be brought back into alignment deliberately.
