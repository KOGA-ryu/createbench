from __future__ import annotations

import json

from checklist.checklist_engine import ChecklistEngine
from export.dsl_builder import DSLBuilder
from export.dsl_builder import DSL_VERSION


def save_project(layout_model, filepath):
    builder = DSLBuilder(
        layout_model,
        layout_model.registry,
        ChecklistEngine(layout_model, layout_model.registry),
    )
    data = builder.build_json(mode="expanded")
    with open(filepath, "w", encoding="utf-8") as handle:
        json.dump({"version": DSL_VERSION, "data": data}, handle, indent=2)


def load_project(layout_model, property_registry, filepath):
    del property_registry
    with open(filepath, "r", encoding="utf-8") as handle:
        payload = json.load(handle)

    if payload.get("version") != DSL_VERSION:
        raise ValueError(f"Unsupported project version: {payload.get('version')}")
    data = payload["data"]

    for child in list(layout_model.get_children(layout_model.root_id)):
        layout_model.remove_node(child.id)
    layout_model.type_counters = {}

    def build(node_dict, parent_id):
        node = layout_model.create_node(
            node_dict["type"],
            node_dict.get("properties", {}),
        )
        layout_model.add_node(parent_id, node)
        for child in node_dict.get("children", []):
            build(child, node.id)

    if "type" in data:
        build(data, layout_model.root_id)
    else:
        for child in data.get("children", []):
            build(child, layout_model.root_id)

    layout_model.validate_integrity()
