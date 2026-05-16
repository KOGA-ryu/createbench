# Refactor Plan Phase 2

Scope is intentionally narrow.

This phase only covers:

1. Extract `Bench Workspace` support from `LayoutModel`
2. Extract `Bench Session` support from `LayoutModel`

Do not refactor anything else in this phase.

## Goals

- reduce pressure on overloaded model code called out in [REPO_PRODUCT_CROSSWALK.md](/Users/kogaryu/dev/createbench/REPO_PRODUCT_CROSSWALK.md)
- keep behavior unchanged
- separate `Bench Workspace` and `Bench Session` responsibilities from the core tree model

## Non-Goals

- do not redesign bench behavior
- do not change bench geometry or defaults
- do not change fork behavior
- do not change scene/source/design semantics
- do not change resolver behavior
- do not change canvas or inspector logic
- do not refactor clone/fork logic out of `LayoutModel` in this phase

## 1. Bench Workspace

### Current Location
- [layout_model.py](/Users/kogaryu/dev/createbench/core/layout_model.py)

### Canonical Product Name
- `Bench Workspace`

### Problem
- `LayoutModel` currently owns:
  - bench workspace constants
  - bench workspace lookup
  - bench workspace creation
  - bench workspace geometry normalization
- this is a real subsystem, but it currently lives inline with generic tree-model code

### Files To Create
- [bench_workspace.py](/Users/kogaryu/dev/createbench/core/bench_workspace.py)

### Code To Move
Move only the bench-workspace-specific support:

- bench workspace constants:
  - `BENCH_WORKSPACE_TITLE`
  - `BENCH_WORKSPACE_X`
  - `BENCH_WORKSPACE_Y`
  - `BENCH_WORKSPACE_WIDTH`
  - `BENCH_WORKSPACE_HEIGHT`
- bench workspace lookup/build helpers:
  - `_find_bench_workspace`
  - `_ensure_bench_workspace`
  - `ensure_bench_workspace`

These should become helper functions used by `LayoutModel`, not a new owner object.

### What Stays In Place
Keep in [layout_model.py](/Users/kogaryu/dev/createbench/core/layout_model.py):

- root/node storage
- node creation/add/remove/move/reorder
- subtree clone/fork logic
- scene forking methods
- public bench entrypoints:
  - `fork_subtree(..., destination="bench")`
  - `open_subtree_in_bench`
  - `open_scene_in_bench`

### Wiring Changes
`LayoutModel` should:

- call extracted workspace helpers from `bench_workspace.py`
- keep public API shape the same
- continue returning `Node` instances from bench workspace accessors

The new module should not own model state.
It should operate on the passed `LayoutModel` instance.

### Minimal Interface
Suggested functions:

```python
def find_bench_workspace(model) -> Node | None
def ensure_bench_workspace(model) -> Node
```

## 2. Bench Session

### Current Location
- [layout_model.py](/Users/kogaryu/dev/createbench/core/layout_model.py)

### Canonical Product Name
- `Bench Session`

### Problem
- `LayoutModel` currently owns:
  - active bench session metadata helpers
  - bench session enumeration
  - close/reopen lifecycle
  - recently closed session history
- those responsibilities are coherent together, but they crowd the model file

### Files To Create
- [bench_sessions.py](/Users/kogaryu/dev/createbench/core/bench_sessions.py)

### Code To Move
Move only the bench-session-specific support:

- `get_active_bench_session_id`
- `set_active_bench_session`
- `clear_active_bench_session`
- `sync_active_bench_session`
- `get_bench_session_ids`
- `get_recently_closed_bench_session_ids`
- `close_bench_session`
- `reopen_closed_bench_session`

These should become helper functions used by `LayoutModel`, not a new subsystem class.

### What Stays In Place
Keep in [layout_model.py](/Users/kogaryu/dev/createbench/core/layout_model.py):

- `scene_metadata`
- `closed_bench_sessions`
- public scene/tree mutation primitives used by bench session helpers
- subtree serialization helper:
  - `_serialize_subtree`
- bench-related clone/open entrypoints:
  - `open_subtree_in_bench`
  - `open_scene_in_bench`

### Wiring Changes
`LayoutModel` should:

- delegate session operations to extracted helpers in `bench_sessions.py`
- continue exposing the same public methods so callers do not change
- pass itself into helper functions rather than moving state ownership out of the model

The new module should not introduce new persistence or new state objects.
It should only relocate the current logic.

### Minimal Interface
Suggested functions:

```python
def get_active_bench_session_id(model) -> str | None
def set_active_bench_session(model, bench_session_id: str | None) -> None
def clear_active_bench_session(model) -> None
def sync_active_bench_session(model) -> None
def get_bench_session_ids(model) -> list[str]
def get_recently_closed_bench_session_ids(model) -> list[str]
def close_bench_session(model, bench_session_id: str) -> list[str]
def reopen_closed_bench_session(model, bench_session_id: str) -> list[str]
```

## Expected Result

After phase 2:

- [layout_model.py](/Users/kogaryu/dev/createbench/core/layout_model.py) still owns the core tree model and bench-facing public API
- bench workspace details live in [bench_workspace.py](/Users/kogaryu/dev/createbench/core/bench_workspace.py)
- bench session details live in [bench_sessions.py](/Users/kogaryu/dev/createbench/core/bench_sessions.py)
- callers do not need to change behavior or semantics

No product behavior should change in this phase.

## Validation

At minimum, re-run:

- [test_layout_model.py](/Users/kogaryu/dev/createbench/tests/test_layout_model.py)
- [test_inspector_panel.py](/Users/kogaryu/dev/createbench/tests/test_inspector_panel.py)
- [test_canvas_widget.py](/Users/kogaryu/dev/createbench/tests/test_canvas_widget.py)
- [test_engine_smoke.py](/Users/kogaryu/dev/createbench/tests/test_engine_smoke.py)
