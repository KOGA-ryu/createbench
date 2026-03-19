from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import QEvent
from canvas.canvas_widget import CanvasWidget
from checklist.checklist_panel import ChecklistPanel
from core.scene_resolution import resolve_scene_state
from export.dsl_builder import DSLBuilder
from export.dsl_builder import DSL_VERSION
from forms.component_form_builder import ComponentFormBuilder
from inspector.inspector_panel import InspectorPanel
from ui_extract_packet import load_packet as load_ui_extract_packet
from ui_extract_packet import load_packet_alongside as load_ui_extract_packet_alongside
from ui_extract_packet import load_packet_in_bench as load_ui_extract_packet_in_bench
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
from project_io import (
    load_project,
    load_project_alongside,
    load_project_in_bench,
    save_project,
)


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
            "Inspector": "Selection",
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
        self._position_tool_workspace_window()

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
        self.scene_source_selector.addItem("Project JSON", "project")
        self.scene_source_selector.addItem("UI Extract Packet", "extract_packet")
        self.scene_source_selector.currentIndexChanged.connect(
            lambda _index: self._update_scene_source_target_field()
        )
        self.scene_source_target_field = QLineEdit()
        self.scene_source_target_field.setObjectName("scene_source_target_field")
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

        project_section = QWidget()
        project_layout = QVBoxLayout(project_section)
        project_layout.setContentsMargins(0, 0, 0, 0)
        project_layout.setSpacing(6)
        project_layout.addWidget(
            self._build_project_group(
                "Save & Persist",
                "project_save_group",
                self.save_button,
                self.save_target_label,
            )
        )
        project_layout.addWidget(
            self._build_project_group(
                "Source Target",
                "project_source_group",
                self.scene_source_selector,
                self.scene_source_target_field,
                self.scene_source_preflight_label,
            )
        )
        project_layout.addWidget(
            self._build_project_group(
                "Scene Actions",
                "project_scene_actions_group",
                self.scene_action_context_label,
                self.scene_replace_button,
                self.scene_alongside_button,
                self.scene_bench_button,
                self.scene_action_hint_label,
            )
        )
        project_layout.addWidget(
            self._build_project_group(
                "Export",
                "project_export_group",
                self.handoff_button,
                export_button,
            )
        )

        validation_section = QWidget()
        validation_layout = QVBoxLayout(validation_section)
        validation_layout.setContentsMargins(0, 0, 0, 0)
        validation_layout.addWidget(checklist_panel)

        self.section_contents = {
            "Inspector": inspector_panel,
            "Geometry": canvas_panel.geometry_tool,
            "Components": components_section,
            "Templates": templates_section,
            "Structure": structure_section,
            "View": view_section,
            "Validation": validation_section,
            "Project": project_section,
        }

        self.tool_workspace_window = self._build_tool_workspace_window()
        self.tool_workspace_window.show()
        left_toolbar = self._build_left_toolbar()

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

    def _build_project_group(
        self, title: str, object_name: str, *widgets: QWidget
    ) -> QFrame:
        group = QFrame()
        group.setObjectName(object_name)
        group.setFrameShape(QFrame.Shape.StyledPanel)
        group.setStyleSheet(self._project_group_style(object_name))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName(f"{object_name}_title")
        title_label.setStyleSheet(self._project_group_title_style(object_name))
        layout.addWidget(title_label)
        for widget in widgets:
            layout.addWidget(widget)
        return group

    def _project_group_title_style(self, object_name: str) -> str:
        if object_name == "project_scene_actions_group":
            return "font-weight: 700; color: #111827;"
        return "font-weight: 600; color: #374151; font-size: 11px;"

    def _project_group_style(self, object_name: str) -> str:
        if object_name == "project_scene_actions_group":
            return "QFrame { background: #f8fafc; border: 1px solid #cbd5e1; }"
        return "QFrame { background: #ffffff; border: 1px solid #e5e7eb; }"

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
        canvas_rect = self.canvas_panel.authored_canvas_rect()
        rect_map = self.canvas_panel.layout_engine.compute_layout(
            self.app_state.layout_model.root_id, canvas_rect
        )
        checklist = self.app_state.checklist_engine.run()
        packet = {
            "selection": self.app_state.selection_state.get_selection(),
            "scene_metadata": dict(getattr(self.app_state.layout_model, "scene_metadata", {})),
            "canvas_rect": canvas_rect,
            "viewport": self.canvas_panel.get_viewport_state(),
            "draw_order": list(self.canvas_panel.layout_engine.draw_order),
            "rect_map": rect_map,
            "checklist": checklist,
            "project_json": None,
            "dsl": None,
            "export_error": None,
        }
        try:
            packet["project_json"] = self.builder.build_json(mode="expanded")
            packet["dsl"] = self.builder.build_dsl(mode="expanded")
        except Exception as exc:
            packet["export_error"] = str(exc)
        return packet

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
        return str(self.scene_source_selector.currentData() or "project")

    def _scene_source_target_path(self) -> str:
        return self.app_state.get_scene_source_target(self._selected_scene_source())

    def _selected_scene_source_label(self) -> str:
        return "UI extract packet" if self._selected_scene_source() == "extract_packet" else "project JSON"

    def _default_scene_source_target_path(self) -> str:
        defaults = {
            "project": "project.json",
            "extract_packet": "ui_extract_packet.json",
        }
        return defaults.get(self._selected_scene_source(), "")

    def _scene_action_target_suffix(self) -> str:
        target_path = self._scene_source_target_path() or ""
        if not target_path:
            return ""
        if target_path == self._default_scene_source_target_path():
            return ""
        return f" at {target_path}"

    def _update_save_target_label(self) -> None:
        self.save_target_label.setText(
            f"Save Target: {self.app_state.get_scene_source_target('project')}"
        )

    def _update_scene_source_target_field(self) -> None:
        self.scene_source_target_field.setText(self._scene_source_target_path())
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

    def _update_scene_source_preflight_label(self) -> None:
        self.scene_source_preflight_label.setText(self._scene_source_preflight_text())

    def _scene_source_preflight_text(self) -> str:
        target_path = Path(self._scene_source_target_path())
        if not target_path.exists():
            return "Preflight: missing target"
        try:
            with open(target_path, "r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except Exception:
            return "Preflight: unreadable file"

        if self._selected_scene_source() == "extract_packet":
            try:
                validate_ui_extract_packet(payload)
            except Exception:
                return "Preflight: invalid extract packet"
            return "Preflight: valid extract packet"

        if not isinstance(payload, dict):
            return "Preflight: invalid project file"
        if payload.get("version") != DSL_VERSION:
            return "Preflight: invalid project version"
        if "data" not in payload:
            return "Preflight: invalid project file"
        return "Preflight: valid project file"

    def _scene_source_is_actionable(self) -> bool:
        return self._scene_source_preflight_text().startswith("Preflight: valid")

    def _update_scene_action_enabled_state(self) -> None:
        enabled = self._scene_source_is_actionable()
        self.scene_replace_button.setEnabled(enabled)
        self.scene_alongside_button.setEnabled(enabled)
        self.scene_bench_button.setEnabled(enabled)

    def _scene_action_hint_text(self, action: str) -> str:
        hints = {
            "replace": "Replace: clears the current scene and loads the selected source into it",
            "alongside": "Alongside: preserves the current scene and adds the selected source beside it",
            "bench": "Recommended: Bench preserves the current scene and opens the selected source in an isolated bench session",
        }
        return hints[action]

    def _recommended_scene_action(self) -> str:
        resolved_scene = resolve_scene_state(
            getattr(self.app_state.layout_model, "scene_metadata", {})
        )
        if resolved_scene["resolved_mode"] in {"source", "bench"}:
            return "bench"
        return "alongside"

    def _scene_action_context_text(self) -> str:
        if not self._scene_source_is_actionable():
            return "Scene actions are unavailable until the selected source passes preflight."
        resolved_scene = resolve_scene_state(
            getattr(self.app_state.layout_model, "scene_metadata", {})
        )
        source_label = self._selected_scene_source_label()
        target_suffix = self._scene_action_target_suffix()
        if resolved_scene["resolved_mode"] == "source":
            return f"Current scene is source-backed, so bench is the safest isolated path for incoming {source_label}{target_suffix}."
        if resolved_scene["resolved_mode"] == "bench":
            return f"Current scene is bench-focused, so bench keeps incoming {source_label}{target_suffix} isolated."
        return f"Current scene is design-only, so alongside keeps existing work visible while adding incoming {source_label}{target_suffix}."

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
        if self._selected_scene_source() == "extract_packet":
            self._handle_load_extract_packet_replace()
        else:
            self._handle_load_replace()

    def _handle_scene_import_alongside(self):
        self._update_scene_action_hint("alongside")
        if self._selected_scene_source() == "extract_packet":
            self._handle_load_extract_packet_alongside()
        else:
            self._handle_load_alongside()

    def _handle_scene_open_in_bench(self):
        self._update_scene_action_hint("bench")
        if self._selected_scene_source() == "extract_packet":
            self._handle_load_extract_packet_in_bench()
        else:
            self._handle_load_in_bench()

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
        load_project(
            self.app_state.layout_model,
            self.app_state.property_registry,
            self.app_state.get_scene_source_target("project"),
        )
        self.app_state.selection_state.clear_selection()
        self.canvas_panel.update()
        self.checklist_panel.update_checklist()
        print("Project replaced current scene")

    def _handle_load_alongside(self):
        """Import the default local project file alongside the current scene."""
        created_root_ids = load_project_alongside(
            self.app_state.layout_model,
            self.app_state.property_registry,
            self.app_state.get_scene_source_target("project"),
        )
        if created_root_ids:
            self.app_state.selection_state.set_selection(created_root_ids[0])
        else:
            self.app_state.selection_state.clear_selection()
        self.canvas_panel.update()
        self.checklist_panel.update_checklist()
        print("Project imported alongside current scene")

    def _handle_load_in_bench(self):
        """Open the default local project file in bench."""
        created_root_ids = load_project_in_bench(
            self.app_state.layout_model,
            self.app_state.property_registry,
            self.app_state.get_scene_source_target("project"),
        )
        if created_root_ids:
            self.app_state.selection_state.set_selection(created_root_ids[0])
        else:
            self.app_state.selection_state.clear_selection()
        self.canvas_panel.update()
        self.checklist_panel.update_checklist()
        print("Project opened in bench")

    def _handle_load_extract_packet_replace(self):
        """Replace the current scene with the default local UI extract packet."""
        load_ui_extract_packet(
            self.app_state.layout_model,
            self.app_state.get_scene_source_target("extract_packet"),
        )
        self.app_state.selection_state.clear_selection()
        self.canvas_panel.update()
        self.checklist_panel.update_checklist()
        print("Extract packet replaced current scene")

    def _handle_load_extract_packet_alongside(self):
        """Import the default local UI extract packet alongside the current scene."""
        created_root_ids = load_ui_extract_packet_alongside(
            self.app_state.layout_model,
            self.app_state.get_scene_source_target("extract_packet"),
        )
        if created_root_ids:
            self.app_state.selection_state.set_selection(created_root_ids[0])
        else:
            self.app_state.selection_state.clear_selection()
        self.canvas_panel.update()
        self.checklist_panel.update_checklist()
        print("Extract packet imported alongside current scene")

    def _handle_load_extract_packet_in_bench(self):
        """Open the default local UI extract packet as a bench projection."""
        created_root_ids = load_ui_extract_packet_in_bench(
            self.app_state.layout_model,
            self.app_state.get_scene_source_target("extract_packet"),
        )
        if created_root_ids:
            self.app_state.selection_state.set_selection(created_root_ids[0])
        else:
            self.app_state.selection_state.clear_selection()
        self.canvas_panel.update()
        self.checklist_panel.update_checklist()
        print("Extract packet opened in bench")

    def _show_component_form(self):
        """Render the generated component form for the selected component type."""
        component_type = self.component_selector.currentText()
        self._clear_component_form()
        form = self.component_form_builder.build_form(component_type, self._handle_component_submit)
        self.component_form_layout.addWidget(form)

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

    def _build_tool_workspace_window(self):
        """Create the floating window that hosts opened tool sections."""
        window = QWidget(self, Qt.WindowType.Tool)
        window.setWindowTitle("Tool Workspace")
        layout = QVBoxLayout(window)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.left_tool_stack = QVBoxLayout(content)
        self.left_tool_stack.setContentsMargins(0, 0, 0, 0)
        self.left_tool_stack.setSpacing(8)
        self.left_tool_stack.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        window.resize(340, 720)
        return window

    def _build_left_toolbar(self):
        """Create the compact left rail of tool section toggles."""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(QLabel("Tools"))
        section_order = [
            "Inspector",
            "Geometry",
            "Components",
            "Templates",
            "Structure",
            "View",
            "Validation",
            "Project",
        ]
        for section_name in section_order:
            button = QToolButton()
            button.setText(self.section_display_names[section_name])
            button.setCheckable(True)
            button.setChecked(False)
            button.setArrowType(Qt.ArrowType.RightArrow)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.toggled.connect(
                lambda checked, name=section_name: self._toggle_tool_section(name, checked)
            )
            self.section_toggle_buttons[section_name] = button
            layout.addWidget(button)
        layout.addStretch()
        return panel

    def _toggle_tool_section(self, section_name: str, checked: bool):
        button = self.section_toggle_buttons[section_name]
        button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        if checked:
            if section_name not in self.active_tool_sections:
                self.active_tool_sections.append(section_name)
        else:
            if section_name in self.active_tool_sections:
                self.active_tool_sections.remove(section_name)
        self._rebuild_left_tool_stack()

    def _rebuild_left_tool_stack(self):
        while self.left_tool_stack.count() > 1:
            item = self.left_tool_stack.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        for section_name in self.active_tool_sections:
            card = self.section_cards.get(section_name)
            if card is None:
                card = self._make_section_card(section_name, self.section_contents[section_name])
                self.section_cards[section_name] = card
            self.left_tool_stack.insertWidget(self.left_tool_stack.count() - 1, card)
        if self.active_tool_sections:
            self.tool_workspace_window.show()
            self.tool_workspace_window.raise_()

    def _make_section_card(self, title: str, content_widget: QWidget):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        header = QLabel(self.section_display_names.get(title, title))
        layout.addWidget(header)
        content_widget.setParent(card)
        layout.addWidget(content_widget)
        return card

    def _position_tool_workspace_window(self):
        if not hasattr(self, "tool_workspace_window"):
            return
        frame = self.frameGeometry()
        self.tool_workspace_window.move(frame.topLeft().x() + 210, frame.topLeft().y() + 80)

    def _update_canvas_status(self, text: str):
        self.canvas_status_label.setText(text)

    def moveEvent(self, event):
        super().moveEvent(event)
        if hasattr(self, "tool_workspace_window") and not self.tool_workspace_window.isHidden():
            self._position_tool_workspace_window()

    def closeEvent(self, event):
        if hasattr(self, "tool_workspace_window"):
            self.tool_workspace_window.close()
        super().closeEvent(event)
