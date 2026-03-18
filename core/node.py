from __future__ import annotations

from typing import Any, Optional


class Node:
    """Pure data object representing a single layout node."""

    def __init__(
        self,
        id: str,
        type: str,
        properties: dict[str, Any],
        parent_id: Optional[str] = None,
        name: Optional[str] = None,
    ):
        self.id = id
        self.type = type
        self.name = name
        self.properties = dict(properties)
        self.properties.setdefault("x", 0)
        self.properties.setdefault("y", 0)
        self.properties.setdefault("width", 200)
        self.properties.setdefault("height", 100)
        self.properties.setdefault("min_width", 50)
        self.properties.setdefault("min_height", 30)
        self.properties.setdefault("max_width", None)
        self.properties.setdefault("max_height", None)
        self.properties.setdefault("layout_mode", "free")
        self.properties.setdefault("locked", False)
        self.properties.setdefault("title", "")
        self.properties.setdefault("description", "")
        self.properties.setdefault("behavior", "")
        self.properties.setdefault("interactions", "")
        self.children: list[str] = []
        self.parent_id = parent_id

    def add_child(self, child_id: str, index: Optional[int] = None) -> None:
        if index is None:
            self.children.append(child_id)
        else:
            self.children.insert(index, child_id)

    def remove_child(self, child_id: str) -> None:
        if child_id in self.children:
            self.children.remove(child_id)

    def reorder_child(self, child_id: str, new_index: int) -> None:
        if child_id not in self.children:
            return
        self.children.remove(child_id)
        self.children.insert(new_index, child_id)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "properties": self.properties,
            "children": self.children,
        }
