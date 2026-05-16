from __future__ import annotations

from PySide6.QtWidgets import QLabel, QPushButton

from core.node_resolution import resolve_node_state
from inspector.property_fields import create_field_widget


def build_schema_edit_section(content_layout, node, schema, registry, model, callbacks):
    groups = ["layout", "appearance", "content", "behavior", "data"]
    known_props = schema.get("properties", {})
    raw_schema = registry.raw_schemas.get(node.type, {})
    raw_props = raw_schema.get("properties", {})

    for group in groups:
        group_props = [
            (name, prop_schema)
            for name, prop_schema in known_props.items()
            if prop_schema.get("group") == group
        ]
        if not group_props:
            continue

        content_layout.addWidget(QLabel(group.title()))
        for prop_name, prop_schema in group_props:
            field = create_field_widget(
                prop_name,
                prop_schema,
                node.properties.get(prop_name),
                lambda name, value, node=node: callbacks["commit_property"](node, name, value),
            )
            _decorate_schema_field(
                field, prop_name, prop_schema, prop_name not in raw_props, node, model, callbacks
            )
            content_layout.addWidget(field)

    unknown = sorted(key for key in node.properties if key not in known_props)
    if unknown:
        content_layout.addWidget(QLabel("Unknown Properties"))
        for prop_name in unknown:
            content_layout.addWidget(_make_unknown_field(node, prop_name, model, callbacks))


def build_raw_properties_section(content_layout, node, model, callbacks):
    for prop_name in sorted(node.properties):
        prop_schema = {"type": "string"}
        field = create_field_widget(
            prop_name,
            prop_schema,
            node.properties.get(prop_name),
            lambda name, value, node=node: callbacks["commit_property"](node, name, value),
        )
        _decorate_schema_field(field, prop_name, prop_schema, False, node, model, callbacks)
        _wire_reset_button(field.reset_button, None, field, prop_name, node, model, callbacks)
        content_layout.addWidget(field)


def build_editability_notice(content_layout, node, model):
    resolved = resolve_node_state(node, getattr(model, "scene_metadata", {}))
    if resolved["editability"] == "editable" or not resolved["reason"]:
        return
    label = QLabel(f"Editing disabled: {resolved['reason']}")
    label.setObjectName("editability_notice")
    content_layout.addWidget(label)


def _decorate_schema_field(field, prop_name, prop_schema, inherited, node, model, callbacks):
    label = field.findChild(QLabel, f"field_label_{prop_name}")
    value = node.properties.get(prop_name)
    locked = bool(node.properties.get("locked"))
    resolved = resolve_node_state(node, getattr(model, "scene_metadata", {}))
    packet_protected = resolved["editability"] != "editable"
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
        if _is_invalid_value(prop_schema, value):
            input_widget.setStyleSheet("border: 1px solid #dc2626;")
        else:
            input_widget.setStyleSheet("")
        if packet_protected:
            input_widget.setEnabled(False)
            field.reset_button.setEnabled(False)
        elif locked and prop_name in {"x", "y", "width", "height", "layout_mode"}:
            input_widget.setEnabled(False)
            field.reset_button.setEnabled(False)
        else:
            input_widget.setEnabled(True)
            field.reset_button.setEnabled(True)

    default_value = prop_schema.get("default", None)
    _wire_reset_button(field.reset_button, default_value, field, prop_name, node, model, callbacks)


def _wire_reset_button(button, default_value, field, prop_name, node, model, callbacks):
    def handle_reset():
        if resolve_node_state(node, getattr(model, "scene_metadata", {}))["editability"] != "editable":
            return
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
        callbacks["notify_model"]()

    button.clicked.connect(handle_reset)


def _make_unknown_field(node, prop_name, model, callbacks):
    field = create_field_widget(
        prop_name,
        {"type": "string"},
        node.properties.get(prop_name),
        lambda name, value, node=node: callbacks["commit_property"](node, name, value),
    )
    remove_button = QPushButton("Remove")
    remove_button.setObjectName(f"unknown_remove_{prop_name}")
    remove_button.clicked.connect(lambda: callbacks["remove_unknown_property"](node, prop_name))
    remove_button.setEnabled(
        resolve_node_state(node, getattr(model, "scene_metadata", {}))["editability"] == "editable"
    )
    layout = field.layout()
    layout.addWidget(remove_button)
    field.reset_button.hide()
    return field


def _is_invalid_value(prop_schema, value):
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
