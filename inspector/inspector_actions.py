from __future__ import annotations


def fork_selected_to_design(model, selection_state, node_id):
    forked_id = model.fork_subtree_to_design(node_id)
    if forked_id is not None:
        selection_state.set_selection(forked_id)


def open_selected_in_bench(model, selection_state, focus_node_callback, node_id):
    bench_id = model.open_subtree_in_bench(node_id)
    if bench_id is not None:
        selection_state.set_selection(bench_id)
        if callable(focus_node_callback):
            focus_node_callback(bench_id)


def fork_scene_to_design(model, selection_state):
    created_root_ids = model.fork_scene_to_design()
    if created_root_ids:
        selection_state.set_selection(created_root_ids[0])


def open_scene_in_bench(model, selection_state, focus_node_callback):
    created_root_ids = model.open_scene_in_bench()
    if created_root_ids:
        selection_state.set_selection(created_root_ids[0])
        if callable(focus_node_callback):
            focus_node_callback(created_root_ids[0])


def focus_bench_session(model, bench_session_id):
    model.set_active_bench_session(bench_session_id)


def clear_bench_focus(model):
    model.clear_active_bench_session()


def close_bench_session(model, selection_state, bench_session_id):
    selected_id = selection_state.get_selection()
    selected = model.get_node(selected_id) if selected_id is not None else None
    selected_session_id = (
        (getattr(selected, "metadata", {}) or {}).get("bench_session_id")
        if selected is not None else None
    )
    deleted = model.close_bench_session(bench_session_id)
    if selected_session_id == bench_session_id and deleted:
        selection_state.clear_selection()


def reopen_bench_session(model, selection_state, bench_session_id):
    restored_roots = model.reopen_closed_bench_session(bench_session_id)
    if restored_roots:
        selection_state.set_selection(restored_roots[0])
