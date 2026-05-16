# Refactor Plan Phase 1

Scope is intentionally narrow.

This phase only covers:

1. Extract `Tool Workspace` from `MainWindow`
2. Extract `Scene Truth Section` and `Node Truth Section` from `InspectorPanel`

Do not refactor anything else in this phase.

## Goals

- reduce pressure on overloaded files called out in [REPO_PRODUCT_CROSSWALK.md](/Users/kogaryu/dev/createbench/REPO_PRODUCT_CROSSWALK.md)
- keep behavior unchanged
- create cleaner surface boundaries for future polish

## Non-Goals

- do not redesign the app shell
- do not change canvas behavior
- do not change bench/source/fork logic
- do not change Project IO behavior
- do not change resolver logic
- do not rename canonical product surfaces in code yet

## 1. Tool Workspace

### Current Location
- [main_window.py](/Users/kogaryu/dev/createbench/ui/main_window.py)

### Canonical Product Name
- `Tool Workspace`

### Problem
- `MainWindow` currently owns:
  - tool workspace assembly
  - section toggle rail behavior
  - section card creation
  - project/tool section grouping
  - tool workspace window construction
- this makes `MainWindow` an overloaded assembler plus tool-surface implementation file

### Files To Create
- [tool_workspace.py](/Users/kogaryu/dev/createbench/ui/tool_workspace.py)

### Code To Move
Move only the `Tool Workspace` UI construction and local section-widget logic:

- tool workspace widget/window assembly
- section toggle button creation
- section card creation
- section content mounting for:
  - `Geometry`
  - `Components`
  - `Templates`
  - `Structure`
  - `View`
  - `Validation`
  - `Project`
- local styling helpers used only by the tool workspace:
  - project group styling helpers
  - project input styling helper
  - project group builder

### What Stays In Place
Keep in [main_window.py](/Users/kogaryu/dev/createbench/ui/main_window.py):

- app-level action handlers
- source loading handlers
- save/export handlers
- scanner probe handlers
- window positioning methods
- selection window creation
- canvas/status wiring
- high-level `_build_ui()` orchestration

### Wiring Changes
`MainWindow` should:

- instantiate a `ToolWorkspace` widget/object
- pass in already-created section content widgets and action widgets
- keep ownership of callbacks and handlers
- ask `ToolWorkspace` for:
  - the tool workspace window/widget
  - section toggle rail widget

The new `ToolWorkspace` object should not own business logic.
It should only own:

- workspace composition
- section display state
- local presentation helpers

### Minimal Interface
Suggested constructor inputs:

```python
ToolWorkspace(
    sections: dict[str, QWidget],
    section_display_names: dict[str, str],
)
```

Suggested exposed outputs:

- `workspace_window`
- `tool_rail_widget`

Optional methods:

- `set_section_visible(name, visible)`
- `toggle_section(name)`

## 2. Scene Truth Section + Node Truth Section

### Current Location
- [inspector_panel.py](/Users/kogaryu/dev/createbench/inspector/inspector_panel.py)

### Canonical Product Names
- `Scene Truth Section`
- `Node Truth Section`

### Problem
- `_render_truth_summary()` currently assembles:
  - node truth lines
  - scene truth lines
  - scene-level actions
  - bench session controls
  - warnings
  - unresolved fields
- this is useful behavior, but too much of the inspector’s truth surface lives in one method

### Files To Create
- [truth_sections.py](/Users/kogaryu/dev/createbench/inspector/truth_sections.py)

### Code To Move
Move only the rendering helpers for:

- `Node Truth Section`
  - resolved mode
  - editability
  - trust/origin/source lines
  - node warnings
  - unresolved fields
  - relationships

- `Scene Truth Section`
  - scene mode/origin/provider/framework/trust
  - scene-level bench/session lines
  - scene-level fork/bench action row
  - bench session list
  - recently closed bench session list

These should be extracted as helper builders/functions, not a new behavior layer.

### What Stays In Place
Keep in [inspector_panel.py](/Users/kogaryu/dev/createbench/inspector/inspector_panel.py):

- tab setup
- selection change handling
- truth vs edit tab switching
- schema/property rendering
- action callbacks:
  - fork node
  - open node in bench
  - fork scene
  - open scene in bench
  - focus/clear bench
  - close/reopen bench session

### Wiring Changes
`InspectorPanel` should:

- keep `_render_truth_summary()`
- make `_render_truth_summary()` much thinner
- call extracted helpers from `truth_sections.py`

Those helpers should accept:

- target layout
- node
- model
- selection state if needed
- small callback bundle for buttons

The extracted module should not import `MainWindow`.
It should remain inspector-local.

### Minimal Interface
Suggested functions:

```python
build_node_truth_section(layout, node, model, callbacks)
build_scene_truth_section(layout, node, model, callbacks)
```

Where `callbacks` is a small dict or lightweight object containing:

- `fork_selected_to_design`
- `open_selected_in_bench`
- `fork_scene_to_design`
- `open_scene_in_bench`
- `focus_bench_session`
- `clear_bench_focus`
- `close_bench_session`
- `reopen_bench_session`

## Expected Result

After phase 1:

- [main_window.py](/Users/kogaryu/dev/createbench/ui/main_window.py) is still the app assembler, but no longer the direct implementation site for the whole `Tool Workspace`
- [inspector_panel.py](/Users/kogaryu/dev/createbench/inspector/inspector_panel.py) still owns inspector behavior, but no longer directly builds the full truth surface inline

No product behavior should change in this phase.

## Validation

At minimum, re-run:

- [test_engine_smoke.py](/Users/kogaryu/dev/createbench/tests/test_engine_smoke.py)
- [test_inspector_panel.py](/Users/kogaryu/dev/createbench/tests/test_inspector_panel.py)
- [test_canvas_widget.py](/Users/kogaryu/dev/createbench/tests/test_canvas_widget.py)

Because this phase is structural, not behavioral, test expectations should stay the same.
