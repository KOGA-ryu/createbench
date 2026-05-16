from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from ui.tool_workspace import ToolWorkspace


class ProjectIOPanel(QWidget):
    def __init__(
        self,
        *,
        save_button,
        save_target_label,
        scene_source_selector,
        scanner_probe_target_selector,
        scene_source_target_field,
        scene_source_preflight_label,
        scene_action_context_label,
        scene_replace_button,
        scene_alongside_button,
        scene_bench_button,
        scene_action_hint_label,
        handoff_button,
        export_button,
    ):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        layout.addWidget(
            ToolWorkspace.build_project_group(
                "Save & Persist",
                "project_save_group",
                save_button,
                save_target_label,
            )
        )
        layout.addWidget(
            ToolWorkspace.build_project_group(
                "Source Target",
                "project_source_group",
                scene_source_selector,
                scanner_probe_target_selector,
                scene_source_target_field,
                scene_source_preflight_label,
            )
        )
        layout.addWidget(
            ToolWorkspace.build_project_group(
                "Scene Actions",
                "project_scene_actions_group",
                scene_action_context_label,
                scene_replace_button,
                scene_alongside_button,
                scene_bench_button,
                scene_action_hint_label,
            )
        )
        layout.addWidget(
            ToolWorkspace.build_project_group(
                "Export",
                "project_export_group",
                handoff_button,
                export_button,
            )
        )
