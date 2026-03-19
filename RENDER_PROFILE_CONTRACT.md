# Render Profile Contract

## Purpose

This document defines the authoritative canvas rendering behavior for Create Bench.

It governs:
- what a node looks like on canvas
- how roles render differently
- how headers, bodies, and overlays are drawn
- how selection and lock states are painted
- how fallback rendering behaves

This contract is implementation law for:
- `canvas/canvas_widget.py`
- any future render profile resolver
- role-specific draw functions
- tests that assert visual role distinctions

This contract does not decide geometry. Geometry truth belongs to [LAYOUT_POLICY_CONTRACT.md](/Users/kogaryu/dev/createbench/LAYOUT_POLICY_CONTRACT.md).

---

## Core Rule

The canvas owns render truth.

The engine computes where a node is and how large it is.

The canvas decides how that node looks inside the rect the engine gives it.

If two roles have different meaning, they must render differently on canvas.

---

## Render Profile Shape

Minimum resolved render profile:

```python
{
    "render_kind": str,
    "fill_style": str,
    "show_header": bool,
    "show_body": bool,
    "show_border": bool,
    "show_label": bool,
    "content_alignment": "left" | "center" | "top",
    "padding": int,
    "corner_radius": int,
    "border_weight": int,
    "draw_children_inside": bool,
    "overlay_layer": bool,
    "selection_style": "outline" | "glow" | "header_only",
    "lock_indicator": bool,
}
```

This is the minimum contract for believable role-specific rendering.

---

## Resolution Rules

Render profile resolution order must be:
1. explicit role profile
2. type profile
3. generic category profile
4. fallback unknown/error profile

### Overrides

Base render profile comes from role/type contract.

Instance-level overrides are allowed only through explicitly supported override fields.

Allowed override examples:
- title visibility
- icon visibility
- theme token
- label text

Disallowed override examples unless explicitly supported:
- arbitrary mutation of core role semantics
- silently converting a toolbar into a dialog by random property override

Unsupported overrides must be:
- rejected
- or visibly ignored

Never silently accepted into undefined behavior.

---

## Role And Type Authority

### Structural type

`node.type` is the concrete node type.

### Semantic role

`ui_role` is the semantic render role when refinement is needed.

### Conflict rule

If `node.type` and `ui_role` disagree:
- render profile: `ui_role` wins
- structural validity: `node.type` remains authoritative unless explicitly overridden elsewhere

---

## Global Canvas Rendering Rules

### 1. Selection is paint-only

Selection may change:
- outline color
- outline thickness
- handle visibility
- subtle highlight

Selection must never change:
- `x`
- `y`
- `width`
- `height`
- layout result

### 2. Render inside the engine rect

Canvas draws inside the rect the engine gives it.

If the canvas uses visual inset, that inset is paint-only.

It must not redefine geometry.

### 3. Labels do not define geometry during paint

Canvas text reflects node state.

Canvas text must not resize or relayout a node while painting.

### 4. Different roles must render differently

If `button`, `sidebar`, `toolbar`, `main`, and `dialog` all look like the same generic card, the canvas is violating contract.

### 5. Overlay and detached roles are visually distinct

Dialogs, popups, and detached tool windows must not render like ordinary in-flow panels.

---

## Role Profiles

## Button

### Meaning

A clickable control. Small, compact, content-sized.

### Render profile

```python
{
    "render_kind": "button",
    "fill_style": "button",
    "show_header": False,
    "show_body": False,
    "show_border": True,
    "show_label": True,
    "content_alignment": "center",
    "padding": 10,
    "corner_radius": 6,
    "border_weight": 1,
    "draw_children_inside": False,
    "overlay_layer": False,
    "selection_style": "outline",
    "lock_indicator": True,
}
```

### Rule

Buttons must look like controls, not panels pretending to be controls.

---

## Text

### Meaning

Display text, usually content-hugging.

### Render profile

```python
{
    "render_kind": "text",
    "fill_style": "none",
    "show_header": False,
    "show_body": False,
    "show_border": False,
    "show_label": True,
    "content_alignment": "left",
    "padding": 2,
    "corner_radius": 0,
    "border_weight": 0,
    "draw_children_inside": False,
    "overlay_layer": False,
    "selection_style": "outline",
    "lock_indicator": True,
}
```

### Rule

Text should look like text sitting in the UI, not like a generic widget card.

---

## Input

### Meaning

An editable field.

### Render profile

```python
{
    "render_kind": "input",
    "fill_style": "input",
    "show_header": False,
    "show_body": False,
    "show_border": True,
    "show_label": True,
    "content_alignment": "left",
    "padding": 8,
    "corner_radius": 4,
    "border_weight": 1,
    "draw_children_inside": False,
    "overlay_layer": False,
    "selection_style": "outline",
    "lock_indicator": True,
}
```

### Rule

Inputs must look like fields, not card containers.

---

## Sidebar

### Meaning

A navigation or utility region anchored to one side.

### Render profile

```python
{
    "render_kind": "sidebar",
    "fill_style": "sidebar",
    "show_header": True,
    "show_body": True,
    "show_border": True,
    "show_label": True,
    "content_alignment": "top",
    "padding": 12,
    "corner_radius": 0,
    "border_weight": 1,
    "draw_children_inside": True,
    "overlay_layer": False,
    "selection_style": "outline",
    "lock_indicator": True,
}
```

### Rule

Sidebar children must visually belong to the sidebar body.

---

## Toolbar

### Meaning

A horizontal control strip, usually near the top.

### Render profile

```python
{
    "render_kind": "toolbar",
    "fill_style": "toolbar",
    "show_header": False,
    "show_body": False,
    "show_border": True,
    "show_label": False,
    "content_alignment": "left",
    "padding": 8,
    "corner_radius": 0,
    "border_weight": 1,
    "draw_children_inside": True,
    "overlay_layer": False,
    "selection_style": "outline",
    "lock_indicator": True,
}
```

### Rule

Toolbar must render as a strip, not a card.

---

## Main

### Meaning

The main content/work surface.

### Render profile

```python
{
    "render_kind": "main",
    "fill_style": "main",
    "show_header": True,
    "show_body": True,
    "show_border": True,
    "show_label": True,
    "content_alignment": "top",
    "padding": 12,
    "corner_radius": 0,
    "border_weight": 1,
    "draw_children_inside": True,
    "overlay_layer": False,
    "selection_style": "outline",
    "lock_indicator": True,
}
```

### Rule

Main must read as the area where the application actually happens.

---

## Panel

### Meaning

A modular region or widget container.

### Render profile

```python
{
    "render_kind": "panel",
    "fill_style": "panel",
    "show_header": True,
    "show_body": True,
    "show_border": True,
    "show_label": True,
    "content_alignment": "top",
    "padding": 10,
    "corner_radius": 6,
    "border_weight": 1,
    "draw_children_inside": True,
    "overlay_layer": False,
    "selection_style": "outline",
    "lock_indicator": True,
}
```

### Rule

Panel is a card-like region, not a raw rectangle.

---

## Dialog

### Meaning

A floating or blocking overlay.

### Render profile

```python
{
    "render_kind": "dialog",
    "fill_style": "dialog",
    "show_header": True,
    "show_body": True,
    "show_border": True,
    "show_label": True,
    "content_alignment": "top",
    "padding": 12,
    "corner_radius": 8,
    "border_weight": 1,
    "draw_children_inside": True,
    "overlay_layer": True,
    "selection_style": "outline",
    "lock_indicator": True,
}
```

### Rule

Dialogs must not render as ordinary in-flow children.

---

## Popup

### Meaning

A transient contextual overlay such as a dropdown or popover.

### Render profile

```python
{
    "render_kind": "popup",
    "fill_style": "popup",
    "show_header": False,
    "show_body": True,
    "show_border": True,
    "show_label": False,
    "content_alignment": "top",
    "padding": 8,
    "corner_radius": 6,
    "border_weight": 1,
    "draw_children_inside": True,
    "overlay_layer": True,
    "selection_style": "outline",
    "lock_indicator": True,
}
```

### Rule

Popups must render as contextual overlays, not normal children in a stack.

---

## Tool Window

### Meaning

A detached utility window.

### Render profile

```python
{
    "render_kind": "tool_window",
    "fill_style": "window",
    "show_header": True,
    "show_body": True,
    "show_border": True,
    "show_label": True,
    "content_alignment": "top",
    "padding": 10,
    "corner_radius": 6,
    "border_weight": 1,
    "draw_children_inside": True,
    "overlay_layer": True,
    "selection_style": "outline",
    "lock_indicator": True,
}
```

### Rule

Tool windows must read as detached windows, not nested content cards.

---

## Unknown Type Fallback

Every node must resolve to a render answer.

Fallback chain:
1. explicit role profile
2. type profile
3. generic category profile
4. unknown fallback profile

Unknown fallback behavior:
- generic region appearance
- visibly distinct from supported roles
- labeled as unknown
- still selectable and editable

It must not silently pretend to be a standard panel.

---

## Selection And Lock Policy

Selection is governed globally by canvas policy.

Roles may provide hints such as:
- `outline`
- `glow`
- `header_only`

But selection behavior remains globally consistent.

### Rule

Selection and lock indicators are paint overlays.

They must not alter geometry.

---

## Header And Body Regions

If `show_header` is true:
- header is a real visual band
- header occupies reserved paint area
- body content must not render through header

If `draw_children_inside` is true:
- children must draw inside the body/content rect
- not through header chrome

### Final rule

The final system must distinguish:
- outer rect
- header rect
- body/content rect

Temporary implementations may paint a visual header first while children still occupy the full outer rect, but that is transitional only.

---

## Overlay Layers

`overlay_layer` affects:
- appearance
- draw order
- hit-testing precedence

Minimum layer model:
1. normal flow
2. overlay
3. detached window/tool layer

Dialogs, popups, and tool windows must be recognized in the contract now, even if implementation is partial.

---

## Renderer Pipeline

### Step 1

Engine computes geometry:
- `x`
- `y`
- `width`
- `height`

### Step 2

Renderer resolves render profile:

```python
profile = resolve_render_profile(node, parent_context=None, layout_context=None)
```

### Step 3

Canvas draws by render kind:

```python
if profile["render_kind"] == "button":
    draw_button(...)
elif profile["render_kind"] == "sidebar":
    draw_sidebar(...)
elif profile["render_kind"] == "toolbar":
    draw_toolbar(...)
...
```

### Step 4

Selection and lock paint on top without changing geometry.

---

## Required Draw Functions

Minimum role draw set:
- `draw_button(rect, node, profile)`
- `draw_text(rect, node, profile)`
- `draw_input(rect, node, profile)`
- `draw_sidebar(rect, node, profile)`
- `draw_toolbar(rect, node, profile)`
- `draw_main(rect, node, profile)`
- `draw_panel(rect, node, profile)`
- `draw_dialog(rect, node, profile)`
- `draw_popup(rect, node, profile)`
- `draw_tool_window(rect, node, profile)`

These functions decide appearance only.

They do not decide geometry.

---

## Context Sensitivity

Render profile may consider:
- node role/type
- parent context
- layout context

Final resolution shape:

```python
resolve_render_profile(node, parent_context=None, layout_context=None)
```

Examples:
- `panel` in a dashboard vs panel in a detached workbench
- `text` label vs `text` body content
- `input` in a form vs `input` in a toolbar

Context-sensitive rendering must be declared, not improvised.

---

## Deferred Work

The following may be deferred in implementation, but not in contract:
- header/body-aware child clipping
- true overlay hit-testing layers
- detached tool window rendering behavior
- context-modified render profile tables
- richer fallback styling
- profile inheritance implementation details

If deferred, the implementation must state:
- what rule is approximated
- what remains to become contract-complete

---

## Non-Goals

This contract does not define:
- geometry computation
- layout distribution
- snapping
- engine constraints
- export format
- import packet shape
- code mirror
- bench mode

Those belong elsewhere.

---

## Governing Rule

A node's role must control both:
1. layout policy
2. render profile

If only one half is correct, the canvas still feels fake.

Buttons must become button-looking because the render contract says they are buttons.

Dialogs must become dialog-looking because the render contract says they are overlays.

If a role renders like a generic box, the render contract is being violated.
