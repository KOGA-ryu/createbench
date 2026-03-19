from __future__ import annotations

from copy import deepcopy
from contextlib import contextmanager
import re
from typing import Callable
from typing import Optional

from config import DEBUG
from core.node import Node


class LayoutModel:
    RESTORED_ID_RE = re.compile(r"^(?P<type>[a-z0-9_]+)_(?P<index>\d+)$")
    FORK_OFFSET = 24
    BENCH_SESSION_PREFIX = "bench_"
    BENCH_WORKSPACE_TITLE = "Bench Workspace"
    BENCH_WORKSPACE_X = 920
    BENCH_WORKSPACE_Y = 72
    BENCH_WORKSPACE_WIDTH = 420
    BENCH_WORKSPACE_HEIGHT = 680

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

    def get_active_bench_session_id(self) -> str | None:
        active = self.scene_metadata.get("active_bench_session_id")
        return None if active is None else str(active)

    def set_active_bench_session(self, bench_session_id: str | None) -> None:
        metadata = dict(self.scene_metadata)
        if bench_session_id is None:
            metadata.pop("active_bench_session_id", None)
        else:
            metadata["active_bench_session_id"] = str(bench_session_id)
        self.set_scene_metadata(metadata)

    def clear_active_bench_session(self) -> None:
        self.set_active_bench_session(None)

    def sync_active_bench_session(self) -> None:
        active_bench_session_id = self.get_active_bench_session_id()
        if active_bench_session_id is None:
            return
        if active_bench_session_id in self.get_bench_session_ids():
            return
        metadata = dict(self.scene_metadata)
        if "active_bench_session_id" not in metadata:
            return
        metadata.pop("active_bench_session_id", None)
        self.scene_metadata = metadata
        self.notify_subscribers()

    def get_bench_session_ids(self) -> list[str]:
        session_ids: set[str] = set()
        for node in self.nodes.values():
            metadata = getattr(node, "metadata", {}) or {}
            bench_session_id = metadata.get("bench_session_id")
            if bench_session_id:
                session_ids.add(str(bench_session_id))
        return sorted(session_ids)

    def get_recently_closed_bench_session_ids(self) -> list[str]:
        return [str(entry["bench_session_id"]) for entry in self.closed_bench_sessions]

    def close_bench_session(self, bench_session_id: str) -> list[str]:
        deleted: list[str] = []
        with self.batch_updates():
            roots_to_capture: list[str] = []
            for node in list(self.nodes.values()):
                if node.id == self.root_id:
                    continue
                metadata = getattr(node, "metadata", {}) or {}
                if str(metadata.get("bench_session_id") or "") != str(bench_session_id):
                    continue
                parent = self.get_parent(node.id)
                parent_session_id = None if parent is None else ((getattr(parent, "metadata", {}) or {}).get("bench_session_id"))
                if str(parent_session_id or "") != str(bench_session_id):
                    roots_to_capture.append(node.id)
            if roots_to_capture:
                self.closed_bench_sessions = [
                    entry for entry in self.closed_bench_sessions
                    if str(entry["bench_session_id"]) != str(bench_session_id)
                ]
                self.closed_bench_sessions.insert(
                    0,
                    {
                        "bench_session_id": str(bench_session_id),
                        "roots": [self._serialize_subtree(node_id) for node_id in roots_to_capture if self.get_node(node_id) is not None],
                    },
                )
            for node in list(self.nodes.values()):
                if node.id == self.root_id:
                    continue
                metadata = getattr(node, "metadata", {}) or {}
                if str(metadata.get("bench_session_id") or "") != str(bench_session_id):
                    continue
                if node.parent_id is None:
                    continue
                if self.get_node(node.id) is None:
                    continue
                deleted.extend(self.remove_node(node.id))

            if self.get_active_bench_session_id() == str(bench_session_id):
                self.clear_active_bench_session()

            workspace = self._find_bench_workspace()
            if workspace is not None and not workspace.children:
                deleted.extend(self.remove_node(workspace.id))

        return deleted

    def reopen_closed_bench_session(self, bench_session_id: str) -> list[str]:
        restored_roots: list[str] = []
        entry = next(
            (entry for entry in self.closed_bench_sessions if str(entry["bench_session_id"]) == str(bench_session_id)),
            None,
        )
        if entry is None:
            return restored_roots

        workspace = self._ensure_bench_workspace()

        def build(snapshot: dict[str, object], parent_id: str) -> str:
            node = self.create_node(
                str(snapshot["type"]),
                deepcopy(snapshot.get("properties", {})),
                name=snapshot.get("name"),
                metadata=deepcopy(snapshot.get("metadata", {})),
            )
            self.add_node(parent_id, node)
            for child_snapshot in snapshot.get("children", []):
                build(child_snapshot, node.id)
            return node.id

        with self.batch_updates():
            for root_snapshot in entry.get("roots", []):
                restored_roots.append(build(root_snapshot, workspace.id))
            self.set_active_bench_session(str(bench_session_id))
            self.closed_bench_sessions = [
                existing for existing in self.closed_bench_sessions
                if str(existing["bench_session_id"]) != str(bench_session_id)
            ]

        return restored_roots

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

        def clone_subtree(source_node_id: str, target_parent_id: str, index: int | None = None) -> str:
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
                clone_subtree(child_id, cloned.id)
            return cloned.id

        with self.batch_updates():
            forked_id = clone_subtree(node_id, target_parent.id, insert_index)
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

    def get_children(self, node_id: str) -> list[Node]:
        node = self.get_node(node_id)
        if node is None:
            return []
        return [self.nodes[child_id] for child_id in node.children if child_id in self.nodes]

    def _ensure_bench_workspace(self) -> Node:
        existing = self._find_bench_workspace()
        if existing is not None:
            return existing

        workspace = self.create_node(
            "panel",
            {
                "title": self.BENCH_WORKSPACE_TITLE,
                "layout_mode": "free",
                "x": self.BENCH_WORKSPACE_X,
                "y": self.BENCH_WORKSPACE_Y,
                "width": self.BENCH_WORKSPACE_WIDTH,
                "height": self.BENCH_WORKSPACE_HEIGHT,
            },
            metadata={
                "trust": {
                    "trust_level": "mock",
                    "representation_origin": "manual",
                    "warnings": [],
                },
                "provenance": {
                    "representation_origin": "manual",
                    "internal_role": "bench_workspace",
                },
            },
        )
        self.add_node(self.root_id, workspace)
        return workspace

    def ensure_bench_workspace(self) -> Node:
        return self._ensure_bench_workspace()

    def _find_bench_workspace(self) -> Node | None:
        for child in self.get_children(self.root_id):
            if (
                child.type == "panel"
                and child.properties.get("title") == self.BENCH_WORKSPACE_TITLE
                and child.properties.get("layout_mode") == "free"
            ):
                return child
        return None

    def _serialize_subtree(self, node_id: str) -> dict[str, object]:
        node = self.get_node(node_id)
        assert node is not None
        return {
            "type": node.type,
            "name": node.name,
            "properties": deepcopy(node.properties),
            "metadata": deepcopy(getattr(node, "metadata", {}) or {}),
            "children": [self._serialize_subtree(child_id) for child_id in node.children if self.get_node(child_id) is not None],
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
