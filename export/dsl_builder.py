from __future__ import annotations

import json

DSL_VERSION = "v1"


class DSLBuilder:
    def __init__(self, layout_model, property_registry, checklist_engine):
        self.model = layout_model
        self.registry = property_registry
        self.checklist = checklist_engine

    def can_export(self) -> bool:
        result = self.checklist.run()
        return result["summary"]["errors"] == 0

    def build_json(self, mode="expanded") -> dict:
        if not self.can_export():
            raise Exception("Export blocked: checklist errors present")
        root_children = self.model.get_children(self.model.root_id)
        exported = [self._build_node_json(node, mode) for node in root_children]
        if len(exported) == 1:
            result = exported[0]
        else:
            result = {
                "id": self.model.root_id,
                "type": "root",
                "properties": {},
                "children": exported,
            }
        assert "id" in result
        assert "type" in result
        assert "properties" in result
        assert "children" in result
        return result

    def build_dsl(self, mode="expanded") -> str:
        if not self.can_export():
            raise Exception("Export blocked: checklist errors present")
        lines = [f"@create_bench {DSL_VERSION}", f"@mode {mode}", ""]
        for node in self.model.get_children(self.model.root_id):
            self._append_node_dsl(lines, node, mode, 0)
        return "\n".join(lines)

    def _build_node_json(self, node, mode: str) -> dict:
        known, unknown = self._split_properties(node, mode)
        properties = dict(known)
        if unknown:
            properties["unknown"] = dict(unknown)
        return {
            "id": node.id,
            "type": node.type,
            "properties": properties,
            "children": [self._build_node_json(child, mode) for child in self.model.get_children(node.id)],
        }

    def _append_node_dsl(self, lines: list[str], node, mode: str, depth: int) -> None:
        indent = "  " * depth
        lines.append(f"{indent}node {node.type} id={node.id}")

        known, unknown = self._split_properties(node, mode)
        for key, value in known.items():
            lines.append(f"{indent}  prop {key} = {self._format_value(value)}")

        if unknown:
            lines.append(f"{indent}  unknown:")
            for key, value in unknown.items():
                lines.append(f"{indent}    {key} = {self._format_value(value)}")

        for child in self.model.get_children(node.id):
            self._append_node_dsl(lines, child, mode, depth + 1)

    def _split_properties(self, node, mode: str) -> tuple[dict, dict]:
        schema = self.registry.get_schema(node.type) if self.registry.has_schema(node.type) else None
        known = {}
        unknown = {}

        schema_props = schema.get("properties", {}) if schema else {}
        for key in sorted(node.properties):
            value = node.properties[key]
            if key in schema_props:
                if mode == "explicit" and self._is_default_value(schema_props[key], value):
                    continue
                known[key] = value
            else:
                unknown[key] = value

        return known, unknown

    def _is_default_value(self, prop_schema: dict, value) -> bool:
        return "default" in prop_schema and prop_schema["default"] == value

    def _format_value(self, value) -> str:
        if isinstance(value, str):
            return json.dumps(value)
        if isinstance(value, bool):
            return "true" if value else "false"
        if isinstance(value, (int, float)):
            return str(value)
        return json.dumps(value, sort_keys=True)
