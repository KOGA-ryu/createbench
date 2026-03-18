from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from inspector.property_fields import create_field_widget


class InspectorPanel(QWidget):
    def __init__(self, layout_model, selection_state, property_registry):
        super().__init__()
        self.model = layout_model
        self.selection_state = selection_state
        self.registry = property_registry
        self.content_layout = QVBoxLayout(self)
        self.content_layout.setContentsMargins(8, 8, 8, 8)
        self.content_layout.setSpacing(8)
        self.selection_state.subscribe(self._on_selection_changed)
        self._on_selection_changed(self.selection_state.get_selection())

    def _on_selection_changed(self, selected_id):
        self._clear_layout()
        if selected_id is None:
            self.content_layout.addWidget(QLabel("No selection"))
            self.content_layout.addStretch()
            return

        node = self.model.get_node(selected_id)
        if node is None:
            self.content_layout.addWidget(QLabel("No selection"))
            self.content_layout.addStretch()
            return

        if self.registry.has_schema(node.type):
            schema = self.registry.get_schema(node.type)
            self._render_schema_node(node, schema)
        else:
            self.content_layout.addWidget(QLabel("No schema found"))
            self._render_raw_properties(node)

        self.content_layout.addStretch()

    def _render_schema_node(self, node, schema):
        groups = ["layout", "appearance", "content", "behavior", "data"]
        known_props = schema.get("properties", {})
        raw_schema = self.registry.raw_schemas.get(node.type, {})
        raw_props = raw_schema.get("properties", {})

        for group in groups:
            group_props = [
                (name, prop_schema)
                for name, prop_schema in known_props.items()
                if prop_schema.get("group") == group
            ]
            if not group_props:
                continue

            self.content_layout.addWidget(QLabel(group.title()))
            for prop_name, prop_schema in group_props:
                field = create_field_widget(
                    prop_name,
                    prop_schema,
                    node.properties.get(prop_name),
                    lambda name, value, node=node: self._commit_property(node, name, value),
                )
                self._decorate_schema_field(
                    field, prop_name, prop_schema, prop_name not in raw_props, node
                )
                self.content_layout.addWidget(field)

        unknown = sorted(key for key in node.properties if key not in known_props)
        if unknown:
            self.content_layout.addWidget(QLabel("Unknown Properties"))
            for prop_name in unknown:
                self.content_layout.addWidget(self._make_unknown_field(node, prop_name))

    def _render_raw_properties(self, node):
        for prop_name in sorted(node.properties):
            prop_schema = {"type": "string"}
            field = create_field_widget(
                prop_name,
                prop_schema,
                node.properties.get(prop_name),
                lambda name, value, node=node: self._commit_property(node, name, value),
            )
            self._wire_reset_button(field.reset_button, None, field, prop_name, node)
            self.content_layout.addWidget(field)

    def _decorate_schema_field(self, field, prop_name, prop_schema, inherited, node):
        label = field.findChild(QLabel, f"field_label_{prop_name}")
        value = node.properties.get(prop_name)
        locked = bool(node.properties.get("locked"))
        if label is not None:
            label_text = prop_name
            if prop_schema.get("required"):
                label_text += " *"
            if inherited:
                label_text += " (inherited)"
            if "default" in prop_schema and value == prop_schema["default"]:
                label_text += " (default)"
            label.setText(label_text)
            if "default" in prop_schema and value == prop_schema["default"]:
                label.setStyleSheet("color: #6b7280;")
            else:
                label.setStyleSheet("")

        input_widget = getattr(field, "input_widget", None)
        if input_widget is not None:
            if self._is_invalid_value(prop_schema, value):
                input_widget.setStyleSheet("border: 1px solid #dc2626;")
            else:
                input_widget.setStyleSheet("")
            if locked and prop_name in {"x", "y", "width", "height", "layout_mode"}:
                input_widget.setEnabled(False)
                field.reset_button.setEnabled(False)
            else:
                input_widget.setEnabled(True)
                field.reset_button.setEnabled(True)

        default_value = prop_schema.get("default", None)
        self._wire_reset_button(field.reset_button, default_value, field, prop_name, node)

    def _wire_reset_button(self, button, default_value, field, prop_name, node):
        def handle_reset():
            node.properties = dict(node.properties)
            if default_value is None:
                node.properties.pop(prop_name, None)
            else:
                node.properties[prop_name] = default_value
                field.set_value(str(default_value) if hasattr(field.input_widget, "setText") else default_value)
                if hasattr(field.input_widget, "setChecked"):
                    field.input_widget.setChecked(bool(default_value))
                if hasattr(field.input_widget, "findText"):
                    index = field.input_widget.findText(str(default_value))
                    if index >= 0:
                        field.input_widget.setCurrentIndex(index)

        button.clicked.connect(handle_reset)

    def _make_unknown_field(self, node, prop_name):
        field = create_field_widget(
            prop_name,
            {"type": "string"},
            node.properties.get(prop_name),
            lambda name, value, node=node: self._commit_property(node, name, value),
        )
        remove_button = QPushButton("Remove")
        remove_button.setObjectName(f"unknown_remove_{prop_name}")
        remove_button.clicked.connect(lambda: self._remove_unknown_property(node, prop_name))
        layout = field.layout()
        layout.addWidget(remove_button)
        field.reset_button.hide()
        return field

    def _commit_property(self, node, prop_name, value):
        node.properties = dict(node.properties)
        node.properties[prop_name] = value
        if prop_name == "locked":
            self._on_selection_changed(node.id)

    def _remove_unknown_property(self, node, prop_name):
        node.properties = dict(node.properties)
        node.properties.pop(prop_name, None)
        self._on_selection_changed(node.id)

    def _clear_layout(self):
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()

    def _is_invalid_value(self, prop_schema, value):
        if value is None:
            return bool(prop_schema.get("required"))

        prop_type = prop_schema.get("type")
        if prop_type == "int":
            return not (isinstance(value, int) and not isinstance(value, bool))
        if prop_type == "float":
            return not (isinstance(value, (int, float)) and not isinstance(value, bool))
        if prop_type in {"string", "enum", "color", "reference"}:
            return not isinstance(value, str)
        if prop_type == "bool":
            return not isinstance(value, bool)
        return False
