from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
import re
from typing import Callable
from typing import Optional

from config import DEBUG
from core import bench_sessions, bench_workspace
from core.layout_model_api import LayoutModelAPI
from core.node import Node


class LayoutModel:
    RESTORED_ID_RE = re.compile(r"^(?P<type>[a-z0-9_]+)_(?P<index>\d+)$")
    FORK_OFFSET = 24
    BENCH_SESSION_PREFIX = "bench_"
    BENCH_WORKSPACE_TITLE = bench_workspace.BENCH_WORKSPACE_TITLE
    BENCH_WORKSPACE_X = bench_workspace.BENCH_WORKSPACE_X
    BENCH_WORKSPACE_Y = bench_workspace.BENCH_WORKSPACE_Y
    BENCH_WORKSPACE_WIDTH = bench_workspace.BENCH_WORKSPACE_WIDTH
    BENCH_WORKSPACE_HEIGHT = bench_workspace.BENCH_WORKSPACE_HEIGHT

    def __init__(self, property_registry):
        self.registry = property_registry
        self.nodes: dict[str, Node] = {}
        self.root_id = "root"
        self.type_counters: dict[str, int] = {}
        self.scene_metadata: dict[str, object] = {}
        self.closed_bench_sessions: list[dict[str, object]] = []
        self._subscribers: list[Callable[[], None]] = []
        self._notification_depth = 0
        self._pending_notification = False

        root = Node(id=self.root_id, type="root", properties={}, parent_id=None)
        self.nodes[self.root_id] = root

    def subscribe(self, callback: Callable[[], None]) -> None:
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[], None]) -> None:
        try:
            self._subscribers.remove(callback)
        except ValueError:
            pass

    def notify_subscribers(self) -> None:
        if self._notification_depth > 0:
            self._pending_notification = True
            return
        for callback in list(self._subscribers):
            callback()

    def set_scene_metadata(self, metadata: dict[str, object] | None) -> None:
        self.scene_metadata = dict(metadata or {})
        self.notify_subscribers()

    def get_root_id(self) -> str:
        return self.root_id

    def get_scene_metadata(self) -> dict[str, object]:
        return self.scene_metadata

    def replace_scene_metadata_and_notify(self, metadata: dict[str, object]) -> None:
        self.scene_metadata = metadata
        self.notify_subscribers()

    def get_closed_bench_sessions(self) -> list[dict[str, object]]:
        return self.closed_bench_sessions

    def set_closed_bench_sessions(self, entries: list[dict[str, object]]) -> None:
        self.closed_bench_sessions = entries

    def iter_nodes(self) -> list[Node]:
        return list(self.nodes.values())

    def get_active_bench_session_id(self) -> str | None:
        return bench_sessions.get_active_bench_session_id(LayoutModelAPI(self))

    def set_active_bench_session(self, bench_session_id: str | None) -> None:
        bench_sessions.set_active_bench_session(LayoutModelAPI(self), bench_session_id)

    def clear_active_bench_session(self) -> None:
        bench_sessions.clear_active_bench_session(LayoutModelAPI(self))

    def sync_active_bench_session(self) -> None:
        bench_sessions.sync_active_bench_session(LayoutModelAPI(self))

    def get_bench_session_ids(self) -> list[str]:
        return bench_sessions.get_bench_session_ids(LayoutModelAPI(self))

    def get_recently_closed_bench_session_ids(self) -> list[str]:
        return bench_sessions.get_recently_closed_bench_session_ids(LayoutModelAPI(self))

    def close_bench_session(self, bench_session_id: str) -> list[str]:
        return bench_sessions.close_bench_session(LayoutModelAPI(self), bench_session_id)

    def reopen_closed_bench_session(self, bench_session_id: str) -> list[str]:
        return bench_sessions.reopen_closed_bench_session(LayoutModelAPI(self), bench_session_id)

    @contextmanager
    def batch_updates(self):
        self._notification_depth += 1
        try:
            yield
        finally:
            self._notification_depth -= 1
            if self._notification_depth == 0 and self._pending_notification:
                self._pending_notification = False
                self.notify_subscribers()

    def _generate_id(self, node_type: str) -> str:
        next_value = self.type_counters.get(node_type, 0) + 1
        self.type_counters[node_type] = next_value
        return f"{node_type}_{next_value}"

    def create_node(
        self,
        node_type: str,
        properties: dict,
        name=None,
        restored_id: str | None = None,
        metadata: dict | None = None,
    ) -> Node:
        node_id = restored_id or self._generate_id(node_type)
        resolved_properties = self.registry.apply_defaults(node_type, properties)
        node = Node(
            id=node_id,
            type=node_type,
            properties=resolved_properties,
            parent_id=None,
            name=name,
            metadata=metadata,
        )
        if node.id in self.nodes:
            raise ValueError(f"Duplicate node id: {node.id}")
        self._register_restored_id(node_type, node_id)
        self.nodes[node.id] = node
        return node

    def _register_restored_id(self, node_type: str, node_id: str) -> None:
        match = self.RESTORED_ID_RE.match(node_id)
        if match is None:
            return
        if match.group("type") != node_type:
            return
        restored_index = int(match.group("index"))
        current_index = self.type_counters.get(node_type, 0)
        if restored_index > current_index:
            self.type_counters[node_type] = restored_index

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
        self.notify_subscribers()

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
        self.notify_subscribers()
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
        self.notify_subscribers()

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
        self.notify_subscribers()

    def fork_subtree(self, node_id: str, destination: str = "here") -> str | None:
        if node_id == self.root_id:
            return None
        node = self.get_node(node_id)
        if node is None:
            return None
        parent = self.get_parent(node_id)
        if parent is None:
            return None
        if destination not in {"here", "bench"}:
            raise ValueError(f"Unsupported fork destination: {destination}")

        insert_index = parent.children.index(node_id) + 1
        bench_session_id = None
        target_parent = parent
        if destination == "bench":
            bench_session_id = f"{self.BENCH_SESSION_PREFIX}{node_id}"
            target_parent = self._ensure_bench_workspace()
            insert_index = None

        with self.batch_updates():
            forked_id = self._clone_subtree(
                node_id,
                target_parent.id,
                destination=destination,
                bench_session_id=bench_session_id,
                index=insert_index,
            )
            self._debug_validate()
        return forked_id

    def fork_subtree_to_design(self, node_id: str) -> str | None:
        return self.fork_subtree(node_id, destination="here")

    def open_subtree_in_bench(self, node_id: str) -> str | None:
        bench_id = self.fork_subtree(node_id, destination="bench")
        if bench_id is not None:
            bench_node = self.get_node(bench_id)
            if bench_node is not None:
                bench_session_id = getattr(bench_node, "metadata", {}).get("bench_session_id")
                self.set_active_bench_session(bench_session_id)
        return bench_id

    def fork_scene_to_design(self) -> list[str]:
        created_root_ids: list[str] = []
        root_children = [
            child for child in self.get_children(self.root_id)
            if child.id != self.root_id and self._find_bench_workspace() is not child
        ]
        with self.batch_updates():
            for child in root_children:
                created_root_ids.append(
                    self._clone_subtree(
                        child.id,
                        self.root_id,
                        destination="here",
                        bench_session_id=None,
                        index=None,
                    )
                )
        return created_root_ids

    def open_scene_in_bench(self) -> list[str]:
        created_root_ids: list[str] = []
        root_children = [
            child for child in self.get_children(self.root_id)
            if child.id != self.root_id and self._find_bench_workspace() is not child
        ]
        if not root_children:
            return created_root_ids
        bench_session_id = f"{self.BENCH_SESSION_PREFIX}scene"
        existing = set(self.get_bench_session_ids()) | set(
            self.get_recently_closed_bench_session_ids()
        )
        if bench_session_id in existing:
            index = 2
            while f"{self.BENCH_SESSION_PREFIX}scene_{index}" in existing:
                index += 1
            bench_session_id = f"{self.BENCH_SESSION_PREFIX}scene_{index}"
        workspace = self._ensure_bench_workspace()
        with self.batch_updates():
            for child in root_children:
                created_root_ids.append(
                    self._clone_subtree(
                        child.id,
                        workspace.id,
                        destination="bench",
                        bench_session_id=bench_session_id,
                        index=None,
                    )
                )
            self.set_active_bench_session(bench_session_id)
        return created_root_ids

    def _clone_subtree(
        self,
        source_node_id: str,
        target_parent_id: str,
        *,
        destination: str,
        bench_session_id: str | None,
        index: int | None = None,
    ) -> str:
        source = self.get_node(source_node_id)
        assert source is not None
        metadata = deepcopy(getattr(source, "metadata", {}) or {})
        metadata["origin_node_id"] = source.id
        if bench_session_id is not None:
            metadata["bench_session_id"] = bench_session_id
        else:
            metadata.pop("bench_session_id", None)

        trust = dict(metadata.get("trust", {}) or {})
        original_origin = (
            metadata.get("provenance", {}).get("representation_origin")
            or trust.get("representation_origin")
            or "unknown"
        )
        if original_origin in {"source", "adapter"}:
            trust["trust_level"] = "partial"
        else:
            trust["trust_level"] = trust.get("trust_level") or "mock"
        trust["representation_origin"] = "manual" if destination == "here" else "adapter"
        metadata["trust"] = trust

        provenance = dict(metadata.get("provenance", {}) or {})
        provenance["representation_origin"] = "manual" if destination == "here" else "adapter"
        provenance["forked_from_origin"] = source.id
        provenance["fork_destination"] = destination
        metadata["provenance"] = provenance

        cloned = self.create_node(
            source.type,
            deepcopy(source.properties),
            name=source.name,
            metadata=metadata,
        )
        if cloned.properties.get("layout_mode") == "free":
            if "x" in cloned.properties and cloned.properties["x"] is not None:
                cloned.properties["x"] = int(cloned.properties["x"]) + self.FORK_OFFSET
            if "y" in cloned.properties and cloned.properties["y"] is not None:
                cloned.properties["y"] = int(cloned.properties["y"]) + self.FORK_OFFSET
        self.add_node(target_parent_id, cloned, index=index)
        for child_id in source.children:
            self._clone_subtree(
                child_id,
                cloned.id,
                destination=destination,
                bench_session_id=bench_session_id,
                index=None,
            )
        return cloned.id

    def get_children(self, node_id: str) -> list[Node]:
        node = self.get_node(node_id)
        if node is None:
            return []
        return [self.nodes[child_id] for child_id in node.children if child_id in self.nodes]

    def _ensure_bench_workspace(self) -> Node:
        return bench_workspace.ensure_bench_workspace(LayoutModelAPI(self))

    def ensure_bench_workspace(self) -> Node:
        return bench_workspace.ensure_bench_workspace(LayoutModelAPI(self))

    def _find_bench_workspace(self) -> Node | None:
        return bench_workspace.find_bench_workspace(LayoutModelAPI(self))

    def serialize_subtree(self, node_id: str) -> dict[str, object]:
        node = self.get_node(node_id)
        assert node is not None
        return {
            "type": node.type,
            "name": node.name,
            "properties": deepcopy(node.properties),
            "metadata": deepcopy(getattr(node, "metadata", {}) or {}),
            "children": [self.serialize_subtree(child_id) for child_id in node.children if self.get_node(child_id) is not None],
        }

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
