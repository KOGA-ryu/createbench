from __future__ import annotations

from typing import Optional

from config import DEBUG
from core.node import Node


class LayoutModel:
    def __init__(self, property_registry):
        self.registry = property_registry
        self.nodes: dict[str, Node] = {}
        self.root_id = "root"
        self.type_counters: dict[str, int] = {}

        root = Node(id=self.root_id, type="root", properties={}, parent_id=None)
        self.nodes[self.root_id] = root

    def _generate_id(self, node_type: str) -> str:
        next_value = self.type_counters.get(node_type, 0) + 1
        self.type_counters[node_type] = next_value
        return f"{node_type}_{next_value}"

    def create_node(self, node_type: str, properties: dict, name=None) -> Node:
        node_id = self._generate_id(node_type)
        resolved_properties = self.registry.apply_defaults(node_type, properties)
        node = Node(
            id=node_id,
            type=node_type,
            properties=resolved_properties,
            parent_id=None,
            name=name,
        )
        if node.id in self.nodes:
            raise ValueError(f"Duplicate node id: {node.id}")
        self.nodes[node.id] = node
        return node

    def add_node(self, parent_id: str, node: Node, index: Optional[int] = None):
        assert node is not None, "Node is required"
        assert parent_id in self.nodes, f"Parent not found: {parent_id}"
        parent = self.get_node(parent_id)
        assert parent is not None, f"Parent not found: {parent_id}"

        if node.id in self.nodes and self.nodes[node.id] is not node:
            raise ValueError(f"Duplicate node id: {node.id}")
        if node.id not in self.nodes:
            self.nodes[node.id] = node

        node.parent_id = parent_id
        parent.add_child(node.id, index=index)
        self._debug_validate()

    def get_node(self, node_id: str) -> Optional[Node]:
        return self.nodes.get(node_id)

    def remove_node(self, node_id: str) -> list[str]:
        assert node_id is not None, "Node id is required"
        if node_id == self.root_id:
            raise ValueError("Root cannot be deleted")
        node = self.get_node(node_id)
        if node is None:
            return []

        deleted: list[str] = []
        if node.parent_id is not None:
            parent = self.get_node(node.parent_id)
            if parent is not None:
                parent.remove_child(node_id)

        self._remove_subtree(node_id, deleted)
        self._debug_validate()
        return deleted

    def move_node(self, node_id: str, new_parent_id: str, index: Optional[int] = None):
        assert node_id is not None, "Node id is required"
        assert new_parent_id is not None, "Parent id is required"
        assert new_parent_id in self.nodes, f"Parent not found: {new_parent_id}"
        if node_id == self.root_id:
            raise ValueError("Root cannot be moved")

        assert node_id in self.nodes, f"Node not found: {node_id}"
        node = self.get_node(node_id)
        if node is None:
            raise ValueError(f"Node not found: {node_id}")

        new_parent = self.get_node(new_parent_id)
        if new_parent is None:
            raise ValueError(f"Parent not found: {new_parent_id}")

        if node_id == new_parent_id:
            raise ValueError("Invalid move: cannot reparent into self")
        if self._is_descendant(new_parent_id, node_id):
            raise ValueError("Invalid move: cannot reparent into descendant")

        old_parent = self.get_parent(node_id)
        if old_parent is not None:
            old_parent.remove_child(node_id)

        new_parent.add_child(node_id, index=index)
        node.parent_id = new_parent_id
        self._debug_validate()

    def reorder_node(self, node_id: str, new_index: int):
        assert node_id is not None, "Node id is required"
        if node_id == self.root_id:
            raise ValueError("Root cannot be reordered")

        assert node_id in self.nodes, f"Node not found: {node_id}"
        parent = self.get_parent(node_id)
        if parent is None:
            return
        parent.reorder_child(node_id, new_index)
        self._debug_validate()

    def get_children(self, node_id: str) -> list[Node]:
        node = self.get_node(node_id)
        if node is None:
            return []
        return [self.nodes[child_id] for child_id in node.children if child_id in self.nodes]

    def get_parent(self, node_id: str) -> Optional[Node]:
        node = self.get_node(node_id)
        if node is None or node.parent_id is None:
            return None
        return self.get_node(node.parent_id)

    def _is_descendant(self, node_id: str, potential_parent_id: str) -> bool:
        node = self.get_node(node_id)
        while node is not None and node.parent_id is not None:
            if node.parent_id == potential_parent_id:
                return True
            node = self.get_node(node.parent_id)
        return False

    def _remove_subtree(self, node_id: str, deleted: list[str]) -> None:
        node = self.get_node(node_id)
        if node is None:
            return

        for child_id in list(node.children):
            self._remove_subtree(child_id, deleted)

        deleted.append(node_id)
        del self.nodes[node_id]

    def validate_integrity(self):
        visited: set[str] = set()
        stack: set[str] = set()

        def visit(node_id: str):
            assert node_id in self.nodes, f"Integrity error: missing node {node_id}"
            if node_id in stack:
                raise AssertionError(f"Integrity error: cycle detected at {node_id}")
            if node_id in visited:
                return

            stack.add(node_id)
            node = self.nodes[node_id]
            for child_id in node.children:
                assert child_id in self.nodes, f"Integrity error: missing child {child_id}"
                child = self.nodes[child_id]
                assert (
                    child.parent_id == node_id
                ), f"Integrity error: parent mismatch for child {child_id}"
                visit(child_id)
            stack.remove(node_id)
            visited.add(node_id)

        visit(self.root_id)
        for node_id, node in self.nodes.items():
            if node_id == self.root_id:
                assert node.parent_id is None, "Integrity error: root parent must be None"
                continue
            if node_id in visited:
                assert (
                    node.parent_id is not None
                ), f"Integrity error: attached node {node_id} missing parent"
                assert (
                    node.parent_id in self.nodes
                ), f"Integrity error: parent {node.parent_id} missing for {node_id}"
                parent = self.nodes[node.parent_id]
                assert (
                    node_id in parent.children
                ), f"Integrity error: child {node_id} missing from parent {node.parent_id}"
            else:
                assert (
                    node.parent_id is None
                ), f"Integrity error: detached node {node_id} has unexpected parent"

    def _debug_validate(self):
        if DEBUG:
            self.validate_integrity()
