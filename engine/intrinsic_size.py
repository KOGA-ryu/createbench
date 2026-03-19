from __future__ import annotations


def get_intrinsic_size(node) -> dict[str, int] | None:
    node_type = node.type
    props = node.properties

    if node_type == "button":
        text = props.get("text") or props.get("title") or "Button"
        return {
            "width": max(80, len(str(text)) * 8 + 24),
            "height": 32,
        }

    if node_type == "text":
        text = props.get("text") or props.get("title") or ""
        lines = str(text).count("\n") + 1
        return {
            "width": int(props.get("width", 200)),
            "height": lines * 18 + 8,
        }

    if node_type == "input":
        return {
            "width": int(props.get("width", 220)),
            "height": 32,
        }

    if node_type == "toolbar":
        return {
            "width": int(props.get("width", 300)),
            "height": 40,
        }

    if node_type == "sidebar":
        return {
            "width": int(props.get("width", 240)),
            "height": int(props.get("height", 600)),
        }

    if node_type == "main":
        return {
            "width": int(props.get("width", 400)),
            "height": int(props.get("height", 300)),
        }

    if node_type == "panel":
        return {
            "width": int(props.get("width", 260)),
            "height": int(props.get("height", 180)),
        }

    return None
