# Product Surfaces Backlog

This document defines the canonical product vocabulary for Create Bench.

Use these exact names in:
- feedback
- design notes
- cleanup plans
- implementation tasks

Do not introduce alternate names unless this document is updated first.

## Level 1 — Product Surfaces

### Left Tool Rail
- Purpose: persistent vertical tool launcher for major workspace sections
- Current state:
  - exists
  - needs visual polish
  - needs stronger tool identity and likely better tool set
- Backlog:
  - refine iconography / visual hierarchy
  - clarify section activation state
  - evaluate whether current section list is sufficient

### Top Toolbar
- Purpose: app-level settings, mode controls, view actions, global commands
- Current state:
  - missing
- Backlog:
  - define scope
  - decide which global actions belong here vs elsewhere
  - add hotkey/status integration later

### Canvas Surface
- Purpose: primary world-space editing and inspection surface
- Current state:
  - strong
  - still needs polish and workflow clarity
- Backlog:
  - continue source/fork/bench clarity
  - continue repo-backed fidelity
  - improve interaction readability

### Tool Workspace
- Purpose: shared floating tool window for secondary tools
- Current state:
  - exists
  - extracted from `MainWindow`
  - useful but still dense
- Backlog:
  - improve hierarchy
  - refine tool grouping
  - decide what belongs here vs other windows

### Project IO Panel
- Purpose: source target, scene actions, save/export flow
- Current state:
  - structurally strong
  - explicit and truthful
  - extracted from `MainWindow`
- Backlog:
  - keep wording tight
  - continue scanability improvements only when needed

### Selection Window
- Purpose: current floating selection/inspector host window
- Current state:
  - exists as separate window
  - build/placement logic extracted from `MainWindow`
  - useful stopgap
- Backlog:
  - manage overlap better
  - decide long-term relationship to Inspector Node Window

### Inspector Node Window
- Purpose: future per-window/per-surface inspection and editing window
- Current state:
  - concept only
  - not implemented as canonical multi-window system yet
- Backlog:
  - likely one window per editable window/surface
  - include metadata, source mapping, code snippets, notes
  - reduce crowding from current single-window approach

## Level 2 — Canvas Contexts

### Source Scene
- Purpose: source-backed imported truth
- Current state:
  - strong
  - protected correctly
- Backlog:
  - continue source-faithful rendering
  - continue workflow cues

### Forked Working Copy
- Purpose: editable design copy of source-backed content
- Current state:
  - works
  - now visible in canvas/status
- Backlog:
  - continue making working-copy state obvious

### Bench Workspace
- Purpose: dedicated world-space area for bench projections
- Current state:
  - works
  - recently improved with larger, separate real estate
- Backlog:
  - continue workspace clarity
  - continue placement/windowing review

### Bench Session
- Purpose: one isolated bench projection set
- Current state:
  - works
  - has focus, close, reopen
- Backlog:
  - continue session UX
  - possibly improve browsing/history later

### Scanner Main Window Render
- Purpose: repo-specific semantic rendering for `scanner` main window
- Current state:
  - strong and actively improving
- Backlog:
  - continue source-backed fidelity
  - continue automation grounding

### Scanner Profile Manager Render
- Purpose: repo-specific semantic rendering for `scanner` profile manager
- Current state:
  - strong and actively improving
- Backlog:
  - continue form fidelity
  - continue source-backed fidelity

## Level 3 — Inspector / Interaction Systems

### Truth Tab
- Purpose: read-only inspection truth
- Current state:
  - exists
  - truth sections extracted
  - correct direction
- Backlog:
  - continue adding useful truthful context

### Edit Tab
- Purpose: lawful editing controls for editable nodes
- Current state:
  - exists
  - edit sections extracted
  - gated correctly
- Backlog:
  - continue refining ergonomics

### Scene Truth Section
- Purpose: scene-level mode/origin/trust/session context
- Current state:
  - exists
  - extracted into `truth_sections.py`
- Backlog:
  - keep concise
  - avoid clutter

### Node Truth Section
- Purpose: node-level source/trust/origin/range context
- Current state:
  - exists
  - extracted into `truth_sections.py`
- Backlog:
  - richer snippet context
  - better note anchoring later

### Snippet Notes
- Purpose: notes attached to exact source snippet / range
- Current state:
  - missing
- Backlog:
  - define note model
  - define snippet anchoring
  - define per-window usage

### Window Placement
- Purpose: where floating windows open and how they avoid overlap
- Current state:
  - weak
- Backlog:
  - reduce overlap
  - support more intentional placement logic

### Window Focus
- Purpose: which window becomes active and why
- Current state:
  - partial
- Backlog:
  - improve predictability
  - unify focus behavior

### Window Dismissal
- Purpose: closing windows quickly and predictably
- Current state:
  - weak
- Backlog:
  - support `Esc`
  - improve close behavior for inspector-style windows

### Hotkey System
- Purpose: app-wide keyboard-driven workflow
- Current state:
  - mostly missing
- Backlog:
  - define core hotkeys
  - implement global/local shortcuts

## Codebase Cleanup

### File Boundaries
- separate generic vs repo-specific concerns cleanly
- avoid oversized UI/controller files
- note:
  - `MainWindow`, `InspectorPanel`, and bench support already had meaningful extraction passes
  - next boundary work should be more selective, not broad

### Naming Consistency
- align code names with canonical product vocabulary where appropriate
- identify ambiguous or drifting names first

### Dead Paths
- remove stale helpers, compatibility shims, or superseded flows
- note:
  - empty `ui/panels.py` and `ui/layout.py` placeholders were already removed

### UI Structure Cleanup
- reduce dense widget assembly methods
- simplify duplicated wiring patterns

### Model / Resolver Cleanup
- centralize truth logic where possible
- reduce metadata reach-through

### Test Cleanup
- normalize test naming and organization
- reduce script-style drift over time

### Docs / Contracts Cleanup
- keep contracts aligned with actual behavior
- remove stale notes once behavior is implemented
