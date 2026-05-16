from __future__ import annotations

from typing import Any

from core.node import Node


class LayoutModelAPI:
    def __init__(self, model):
        self._model = model

    def get_root_id(self) -> str:
        return self._model.get_root_id()

    def get_scene_metadata(self) -> dict[str, object]:
        return self._model.get_scene_metadata()

    def set_scene_metadata(self, metadata: dict[str, object] | None) -> None:
        self._model.set_scene_metadata(metadata)

    def replace_scene_metadata_and_notify(self, metadata: dict[str, object]) -> None:
        self._model.replace_scene_metadata_and_notify(metadata)

    def get_closed_bench_sessions(self) -> list[dict[str, object]]:
        return self._model.get_closed_bench_sessions()

    def set_closed_bench_sessions(self, entries: list[dict[str, object]]) -> None:
        self._model.set_closed_bench_sessions(entries)

    def iter_nodes(self) -> list[Node]:
        return self._model.iter_nodes()

    def get_children(self, node_id: str) -> list[Node]:
        return self._model.get_children(node_id)

    def get_node(self, node_id: str) -> Node | None:
        return self._model.get_node(node_id)

    def get_parent(self, node_id: str) -> Node | None:
        return self._model.get_parent(node_id)

    def create_node(self, node_type: str, properties: dict, name=None, metadata: dict | None = None) -> Node:
        return self._model.create_node(node_type, properties, name=name, metadata=metadata)

    def add_node(self, parent_id: str, node: Node, index: int | None = None) -> None:
        self._model.add_node(parent_id, node, index=index)

    def remove_node(self, node_id: str) -> list[str]:
        return self._model.remove_node(node_id)

    def serialize_subtree(self, node_id: str) -> dict[str, object]:
        return self._model.serialize_subtree(node_id)

    def batch_updates(self) -> Any:
        return self._model.batch_updates()
