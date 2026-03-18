from __future__ import annotations

from core.node import Node


class TreeManager:
    def __init__(self, layout_model):
        self.model = layout_model

    def add_node(self, parent_id: str, node: Node, index=None):
        assert node is not None, "Node is required"
        assert parent_id in self.model.nodes, f"Parent not found: {parent_id}"
        self.model.add_node(parent_id, node, index=index)
        return {"action": "add", "node_id": node.id, "parent_id": parent_id}

    def remove_node(self, node_id: str) -> dict:
        assert node_id in self.model.nodes, f"Node not found: {node_id}"
        assert node_id != self.model.root_id, "Root cannot be removed"
        deleted_ids = self.model.remove_node(node_id)
        return {"action": "remove", "deleted_ids": deleted_ids}

    def move_node(self, node_id: str, new_parent_id: str, index=None):
        assert node_id in self.model.nodes, f"Node not found: {node_id}"
        assert new_parent_id in self.model.nodes, f"Parent not found: {new_parent_id}"
        assert node_id != self.model.root_id, "Root cannot be moved"
        self.model.move_node(node_id, new_parent_id, index=index)
        return {
            "action": "move",
            "node_id": node_id,
            "new_parent_id": new_parent_id,
        }

    def reorder_node(self, node_id: str, new_index: int):
        assert node_id in self.model.nodes, f"Node not found: {node_id}"
        assert node_id != self.model.root_id, "Root cannot be reordered"
        self.model.reorder_node(node_id, new_index)
        return {
            "action": "reorder",
            "node_id": node_id,
            "new_index": new_index,
        }

    def get_parent(self, node_id: str):
        assert node_id in self.model.nodes, f"Node not found: {node_id}"
        return self.model.get_parent(node_id)

    def get_children(self, node_id: str):
        assert node_id in self.model.nodes, f"Node not found: {node_id}"
        return self.model.get_children(node_id)
