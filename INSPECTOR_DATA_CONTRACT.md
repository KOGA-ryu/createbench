# Inspector Data Contract

## Purpose

This document defines the normalized inspector payload Create Bench must use when displaying information about a selected node.

This contract exists to solve a specific product problem:

- the user and the AI need a shared, explicit, inspectable reference object
- that object must expose what the visible thing is
- where it came from
- whether it is source-faithful or inferred
- what geometry and behavior rules currently apply

If a node cannot explain those things through the inspector contract, Create Bench is not serving its core job as a communication surface.

This contract is implementation law for inspector data.

It is written to support:

- Create Bench internal inspection
- Bluebench-backed source inspection through an adapter
- future repo extraction and source-faithful UI mapping

This contract does not require all fields to be available immediately.
It does require that:

- missing information is explicit
- inferred information is explicit
- mock information is explicit
- unsupported fields do not silently pretend to be source truth

## Core Principles

1. The inspector is a truth surface, not a convenience panel.
2. Geometry truth comes from Create Bench engine/layout state.
3. Source truth comes from mapped source data, not template assumptions.
4. Render truth comes from resolved render profile, not ad hoc canvas paint decisions.
5. Trust state must be explicit.
6. Missing data must remain visible as missing, not guessed silently.
7. The same node must resolve to the same inspector payload deterministically.

## Contract Scope

This contract governs:

- what data an inspector payload must contain
- what data may be omitted temporarily
- how source, layout, render, and relationship data are represented
- how trust state is communicated
- how adapters such as Bluebench may populate the contract

This contract does not govern:

- visual layout of the inspector UI
- number of inspector tabs
- docking vs detached window behavior
- source editing behavior
- diff tools

Those are implementation choices.
The data contract is the law beneath them.

## Canonical Inspector Payload

The canonical inspector payload shape is:

```json
{
  "node_id": "string",
  "node_type": "string",
  "ui_role": "string|null",
  "display_name": "string|null",
  "trust_level": "source|inferred|mock|partial",
  "selection_context": {
    "selected": true,
    "focused": false,
    "locked": false
  },
  "source": {
    "file": "string|null",
    "symbol": "string|null",
    "language": "string|null",
    "line_start": 0,
    "line_end": 0,
    "column_start": 0,
    "column_end": 0,
    "source_kind": "repo|generated|template|unknown",
    "source_id": "string|null"
  },
  "layout": {
    "layout_mode": "free|auto",
    "x": 0,
    "y": 0,
    "width": 0,
    "height": 0,
    "width_policy": "fixed|preferred|fill|null",
    "height_policy": "fixed|preferred|fill|null",
    "min_width": 0,
    "min_height": 0,
    "max_width": 0,
    "max_height": 0,
    "align_x": "left|center|right|null",
    "align_y": "top|center|bottom|null",
    "layout_root_id": "string|null",
    "geometry_source": "engine|explicit|inferred|unknown"
  },
  "render": {
    "render_kind": "string",
    "fill_style": "string",
    "show_header": false,
    "show_body": false,
    "show_border": true,
    "show_label": true,
    "content_alignment": "left|center|top",
    "padding": 0,
    "corner_radius": 0,
    "border_weight": 0,
    "draw_children_inside": false,
    "overlay_layer": false,
    "selection_style": "outline|glow|header_only",
    "lock_indicator": true,
    "render_source": "resolved_role|type_fallback|generic_fallback"
  },
  "relationships": {
    "parent": "string|null",
    "children": [],
    "related_nodes": [],
    "depends_on": [],
    "communicates_to": []
  },
  "provenance": {
    "representation_origin": "source|adapter|template|manual|unknown",
    "adapter": "string|null",
    "adapter_node_id": "string|null",
    "warnings": []
  },
  "raw": {
    "properties": {},
    "supported_overrides": {},
    "unsupported_overrides": {}
  }
}
```

## Required Fields

The following fields are required for every inspector payload:

- `node_id`
- `node_type`
- `ui_role`
- `display_name`
- `trust_level`
- `layout.layout_mode`
- `layout.x`
- `layout.y`
- `layout.width`
- `layout.height`
- `render.render_kind`
- `relationships.parent`
- `relationships.children`
- `provenance.representation_origin`
- `raw.properties`

If the real value is unknown, it must still be present with:

- `null`
- empty array
- empty object
- or explicit fallback enum value

The field must not disappear silently.

## Trust Level

`trust_level` is required and must always be one of:

- `source`
- `inferred`
- `mock`
- `partial`

Definitions:

- `source`
  - the visible representation is backed by direct repo/source extraction or authoritative mapped source data
- `inferred`
  - the representation is derived from heuristics or incomplete metadata
- `mock`
  - the representation is hand-authored or illustrative
- `partial`
  - part of the node is source-backed and part is inferred or missing

Inspector UI must never present a node as source-faithful if the contract resolves `inferred`, `mock`, or `partial`.

## Source Section

The `source` section answers:

- where this node came from
- what file or symbol it maps to
- what region in source is relevant

### Required behavior

- `source.file` may be null
- `source.symbol` may be null
- line/column bounds may be null or `0` when unavailable
- `source_kind` must always be explicit

### Allowed `source_kind` values

- `repo`
- `generated`
- `template`
- `unknown`

### Source rules

1. If the node is repo-backed, `source_kind` must not be `template`.
2. If the node comes from a hand-authored template, `source_kind` must be `template`.
3. If a source mapping is approximate, that must be reflected through `trust_level`, not hidden.
4. `source_id` may store an upstream stable id from Bluebench or another adapter.

## Layout Section

The `layout` section answers:

- what rect the engine currently believes
- how that rect was produced
- what policy governs each axis

### Required rules

1. `x`, `y`, `width`, `height` must reflect current engine/layout truth, not paint-only insets.
2. `layout_mode` must reflect the actual node layout mode.
3. `width_policy` and `height_policy` must reflect resolved layout policy when available.
4. `geometry_source` must be explicit.

### Allowed `geometry_source` values

- `engine`
- `explicit`
- `inferred`
- `unknown`

Definitions:

- `engine`
  - current geometry comes from engine computation
- `explicit`
  - geometry comes from explicit node properties in free layout
- `inferred`
  - geometry is estimated from heuristics or partial mapping
- `unknown`
  - current system cannot state the source of the geometry confidently

### Layout contract interaction

This inspector contract does not replace `LAYOUT_POLICY_CONTRACT.md`.
It must report the result of that contract.

If the engine cannot yet resolve full policy data, the payload must still surface:

- known resolved values where available
- `null` for missing policy data

It must not invent unsupported policy values.

## Render Section

The `render` section answers:

- what visual role the node is currently rendered as
- what profile flags are active
- whether render resolution came from role truth or fallback

### Required rules

1. `render_kind` must always be explicit.
2. `render_source` must always be explicit.
3. Unsupported role overrides must not silently appear as successful render resolution.

### Allowed `render_source` values

- `resolved_role`
- `type_fallback`
- `generic_fallback`

Definitions:

- `resolved_role`
  - render profile resolved from supported `ui_role` or supported role truth
- `type_fallback`
  - unsupported `ui_role` had zero effect and rendering fell back to supported `node_type`
- `generic_fallback`
  - neither role nor type resolved to a supported role-aware render profile

This section must reflect the result of `RENDER_PROFILE_CONTRACT.md`.

## Relationships Section

The `relationships` section answers:

- where this node sits in the visible structure
- what other nodes it is directly connected to

### Required fields

- `parent`
- `children`

### Optional but reserved now

- `related_nodes`
- `depends_on`
- `communicates_to`

These lists may be empty in early implementations.
They still belong in the contract now because Create Bench’s real job includes communicating structural and behavioral relationships clearly.

## Provenance Section

The `provenance` section is where Create Bench admits how the current representation was produced.

Required fields:

- `representation_origin`
- `adapter`
- `adapter_node_id`
- `warnings`

Allowed `representation_origin` values:

- `source`
- `adapter`
- `template`
- `manual`
- `unknown`

Definitions:

- `source`
  - directly built from authoritative project/source extraction
- `adapter`
  - built through an external system such as Bluebench
- `template`
  - from an authored template/scaffold
- `manual`
  - explicitly authored by user edits inside Create Bench
- `unknown`
  - system cannot currently determine the origin safely

Warnings are user-visible truths such as:

- source location missing
- geometry inferred
- unsupported ui_role ignored
- partial role resolution

## Raw Section

The `raw` section preserves the underlying authored node state and override truth.

Required fields:

- `properties`
- `supported_overrides`
- `unsupported_overrides`

Rules:

1. `raw.properties` is the current node property bag as stored.
2. `supported_overrides` lists overrides currently honored by the system.
3. `unsupported_overrides` lists authored override attempts that currently have zero effect.

This matters because Create Bench must not quietly pretend an override works when it does not.

## Resolution Order

Inspector payload resolution order:

1. start from current Create Bench node
2. resolve layout data from current engine/layout truth
3. resolve render data from current render profile truth
4. resolve source/provenance fields from mapped source or adapter data
5. compute trust level from the combination of available truth sources
6. surface unsupported overrides explicitly

The inspector must not reverse that order by inventing source truth from render or layout guesses.

## Bluebench Adapter Mapping

Bluebench can populate a subset of this contract through an adapter.

Useful Bluebench source fields:

- `id`
- `name`
- `type`
- `parent`
- `file_path`
- `line_number`
- `line_start`
- `line_end`

Useful Bluebench provenance fields:

- active run metadata
- warnings/comparison context

### Bluebench mapping example

```json
{
  "node_id": "<bluebench id>",
  "node_type": "<bluebench type>",
  "ui_role": null,
  "display_name": "<name>",
  "trust_level": "partial",
  "source": {
    "file": "<file_path>",
    "symbol": "<name>",
    "language": "python",
    "line_start": 12,
    "line_end": 24,
    "column_start": null,
    "column_end": null,
    "source_kind": "repo",
    "source_id": "<bluebench id>"
  },
  "provenance": {
    "representation_origin": "adapter",
    "adapter": "bluebench",
    "adapter_node_id": "<bluebench id>",
    "warnings": [
      "ui role unresolved from adapter",
      "layout geometry not source-backed"
    ]
  }
}
```

Bluebench does not currently provide:

- Create Bench `ui_role`
- Create Bench geometry
- Create Bench layout policy
- Create Bench render profile

So a Bluebench-backed inspector payload is necessarily partial unless Create Bench supplies those fields itself.

## Deferred Work

The contract is final-shape law.
The following implementation work may be deferred temporarily:

- direct repo extraction feeding the contract
- column-accurate source ranges
- relationship graphs beyond parent/children
- render/body/content rect reporting
- diff against source
- trust computation automation
- adapter validation diagnostics

If deferred, the inspector must still:

- keep the fields present
- mark unavailable fields explicitly
- mark trust honestly

## Non-Goals

This contract is not:

- a renderer contract
- a layout algorithm
- a source parser spec
- a diff protocol
- an inspector UI wireframe

It is only the normalized data truth the inspector must expose.

## Implementation Notes For First Adoption

The first Create Bench implementation may resolve this contract in layers:

1. node identity and raw properties
2. current geometry and layout mode
3. resolved render kind and render source
4. parent/children relationships
5. source mapping and provenance
6. trust-level automation

That is acceptable.

What is not acceptable is:

- hiding missing information
- presenting mock templates as source-faithful
- pretending unsupported overrides are active

## Source of Truth

If code and this document diverge, this document is the intended contract law and the implementation should be brought back into alignment deliberately.
