# Layout Policy Contract

## Purpose

This document defines the authoritative layout behavior for Create Bench.

It governs:
- how node roles resolve to layout behavior
- how preferred, fixed, and fill sizing work
- how parent layout distributes space
- how context-specific overrides are allowed
- how impossible layouts degrade

This contract is implementation law for:
- `engine/layout_engine.py`
- any future layout policy helpers
- schema/profile-backed layout behavior
- tests that assert layout intent

This contract does not define paint appearance. That belongs to [RENDER_PROFILE_CONTRACT.md](/Users/kogaryu/dev/createbench/RENDER_PROFILE_CONTRACT.md).

---

## Core Rule

Layout logic must represent how real UI behaves.

If a role says a node should keep a stable size, parent size must not silently force it to stretch.

The engine owns geometry truth.

---

## Sources Of Truth

### Structural type

`node.type` is the concrete structural/component type.

Examples:
- `button`
- `sidebar`
- `toolbar`
- `panel`
- `dialog`

### Semantic role

`ui_role` is the semantic layout/render role when specialization is needed.

Examples:
- `panel` with `ui_role="sidebar"`
- `panel` with `ui_role="dialog"`

### Resolution order

Layout role resolution must use:
1. explicit `ui_role`, if supported
2. `node.type`
3. category fallback
4. error/fallback profile

### Conflict rule

If `node.type` and `ui_role` disagree:
- layout policy: `ui_role` wins if the role system explicitly allows it
- structural validity: `node.type` wins unless a declared structural override exists

---

## Axis Policy Model

Layout policy is per axis.

Each node resolves:
- `width_policy`
- `height_policy`

Allowed policy values:
- `fixed`
- `preferred`
- `fill`

### Meaning

#### `fixed`

The node keeps an explicit stable size on that axis.

Use for:
- hard-sized controls
- intentionally fixed chrome
- detached windows with explicit dimensions

#### `preferred`

The node wants a preferred size on that axis, usually from content, schema defaults, or explicit preferred-size properties.

It does not automatically fill extra space.

Use for:
- buttons
- text labels
- inputs
- many panels by default

#### `fill`

The node is eligible to absorb available remaining space on that axis.

Use for:
- `main` regions
- `sidebar` height
- `toolbar` width
- container-like work regions

---

## Preferred Size Resolution

Preferred size resolution order must be:
1. explicit instance property
2. schema/profile preferred size
3. intrinsic heuristic from content
4. fallback default

Examples:
- a user-edited sidebar width becomes explicit preferred width
- a button uses text-based width if no explicit preferred width exists
- a toolbar uses schema/profile preferred height if not overridden

### Important rule

If a user edits width or height on an auto-layout node, that becomes explicit preferred size.

It does not:
- silently switch to free layout
- get ignored

Only out-of-flow direct manipulation such as drag/move may imply switching to free layout.

---

## Role Table

This is the target finished behavior.

| Role | Width Policy | Height Policy | Default Alignment |
|---|---|---|---|
| `button` | `preferred` | `preferred` | left/top by parent defaults |
| `text` | `preferred` | `preferred` | left/top by parent defaults |
| `input` | `preferred` | `preferred` | left/top by parent defaults |
| `toolbar` | `fill` | `preferred` | left/top |
| `sidebar` | `preferred` | `fill` | left/top |
| `main` | `fill` | `fill` | left/top |
| `panel` | `preferred` | `preferred` | left/top |
| `dialog` | `preferred` | `preferred` | overlay/detached rules apply |
| `popup` | `preferred` | `preferred` | overlay/detached rules apply |
| `tool_window` | `preferred` | `preferred` | overlay/detached rules apply |

### Notes

- `panel` is context-sensitive.
- `text` is context-sensitive.
- `input` is context-sensitive.
- Context sensitivity must come from declared override rules, not ad hoc inference.

---

## Context Overrides

Context overrides are allowed, but only when declared by the role system.

Examples of allowed context-sensitive behavior:
- `input` in a form row may become `fill` on width
- `text` with a body-text role may become `fill` on width and `preferred` on height
- `panel` in a dashboard may become `preferred/fill`
- `panel` as a work surface may become `fill/fill`

### Rule

Context overrides must be explicit and deterministic.

They must not be inferred from vague heuristics like:
- “it looks like a form”
- “it has children so fill it”

The system must declare:
- what context exists
- what override is allowed
- which role it applies to

---

## Parent Layout Rules

### Vertical parents

Examples:
- `document`
- `vertical`
- `container` by default unless explicitly horizontal

Behavior:
1. measure children
2. resolve each child's height policy
3. fixed/preferred-height children keep measured or preferred height
4. fill-height children share remaining height
5. cross-axis width respects child width policy
6. default cross-axis alignment is left

### Horizontal parents

Examples:
- `horizontal`

Behavior:
1. measure children
2. resolve each child's width policy
3. fixed/preferred-width children keep measured or preferred width
4. fill-width children share remaining width
5. cross-axis height respects child height policy
6. default cross-axis alignment is top

---

## Cross-Axis Alignment

Alignment belongs to layout policy.

Supported horizontal alignment within wider parents:
- `left`
- `center`
- `right`

Supported vertical alignment within taller parents:
- `top`
- `center`
- `bottom`

Default alignment rules:
- fixed/preferred width inside vertical parent: `left`
- fixed/preferred height inside horizontal parent: `top`

### Rule

Parent layout must not silently override a child's fixed or preferred cross-axis size just to fake uniformity.

If a child is `preferred` or `fixed` on the cross-axis, parent must respect it unless:
- the child explicitly opts into `fill`
- a declared context rule upgrades that axis to `fill`

---

## Space Deficit Rules

When available space is smaller than total requested space:
1. honor minimum sizes
2. fixed/preferred children shrink only if explicit shrink policy allows it
3. fill children lose space first
4. overlap is never automatic
5. if still impossible, overflow or clipping must be explicit

### Rule

The engine must not silently overlap children to satisfy layout.

If impossible:
- clamp
- overflow
- or clip explicitly

But never collapse into accidental overlap as a hidden fallback.

---

## Equal-Split Fallback

Equal split is not the default behavior for real UI roles.

Equal split may exist only as a fallback for:
- unsupported node types
- generic layout containers with no declared preferred/fill behavior

Equal split must not override known role behavior for:
- `button`
- `text`
- `input`
- `toolbar`
- `sidebar`
- `main`
- `dialog`
- `popup`
- `tool_window`

---

## Free Layout Rule

If `layout_mode == "free"`:
- explicit `x`, `y`, `width`, `height` define geometry
- layout policy does not override those dimensions
- min/max and parent/canvas bounds still apply

Intrinsic or preferred size must not overwrite explicit free geometry.

---

## Overlay And Detached Roles

The following are first-class roles:
- `dialog`
- `popup`
- `tool_window`

They must exist in the layout contract now, even if implementation is partial.

They affect:
- layout participation
- z-layer participation
- hit-testing priority later
- render profile later

### Rule

Overlay and detached roles are not ordinary in-flow children.

Even before full implementation, the contract must recognize that distinction.

---

## Required Engine Outputs

The final layout-capable system should expose at least:
- outer rect
- content/body rect where applicable
- header rect where applicable

Temporary implementations may compute only outer rects first, but the final contract requires content-aware layout regions.

---

## Deferred Work

The following may be deferred in implementation, but not in contract:
- full shrink policy
- explicit stretch priorities
- explicit content min/content max policy
- content/body rect-aware child placement
- overlay role-specific placement rules
- context override tables beyond the first supported roles

If deferred, implementation must document:
- what is partial
- what rule is being temporarily approximated
- what remains to reach contract compliance

---

## Non-Goals

This contract does not define:
- paint style
- theming
- border colors
- selection chrome
- icon systems
- typography
- export format
- import packet shape
- bench mode

Those belong elsewhere.

---

## Pseudocode Shape

```python
role = resolve_layout_role(node)
policy = resolve_axis_policy(role, parent_context)
preferred = resolve_preferred_size(node, role, policy)

if parent_orientation == "vertical":
    fixed_or_preferred_children = [...]
    fill_children = [...]
    remaining_height = available_height - sum(child.height for child in fixed_or_preferred_children)
    assign fill heights from remainder
    assign widths by each child's width policy
elif parent_orientation == "horizontal":
    fixed_or_preferred_children = [...]
    fill_children = [...]
    remaining_width = available_width - sum(child.width for child in fixed_or_preferred_children)
    assign fill widths from remainder
    assign heights by each child's height policy
```

---

## Governing Rule

Buttons must become button-sized because the layout contract says they are `preferred/preferred`.

Toolbars must become toolbar-sized because the layout contract says they are `fill/preferred`.

Main regions must fill because the layout contract says they are `fill/fill`.

If a node stretches incorrectly, the layout contract is being violated.
