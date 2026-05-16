from __future__ import annotations

from project_io import load_project, load_project_alongside, load_project_in_bench
from scanner_ui_probe import (
    load_scanner_main_window_alongside,
    load_scanner_main_window_in_bench,
    load_scanner_main_window_replace,
    load_scanner_profile_manager_alongside,
    load_scanner_profile_manager_in_bench,
    load_scanner_profile_manager_replace,
)
from ui_extract_packet import (
    load_packet as load_ui_extract_packet,
    load_packet_alongside as load_ui_extract_packet_alongside,
    load_packet_in_bench as load_ui_extract_packet_in_bench,
)


def _finalize_replace(selection_state, canvas_panel, checklist_panel) -> None:
    selection_state.clear_selection()
    canvas_panel.update()
    checklist_panel.update_checklist()


def _finalize_alongside(selection_state, canvas_panel, checklist_panel, created_root_ids) -> None:
    if created_root_ids:
        selection_state.set_selection(created_root_ids[0])
    else:
        selection_state.clear_selection()
    canvas_panel.update()
    checklist_panel.update_checklist()


def _finalize_bench(selection_state, canvas_panel, checklist_panel, created_root_ids) -> None:
    if created_root_ids:
        selection_state.set_selection(created_root_ids[0])
        canvas_panel.focus_selected_node()
    else:
        selection_state.clear_selection()
    canvas_panel.update()
    checklist_panel.update_checklist()


def project_replace(*, layout_model, property_registry, selection_state, canvas_panel, checklist_panel, target_path) -> None:
    load_project(layout_model, property_registry, target_path)
    _finalize_replace(selection_state, canvas_panel, checklist_panel)


def project_alongside(*, layout_model, property_registry, selection_state, canvas_panel, checklist_panel, target_path) -> None:
    created_root_ids = load_project_alongside(layout_model, property_registry, target_path)
    _finalize_alongside(selection_state, canvas_panel, checklist_panel, created_root_ids)


def project_bench(*, layout_model, property_registry, selection_state, canvas_panel, checklist_panel, target_path) -> None:
    created_root_ids = load_project_in_bench(layout_model, property_registry, target_path)
    _finalize_bench(selection_state, canvas_panel, checklist_panel, created_root_ids)


def extract_packet_replace(*, layout_model, selection_state, canvas_panel, checklist_panel, target_path) -> None:
    load_ui_extract_packet(layout_model, target_path)
    _finalize_replace(selection_state, canvas_panel, checklist_panel)


def extract_packet_alongside(*, layout_model, selection_state, canvas_panel, checklist_panel, target_path) -> None:
    created_root_ids = load_ui_extract_packet_alongside(layout_model, target_path)
    _finalize_alongside(selection_state, canvas_panel, checklist_panel, created_root_ids)


def extract_packet_bench(*, layout_model, selection_state, canvas_panel, checklist_panel, target_path) -> None:
    created_root_ids = load_ui_extract_packet_in_bench(layout_model, target_path)
    _finalize_bench(selection_state, canvas_panel, checklist_panel, created_root_ids)


def scanner_replace(*, layout_model, selection_state, canvas_panel, checklist_panel, target_path, probe_target) -> None:
    if probe_target == "profile_manager":
        load_scanner_profile_manager_replace(layout_model, target_path)
    else:
        load_scanner_main_window_replace(layout_model, target_path)
    _finalize_replace(selection_state, canvas_panel, checklist_panel)


def scanner_alongside(*, layout_model, selection_state, canvas_panel, checklist_panel, target_path, probe_target) -> None:
    if probe_target == "profile_manager":
        created_root_ids = load_scanner_profile_manager_alongside(layout_model, target_path)
    else:
        created_root_ids = load_scanner_main_window_alongside(layout_model, target_path)
    _finalize_alongside(selection_state, canvas_panel, checklist_panel, created_root_ids)


def scanner_bench(*, layout_model, selection_state, canvas_panel, checklist_panel, target_path, probe_target) -> None:
    if probe_target == "profile_manager":
        created_root_ids = load_scanner_profile_manager_in_bench(layout_model, target_path)
    else:
        created_root_ids = load_scanner_main_window_in_bench(layout_model, target_path)
    _finalize_bench(selection_state, canvas_panel, checklist_panel, created_root_ids)
