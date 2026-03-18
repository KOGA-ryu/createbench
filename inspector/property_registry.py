import json
import os
import re
from copy import deepcopy
from typing import Any, Dict, Optional, Set


SCHEMA_VERSION = 1
PROPERTY_KEY_RE = re.compile(r"^[a-z0-9_]+$")
VALID_PROPERTY_TYPES = {"int", "float", "string", "bool", "enum", "color", "reference"}
VALID_GROUPS = {"layout", "appearance", "content", "behavior", "data"}


class SchemaError(Exception):
    """Raised when a schema cannot be loaded or resolved."""


class PropertyRegistry:
    def __init__(self, core_path: str, user_path: Optional[str] = None):
        self.core_path = core_path
        self.user_path = user_path
        self.raw_schemas: Dict[str, Dict[str, Any]] = {}
        self.resolved_schemas: Dict[str, Dict[str, Any]] = {}
        self.user_schema_errors: Dict[str, str] = {}

        self._load_all()
        self._resolve_all()

    def get_schema(self, node_type: str) -> Dict[str, Any]:
        if node_type not in self.resolved_schemas:
            raise SchemaError(f"Schema not found: {node_type}")
        return self.resolved_schemas[node_type]

    def has_schema(self, node_type: str) -> bool:
        return node_type in self.resolved_schemas

    def apply_defaults(self, node_type: str, properties: Dict[str, Any]) -> Dict[str, Any]:
        schema = self.get_schema(node_type)
        result: Dict[str, Any] = {}

        for key, prop in schema["properties"].items():
            if key in properties:
                result[key] = properties[key]
            elif "default" in prop:
                result[key] = deepcopy(prop["default"])

        for key, value in properties.items():
            if key not in result:
                result[key] = value

        for key in ("x", "y", "width", "height", "layout_mode"):
            if key not in result and key in schema["properties"] and "default" in schema["properties"][key]:
                result[key] = deepcopy(schema["properties"][key]["default"])

        return result

    def _load_all(self) -> None:
        self._load_dir(self.core_path, strict=True, source="core")
        if self.user_path and os.path.isdir(self.user_path):
            self._load_dir(self.user_path, strict=False, source="user")

    def _load_dir(self, path: str, strict: bool, source: str) -> None:
        if not os.path.isdir(path):
            if strict:
                raise SchemaError(f"Schema directory not found: {path}")
            return

        for filename in sorted(os.listdir(path)):
            if not filename.endswith(".json"):
                continue

            file_path = os.path.join(path, filename)

            try:
                with open(file_path, "r", encoding="utf-8") as handle:
                    schema = json.load(handle)

                self._validate_schema_structure(schema, filename)
                node_type = schema["type"]

                if node_type in self.raw_schemas and not schema.get("override", False):
                    raise SchemaError(
                        f"{filename}: duplicate schema '{node_type}' without override=true"
                    )

                schema["_source"] = source
                schema["_filename"] = filename
                self.raw_schemas[node_type] = schema
            except Exception as exc:
                if strict:
                    raise
                self.user_schema_errors[filename] = str(exc)

    def _validate_schema_structure(self, schema: Dict[str, Any], filename: str) -> None:
        required_fields = {
            "type": str,
            "version": int,
            "display_name": str,
            "category": str,
            "layout": bool,
            "allowed_children": list,
            "properties": dict,
        }
        for field, expected_type in required_fields.items():
            if field not in schema:
                raise SchemaError(f"{filename}: missing '{field}'")
            if not isinstance(schema[field], expected_type):
                raise SchemaError(f"{filename}: '{field}' must be {expected_type.__name__}")

        if schema["version"] != SCHEMA_VERSION:
            raise SchemaError(
                f"{filename}: unsupported schema version {schema['version']}"
            )

        remove = schema.get("remove")
        if remove is not None:
            if not isinstance(remove, dict):
                raise SchemaError(f"{filename}: 'remove' must be an object")
            for key in ("properties", "allowed_children"):
                if key in remove and not isinstance(remove[key], list):
                    raise SchemaError(f"{filename}: remove.{key} must be a list")

        for child in schema["allowed_children"]:
            self._validate_type_or_category_token(child, filename, "allowed_children")

        for prop_key, prop in schema["properties"].items():
            if not PROPERTY_KEY_RE.match(prop_key):
                raise SchemaError(f"{filename}: invalid property key '{prop_key}'")
            self._validate_property_definition(filename, prop_key, prop)

    def _validate_property_definition(
        self, filename: str, prop_key: str, prop: Dict[str, Any]
    ) -> None:
        if not isinstance(prop, dict):
            raise SchemaError(f"{filename}:{prop_key} must be an object")
        if "type" not in prop:
            raise SchemaError(f"{filename}:{prop_key} missing 'type'")
        if prop["type"] not in VALID_PROPERTY_TYPES:
            raise SchemaError(f"{filename}:{prop_key} unknown property type '{prop['type']}'")

        if "group" in prop and prop["group"] not in VALID_GROUPS:
            raise SchemaError(f"{filename}:{prop_key} invalid group '{prop['group']}'")

        if prop["type"] == "enum" and "allowed_values" not in prop:
            raise SchemaError(f"{filename}:{prop_key} enum requires 'allowed_values'")
        if "allowed_values" in prop and "regex" in prop:
            raise SchemaError(
                f"{filename}:{prop_key} cannot define both 'allowed_values' and 'regex'"
            )

        if "reference_targets" in prop:
            if prop["type"] != "reference":
                raise SchemaError(
                    f"{filename}:{prop_key} reference_targets require type='reference'"
                )
            if not isinstance(prop["reference_targets"], list):
                raise SchemaError(
                    f"{filename}:{prop_key} reference_targets must be a list"
                )
            for target in prop["reference_targets"]:
                self._validate_type_or_category_token(
                    target, filename, f"{prop_key}.reference_targets"
                )

    def _validate_type_or_category_token(
        self, value: Any, filename: str, field_name: str
    ) -> None:
        if not isinstance(value, str):
            raise SchemaError(f"{filename}: {field_name} entries must be strings")
        if value.startswith("@"):
            if len(value) == 1:
                raise SchemaError(f"{filename}: invalid category token in {field_name}")
        elif not PROPERTY_KEY_RE.match(value):
            raise SchemaError(f"{filename}: invalid type name '{value}' in {field_name}")

    def _resolve_all(self) -> None:
        for node_type in sorted(self.raw_schemas):
            self._resolve(node_type, set())

        category_map = self._build_category_map()
        for node_type in sorted(self.resolved_schemas):
            schema = self.resolved_schemas[node_type]
            schema["allowed_children_resolved"] = self._expand_tokens(
                schema.get("allowed_children", []), category_map
            )
            for prop in schema["properties"].values():
                if prop["type"] == "reference":
                    prop["reference_targets_resolved"] = self._expand_tokens(
                        prop.get("reference_targets", []), category_map
                    )

    def _resolve(self, node_type: str, stack: Set[str]) -> Dict[str, Any]:
        if node_type in self.resolved_schemas:
            return self.resolved_schemas[node_type]
        if node_type in stack:
            cycle = " -> ".join(list(stack) + [node_type])
            raise SchemaError(f"Circular inheritance detected: {cycle}")
        if node_type not in self.raw_schemas:
            raise SchemaError(f"Schema not found during resolution: {node_type}")

        stack.add(node_type)
        schema = self.raw_schemas[node_type]
        parent_type = schema.get("extends")

        parent_schema: Dict[str, Any] = {}
        if parent_type:
            if parent_type not in self.raw_schemas:
                raise SchemaError(f"{node_type}: unknown parent schema '{parent_type}'")
            parent_schema = self._resolve(parent_type, stack)

        resolved = self._merge_schema(parent_schema, schema)
        self.resolved_schemas[node_type] = resolved
        stack.remove(node_type)
        return resolved

    def _merge_schema(
        self, parent: Dict[str, Any], child: Dict[str, Any]
    ) -> Dict[str, Any]:
        merged: Dict[str, Any] = {
            "type": child["type"],
            "version": child["version"],
            "display_name": child.get("display_name", parent.get("display_name")),
            "category": child.get("category", parent.get("category")),
            "extends": child.get("extends"),
            "layout": child.get("layout", parent.get("layout", False)),
            "override": child.get("override", False),
            "_source": child.get("_source", parent.get("_source")),
            "_filename": child.get("_filename", parent.get("_filename")),
        }

        remove = child.get("remove", {})

        properties: Dict[str, Any] = {
            key: deepcopy(value) for key, value in parent.get("properties", {}).items()
        }
        for key in remove.get("properties", []):
            properties.pop(key, None)
        for key, value in child.get("properties", {}).items():
            properties[key] = deepcopy(value)
        merged["properties"] = properties

        allowed_children = list(parent.get("allowed_children", []))
        if "allowed_children" in child:
            allowed_children = list(child["allowed_children"])
        remove_children = set(remove.get("allowed_children", []))
        merged["allowed_children"] = [
            entry for entry in allowed_children if entry not in remove_children
        ]

        return merged

    def _build_category_map(self) -> Dict[str, Set[str]]:
        category_map: Dict[str, Set[str]] = {}
        for node_type, schema in self.resolved_schemas.items():
            category_map.setdefault(schema["category"], set()).add(node_type)
        return category_map

    def _expand_tokens(
        self, items: list[Any], category_map: Dict[str, Set[str]]
    ) -> list[str]:
        expanded: Set[str] = set()
        for item in items:
            if item.startswith("@"):
                expanded.update(category_map.get(item[1:], set()))
            else:
                expanded.add(item)
        return sorted(expanded)
