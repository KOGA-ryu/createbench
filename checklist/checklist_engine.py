from __future__ import annotations

from checklist.checklist_rules import (
    rule_constraints,
    rule_excessive_depth,
    rule_invalid_child_type,
    rule_invalid_property_type,
    rule_missing_required_properties,
    rule_unknown_properties,
)


class ChecklistEngine:
    def __init__(self, layout_model, property_registry):
        self.model = layout_model
        self.registry = property_registry
        self.last_result = {
            "summary": {"errors": 0, "warnings": 0, "info": 0},
            "issues": [],
        }

    def run(self) -> dict:
        issues = []
        self.registry.model = self.model
        self._walk(self.model.root_id, 0, issues)
        issues.sort(key=lambda i: (i["severity"], i["node_id"], i.get("property") or ""))
        summary = {"errors": 0, "warnings": 0, "info": 0}
        for issue in issues:
            if issue["severity"] == "error":
                summary["errors"] += 1
            elif issue["severity"] == "warning":
                summary["warnings"] += 1
            elif issue["severity"] == "info":
                summary["info"] += 1
        self.last_result = {"summary": summary, "issues": issues}
        return self.last_result

    def filter_by_node(self, node_id):
        return [issue for issue in self.last_result["issues"] if issue["node_id"] == node_id]

    def _walk(self, node_id: str, depth: int, issues: list[dict]) -> None:
        node = self.model.get_node(node_id)
        if node is None:
            return

        if node.id != self.model.root_id:
            schema = self.registry.get_schema(node.type) if self.registry.has_schema(node.type) else None
            if schema is None:
                issues.append(
                    {
                        "node_id": node.id,
                        "property": None,
                        "code": "missing_schema",
                        "severity": "warning",
                        "message": f"Missing schema for node type '{node.type}'",
                    }
                )
            else:
                issues.extend(rule_missing_required_properties(node, schema))
                issues.extend(rule_invalid_property_type(node, schema))
                issues.extend(rule_constraints(node, schema))
                issues.extend(rule_invalid_child_type(node, schema, self.registry))
                issues.extend(rule_unknown_properties(node, schema))
            issues.extend(rule_excessive_depth(node, depth))

        for child_id in node.children:
            self._walk(child_id, depth + 1, issues)
