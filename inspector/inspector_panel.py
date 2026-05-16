from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTabWidget, QVBoxLayout, QWidget

from core.node_resolution import resolve_node_state
from inspector.inspector_actions import (
    clear_bench_focus,
    close_bench_session,
    focus_bench_session,
    fork_scene_to_design,
    fork_selected_to_design,
    open_scene_in_bench,
    open_selected_in_bench,
    reopen_bench_session,
)
from inspector.edit_sections import (
    build_editability_notice,
    build_raw_properties_section,
    build_schema_edit_section,
)
from inspector.truth_sections import build_node_truth_section, build_scene_truth_section


class InspectorPanel(QWidget):
    def __init__(self, layout_model, selection_state, property_registry, focus_node_callback=None):
        super().__init__()
        self.model = layout_model
        self.selection_state = selection_state
        self.registry = property_registry
        self.focus_node_callback = focus_node_callback
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
        self._render_editability_notice(node)

        if self.registry.has_schema(node.type):
            schema = self.registry.get_schema(node.type)
            self._render_schema_node(node, schema)
        else:
            self.content_layout.addWidget(QLabel("No schema found"))
            self._render_raw_properties(node)

        self.truth_layout.addStretch()
        self.content_layout.addStretch()

    def _render_truth_summary(self, node):
        callbacks = {
            "fork_selected_to_design": self._fork_selected_to_design,
            "open_selected_in_bench": self._open_selected_in_bench,
            "fork_scene_to_design": self._fork_scene_to_design,
            "open_scene_in_bench": self._open_scene_in_bench,
            "focus_bench_session": self._focus_bench_session,
            "clear_bench_focus": self._clear_bench_focus,
            "close_bench_session": self._close_bench_session,
            "reopen_bench_session": self._reopen_bench_session,
        }
        build_node_truth_section(self.truth_layout, node, self.model, callbacks)
        build_scene_truth_section(self.truth_layout, node, self.model, callbacks)

    def _render_schema_node(self, node, schema):
        build_schema_edit_section(
            self.content_layout,
            node,
            schema,
            self.registry,
            self.model,
            self._edit_callbacks(),
        )

    def _render_raw_properties(self, node):
        build_raw_properties_section(
            self.content_layout,
            node,
            self.model,
            self._edit_callbacks(),
        )

    def _render_editability_notice(self, node):
        build_editability_notice(self.content_layout, node, self.model)

    def _edit_callbacks(self):
        return {
            "commit_property": self._commit_property,
            "remove_unknown_property": self._remove_unknown_property,
            "notify_model": self.model.notify_subscribers,
        }

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
        fork_selected_to_design(self.model, self.selection_state, node_id)

    def _open_selected_in_bench(self, node_id):
        open_selected_in_bench(
            self.model,
            self.selection_state,
            self.focus_node_callback,
            node_id,
        )

    def _fork_scene_to_design(self):
        fork_scene_to_design(self.model, self.selection_state)

    def _open_scene_in_bench(self):
        open_scene_in_bench(
            self.model,
            self.selection_state,
            self.focus_node_callback,
        )

    def _focus_bench_session(self, bench_session_id):
        focus_bench_session(self.model, bench_session_id)

    def _clear_bench_focus(self):
        clear_bench_focus(self.model)

    def _close_bench_session(self, bench_session_id):
        close_bench_session(self.model, self.selection_state, bench_session_id)

    def _reopen_bench_session(self, bench_session_id):
        reopen_bench_session(self.model, self.selection_state, bench_session_id)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
