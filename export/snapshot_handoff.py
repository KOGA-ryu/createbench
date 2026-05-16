from __future__ import annotations

from core.node_resolution import resolve_node_state


def _layout_intent(properties: dict[str, object]) -> dict[str, object]:
    return {
        "layout_mode": properties.get("layout_mode"),
        "position": {
            "x": properties.get("x"),
            "y": properties.get("y"),
        },
        "size": {
            "width": properties.get("width"),
            "height": properties.get("height"),
        },
    }


def _role_hints(properties: dict[str, object], metadata: dict[str, object]) -> dict[str, object]:
    render_hints = dict(metadata.get("render_hints", {}) or {})
    return {
        "ui_role": properties.get("ui_role"),
        "title": render_hints.get("title", properties.get("title")),
        "text": render_hints.get("text", properties.get("text")),
        "placeholder": render_hints.get("placeholder", properties.get("placeholder")),
    }


def _trust_label(trust: dict[str, object], provenance: dict[str, object]) -> str:
    trust_level = trust.get("trust_level") or "unknown"
    origin = provenance.get("representation_origin") or trust.get("representation_origin") or "unknown"
    return f"{trust_level}:{origin}"


def _node_ref(snapshot: dict[str, object], path: tuple[int, ...]) -> str:
    node_type = str(snapshot.get("type") or "unknown")
    node_name = snapshot.get("name")
    suffix = ".".join(str(part) for part in path) if path else "root"
    if node_name:
        return f"{node_type}:{node_name}@{suffix}"
    return f"{node_type}@{suffix}"


def build_snapshot_handoff(
    snapshot: dict[str, object],
    *,
    model,
    node,
    scene_metadata: dict[str, object] | None = None,
    path: tuple[int, ...] = (),
    parent_ref: str | None = None,
) -> dict[str, object]:
    children = snapshot.get("children", [])
    metadata = dict(snapshot.get("metadata", {}) or {})
    source = dict(metadata.get("source", {}) or {})
    trust = dict(metadata.get("trust", {}) or {})
    provenance = dict(metadata.get("provenance", {}) or {})
    relationships = dict(metadata.get("relationships", {}) or {})
    properties = dict(snapshot.get("properties", {}) or {})
    node_ref = _node_ref(snapshot, path)
    child_refs = [_node_ref(child, path + (index,)) for index, child in enumerate(children)]
    resolved = resolve_node_state(node, scene_metadata or {})

    return {
        "node": {
            "ref": node_ref,
            "type": snapshot.get("type"),
            "name": snapshot.get("name"),
            "child_count": len(children),
        },
        "mode": resolved["resolved_mode"],
        "editability": resolved["editability"],
        "source": {
            "file": source.get("file"),
            "symbol": source.get("symbol"),
            "line_start": source.get("line_start"),
            "line_end": source.get("line_end"),
        },
        "trust": {
            "trust_level": trust.get("trust_level"),
            "representation_origin": provenance.get("representation_origin")
            or trust.get("representation_origin"),
            "label": _trust_label(trust, provenance),
            "warnings": list(trust.get("warnings") or []),
        },
        "relationships": {
            "parent": parent_ref,
            "children": child_refs,
            "communicates_to": list(relationships.get("communicates_to") or []),
            "depends_on": list(relationships.get("depends_on") or []),
        },
        "layout_intent": _layout_intent(properties),
        "role_hints": _role_hints(properties, metadata),
        "properties": properties,
        "children": [
            build_snapshot_handoff(
                child,
                model=model,
                node=child_node,
                scene_metadata=scene_metadata,
                path=path + (index,),
                parent_ref=node_ref,
            )
            for index, (child, child_node) in enumerate(
                (
                    (child, model.get_node(child_id))
                    for child, child_id in zip(children, node.children)
                )
            )
            if child_node is not None
        ],
    }
