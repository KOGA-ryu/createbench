# Repo Product Crosswalk

This document maps current code to the canonical product vocabulary.

Purpose:
- current implementation name
- canonical product name
- file path
- status: `clean`, `overloaded`, or `missing`
- notes on ambiguity, duplication, or gaps

Do not rename code yet. Use this map first.

## Level 1 — Product Surfaces

### Left Tool Rail
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| section toggle rail inside `MainWindow` | Left Tool Rail | [/Users/kogaryu/dev/createbench/ui/main_window.py](/Users/kogaryu/dev/createbench/ui/main_window.py) | overloaded | Implemented inside `MainWindow`; likely needs its own widget later. |

### Top Toolbar
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| none | Top Toolbar | - | missing | App-level toolbar is not implemented yet. |

### Canvas Surface
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `CanvasWidget` | Canvas Surface | [/Users/kogaryu/dev/createbench/canvas/canvas_widget.py](/Users/kogaryu/dev/createbench/canvas/canvas_widget.py) | overloaded | Core surface is strong but still carries rendering, interaction, status, and tool overlay logic. |
| `InteractionController` | Canvas Surface | [/Users/kogaryu/dev/createbench/canvas/interaction_controller.py](/Users/kogaryu/dev/createbench/canvas/interaction_controller.py) | clean | Narrow support role. |
| `ResizeHandles` | Canvas Surface | [/Users/kogaryu/dev/createbench/canvas/resize_handles.py](/Users/kogaryu/dev/createbench/canvas/resize_handles.py) | clean | Narrow support role. |

### Tool Workspace
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `ToolWorkspace` | Tool Workspace | [/Users/kogaryu/dev/createbench/ui/tool_workspace.py](/Users/kogaryu/dev/createbench/ui/tool_workspace.py) | clean | Workspace composition and section display state are extracted. |
| tool workspace orchestration | Tool Workspace | [/Users/kogaryu/dev/createbench/ui/main_window.py](/Users/kogaryu/dev/createbench/ui/main_window.py) | clean | `MainWindow` now wires and owns lifecycle only. |

### Project IO Panel
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `ProjectIOPanel` | Project IO Panel | [/Users/kogaryu/dev/createbench/ui/project_io_panel.py](/Users/kogaryu/dev/createbench/ui/project_io_panel.py) | clean | Panel assembly is extracted from `MainWindow`. |
| project IO policy/preflight helpers | Project IO Panel | [/Users/kogaryu/dev/createbench/ui/project_io_logic.py](/Users/kogaryu/dev/createbench/ui/project_io_logic.py) | clean | Recommendation, hint, and preflight text are separated. |
| scene-action routing | Project IO Panel | [/Users/kogaryu/dev/createbench/ui/scene_action_routing.py](/Users/kogaryu/dev/createbench/ui/scene_action_routing.py) | clean | Explicit dispatch table extracted from `MainWindow`. |
| scene-load execution | Project IO Panel | [/Users/kogaryu/dev/createbench/ui/scene_load_execution.py](/Users/kogaryu/dev/createbench/ui/scene_load_execution.py) | clean | Source-specific load execution bodies are extracted. |
| scene-source selection helpers | Project IO Panel | [/Users/kogaryu/dev/createbench/ui/scene_source_selection.py](/Users/kogaryu/dev/createbench/ui/scene_source_selection.py) | clean | Current source/target/probe selection helpers are extracted. |
| project save/load helpers | Project IO Panel | [/Users/kogaryu/dev/createbench/io/project_io.py](/Users/kogaryu/dev/createbench/io/project_io.py) | clean | IO side is separate. |
| packet load helpers | Project IO Panel | [/Users/kogaryu/dev/createbench/io/ui_extract_packet.py](/Users/kogaryu/dev/createbench/io/ui_extract_packet.py) | clean | Intake side is separate. |

### Selection Window
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| selection-window build and placement helpers | Selection Window | [/Users/kogaryu/dev/createbench/ui/windowing.py](/Users/kogaryu/dev/createbench/ui/windowing.py) | clean | Window construction, placement, sync, and close behavior are extracted. |
| selection window orchestration | Selection Window | [/Users/kogaryu/dev/createbench/ui/main_window.py](/Users/kogaryu/dev/createbench/ui/main_window.py) | clean | `MainWindow` retains lifecycle ownership only. |

### Inspector Node Window
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `InspectorPanel` coordinator | Inspector Node Window | [/Users/kogaryu/dev/createbench/inspector/inspector_panel.py](/Users/kogaryu/dev/createbench/inspector/inspector_panel.py) | clean | Panel now coordinates truth, edit, and action modules instead of rendering everything inline. |

## Level 2 — Canvas Contexts

### Source Scene
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| scene metadata + scene resolver | Source Scene | [/Users/kogaryu/dev/createbench/core/scene_resolution.py](/Users/kogaryu/dev/createbench/core/scene_resolution.py) | clean | Resolver is narrow and clear. |
| source-scene protection in canvas/inspector | Source Scene | [/Users/kogaryu/dev/createbench/canvas/canvas_widget.py](/Users/kogaryu/dev/createbench/canvas/canvas_widget.py) | overloaded | Uses resolver correctly, but enforcement still lives in larger widget file. |

### Forked Working Copy
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `fork_subtree_to_design`, `fork_scene_to_design` | Forked Working Copy | [/Users/kogaryu/dev/createbench/core/layout_model.py](/Users/kogaryu/dev/createbench/core/layout_model.py) | ambiguous | Works, but still lives with remaining model/workflow ownership in `LayoutModel`. |

### Bench Workspace
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| bench workspace helpers | Bench Workspace | [/Users/kogaryu/dev/createbench/core/bench_workspace.py](/Users/kogaryu/dev/createbench/core/bench_workspace.py) | clean | Workspace support is extracted behind the model API boundary. |

### Bench Session
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| bench session helpers | Bench Session | [/Users/kogaryu/dev/createbench/core/bench_sessions.py](/Users/kogaryu/dev/createbench/core/bench_sessions.py) | clean | Session support is extracted behind the model API boundary. |
| `LayoutModelAPI` boundary | Bench Session | [/Users/kogaryu/dev/createbench/core/layout_model_api.py](/Users/kogaryu/dev/createbench/core/layout_model_api.py) | clean | Bench helpers no longer reach through private model internals. |

### Scanner Main Window Render
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| scanner-specific renderer paths for main window | Scanner Main Window Render | [/Users/kogaryu/dev/createbench/canvas/scanner_renderer.py](/Users/kogaryu/dev/createbench/canvas/scanner_renderer.py) | clean | Correctly extracted from generic canvas. |
| scanner main-window probe | Scanner Main Window Render | [/Users/kogaryu/dev/createbench/io/scanner_ui_probe_runtime.py](/Users/kogaryu/dev/createbench/io/scanner_ui_probe_runtime.py) | clean | Upstream extraction side is separated. |

### Scanner Profile Manager Render
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| scanner-specific renderer paths for profile manager | Scanner Profile Manager Render | [/Users/kogaryu/dev/createbench/canvas/scanner_renderer.py](/Users/kogaryu/dev/createbench/canvas/scanner_renderer.py) | clean | Shares renderer module with scanner main window, which is acceptable for now. |
| scanner profile-manager probe | Scanner Profile Manager Render | [/Users/kogaryu/dev/createbench/io/scanner_ui_probe_runtime.py](/Users/kogaryu/dev/createbench/io/scanner_ui_probe_runtime.py) | clean | Upstream extraction side is separated. |

## Level 3 — Inspector / Interaction Systems

### Truth Tab
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `truth_tab`, `truth_layout` | Truth Tab | [/Users/kogaryu/dev/createbench/inspector/inspector_panel.py](/Users/kogaryu/dev/createbench/inspector/inspector_panel.py) | clean | Good direction. |

### Edit Tab
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `edit_tab`, `content_layout` | Edit Tab | [/Users/kogaryu/dev/createbench/inspector/inspector_panel.py](/Users/kogaryu/dev/createbench/inspector/inspector_panel.py) | clean | Good direction. |

### Scene Truth Section
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `build_scene_truth_section` | Scene Truth Section | [/Users/kogaryu/dev/createbench/inspector/truth_sections.py](/Users/kogaryu/dev/createbench/inspector/truth_sections.py) | clean | Extracted from `InspectorPanel` as planned. |

### Node Truth Section
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `build_node_truth_section` | Node Truth Section | [/Users/kogaryu/dev/createbench/inspector/truth_sections.py](/Users/kogaryu/dev/createbench/inspector/truth_sections.py) | clean | Extracted from `InspectorPanel` as planned. |

### Snippet Notes
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| none | Snippet Notes | - | missing | No note model or source-range note UI yet. |

### Window Placement
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| window placement helpers | Window Placement | [/Users/kogaryu/dev/createbench/ui/windowing.py](/Users/kogaryu/dev/createbench/ui/windowing.py) | ambiguous | Extracted from `MainWindow`, but overlap/placement quality is still a known product issue. |

### Window Focus
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| canvas focus methods + bench focus callback | Window Focus | [/Users/kogaryu/dev/createbench/canvas/canvas_widget.py](/Users/kogaryu/dev/createbench/canvas/canvas_widget.py) | overloaded | Focus behavior spans canvas, main window, and inspector. |
| `_focus_node_in_canvas` | Window Focus | [/Users/kogaryu/dev/createbench/ui/main_window.py](/Users/kogaryu/dev/createbench/ui/main_window.py) | clean | Good small integration point. |

### Window Dismissal
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| close behavior through window close events | Window Dismissal | [/Users/kogaryu/dev/createbench/ui/main_window.py](/Users/kogaryu/dev/createbench/ui/main_window.py) | missing | No real dismissal system, no `Esc` close behavior yet. |

### Hotkey System
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| minimal `Delete` handling in canvas | Hotkey System | [/Users/kogaryu/dev/createbench/canvas/canvas_widget.py](/Users/kogaryu/dev/createbench/canvas/canvas_widget.py) | missing | No broader hotkey system yet. |

## Codebase Cleanup

### File Boundaries
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `MainWindow` orchestration + remaining app assembly | File Boundaries | [/Users/kogaryu/dev/createbench/ui/main_window.py](/Users/kogaryu/dev/createbench/ui/main_window.py) | ambiguous | Significantly reduced; still an orchestrator hotspot, but no longer the largest cleanup target. |
| `LayoutModel` data model + remaining fork/scene workflow | File Boundaries | [/Users/kogaryu/dev/createbench/core/layout_model.py](/Users/kogaryu/dev/createbench/core/layout_model.py) | ambiguous | Bench ownership pressure is reduced after extraction and API hardening. |
| `CanvasWidget` render dispatch + interaction + status + overlay tools | File Boundaries | [/Users/kogaryu/dev/createbench/canvas/canvas_widget.py](/Users/kogaryu/dev/createbench/canvas/canvas_widget.py) | overloaded | Better than before, but still dense. |
| `ScannerRenderer` repo-specific rendering | File Boundaries | [/Users/kogaryu/dev/createbench/canvas/scanner_renderer.py](/Users/kogaryu/dev/createbench/canvas/scanner_renderer.py) | clean | Good extraction already done. |
| `InspectorPanel` coordination only | File Boundaries | [/Users/kogaryu/dev/createbench/inspector/inspector_panel.py](/Users/kogaryu/dev/createbench/inspector/inspector_panel.py) | clean | Truth, edit rendering, and actions are extracted into dedicated modules. |

### Naming Consistency
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| mixed use of `Selection Window`, `InspectorPanel`, `truth`, `scene truth`, `tool workspace` names in code | Naming Consistency | multiple | overloaded | Canon vocabulary now exists; code names can be aligned later. |
| wrapper modules `project_io.py`, `scanner_ui_probe.py`, `ui_extract_packet.py` at repo root | Naming Consistency | [/Users/kogaryu/dev/createbench/project_io.py](/Users/kogaryu/dev/createbench/project_io.py), [/Users/kogaryu/dev/createbench/scanner_ui_probe.py](/Users/kogaryu/dev/createbench/scanner_ui_probe.py), [/Users/kogaryu/dev/createbench/ui_extract_packet.py](/Users/kogaryu/dev/createbench/ui_extract_packet.py) | ambiguous | Thin wrappers are acceptable but add naming duplication. |

### Dead Paths
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| empty `ui/panels.py`, `ui/layout.py` stubs | Dead Paths | removed | clean | Deleted as dead, unreferenced placeholder files. |
| docs/md mirrors of implementation files | Dead Paths | `docs/*.md`, `core/*.md`, `engine/*.md` | ambiguous | Need audit for staleness, not removal yet. |

### UI Structure Cleanup
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| remaining app-level assembly in `MainWindow` | UI Structure Cleanup | [/Users/kogaryu/dev/createbench/ui/main_window.py](/Users/kogaryu/dev/createbench/ui/main_window.py) | ambiguous | Much cleaner after current batches; next structure work should be more selective. |
| inspector coordinator | UI Structure Cleanup | [/Users/kogaryu/dev/createbench/inspector/inspector_panel.py](/Users/kogaryu/dev/createbench/inspector/inspector_panel.py) | clean | Truth, edit, and action clusters are already extracted. |

### Model / Resolver Cleanup
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `resolve_node_state` | Model / Resolver Cleanup | [/Users/kogaryu/dev/createbench/core/node_resolution.py](/Users/kogaryu/dev/createbench/core/node_resolution.py) | clean | Good narrow resolver. |
| `resolve_scene_state` | Model / Resolver Cleanup | [/Users/kogaryu/dev/createbench/core/scene_resolution.py](/Users/kogaryu/dev/createbench/core/scene_resolution.py) | clean | Good narrow resolver. |
| metadata reach-through from widgets/renderers | Model / Resolver Cleanup | multiple | overloaded | Still common in renderer and inspector code. |

### Test Cleanup
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| `test_pytest_bridge.py` unified bridge | Test Cleanup | [/Users/kogaryu/dev/createbench/tests/test_pytest_bridge.py](/Users/kogaryu/dev/createbench/tests/test_pytest_bridge.py) | ambiguous | Broad script-style coverage now runs under pytest, but the suite is still fundamentally script-style underneath. |

### Docs / Contracts Cleanup
| Current Implementation | Canonical Product Name | File Path | Status | Notes |
|---|---|---|---|---|
| contract docs at repo root | Docs / Contracts Cleanup | repo root contracts | clean | Strong foundation. |
| implementation docs mirroring code | Docs / Contracts Cleanup | `docs/*.md`, `core/*.md`, `engine/*.md` | ambiguous | Need staleness audit later. |
