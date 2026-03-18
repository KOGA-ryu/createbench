from __future__ import annotations

import json
from pathlib import Path

from canvas.canvas_widget import CanvasWidget
from checklist.checklist_panel import ChecklistPanel
from export.dsl_builder import DSLBuilder
from forms.component_form_builder import ComponentFormBuilder
from inspector.inspector_panel import InspectorPanel
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from project_io import load_project, save_project


class MainWindow(QMainWindow):
    def __init__(self, app_state):
        super().__init__()
        self.app_state = app_state
        self.builder = DSLBuilder(
            self.app_state.layout_model,
            self.app_state.property_registry,
            self.app_state.checklist_engine,
        )
        self.setWindowTitle("Create Bench")
        self._build_ui()

    def _build_ui(self):
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
        self.save_button = QPushButton("Save")
        self.save_button.clicked.connect(self._handle_save)
        self.load_button = QPushButton("Load")
        self.load_button.clicked.connect(self._handle_load)

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

        canvas_container = QWidget()
        canvas_layout = QVBoxLayout(canvas_container)
        canvas_layout.setContentsMargins(0, 0, 0, 0)
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
        canvas_layout.addWidget(self.template_selector)
        canvas_layout.addWidget(self.template_button)
        canvas_layout.addWidget(self.replace_template_button)
        canvas_layout.addLayout(toolbar_layout)
        canvas_layout.addLayout(component_layout)
        canvas_layout.addWidget(self.component_form_container)
        canvas_layout.addWidget(canvas_panel)

        checklist_container = QWidget()
        checklist_layout = QVBoxLayout(checklist_container)
        checklist_layout.setContentsMargins(0, 0, 0, 0)
        checklist_layout.addWidget(self.save_button)
        checklist_layout.addWidget(self.load_button)
        checklist_layout.addWidget(export_button)
        checklist_layout.addWidget(checklist_panel)

        right_splitter = QSplitter(Qt.Orientation.Vertical)
        right_splitter.addWidget(inspector_panel)
        right_splitter.addWidget(checklist_container)
        right_splitter.setSizes([60, 40])
        right_splitter.setChildrenCollapsible(False)

        horizontal_splitter = QSplitter(Qt.Orientation.Horizontal)
        horizontal_splitter.addWidget(canvas_container)
        horizontal_splitter.addWidget(right_splitter)
        horizontal_splitter.setSizes([70, 30])
        horizontal_splitter.setChildrenCollapsible(False)

        canvas_container.setMinimumWidth(320)
        inspector_panel.setMinimumHeight(160)
        checklist_container.setMinimumHeight(120)
        right_splitter.setMinimumWidth(260)

        self.setCentralWidget(horizontal_splitter)
        self.checklist_panel = checklist_panel
        self.export_button = export_button
        self.app_state.selection_state.subscribe(lambda _selected_id: self.checklist_panel.update_checklist())
        self.checklist_panel.update_checklist()

    def _handle_export(self):
        if self.builder.can_export():
            print(self.builder.build_dsl())
            print("Export successful")
        else:
            print("Export blocked: fix errors in checklist")

    def _handle_add_template(self):
        template_name = self.template_selector.currentText()
        template = self.template_data.get(template_name)
        if template is None:
            return
        self.canvas_panel.apply_template(template, replace_root=False)
        self.checklist_panel.update_checklist()

    def _handle_replace_with_template(self):
        template_name = self.template_selector.currentText()
        template = self.template_data.get(template_name)
        if template is None:
            return
        self.canvas_panel.apply_template(template, replace_root=True)
        self.checklist_panel.update_checklist()

    def _handle_save(self):
        save_project(self.app_state.layout_model, "project.json")
        print("Project saved")

    def _handle_load(self):
        load_project(
            self.app_state.layout_model,
            self.app_state.property_registry,
            "project.json",
        )
        self.app_state.selection_state.clear_selection()
        self.canvas_panel.update()
        self.checklist_panel.update_checklist()
        print("Project loaded")

    def _show_component_form(self):
        component_type = self.component_selector.currentText()
        self._clear_component_form()
        form = self.component_form_builder.build_form(component_type, self._handle_component_submit)
        self.component_form_layout.addWidget(form)

    def _handle_component_submit(self, payload):
        self.canvas_panel.create_component_node(payload["type"], payload["properties"])
        self.checklist_panel.update_checklist()

    def _clear_component_form(self):
        while self.component_form_layout.count():
            item = self.component_form_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _load_templates(self):
        templates_path = Path(__file__).resolve().parents[1] / "templates" / "templates.json"
        with open(templates_path, "r", encoding="utf-8") as handle:
            return json.load(handle)
