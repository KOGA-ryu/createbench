from __future__ import annotations


def can_move(node) -> bool:
    return not _is_locked(node)


def can_resize(node) -> bool:
    return not _is_locked(node)


def _is_locked(node) -> bool:
    if hasattr(node, "properties") and isinstance(node.properties, dict):
        return bool(node.properties.get("locked", False))
    if isinstance(node, dict):
        return bool(node.get("locked", False))
    return False
