from __future__ import annotations

from checklist.checklist_engine import ChecklistEngine
from core.layout_model import LayoutModel
from inspector.property_registry import PropertyRegistry
from state.selection_state import SelectionState


class AppState:
    def __setattr__(self, key, value):
        if hasattr(self, "_locked") and self._locked:
            if not hasattr(self, key):
                raise AttributeError("AppState is immutable after initialization")
        super().__setattr__(key, value)

    def __init__(self, core_schema_path, user_schema_path=None):
        self.property_registry = PropertyRegistry(core_schema_path, user_schema_path)
        self.layout_model = LayoutModel(self.property_registry)
        self.selection_state = SelectionState(self.layout_model)
        self.checklist_engine = ChecklistEngine(
            self.layout_model, self.property_registry
        )
        self.scene_source_targets = {
            "project": "project.json",
            "extract_packet": "ui_extract_packet.json",
        }
        self._locked = True

    def get_selected_node(self):
        selected_id = self.selection_state.get_selection()
        if selected_id is None:
            return None
        return self.layout_model.get_node(selected_id)

    def get_node(self, node_id):
        return self.layout_model.get_node(node_id)

    def get_scene_source_target(self, source_type: str) -> str:
        return str(self.scene_source_targets.get(source_type, ""))

    def set_scene_source_target(self, source_type: str, target_path: str) -> None:
        if source_type not in self.scene_source_targets:
            raise ValueError(f"Unknown scene source type: {source_type}")
        self.scene_source_targets[source_type] = str(target_path)
