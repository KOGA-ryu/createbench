from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class ComponentFormBuilder:
    def __init__(self, component_templates_path):
        self.templates_path = Path(component_templates_path)
        self.templates: dict[str, dict] = {}
        self._load_templates()

    def list_components(self) -> list[str]:
        return sorted(self.templates)

    def get_template(self, component_type: str) -> dict:
        if component_type not in self.templates:
            raise ValueError(f"Unknown component template: {component_type}")
        return dict(self.templates[component_type])

    def build_form(self, component_type: str, on_submit) -> QWidget:
        template = self.get_template(component_type)
        form = QWidget()
        form.setObjectName(f"component_form_{component_type}")
        layout = QVBoxLayout(form)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        title = QLabel(template.get("display_name", component_type))
        title.setObjectName("component_form_title")
        description = QLabel(template.get("description", ""))
        description.setWordWrap(True)
        description.setObjectName("component_form_description")
        layout.addWidget(title)
        layout.addWidget(description)

        field_widgets: dict[str, QWidget] = {}
        for trait_name, trait_def in template.get("traits", {}).items():
            field = self._build_trait_field(component_type, trait_name, trait_def)
            field_widgets[trait_name] = field["input"]
            layout.addWidget(field["container"])

        custom_name = QLineEdit()
        custom_name.setObjectName("component_custom_trait_name")
        custom_value = QLineEdit()
        custom_value.setObjectName("component_custom_trait_value")
        custom_add = QPushButton("Add Custom Trait")
        custom_add.setObjectName("component_custom_trait_add")
        custom_list = QLabel("")
        custom_list.setObjectName("component_custom_trait_list")
        custom_list.setWordWrap(True)
        custom_traits: dict[str, str] = {}

        custom_row = QHBoxLayout()
        custom_row.addWidget(custom_name)
        custom_row.addWidget(custom_value)
        custom_row.addWidget(custom_add)
        layout.addLayout(custom_row)
        layout.addWidget(custom_list)

        def add_custom_trait():
            name = custom_name.text().strip()
            value = custom_value.text()
            if not name:
                return
            custom_traits[name] = value
            custom_list.setText(", ".join(f"{key}={custom_traits[key]}" for key in sorted(custom_traits)))
            custom_name.clear()
            custom_value.clear()

        custom_add.clicked.connect(add_custom_trait)

        submit = QPushButton("Create Component")
        submit.setObjectName("component_form_submit")
        layout.addWidget(submit)

        def handle_submit():
            properties = {}
            for trait_name, trait_def in template.get("traits", {}).items():
                value = self._read_trait_value(field_widgets[trait_name], trait_def)
                properties[trait_name] = value

            display_rules = template.get("display_rules", {})
            if "width" not in properties and "preferred_width" in display_rules:
                properties["width"] = display_rules["preferred_width"]
            if "height" not in properties and "preferred_height" in display_rules:
                properties["height"] = display_rules["preferred_height"]
            if "width" not in template.get("traits", {}) and "preferred_width" in display_rules:
                properties.setdefault("width", display_rules["preferred_width"])
            if "height" not in template.get("traits", {}) and "preferred_height" in display_rules:
                properties.setdefault("height", display_rules["preferred_height"])

            properties.update(custom_traits)
            on_submit({"type": template["type"], "properties": properties})

        submit.clicked.connect(handle_submit)
        return form

    def _load_templates(self) -> None:
        for file_path in sorted(self.templates_path.glob("*.json")):
            with open(file_path, "r", encoding="utf-8") as handle:
                self.templates[file_path.stem] = json.load(handle)

    def _build_trait_field(self, component_type: str, trait_name: str, trait_def: dict) -> dict:
        container = QWidget()
        container.setObjectName(f"component_trait_container_{trait_name}")
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        label = QLabel(trait_name)
        label.setObjectName(f"component_trait_label_{trait_name}")
        description = QLabel(trait_def.get("description", ""))
        description.setWordWrap(True)
        description.setObjectName(f"component_trait_description_{trait_name}")

        trait_type = trait_def.get("type")
        default = trait_def.get("default")
        if trait_type == "bool":
            input_widget = QCheckBox()
            input_widget.setChecked(bool(default))
        elif trait_type == "enum":
            input_widget = QComboBox()
            for value in trait_def.get("allowed_values", []):
                input_widget.addItem(str(value))
            if default is not None:
                index = input_widget.findText(str(default))
                if index >= 0:
                    input_widget.setCurrentIndex(index)
        else:
            input_widget = QLineEdit("" if default is None else str(default))
        input_widget.setObjectName(f"component_trait_input_{component_type}_{trait_name}")

        layout.addWidget(label)
        layout.addWidget(input_widget)
        layout.addWidget(description)
        return {"container": container, "input": input_widget}

    def _read_trait_value(self, widget: QWidget, trait_def: dict):
        trait_type = trait_def.get("type")
        default = trait_def.get("default")
        if trait_type == "bool":
            return widget.isChecked()
        if trait_type == "enum":
            return widget.currentText()
        if trait_type == "int":
            text = widget.text().strip()
            if not text:
                return default
            try:
                return int(text)
            except ValueError:
                return default
        return widget.text()
