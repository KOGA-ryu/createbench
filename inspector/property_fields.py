from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QWidget,
)


def create_field_widget(prop_name, prop_schema, value, on_commit):
    container = QWidget()
    container.setObjectName(f"field_container_{prop_name}")
    layout = QHBoxLayout(container)
    layout.setContentsMargins(0, 0, 0, 0)

    label = QLabel(prop_name)
    label.setObjectName(f"field_label_{prop_name}")
    layout.addWidget(label)

    prop_type = prop_schema.get("type", "string")

    if prop_type == "bool":
        editor = QCheckBox()
        editor.setChecked(bool(value))

        def commit_bool(checked):
            on_commit(prop_name, checked)

        editor.toggled.connect(commit_bool)
        setter = editor.setChecked
    elif prop_type == "enum":
        editor = QComboBox()
        for option in prop_schema.get("allowed_values", []):
            editor.addItem(str(option))
        if value is not None:
            index = editor.findText(str(value))
            if index >= 0:
                editor.setCurrentIndex(index)

        def commit_enum(_index):
            on_commit(prop_name, editor.currentText())

        editor.currentIndexChanged.connect(commit_enum)
        setter = lambda new_value: _set_combo_value(editor, new_value)
    else:
        editor = QLineEdit("" if value is None else str(value))

        def commit_text():
            text = editor.text()
            converted = _convert_value(prop_type, text)
            if converted is not _INVALID:
                on_commit(prop_name, converted)

        editor.editingFinished.connect(commit_text)
        setter = editor.setText

    editor.setObjectName(f"field_editor_{prop_name}")
    layout.addWidget(editor)

    reset_button = QPushButton("Reset")
    reset_button.setObjectName(f"field_reset_{prop_name}")
    layout.addWidget(reset_button)

    container.input_widget = editor
    container.reset_button = reset_button
    container.set_value = setter
    return container


_INVALID = object()


def _convert_value(prop_type, text):
    if prop_type == "int":
        try:
            return int(text)
        except ValueError:
            return _INVALID
    if prop_type == "float":
        try:
            return float(text)
        except ValueError:
            return _INVALID
    return text


def _set_combo_value(combo, value):
    index = combo.findText(str(value))
    if index >= 0:
        combo.setCurrentIndex(index)
