from __future__ import annotations

import re
from typing import Any


def _issue(node_id: str, property: str | None, code: str, severity: str, message: str) -> dict:
    return {
        "node_id": node_id,
        "property": property,
        "code": code,
        "severity": severity,
        "message": message,
    }


def rule_missing_required_properties(node, schema) -> list[dict]:
    issues = []
    for prop_name, prop_def in schema.get("properties", {}).items():
        if prop_def.get("required") and prop_name not in node.properties:
            issues.append(
                _issue(
                    node.id,
                    prop_name,
                    "missing_required_property",
                    "error",
                    f"Missing required property '{prop_name}'",
                )
            )
    return issues


def rule_invalid_property_type(node, schema) -> list[dict]:
    issues = []
    for prop_name, value in node.properties.items():
        prop_def = schema.get("properties", {}).get(prop_name)
        if not prop_def:
            continue
        expected_type = prop_def.get("type")
        if not _matches_type(expected_type, value):
            issues.append(
                _issue(
                    node.id,
                    prop_name,
                    "invalid_property_type",
                    "error",
                    f"Property '{prop_name}' has invalid type for '{expected_type}'",
                )
            )
    return issues


def rule_constraints(node, schema) -> list[dict]:
    issues = []
    for prop_name, value in node.properties.items():
        prop_def = schema.get("properties", {}).get(prop_name)
        if not prop_def:
            continue

        if "min" in prop_def and value < prop_def["min"]:
            issues.append(
                _issue(
                    node.id,
                    prop_name,
                    "constraint_min",
                    "error",
                    f"Property '{prop_name}' is below minimum {prop_def['min']}",
                )
            )
        if "max" in prop_def and value > prop_def["max"]:
            issues.append(
                _issue(
                    node.id,
                    prop_name,
                    "constraint_max",
                    "error",
                    f"Property '{prop_name}' exceeds maximum {prop_def['max']}",
                )
            )
        if "allowed_values" in prop_def and value not in prop_def["allowed_values"]:
            issues.append(
                _issue(
                    node.id,
                    prop_name,
                    "constraint_allowed_values",
                    "error",
                    f"Property '{prop_name}' must be one of the allowed values",
                )
            )
        if "regex" in prop_def and not re.match(prop_def["regex"], str(value)):
            issues.append(
                _issue(
                    node.id,
                    prop_name,
                    "constraint_regex",
                    "error",
                    f"Property '{prop_name}' does not match required pattern",
                )
            )
    return issues


def rule_invalid_child_type(node, schema, registry) -> list[dict]:
    issues = []
    allowed = set(schema.get("allowed_children_resolved", []))
    if not allowed:
        allowed = set(schema.get("allowed_children", []))
    for child_id in node.children:
        child = registry.model.get_node(child_id) if hasattr(registry, "model") else None
        if child is None:
            continue
        if child.type not in allowed:
            issues.append(
                _issue(
                    node.id,
                    None,
                    "invalid_child_type",
                    "error",
                    f"Child '{child.id}' of type '{child.type}' is not allowed",
                )
            )
    return issues


def rule_unknown_properties(node, schema) -> list[dict]:
    issues = []
    known = set(schema.get("properties", {}))
    for prop_name in sorted(node.properties):
        if prop_name not in known:
            issues.append(
                _issue(
                    node.id,
                    prop_name,
                    "unknown_property",
                    "warning",
                    f"Unknown property '{prop_name}'",
                )
            )
    return issues


def rule_excessive_depth(node, depth: int) -> list[dict]:
    if depth > 10:
        return [
            _issue(
                node.id,
                None,
                "excessive_nesting",
                "warning",
                f"Node depth {depth} exceeds recommended maximum",
            )
        ]
    return []


def _matches_type(expected_type: str, value: Any) -> bool:
    if expected_type == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "float":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected_type == "string":
        return isinstance(value, str)
    if expected_type == "bool":
        return isinstance(value, bool)
    if expected_type == "enum":
        return isinstance(value, str)
    if expected_type in {"color", "reference"}:
        return isinstance(value, str)
    return True
