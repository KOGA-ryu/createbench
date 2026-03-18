from __future__ import annotations

from typing import Callable, Optional


class SelectionState:
    def __init__(self, layout_model):
        self.model = layout_model
        self.selected_id: Optional[str] = None
        self.subscribers: list[Callable[[Optional[str]], None]] = []

    def set_selection(self, node_id: Optional[str]):
        if node_id is not None and self.model.get_node(node_id) is None:
            self.selected_id = None
        else:
            self.selected_id = node_id
        self.notify_subscribers()

    def get_selection(self) -> Optional[str]:
        return self.selected_id

    def clear_selection(self):
        self.selected_id = None
        self.notify_subscribers()

    def subscribe(self, callback):
        self.subscribers.append(callback)

    def notify_subscribers(self):
        for callback in self.subscribers:
            callback(self.selected_id)

    def handle_node_deleted(self, node_id: str):
        if node_id != self.selected_id:
            return

        if self.model.get_node(node_id) is None:
            self.clear_selection()
            return

        parent = self.model.get_parent(node_id)
        if parent is not None:
            self.set_selection(parent.id)
        else:
            self.clear_selection()
