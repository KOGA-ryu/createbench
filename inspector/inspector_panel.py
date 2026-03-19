from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.node_resolution import resolve_node_state
from core.scene_resolution import resolve_scene_state
from inspector.property_fields import create_field_widget


class InspectorPanel(QWidget):
    def __init__(self, layout_model, selection_state, property_registry):
        super().__init__()
        self.model = layout_model
        self.selection_state = selection_state
        self.registry = property_registry
        self.root_layout = QVBoxLayout(self)
        self.root_layout.setContentsMargins(8, 8, 8, 8)
        self.root_layout.setSpacing(8)
        self.tabs = QTabWidget()
        self.tabs.setObjectName("inspector_tabs")
        self.truth_tab = QWidget()
        self.truth_layout = QVBoxLayout(self.truth_tab)
        self.truth_layout.setContentsMargins(0, 0, 0, 0)
        self.truth_layout.setSpacing(8)
        self.edit_tab = QWidget()
        self.content_layout = QVBoxLayout(self.edit_tab)
        self.content_layout.setContentsMargins(0, 0, 0, 0)
        self.content_layout.setSpacing(8)
        self.tabs.addTab(self.truth_tab, "Truth")
        self.tabs.addTab(self.edit_tab, "Edit")
        self.root_layout.addWidget(self.tabs)
        self.model.subscribe(self._handle_model_changed)
        self.destroyed.connect(lambda _obj=None: self.model.unsubscribe(self._handle_model_changed))
        self.selection_state.subscribe(self._on_selection_changed)
        self._on_selection_changed(self.selection_state.get_selection())

    def _handle_model_changed(self):
        self._on_selection_changed(self.selection_state.get_selection())

    def _on_selection_changed(self, selected_id):
        self._clear_layout(self.truth_layout)
        self._clear_layout(self.content_layout)
        if selected_id is None:
            self.truth_layout.addWidget(QLabel("No selection"))
            self.truth_layout.addStretch()
            self.tabs.setCurrentWidget(self.truth_tab)
            return

        node = self.model.get_node(selected_id)
        if node is None:
            self.truth_layout.addWidget(QLabel("No selection"))
            self.truth_layout.addStretch()
            self.tabs.setCurrentWidget(self.truth_tab)
            return

        resolved = resolve_node_state(node, getattr(self.model, "scene_metadata", {}))
        if resolved["editability"] == "editable" and resolved["resolved_mode"] == "design":
            self.tabs.setCurrentWidget(self.edit_tab)
        else:
            self.tabs.setCurrentWidget(self.truth_tab)

        self._render_truth_summary(node)

        if self.registry.has_schema(node.type):
            schema = self.registry.get_schema(node.type)
            self._render_schema_node(node, schema)
        else:
            self.content_layout.addWidget(QLabel("No schema found"))
            self._render_raw_properties(node)

        self.truth_layout.addStretch()
        self.content_layout.addStretch()

    def _render_truth_summary(self, node):
        metadata = getattr(node, "metadata", {}) or {}
        source = metadata.get("source", {})
        trust = metadata.get("trust", {})
        provenance = metadata.get("provenance", {})
        raw = metadata.get("raw", {})
        scene_metadata = getattr(self.model, "scene_metadata", {})
        resolved = resolve_node_state(node, scene_metadata)
        warnings = list(trust.get("warnings") or []) + list(provenance.get("packet_warnings") or [])
        if not any([source, trust, provenance, raw, scene_metadata]):
            self.truth_layout.addWidget(QLabel("Truth"))
            return

        self.truth_layout.addWidget(QLabel("Truth"))
        lines = [
            f"resolved_mode: {resolved['resolved_mode']}",
            f"editability: {resolved['editability']}",
            f"trust_level: {trust.get('trust_level') or '-'}",
            f"representation_origin: {provenance.get('representation_origin') or trust.get('representation_origin') or '-'}",
            f"source_provider: {provenance.get('source_provider') or '-'}",
            f"source_framework: {provenance.get('source_framework') or '-'}",
            f"packet_trust_level: {provenance.get('packet_trust_level') or '-'}",
            f"source.file: {source.get('file') or '-'}",
            f"source.symbol: {source.get('symbol') or '-'}",
            f"line_range: {self._format_line_range(source)}",
        ]
        for index, line in enumerate(lines):
            label = QLabel(line)
            label.setObjectName(f"truth_label_{index}")
            self.truth_layout.addWidget(label)

        if resolved["reason"]:
            reason_label = QLabel(f"edit_reason: {resolved['reason']}")
            reason_label.setObjectName("truth_edit_reason")
            self.truth_layout.addWidget(reason_label)
        if resolved["origin_node_id"]:
            origin_label = QLabel(f"origin_node_id: {resolved['origin_node_id']}")
            origin_label.setObjectName("truth_origin_node_id")
            self.truth_layout.addWidget(origin_label)
        if resolved["bench_session_id"]:
            bench_label = QLabel(f"bench_session_id: {resolved['bench_session_id']}")
            bench_label.setObjectName("truth_bench_session_id")
            self.truth_layout.addWidget(bench_label)
        fork_destination = provenance.get("fork_destination")
        if fork_destination:
            destination_label = QLabel(f"fork_destination: {fork_destination}")
            destination_label.setObjectName("truth_fork_destination")
            self.truth_layout.addWidget(destination_label)
        if resolved["editability"] == "forkable":
            actions = QHBoxLayout()
            fork_button = QPushButton("Fork Here")
            fork_button.setObjectName("truth_fork_to_design")
            fork_button.clicked.connect(
                lambda _checked=False, node_id=node.id: self._fork_selected_to_design(node_id)
            )
            actions.addWidget(fork_button)
            bench_button = QPushButton("Open In Bench")
            bench_button.setObjectName("truth_open_in_bench")
            bench_button.clicked.connect(
                lambda _checked=False, node_id=node.id: self._open_selected_in_bench(node_id)
            )
            actions.addWidget(bench_button)
            self.truth_layout.addLayout(actions)
        elif resolved["resolved_mode"] == "bench" and resolved["bench_session_id"]:
            actions = QHBoxLayout()
            focus_button = QPushButton("Focus Bench Session")
            focus_button.setObjectName("truth_focus_bench_session")
            focus_button.clicked.connect(
                lambda _checked=False, bench_session_id=resolved["bench_session_id"]: self._focus_bench_session(bench_session_id)
            )
            actions.addWidget(focus_button)
            clear_button = QPushButton("Clear Bench Focus")
            clear_button.setObjectName("truth_clear_bench_focus")
            clear_button.clicked.connect(lambda _checked=False: self._clear_bench_focus())
            actions.addWidget(clear_button)
            self.truth_layout.addLayout(actions)

        if warnings:
            self.truth_layout.addWidget(QLabel("Warnings"))
            for index, warning in enumerate(warnings):
                label = QLabel(str(warning))
                label.setObjectName(f"truth_warning_{index}")
                self.truth_layout.addWidget(label)

        relationships = metadata.get("relationships", {})
        if relationships:
            self.truth_layout.addWidget(QLabel("Relationships"))
            for field_name in ("communicates_to", "depends_on", "updated_by", "triggered_by"):
                values = relationships.get(field_name) or []
                label = QLabel(f"{field_name}: {', '.join(str(value) for value in values) if values else '-'}")
                label.setObjectName(f"truth_relationship_{field_name}")
                self.truth_layout.addWidget(label)

        unresolved_fields = raw.get("unresolved_fields") or []
        if unresolved_fields:
            self.truth_layout.addWidget(QLabel("Unresolved Fields"))
            label = QLabel(", ".join(str(field) for field in unresolved_fields))
            label.setObjectName("truth_unresolved_fields")
            self.truth_layout.addWidget(label)

        bench_sessions = self.model.get_bench_session_ids()
        closed_sessions = self.model.get_recently_closed_bench_session_ids()
        if scene_metadata or bench_sessions or closed_sessions:
            scene_resolved = resolve_scene_state(scene_metadata)
            self.truth_layout.addWidget(QLabel("Scene Truth"))
            scene_lines = [
                f"scene_mode: {scene_resolved['resolved_mode']}",
                f"scene_origin: {scene_resolved['origin']}",
                f"scene_source_provider: {scene_resolved['source_provider']}",
                f"scene_source_framework: {scene_resolved['source_framework']}",
                f"scene_packet_trust_level: {scene_resolved['trust_level']}",
                f"scene_active_bench_session_id: {scene_resolved['active_bench_session_id'] or '-'}",
            ]
            for index, line in enumerate(scene_lines):
                label = QLabel(line)
                label.setObjectName(f"scene_truth_label_{index}")
                self.truth_layout.addWidget(label)

            if bench_sessions:
                self.truth_layout.addWidget(QLabel("Bench Sessions"))
                for index, bench_session_id in enumerate(bench_sessions):
                    row = QHBoxLayout()
                    session_label = QLabel(bench_session_id)
                    session_label.setObjectName(f"bench_session_label_{index}")
                    row.addWidget(session_label)
                    focus_button = QPushButton(
                        "Active" if bench_session_id == scene_resolved["active_bench_session_id"] else "Focus"
                    )
                    focus_button.setObjectName(f"bench_session_focus_{index}")
                    focus_button.setEnabled(bench_session_id != scene_resolved["active_bench_session_id"])
                    focus_button.clicked.connect(
                        lambda _checked=False, bench_session_id=bench_session_id: self._focus_bench_session(bench_session_id)
                    )
                    row.addWidget(focus_button)
                    close_button = QPushButton("Close")
                    close_button.setObjectName(f"bench_session_close_{index}")
                    close_button.clicked.connect(
                        lambda _checked=False, bench_session_id=bench_session_id: self._close_bench_session(bench_session_id)
                    )
                    row.addWidget(close_button)
                    self.truth_layout.addLayout(row)
                clear_button = QPushButton("Clear Bench Session Focus")
                clear_button.setObjectName("bench_session_clear_focus")
                clear_button.setEnabled(scene_resolved["active_bench_session_id"] is not None)
                clear_button.clicked.connect(lambda _checked=False: self._clear_bench_focus())
                self.truth_layout.addWidget(clear_button)

            if closed_sessions:
                self.truth_layout.addWidget(QLabel("Recently Closed Bench Sessions"))
                for index, bench_session_id in enumerate(closed_sessions):
                    row = QHBoxLayout()
                    session_label = QLabel(bench_session_id)
                    session_label.setObjectName(f"closed_bench_session_label_{index}")
                    row.addWidget(session_label)
                    reopen_button = QPushButton("Reopen")
                    reopen_button.setObjectName(f"closed_bench_session_reopen_{index}")
                    reopen_button.clicked.connect(
                        lambda _checked=False, bench_session_id=bench_session_id: self._reopen_bench_session(bench_session_id)
                    )
                    row.addWidget(reopen_button)
                    self.truth_layout.addLayout(row)

    def _format_line_range(self, source):
        line_start = source.get("line_start")
        line_end = source.get("line_end")
        if line_start is None and line_end is None:
            return "-"
        if line_start == line_end or line_end is None:
            return str(line_start)
        if line_start is None:
            return str(line_end)
        return f"{line_start}-{line_end}"

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
        resolved = resolve_node_state(node, getattr(self.model, "scene_metadata", {}))
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
            if self._is_invalid_value(prop_schema, value):
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
        self._wire_reset_button(field.reset_button, default_value, field, prop_name, node)

    def _wire_reset_button(self, button, default_value, field, prop_name, node):
        def handle_reset():
            if resolve_node_state(node, getattr(self.model, "scene_metadata", {}))["editability"] != "editable":
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
            self.model.notify_subscribers()

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
        if resolve_node_state(node, getattr(self.model, "scene_metadata", {}))["editability"] != "editable":
            return
        node.properties = dict(node.properties)
        node.properties[prop_name] = value
        self.model.notify_subscribers()

    def _remove_unknown_property(self, node, prop_name):
        if resolve_node_state(node, getattr(self.model, "scene_metadata", {}))["editability"] != "editable":
            return
        node.properties = dict(node.properties)
        node.properties.pop(prop_name, None)
        self.model.notify_subscribers()

    def _fork_selected_to_design(self, node_id):
        forked_id = self.model.fork_subtree_to_design(node_id)
        if forked_id is not None:
            self.selection_state.set_selection(forked_id)

    def _open_selected_in_bench(self, node_id):
        bench_id = self.model.open_subtree_in_bench(node_id)
        if bench_id is not None:
            self.selection_state.set_selection(bench_id)

    def _focus_bench_session(self, bench_session_id):
        self.model.set_active_bench_session(bench_session_id)

    def _clear_bench_focus(self):
        self.model.clear_active_bench_session()

    def _close_bench_session(self, bench_session_id):
        selected_id = self.selection_state.get_selection()
        selected = self.model.get_node(selected_id) if selected_id is not None else None
        selected_session_id = (
            (getattr(selected, "metadata", {}) or {}).get("bench_session_id")
            if selected is not None else None
        )
        deleted = self.model.close_bench_session(bench_session_id)
        if selected_session_id == bench_session_id and deleted:
            self.selection_state.clear_selection()

    def _reopen_bench_session(self, bench_session_id):
        restored_roots = self.model.reopen_closed_bench_session(bench_session_id)
        if restored_roots:
            self.selection_state.set_selection(restored_roots[0])

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
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
