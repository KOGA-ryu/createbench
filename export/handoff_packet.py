from __future__ import annotations

from export.snapshot_handoff import build_snapshot_handoff


def build_handoff_packet(
    *,
    layout_model,
    selection_state,
    checklist_engine,
    canvas_panel,
    builder,
) -> dict[str, object]:
    canvas_rect = canvas_panel.authored_canvas_rect()
    rect_map = canvas_panel.layout_engine.compute_layout(
        layout_model.root_id, canvas_rect
    )
    checklist = checklist_engine.run()
    packet = {
        "selection": selection_state.get_selection(),
        "scene_metadata": dict(getattr(layout_model, "scene_metadata", {})),
        "canvas_rect": canvas_rect,
        "viewport": canvas_panel.get_viewport_state(),
        "draw_order": list(canvas_panel.layout_engine.draw_order),
        "rect_map": rect_map,
        "checklist": checklist,
        "project_json": None,
        "dsl": None,
        "snapshot_handoff": None,
        "export_error": None,
    }
    try:
        packet["project_json"] = builder.build_json(mode="expanded")
        packet["dsl"] = builder.build_dsl(mode="expanded")
        selected_id = selection_state.get_selection()
        selected_node = None if selected_id is None else layout_model.get_node(selected_id)
        if selected_id is not None and selected_node is not None:
            packet["snapshot_handoff"] = build_snapshot_handoff(
                layout_model.serialize_subtree(selected_id),
                model=layout_model,
                node=selected_node,
                scene_metadata=dict(getattr(layout_model, "scene_metadata", {})),
            )
    except Exception as exc:
        packet["export_error"] = str(exc)
    return packet
