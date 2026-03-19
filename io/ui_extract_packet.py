from __future__ import annotations

from copy import deepcopy
import json


REQUIRED_PACKET_FIELDS = {
    "packet_version",
    "source_framework",
    "source_provider",
    "trust_level",
    "roots",
    "nodes",
    "warnings",
}

REQUIRED_NODE_FIELDS = {
    "id",
    "type",
    "parent",
    "children",
    "source",
    "layout_hints",
    "render_hints",
    "relationships",
    "trust",
    "raw",
}

REQUIRED_SECTIONS = {
    "source": {"file", "symbol", "line_start", "line_end", "source_id"},
    "layout_hints": {
        "layout_mode",
        "layout_direction",
        "preferred_width",
        "preferred_height",
        "min_width",
        "min_height",
        "max_width",
        "max_height",
        "x",
        "y",
        "width",
        "height",
    },
    "render_hints": {
        "title",
        "text",
        "placeholder",
        "icon",
        "visible",
        "enabled",
        "window_mode",
    },
    "relationships": {"communicates_to", "depends_on", "updated_by", "triggered_by"},
    "trust": {"trust_level", "representation_origin", "warnings"},
    "raw": {"provider_type", "provider_data", "unresolved_fields"},
}


def validate_packet(packet: dict) -> None:
    if not isinstance(packet, dict):
        raise ValueError("Packet must be a dictionary")

    missing_packet_fields = sorted(REQUIRED_PACKET_FIELDS - set(packet))
    if missing_packet_fields:
        raise ValueError(f"Packet missing required fields: {', '.join(missing_packet_fields)}")

    if not isinstance(packet["roots"], list):
        raise ValueError("Packet field 'roots' must be a list")
    if not isinstance(packet["nodes"], list):
        raise ValueError("Packet field 'nodes' must be a list")
    if not isinstance(packet["warnings"], list):
        raise ValueError("Packet field 'warnings' must be a list")

    node_ids: set[str] = set()
    nodes_by_id: dict[str, dict] = {}
    for index, node in enumerate(packet["nodes"]):
        if not isinstance(node, dict):
            raise ValueError(f"Node at index {index} must be a dictionary")
        missing_node_fields = sorted(REQUIRED_NODE_FIELDS - set(node))
        if missing_node_fields:
            raise ValueError(
                f"Node at index {index} missing required fields: {', '.join(missing_node_fields)}"
            )
        node_id = node["id"]
        if not isinstance(node_id, str) or not node_id:
            raise ValueError(f"Node at index {index} must have a non-empty string id")
        if node_id in node_ids:
            raise ValueError(f"Duplicate packet node id: {node_id}")
        node_ids.add(node_id)
        nodes_by_id[node_id] = node

        if not isinstance(node["children"], list):
            raise ValueError(f"Node '{node_id}' field 'children' must be a list")
        for section_name, required_fields in REQUIRED_SECTIONS.items():
            section = node[section_name]
            if not isinstance(section, dict):
                raise ValueError(f"Node '{node_id}' field '{section_name}' must be a dictionary")
            missing_section_fields = sorted(required_fields - set(section))
            if missing_section_fields:
                raise ValueError(
                    f"Node '{node_id}' field '{section_name}' missing required fields: {', '.join(missing_section_fields)}"
                )

    for root_id in packet["roots"]:
        if root_id not in nodes_by_id:
            raise ValueError(f"Root id '{root_id}' does not exist in packet nodes")

    for node_id, node in nodes_by_id.items():
        parent_id = node["parent"]
        if parent_id is not None:
            if not isinstance(parent_id, str) or not parent_id:
                raise ValueError(f"Node '{node_id}' has invalid parent id")
            if parent_id not in nodes_by_id:
                raise ValueError(f"Node '{node_id}' parent '{parent_id}' does not exist")
            if node_id not in nodes_by_id[parent_id]["children"]:
                raise ValueError(
                    f"Node '{node_id}' parent/child mismatch: parent '{parent_id}' does not list child"
                )

        for child_id in node["children"]:
            if child_id not in nodes_by_id:
                raise ValueError(f"Node '{node_id}' child '{child_id}' does not exist")
            child = nodes_by_id[child_id]
            if child["parent"] != node_id:
                raise ValueError(
                    f"Node '{node_id}' child '{child_id}' parent mismatch: found '{child['parent']}'"
                )


def normalize_packet(packet: dict) -> dict:
    validate_packet(packet)
    normalized = deepcopy(packet)
    normalized["packet_version"] = str(normalized["packet_version"])
    normalized["source_framework"] = (
        None if normalized["source_framework"] is None else str(normalized["source_framework"])
    )
    normalized["source_provider"] = (
        None if normalized["source_provider"] is None else str(normalized["source_provider"])
    )
    normalized["trust_level"] = str(normalized["trust_level"])
    normalized["roots"] = [str(node_id) for node_id in normalized["roots"]]

    for node in normalized["nodes"]:
        node["id"] = str(node["id"])
        node["type"] = str(node["type"])
        node["ui_role"] = None if node.get("ui_role") is None else str(node["ui_role"])
        node["parent"] = None if node["parent"] is None else str(node["parent"])
        node["children"] = [str(child_id) for child_id in node["children"]]
        node["trust"]["trust_level"] = str(node["trust"]["trust_level"])
        node["trust"]["representation_origin"] = str(node["trust"]["representation_origin"])

    return normalized


def _scene_metadata_from_packet(normalized: dict) -> dict[str, object]:
    return {
        "packet_version": normalized["packet_version"],
        "source_framework": normalized["source_framework"],
        "source_provider": normalized["source_provider"],
        "packet_trust_level": normalized["trust_level"],
        "packet_warnings": deepcopy(normalized["warnings"]),
        "representation_origin": "adapter"
        if normalized["source_provider"] not in {None, "template", "unknown"}
        else normalized["source_provider"] or "unknown",
    }


def _build_node_metadata(
    packet_node: dict,
    normalized: dict,
    *,
    packet_node_id: str | None = None,
    bench_session_id: str | None = None,
    bench_import: bool = False,
) -> dict[str, object]:
    metadata = {
        "source": deepcopy(packet_node["source"]),
        "trust": deepcopy(packet_node["trust"]),
        "provenance": {
            "representation_origin": packet_node["trust"]["representation_origin"],
            "source_framework": normalized["source_framework"],
            "source_provider": normalized["source_provider"],
            "packet_version": normalized["packet_version"],
            "packet_trust_level": normalized["trust_level"],
            "packet_warnings": deepcopy(normalized["warnings"]),
        },
        "relationships": deepcopy(packet_node["relationships"]),
        "raw": deepcopy(packet_node["raw"]),
    }
    if packet_node_id is not None:
        metadata["provenance"]["packet_node_id"] = str(packet_node_id)
    if bench_session_id is not None:
        metadata["bench_session_id"] = str(bench_session_id)
    if bench_import:
        metadata["provenance"]["fork_destination"] = "bench"
    return metadata


def _next_bench_session_id(layout_model, seed: str) -> str:
    base = f"{layout_model.BENCH_SESSION_PREFIX}{seed}"
    existing = set(layout_model.get_bench_session_ids()) | set(
        layout_model.get_recently_closed_bench_session_ids()
    )
    if base not in existing:
        return base
    index = 2
    while f"{base}_{index}" in existing:
        index += 1
    return f"{base}_{index}"


def _import_normalized_packet(layout_model, normalized: dict, destination: str) -> list[str]:
    nodes_by_id = {node["id"]: node for node in normalized["nodes"]}
    created_root_ids: list[str] = []

    if destination == "replace":
        target_parent_id = layout_model.root_id
        restored_ids = True
        bench_session_id = None
    elif destination == "alongside":
        target_parent_id = layout_model.root_id
        restored_ids = False
        bench_session_id = None
    elif destination == "bench":
        target_parent_id = layout_model.ensure_bench_workspace().id
        restored_ids = False
        bench_session_id = _next_bench_session_id(
            layout_model,
            f"packet_{normalized['roots'][0]}",
        )
    else:
        raise ValueError(f"Unsupported packet import destination: {destination}")

    def build(node_id: str, parent_id: str) -> str:
        packet_node = nodes_by_id[node_id]
        properties: dict[str, object] = {}
        if packet_node.get("ui_role") is not None:
            properties["ui_role"] = packet_node["ui_role"]

        layout_hints = packet_node["layout_hints"]
        if layout_hints.get("layout_mode") is not None:
            properties["layout_mode"] = layout_hints["layout_mode"]
        for field in ("x", "y", "width", "height"):
            if layout_hints.get(field) is not None:
                properties[field] = layout_hints[field]

        render_hints = packet_node["render_hints"]
        for field in ("text", "title", "placeholder"):
            if render_hints.get(field) is not None:
                properties[field] = render_hints[field]

        node = layout_model.create_node(
            packet_node["type"],
            properties,
            restored_id=packet_node["id"] if restored_ids else None,
        )
        node.metadata = _build_node_metadata(
            packet_node,
            normalized,
            packet_node_id=None if restored_ids else packet_node["id"],
            bench_session_id=bench_session_id,
            bench_import=destination == "bench",
        )
        layout_model.add_node(parent_id, node)
        for child_id in packet_node["children"]:
            build(child_id, node.id)
        return node.id

    for root_id in normalized["roots"]:
        created_root_ids.append(build(root_id, target_parent_id))

    if destination == "bench":
        layout_model.set_active_bench_session(bench_session_id)

    return created_root_ids


def import_packet_into_layout(layout_model, packet, destination: str = "replace") -> list[str]:
    normalized = normalize_packet(packet)
    with layout_model.batch_updates():
        if destination == "replace":
            for child in list(layout_model.get_children(layout_model.root_id)):
                layout_model.remove_node(child.id)
            layout_model.set_scene_metadata(_scene_metadata_from_packet(normalized))
        created_root_ids = _import_normalized_packet(layout_model, normalized, destination)
        layout_model.validate_integrity()
    return created_root_ids


def load_packet(layout_model, filepath) -> None:
    with open(filepath, "r", encoding="utf-8") as handle:
        packet = json.load(handle)
    import_packet_into_layout(layout_model, packet, destination="replace")


def load_packet_alongside(layout_model, filepath) -> list[str]:
    with open(filepath, "r", encoding="utf-8") as handle:
        packet = json.load(handle)
    return import_packet_into_layout(layout_model, packet, destination="alongside")


def load_packet_in_bench(layout_model, filepath) -> list[str]:
    with open(filepath, "r", encoding="utf-8") as handle:
        packet = json.load(handle)
    return import_packet_into_layout(layout_model, packet, destination="bench")
