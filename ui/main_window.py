from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QEvent
from PySide6.QtGui import QKeySequence, QShortcut
from canvas.canvas_widget import CanvasWidget
from checklist.checklist_panel import ChecklistPanel
from export.dsl_builder import DSLBuilder
from export.dsl_builder import DSL_VERSION
from export.handoff_packet import build_handoff_packet
from forms.component_form_builder import ComponentFormBuilder
from inspector.inspector_panel import InspectorPanel
from scanner_ui_probe import validate_scanner_probe_target, validate_scanner_repo_root
from ui.project_io_panel import ProjectIOPanel
from ui.project_io_logic import (
    default_scene_source_target_path,
    recommended_scene_action,
    scene_action_context_text,
    scene_action_hint_text,
    scene_action_target_suffix,
    scene_source_preflight_text,
)
from ui.scene_load_execution import (
    extract_packet_alongside,
    extract_packet_bench,
    extract_packet_replace,
    project_alongside,
    project_bench,
    project_replace,
    scanner_alongside,
    scanner_bench,
    scanner_replace,
)
from ui.scene_action_routing import route_scene_action
from ui.scene_source_selection import (
    scene_source_target_path,
    selected_scanner_probe_label,
    selected_scanner_probe_target,
    selected_scene_source,
    selected_scene_source_label,
)
from ui.tool_workspace import ToolWorkspace
from ui.windowing import (
    build_selection_window,
    close_selection_window,
    close_floating_windows,
    focus_selection_window,
    position_selection_window,
    position_tool_workspace_window,
    sync_floating_windows,
)
from ui_extract_packet import validate_packet as validate_ui_extract_packet
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from project_io import save_project


class MainWindow(QMainWindow):
    """Assemble the main editing window, floating tool workspace, and app actions."""

    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state
        self.builder = DSLBuilder(
            self.app_state.layout_model,
            self.app_state.property_registry,
            self.app_state.checklist_engine,
        )
        self.setWindowTitle("Create Bench")
        self.section_toggle_buttons: dict[str, QToolButton] = {}
        self.section_cards: dict[str, QFrame] = {}
        self.section_contents: dict[str, QWidget] = {}
        self.active_tool_sections: list[str] = []
        self.section_display_names = {
            "Geometry": "Geometry",
            "Components": "Components",
            "Templates": "Scaffolds",
            "Structure": "Structure",
            "View": "Canvas View",
            "Validation": "Issues",
            "Project": "Project IO",
        }
        self._build_ui()
        self.resize(1600, 1000)
        position_selection_window(self, getattr(self, "selection_window", None))
        position_tool_workspace_window(self, getattr(self, "tool_workspace_window", None))
        self._install_hotkeys()

    def _build_ui(self):
        """Create the canvas-centered window and register the available tool sections."""
        canvas_panel = CanvasWidget(
            self.app_state.layout_model, self.app_state.selection_state
        )
        self.canvas_panel = canvas_panel
        inspector_panel = InspectorPanel(
            self.app_state.layout_model,
            self.app_state.selection_state,
            self.app_state.property_registry,
            focus_node_callback=self._focus_node_in_canvas,
        )
        checklist_panel = ChecklistPanel(
            self.app_state.layout_model,
            self.app_state.checklist_engine,
            self.app_state.selection_state,
        )
        export_button = QPushButton("Export DSL")
        export_button.clicked.connect(self._handle_export)
        self.handoff_button = QPushButton("Export Handoff")
        self.handoff_button.clicked.connect(self._handle_export_handoff)
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._handle_save)
        self.save_target_label = QLabel()
        self.save_target_label.setObjectName("save_target_label")
        self.scene_source_selector = QComboBox()
        self.scene_source_selector.setObjectName("scene_source_selector")
        self.scene_source_selector.setStyleSheet(ToolWorkspace.project_input_style())
        self.scene_source_selector.addItem("Project JSON", "project")
        self.scene_source_selector.addItem("UI Extract Packet", "extract_packet")
        self.scene_source_selector.addItem("Scanner Qt Probe", "scanner_repo")
        self.scene_source_selector.currentIndexChanged.connect(
            lambda _index: self._update_scene_source_target_field()
        )
        self.scanner_probe_target_selector = QComboBox()
        self.scanner_probe_target_selector.setObjectName("scanner_probe_target_selector")
        self.scanner_probe_target_selector.setStyleSheet(ToolWorkspace.project_input_style())
        self.scanner_probe_target_selector.addItem("Scanner Main Window", "main_window")
        self.scanner_probe_target_selector.addItem("Scanner Profile Manager", "profile_manager")
        current_scanner_target = self.app_state.get_scanner_probe_target()
        target_index = self.scanner_probe_target_selector.findData(current_scanner_target)
        if target_index >= 0:
            self.scanner_probe_target_selector.setCurrentIndex(target_index)
        self.scanner_probe_target_selector.currentIndexChanged.connect(
            self._commit_scanner_probe_target
        )
        self.scene_source_target_field = QLineEdit()
        self.scene_source_target_field.setObjectName("scene_source_target_field")
        self.scene_source_target_field.setStyleSheet(ToolWorkspace.project_input_style())
        self.scene_source_target_field.editingFinished.connect(
            self._commit_scene_source_target
        )
        self.scene_source_preflight_label = QLabel()
        self.scene_source_preflight_label.setObjectName("scene_source_preflight_label")
        self.scene_action_hint_label = QLabel()
        self.scene_action_hint_label.setObjectName("scene_action_hint_label")
        self.scene_action_hint_label.setWordWrap(True)
        self.scene_action_hint_label.setStyleSheet("color: #6b7280;")
        self.scene_action_context_label = QLabel()
        self.scene_action_context_label.setObjectName("scene_action_context_label")
        self.scene_action_context_label.setWordWrap(True)
        self.scene_action_context_label.setStyleSheet("color: #4b5563;")
        self.scene_replace_button = QPushButton("Replace Current Scene")
        self.scene_replace_button.setObjectName("scene_replace_button")
        self.scene_replace_button.setStyleSheet(
            "color: #991b1b; border: 1px solid #fca5a5;"
        )
        self.scene_replace_button.clicked.connect(self._handle_scene_replace)
        self.scene_alongside_button = QPushButton("Import Alongside")
        self.scene_alongside_button.setObjectName("scene_alongside_button")
        self.scene_alongside_button.clicked.connect(self._handle_scene_import_alongside)
        self.scene_bench_button = QPushButton("Open In Bench")
        self.scene_bench_button.setObjectName("scene_bench_button")
        self.scene_bench_button.setStyleSheet(
            "font-weight: 600; color: #1d4ed8;"
        )
        self.scene_bench_button.clicked.connect(self._handle_scene_open_in_bench)

        self.template_data = self._load_templates()
        self.component_form_builder = ComponentFormBuilder(
            Path(__file__).resolve().parents[1] / "component_templates"
        )
        self.template_selector = QComboBox()
        for name in self.template_data:
            self.template_selector.addItem(name)
        self.template_button = QPushButton("Apply Template")
        self.template_button.clicked.connect(self._handle_add_template)
        self.replace_template_button = QPushButton("Replace With Template")
        self.replace_template_button.clicked.connect(self._handle_replace_with_template)
        self.component_selector = QComboBox()
        for component_name in self.component_form_builder.list_components():
            self.component_selector.addItem(component_name)
        self.new_component_button = QPushButton("New Component")
        self.new_component_button.clicked.connect(self._show_component_form)
        self.add_child_button = QPushButton("Add Child")
        self.add_child_button.clicked.connect(canvas_panel.add_child_to_selected)
        self.delete_button = QPushButton("Delete")
        self.delete_button.clicked.connect(canvas_panel.delete_selected)
        self.focus_selected_button = QPushButton("Focus Selected")
        self.focus_selected_button.clicked.connect(canvas_panel.focus_selected_node)
        self.focus_parent_button = QPushButton("Focus Parent")
        self.focus_parent_button.clicked.connect(canvas_panel.focus_parent)
        self.show_all_button = QPushButton("Show All")
        self.show_all_button.clicked.connect(canvas_panel.clear_focus)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.addWidget(self.add_child_button)
        toolbar_layout.addWidget(self.delete_button)
        component_layout = QHBoxLayout()
        component_layout.setContentsMargins(0, 0, 0, 0)
        component_layout.addWidget(self.component_selector)
        component_layout.addWidget(self.new_component_button)
        self.component_form_container = QWidget()
        self.component_form_layout = QVBoxLayout(self.component_form_container)
        self.component_form_layout.setContentsMargins(0, 0, 0, 0)
        templates_section = QWidget()
        templates_layout = QVBoxLayout(templates_section)
        templates_layout.setContentsMargins(0, 0, 0, 0)
        templates_layout.setSpacing(6)
        templates_layout.addWidget(self.template_selector)
        templates_layout.addWidget(self.template_button)
        templates_layout.addWidget(self.replace_template_button)

        structure_section = QWidget()
        structure_layout = QVBoxLayout(structure_section)
        structure_layout.setContentsMargins(0, 0, 0, 0)
        structure_layout.addLayout(toolbar_layout)

        view_section = QWidget()
        view_layout = QVBoxLayout(view_section)
        view_layout.setContentsMargins(0, 0, 0, 0)
        view_layout.setSpacing(6)
        view_layout.addWidget(self.focus_selected_button)
        view_layout.addWidget(self.focus_parent_button)
        view_layout.addWidget(self.show_all_button)

        components_section = QWidget()
        components_layout = QVBoxLayout(components_section)
        components_layout.setContentsMargins(0, 0, 0, 0)
        components_layout.setSpacing(6)
        components_layout.addLayout(component_layout)
        components_layout.addWidget(self.component_form_container)

        project_section = ProjectIOPanel(
            save_button=self.save_button,
            save_target_label=self.save_target_label,
            scene_source_selector=self.scene_source_selector,
            scanner_probe_target_selector=self.scanner_probe_target_selector,
            scene_source_target_field=self.scene_source_target_field,
            scene_source_preflight_label=self.scene_source_preflight_label,
            scene_action_context_label=self.scene_action_context_label,
            scene_replace_button=self.scene_replace_button,
            scene_alongside_button=self.scene_alongside_button,
            scene_bench_button=self.scene_bench_button,
            scene_action_hint_label=self.scene_action_hint_label,
            handoff_button=self.handoff_button,
            export_button=export_button,
        )

        validation_section = QWidget()
        validation_layout = QVBoxLayout(validation_section)
        validation_layout.setContentsMargins(0, 0, 0, 0)
        validation_layout.addWidget(checklist_panel)

        self.section_contents = {
            "Geometry": canvas_panel.geometry_tool,
            "Components": components_section,
            "Templates": templates_section,
            "Structure": structure_section,
            "View": view_section,
            "Validation": validation_section,
            "Project": project_section,
        }

        self.tool_workspace = ToolWorkspace(
            self,
            self.section_contents,
            self.section_display_names,
        )
        self.selection_window = build_selection_window(self, inspector_panel)
        self.selection_window.show()
        self.tool_workspace_window = self.tool_workspace.workspace_window
        self.tool_workspace_window.show()
        left_toolbar = self.tool_workspace.tool_rail_widget

        center_container = QWidget()
        center_layout = QHBoxLayout(center_container)
        center_layout.setContentsMargins(0, 0, 0, 0)
        center_layout.setSpacing(8)
        center_layout.addWidget(left_toolbar)
        canvas_column = QWidget()
        canvas_column_layout = QVBoxLayout(canvas_column)
        canvas_column_layout.setContentsMargins(0, 0, 0, 0)
        canvas_column_layout.setSpacing(6)
        self.canvas_status_label = QLabel(canvas_panel.get_status_text())
        canvas_column_layout.addWidget(self.canvas_status_label)
        canvas_column_layout.addWidget(canvas_panel, 1)
        center_layout.addWidget(canvas_column, 1)

        center_container.setMinimumWidth(1040)
        left_toolbar.setMinimumWidth(150)
        left_toolbar.setMaximumWidth(190)

        self.setCentralWidget(center_container)
        self.left_toolbar = left_toolbar
        self.section_toggle_buttons = self.tool_workspace.section_toggle_buttons
        self.section_cards = self.tool_workspace.section_cards
        self.active_tool_sections = self.tool_workspace.active_sections
        self.checklist_panel = checklist_panel
        self.inspector_panel = inspector_panel
        self.export_button = export_button
        self.canvas_panel.status_listener = self._update_canvas_status
        self.app_state.selection_state.subscribe(lambda _selected_id: self.checklist_panel.update_checklist())
        self.app_state.layout_model.subscribe(self._handle_model_changed)
        self.checklist_panel.update_checklist()
        self._update_canvas_status(self.canvas_panel.get_status_text())
        self._update_save_target_label()
        self._update_scene_source_target_field()
        self._apply_scene_action_recommendation()
        self._update_scene_action_hint()
        for button in (
            self.scene_replace_button,
            self.scene_alongside_button,
            self.scene_bench_button,
        ):
            button.installEventFilter(self)

    def _install_hotkeys(self):
        self.selection_window_close_shortcut = QShortcut(QKeySequence(Qt.Key.Key_Escape), self)
        self.selection_window_close_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.selection_window_close_shortcut.activated.connect(self._handle_escape_dismissal)

        self.canvas_focus_shortcut = QShortcut(QKeySequence("Ctrl+1"), self)
        self.canvas_focus_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.canvas_focus_shortcut.activated.connect(self._focus_canvas_surface)

        self.selection_window_focus_shortcut = QShortcut(QKeySequence("Ctrl+2"), self)
        self.selection_window_focus_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
        self.selection_window_focus_shortcut.activated.connect(self._focus_selection_window)

    def _handle_export(self):
        """Print DSL export when the checklist allows it."""
        if self.builder.can_export():
            print(self.builder.build_dsl())
            print("Export successful")
        else:
            print("Export blocked: fix errors in checklist")

    def _handle_export_handoff(self):
        """Print a deterministic handoff packet describing the current project state."""
        print(json.dumps(self._build_handoff_packet(), indent=2, sort_keys=True))

    def _build_handoff_packet(self):
        """Capture selection, camera, layout, and export state for AI handoff."""
        return build_handoff_packet(
            layout_model=self.app_state.layout_model,
            selection_state=self.app_state.selection_state,
            checklist_engine=self.app_state.checklist_engine,
            canvas_panel=self.canvas_panel,
            builder=self.builder,
        )

    def _handle_add_template(self):
        """Insert the selected scaffold into the current project."""
        template_name = self.template_selector.currentText()
        template = self.template_data.get(template_name)
        if template is None:
            return
        self.canvas_panel.apply_template(template, replace_root=False)
        self.checklist_panel.update_checklist()

    def _handle_replace_with_template(self):
        """Replace the current root content with the selected scaffold."""
        template_name = self.template_selector.currentText()
        template = self.template_data.get(template_name)
        if template is None:
            return
        self.canvas_panel.apply_template(template, replace_root=True)
        self.checklist_panel.update_checklist()

    def _handle_save(self):
        """Save the current project JSON to the default local file."""
        save_project(
            self.app_state.layout_model,
            self.app_state.get_scene_source_target("project"),
        )
        print("Project saved")

    def _selected_scene_source(self) -> str:
        return selected_scene_source(self.scene_source_selector)

    def _scene_source_target_path(self) -> str:
        return scene_source_target_path(self.app_state, self._selected_scene_source())

    def _selected_scene_source_label(self) -> str:
        return selected_scene_source_label(
            self._selected_scene_source(),
            self._selected_scanner_probe_label(),
        )

    def _selected_scanner_probe_target(self) -> str:
        return selected_scanner_probe_target(self.scanner_probe_target_selector)

    def _selected_scanner_probe_label(self) -> str:
        return selected_scanner_probe_label(self._selected_scanner_probe_target())

    def _default_scene_source_target_path(self) -> str:
        return default_scene_source_target_path(self._selected_scene_source())

    def _scene_action_target_suffix(self) -> str:
        return scene_action_target_suffix(
            self._scene_source_target_path() or "",
            self._default_scene_source_target_path(),
        )

    def _update_save_target_label(self) -> None:
        self.save_target_label.setText(
            f"Save Target: {self.app_state.get_scene_source_target('project')}"
        )

    def _update_scene_source_target_field(self) -> None:
        self.scene_source_target_field.setText(self._scene_source_target_path())
        self.scanner_probe_target_selector.setVisible(
            self._selected_scene_source() == "scanner_repo"
        )
        self._update_scene_source_preflight_label()
        self._update_scene_action_enabled_state()
        self._apply_scene_action_recommendation()
        self._update_scene_action_hint()

    def _commit_scene_source_target(self) -> None:
        self.app_state.set_scene_source_target(
            self._selected_scene_source(),
            self.scene_source_target_field.text().strip(),
        )
        self._update_save_target_label()
        self._update_scene_source_target_field()

    def _commit_scanner_probe_target(self, _index: int) -> None:
        self.app_state.set_scanner_probe_target(self._selected_scanner_probe_target())
        self._apply_scene_action_recommendation()
        self._update_scene_action_hint()

    def _update_scene_source_preflight_label(self) -> None:
        self.scene_source_preflight_label.setText(self._scene_source_preflight_text())

    def _scene_source_preflight_text(self) -> str:
        return scene_source_preflight_text(
            selected_source=self._selected_scene_source(),
            target_path=self._scene_source_target_path(),
            scanner_probe_target=self._selected_scanner_probe_target(),
            validate_scanner_repo_root=validate_scanner_repo_root,
            validate_scanner_probe_target=validate_scanner_probe_target,
            validate_ui_extract_packet=validate_ui_extract_packet,
        )

    def _scene_source_is_actionable(self) -> bool:
        return self._scene_source_preflight_text().startswith("Preflight: valid")

    def _update_scene_action_enabled_state(self) -> None:
        enabled = self._scene_source_is_actionable()
        self.scene_replace_button.setEnabled(enabled)
        self.scene_alongside_button.setEnabled(enabled)
        self.scene_bench_button.setEnabled(enabled)

    def _scene_action_hint_text(self, action: str) -> str:
        return scene_action_hint_text(action)

    def _recommended_scene_action(self) -> str:
        return recommended_scene_action(
            getattr(self.app_state.layout_model, "scene_metadata", {})
        )

    def _scene_action_context_text(self) -> str:
        return scene_action_context_text(
            actionable=self._scene_source_is_actionable(),
            scene_metadata=getattr(self.app_state.layout_model, "scene_metadata", {}),
            source_label=self._selected_scene_source_label(),
            target_suffix=self._scene_action_target_suffix(),
        )

    def _apply_scene_action_recommendation(self) -> None:
        recommended = self._recommended_scene_action()
        self.scene_replace_button.setText("Replace Current Scene")
        self.scene_alongside_button.setText("Import Alongside")
        self.scene_bench_button.setText("Open In Bench")
        self.scene_action_context_label.setText(self._scene_action_context_text())
        if recommended == "alongside":
            self.scene_alongside_button.setText("Import Alongside (Recommended)")
        elif recommended == "bench":
            self.scene_bench_button.setText("Open In Bench (Recommended)")

    def _update_scene_action_hint(self, action: str | None = None) -> None:
        if not self._scene_source_is_actionable():
            self.scene_action_hint_label.setText("")
            return
        action = action or self._recommended_scene_action()
        self.scene_action_hint_label.setText(self._scene_action_hint_text(action))

    def _handle_model_changed(self) -> None:
        self._apply_scene_action_recommendation()
        self._update_scene_action_hint()

    def _handle_scene_replace(self):
        self._update_scene_action_hint("replace")
        self._dispatch_scene_action("replace")

    def _handle_scene_import_alongside(self):
        self._update_scene_action_hint("alongside")
        self._dispatch_scene_action("alongside")

    def _handle_scene_open_in_bench(self):
        self._update_scene_action_hint("bench")
        self._dispatch_scene_action("bench")

    def _dispatch_scene_action(self, action: str) -> None:
        route = route_scene_action(self._selected_scene_source(), action)
        handlers = {
            "project_replace": self._handle_load_replace,
            "project_alongside": self._handle_load_alongside,
            "project_bench": self._handle_load_in_bench,
            "extract_packet_replace": self._handle_load_extract_packet_replace,
            "extract_packet_alongside": self._handle_load_extract_packet_alongside,
            "extract_packet_bench": self._handle_load_extract_packet_in_bench,
            "scanner_replace": self._handle_load_scanner_probe_replace,
            "scanner_alongside": self._handle_load_scanner_probe_alongside,
            "scanner_bench": self._handle_load_scanner_probe_in_bench,
        }
        handler = handlers.get(route)
        if handler is None:
            raise ValueError(f"Unknown scene action route: {route}")
        handler()

    def eventFilter(self, watched, event):
        if watched is self.scene_replace_button and event.type() in {QEvent.Type.FocusIn, QEvent.Type.Enter}:
            self._update_scene_action_hint("replace")
        elif watched is self.scene_alongside_button and event.type() in {QEvent.Type.FocusIn, QEvent.Type.Enter}:
            self._update_scene_action_hint("alongside")
        elif watched is self.scene_bench_button and event.type() in {QEvent.Type.FocusIn, QEvent.Type.Enter}:
            self._update_scene_action_hint("bench")
        return super().eventFilter(watched, event)

    def _handle_load_replace(self):
        """Replace the current scene with the default local project file."""
        project_replace(
            layout_model=self.app_state.layout_model,
            property_registry=self.app_state.property_registry,
            selection_state=self.app_state.selection_state,
            canvas_panel=self.canvas_panel,
            checklist_panel=self.checklist_panel,
            target_path=self.app_state.get_scene_source_target("project"),
        )
        print("Project replaced current scene")

    def _handle_load_alongside(self):
        """Import the default local project file alongside the current scene."""
        project_alongside(
            layout_model=self.app_state.layout_model,
            property_registry=self.app_state.property_registry,
            selection_state=self.app_state.selection_state,
            canvas_panel=self.canvas_panel,
            checklist_panel=self.checklist_panel,
            target_path=self.app_state.get_scene_source_target("project"),
        )
        print("Project imported alongside current scene")

    def _handle_load_in_bench(self):
        """Open the default local project file in bench."""
        project_bench(
            layout_model=self.app_state.layout_model,
            property_registry=self.app_state.property_registry,
            selection_state=self.app_state.selection_state,
            canvas_panel=self.canvas_panel,
            checklist_panel=self.checklist_panel,
            target_path=self.app_state.get_scene_source_target("project"),
        )
        print("Project opened in bench")

    def _handle_load_extract_packet_replace(self):
        """Replace the current scene with the default local UI extract packet."""
        extract_packet_replace(
            layout_model=self.app_state.layout_model,
            selection_state=self.app_state.selection_state,
            canvas_panel=self.canvas_panel,
            checklist_panel=self.checklist_panel,
            target_path=self.app_state.get_scene_source_target("extract_packet"),
        )
        print("Extract packet replaced current scene")

    def _handle_load_extract_packet_alongside(self):
        """Import the default local UI extract packet alongside the current scene."""
        extract_packet_alongside(
            layout_model=self.app_state.layout_model,
            selection_state=self.app_state.selection_state,
            canvas_panel=self.canvas_panel,
            checklist_panel=self.checklist_panel,
            target_path=self.app_state.get_scene_source_target("extract_packet"),
        )
        print("Extract packet imported alongside current scene")

    def _handle_load_extract_packet_in_bench(self):
        """Open the default local UI extract packet as a bench projection."""
        extract_packet_bench(
            layout_model=self.app_state.layout_model,
            selection_state=self.app_state.selection_state,
            canvas_panel=self.canvas_panel,
            checklist_panel=self.checklist_panel,
            target_path=self.app_state.get_scene_source_target("extract_packet"),
        )
        print("Extract packet opened in bench")

    def _handle_load_scanner_probe_replace(self):
        """Replace the current scene with the probed scanner main window."""
        scanner_replace(
            layout_model=self.app_state.layout_model,
            selection_state=self.app_state.selection_state,
            canvas_panel=self.canvas_panel,
            checklist_panel=self.checklist_panel,
            target_path=self.app_state.get_scene_source_target("scanner_repo"),
            probe_target=self._selected_scanner_probe_target(),
        )
        print("Scanner probe replaced current scene")

    def _handle_load_scanner_probe_alongside(self):
        """Import the probed scanner main window alongside the current scene."""
        scanner_alongside(
            layout_model=self.app_state.layout_model,
            selection_state=self.app_state.selection_state,
            canvas_panel=self.canvas_panel,
            checklist_panel=self.checklist_panel,
            target_path=self.app_state.get_scene_source_target("scanner_repo"),
            probe_target=self._selected_scanner_probe_target(),
        )
        print("Scanner probe imported alongside current scene")

    def _handle_load_scanner_probe_in_bench(self):
        """Open the probed scanner main window in bench."""
        scanner_bench(
            layout_model=self.app_state.layout_model,
            selection_state=self.app_state.selection_state,
            canvas_panel=self.canvas_panel,
            checklist_panel=self.checklist_panel,
            target_path=self.app_state.get_scene_source_target("scanner_repo"),
            probe_target=self._selected_scanner_probe_target(),
        )
        print("Scanner probe opened in bench")

    def _show_component_form(self):
        """Render the generated component form for the selected component type."""
        component_type = self.component_selector.currentText()
        self._clear_component_form()
        form = self.component_form_builder.build_form(component_type, self._handle_component_submit)
        self.component_form_layout.addWidget(form)

    def _focus_node_in_canvas(self, node_id: str):
        if not node_id:
            return
        self.app_state.selection_state.set_selection(node_id)
        self.canvas_panel.focus_selected_node()

    def _handle_escape_dismissal(self):
        close_selection_window(getattr(self, "selection_window", None))

    def _focus_canvas_surface(self):
        self.activateWindow()
        self.raise_()
        self.canvas_panel.setFocus(Qt.FocusReason.ShortcutFocusReason)

    def _focus_selection_window(self):
        focus_selection_window(
            self,
            getattr(self, "selection_window", None),
            getattr(self, "inspector_panel", None),
        )

    def _handle_component_submit(self, payload):
        """Create a component from the submitted form payload."""
        self.canvas_panel.create_component_node(payload["type"], payload["properties"])
        self.checklist_panel.update_checklist()

    def _clear_component_form(self):
        """Remove any previously rendered component form widget."""
        while self.component_form_layout.count():
            item = self.component_form_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _load_templates(self):
        """Load scaffold definitions from the repo template file."""
        templates_path = Path(__file__).resolve().parents[1] / "templates" / "templates.json"
        with open(templates_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _position_tool_workspace_window(self):
        position_tool_workspace_window(
            self,
            getattr(self, "tool_workspace_window", None),
        )

    def _position_selection_window(self):
        position_selection_window(
            self,
            getattr(self, "selection_window", None),
        )

    def _update_canvas_status(self, text: str):
        self.canvas_status_label.setText(text)

    def moveEvent(self, event):
        super().moveEvent(event)
        sync_floating_windows(
            self,
            getattr(self, "selection_window", None),
            getattr(self, "tool_workspace_window", None),
        )

    def closeEvent(self, event):
        close_floating_windows(
            getattr(self, "selection_window", None),
            getattr(self, "tool_workspace_window", None),
        )
        super().closeEvent(event)
