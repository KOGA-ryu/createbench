# Bluebench Integration Notes

## Purpose

This document defines how Bluebench relates to Create Bench and how its inspector capabilities should be used without confusing code-graph truth for UI truth.

Bluebench is relevant because it already provides:

- code-aware inspection
- structural context
- file and symbol visibility
- stable node inspection payloads
- detached inspector windows

Bluebench is not, by itself, a UI-faithful renderer or layout source for Create Bench.

This document exists to prevent a bad integration path:

- copying the Bluebench inspector wholesale
- then pretending that code-node metadata alone is enough to express UI truth

It is not enough.

Bluebench should be treated as:

- a useful upstream source of source/structure/provenance data
- an adapter candidate
- a reference implementation for inspector workflow

It should not be treated as:

- the final Create Bench inspector model
- the final Create Bench node model
- the final Create Bench layout/render truth source

## What Bluebench Already Has

Based on the current Bluebench implementation in:

- [backend/main.py](/Users/kogaryu/dev/bluebench/backend/main.py)
- [backend/api/bridge.py](/Users/kogaryu/dev/bluebench/backend/api/bridge.py)
- [docs/node_inspector_window.md](/Users/kogaryu/dev/bluebench/docs/node_inspector_window.md)
- [docs/bluebench_architecture.md](/Users/kogaryu/dev/bluebench/docs/bluebench_architecture.md)

Bluebench already provides these useful inspection capabilities:

### 1. Normalized node inspection entry

Selection flow:

- graph selection event
- canonical node resolution
- normalized inspector payload
- detached inspector window creation or refresh

This is useful to Create Bench because it shows a stable way to map selection into an inspectable object.

### 2. Stable per-node inspector windows

Bluebench keeps one inspector window per node id.

This is useful because Create Bench will also need stable reference surfaces where:

- one visible node maps to one inspector instance
- reselection refreshes rather than duplicating

### 3. Source anchoring

Bluebench payloads already carry:

- `id`
- `name`
- `type`
- `parent`
- `file_path`
- `line_number`
- `line_start`
- `line_end`

This is directly relevant to Create Bench because repo-faithful UI representation requires:

- file mapping
- symbol mapping
- region mapping

### 4. Structural relationship surfacing

Bluebench inspector exposes:

- file-local outline
- file relationships
- parent context
- related module relationships

Create Bench will need its own version of this for UI structure:

- parent / children
- communicating regions
- source component relationships

### 5. Provenance mindset

Bluebench carries run and comparison context such as:

- active run
- previous run
- warnings
- compute summaries

Create Bench does not need the compute UI itself.
It does need the same mindset:

- where did this representation come from
- what evidence supports it
- what warnings apply

## What Bluebench Does Not Solve For Create Bench

Bluebench is a code graph tool.
Create Bench is a UI representation and communication tool.

Bluebench does not currently provide the fields Create Bench needs for truthful UI work:

- `ui_role`
- layout mode
- engine geometry
- layout policy
- render profile
- trust level for UI representation
- whether the current visual is source-faithful, inferred, mock, or partial
- content/body/header rect distinctions
- UI-specific interaction relationships

This means Bluebench cannot be copied directly as the Create Bench inspector.

At best, Bluebench can satisfy the source-facing subset of the Create Bench inspector contract.

## Recommended Integration Model

The correct near-term model is:

- Create Bench owns the inspector contract
- Bluebench may supply source/provenance data through an adapter
- Create Bench merges that with its own layout and render truth

In other words:

- Create Bench is the contract owner
- Bluebench is an upstream data provider

This avoids a bad coupling where Create Bench becomes dependent on Bluebench internal graph assumptions.

## Adapter Boundary

Bluebench integration should happen through a narrow adapter boundary.

Recommended adapter responsibility:

1. accept a Create Bench node or mapped source reference
2. query Bluebench for matching code-node data
3. normalize Bluebench output into the Create Bench inspector contract
4. mark all Bluebench-provided fields as adapter-backed provenance

The adapter must not:

- overwrite Create Bench geometry truth
- invent `ui_role`
- invent render profile truth
- silently promote adapter data to source-faithful UI truth

## Bluebench Fields Worth Reusing

These fields are worth reusing directly or near-directly:

- `id`
- `name`
- `type`
- `parent`
- `file_path`
- `line_number`
- `line_start`
- `line_end`

These fields are useful but optional:

- `call_path_total_compute`
- `active_run_id`
- `active_run_name`
- `active_run_scenario`
- `active_run_hardware`
- `active_run_status`
- `active_run_comparison_warnings`

These are useful mostly as provenance or diagnostics, not as core inspector identity.

## Bluebench Fields That Must Not Be Misinterpreted

The following must not be mistaken for Create Bench UI truth:

- Bluebench `type`
  - code graph type is not automatically Create Bench `ui_role`
- Bluebench line range
  - source region is not geometry
- Bluebench relationship graph
  - code dependencies are not UI containment
- Bluebench compute score
  - performance metadata is not visual/render truth

This distinction matters because Create Bench must remain honest about what the user is seeing.

## Recommended Mapping Strategy

Create Bench should resolve inspector data in this order:

1. Create Bench node identity
2. Create Bench geometry and layout policy
3. Create Bench render profile
4. Bluebench adapter source data
5. provenance and trust-level resolution

Bluebench should never be allowed to replace steps 1 through 3.

## Mapping Table

Suggested mapping from Bluebench to Create Bench inspector contract:

| Bluebench field | Create Bench target | Notes |
| --- | --- | --- |
| `id` | `source.source_id` or `provenance.adapter_node_id` | keep separate from Create Bench `node_id` unless they are intentionally identical |
| `name` | `display_name` or `source.symbol` | depends on mapping quality |
| `type` | provenance-only or source classification | not automatic `ui_role` |
| `parent` | `relationships.related_nodes` or source relationship note | not automatic UI parent |
| `file_path` | `source.file` | direct mapping |
| `line_number` | `source.line_start` | if no better start/end info |
| `line_start` | `source.line_start` | direct mapping |
| `line_end` | `source.line_end` | direct mapping |
| active run fields | `provenance.warnings` or future diagnostics | optional |

## Reuse Recommendation

Best near-term approach:

- reuse the Bluebench inspector concept
- reuse Bluebench’s normalized source payload shape where practical
- do not embed Bluebench UI wholesale
- do not make Create Bench depend on Bluebench tabs, compute UI, or graph manager internals

This is best described as:

- adapter reuse
- not widget reuse

## Why Blind Reuse Is Dangerous

Blind reuse would create several problems:

1. Create Bench would inherit Python/code-graph assumptions as if they were UI truth.
2. The inspector would be code-centric when Create Bench needs combined code/layout/render truth.
3. Missing UI-role and trust-level fields would be hidden under a familiar-looking inspector window.
4. The user would see inspection data that looks authoritative but is incomplete for UI work.

That is exactly the kind of trust failure Create Bench is meant to prevent.

## Good Integration Target

Create Bench’s final inspector should feel like:

- Bluebench’s source-awareness
- plus Create Bench’s geometry truth
- plus Create Bench’s layout policy truth
- plus Create Bench’s render profile truth
- plus explicit provenance and trust state

Bluebench alone gives only one of those layers cleanly.

## Implementation Sequence

Recommended order:

1. lock `INSPECTOR_DATA_CONTRACT.md`
2. implement Create Bench local inspector payload resolution for current nodes
3. add provenance/trust fields even if many are initially `mock` or `partial`
4. add Bluebench adapter for source-backed fields
5. only then consider UI reuse patterns such as detached windows or code panes

This order matters because:

- contract first keeps integration honest
- local payload first prevents Bluebench from becoming the accidental owner of inspector truth

## Deferred Work

The following may be deferred after the initial contract adoption:

- live Bluebench process integration
- deep symbol mapping
- two-way selection sync
- code diff and compare
- source jump actions
- richer relationship sections
- evidence ranking and conflict display

What may not be deferred conceptually:

- provenance honesty
- trust-level honesty
- separation between source data and UI truth

## Non-Goals

This document does not propose:

- embedding Bluebench inside Create Bench
- making Bluebench the source of geometry truth
- making Bluebench the source of render truth
- importing Bluebench’s compute UI into Create Bench
- coupling Create Bench node ids to Bluebench node ids by default

## Decision Summary

Bluebench should be integrated as an adapter-backed source inspection provider.

It should not be treated as:

- the Create Bench inspector itself
- the owner of Create Bench node semantics
- the owner of layout or render truth

Create Bench must own:

- inspector contract
- geometry truth
- layout policy truth
- render profile truth
- trust-state presentation

Bluebench may strengthen:

- source mapping
- symbol visibility
- structural code context
- provenance detail

That is the correct relationship between the two systems.
