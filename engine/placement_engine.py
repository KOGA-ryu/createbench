from __future__ import annotations


PLACEMENT_OFFSET = 16


def place_new_node(node, parent, parent_rect=None, cursor_pos=None):
    parent_props = getattr(parent, "properties", {}) or {}
    parent_layout_mode = parent_props.get("layout_mode", "free")

    node.properties = dict(node.properties)

    if parent_layout_mode == "auto":
        node.properties["layout_mode"] = "auto"
        return node.properties

    base_x, base_y = _resolve_base_position(parent_rect, cursor_pos)
    sibling_count = len(getattr(parent, "children", []) or [])
    offset = sibling_count * PLACEMENT_OFFSET

    node.properties["layout_mode"] = "free"
    node.properties["x"] = int(base_x + offset)
    node.properties["y"] = int(base_y + offset)
    return node.properties


def place_template_subtree(template_dict, parent_id, model, layout_engine):
    first_created_id = None

    def build(template_node, target_parent_id):
        nonlocal first_created_id
        parent = model.get_node(target_parent_id)
        parent_rect = _resolve_parent_rect(target_parent_id, layout_engine)
        node = model.create_node(template_node["type"], template_node.get("properties", {}))
        if parent is not None:
            place_new_node(node, parent, parent_rect=parent_rect, cursor_pos=None)
        model.add_node(target_parent_id, node)
        if first_created_id is None:
            first_created_id = node.id
        for child_template in template_node.get("children", []):
            build(child_template, node.id)
        return node

    build(template_dict, parent_id)
    return first_created_id


def _resolve_base_position(parent_rect, cursor_pos):
    if cursor_pos is not None:
        return cursor_pos
    if parent_rect is not None:
        return parent_rect["x"], parent_rect["y"]
    return 0, 0


def _resolve_parent_rect(parent_id, layout_engine):
    if layout_engine is None:
        return None
    if hasattr(layout_engine, "get_node_rect"):
        return layout_engine.get_node_rect(parent_id)
    rect_map = getattr(layout_engine, "rect_map", None)
    if isinstance(rect_map, dict):
        return rect_map.get(parent_id)
    return None
