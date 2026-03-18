from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from canvas.interaction_controller import InteractionController
from canvas.resize_handles import ResizeHandles


class CanvasWidget(QWidget):
    def __init__(self, layout_model, selection_state):
        super().__init__()
        self.model = layout_model
        self.selection_state = selection_state
        self.controller = InteractionController(layout_model, selection_state)
        self.resize_handles = ResizeHandles(layout_model)
        self.node_rects: dict[str, QRect] = {}
        self.setMinimumSize(400, 300)

    def paintEvent(self, event):
        del event
        self.node_rects = {}
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#f7f7f7"))
        root_children = self.model.get_children(self.model.root_id)
        if not root_children:
            painter.setPen(QColor("#666666"))
            painter.drawText(
                self.rect(),
                Qt.AlignmentFlag.AlignCenter,
                "Add nodes from templates (coming next)",
            )
            painter.end()
            return

        content_rect = self.rect().adjusted(8, 8, -8, -8)
        self._layout_children(root_children, content_rect, "vertical", painter)
        painter.end()

    def mousePressEvent(self, event):
        point = event.position().toPoint()
        selected_id = None
        for node_id, rect in reversed(list(self.node_rects.items())):
            if rect.contains(point):
                selected_id = node_id
                break
        self.selection_state.set_selection(selected_id)
        super().mousePressEvent(event)

    def apply_template(self, template_dict, parent_id):
        first_created_id = None
        created_ids = []

        def build(template_node, target_parent_id):
            nonlocal first_created_id
            node = self.model.create_node(template_node["type"], {})
            self.model.add_node(target_parent_id, node)
            created_ids.append(node.id)
            if first_created_id is None:
                first_created_id = node.id
            for child_template in template_node.get("children", []):
                build(child_template, node.id)
            return node

        build(template_dict, parent_id)
        assert len(created_ids) == len(set(created_ids)), "Template application created duplicate ids"
        for node_id in created_ids:
            node = self.model.get_node(node_id)
            assert node is not None, f"Template application missing node {node_id}"
            assert node.parent_id is not None, f"Template node missing parent_id: {node_id}"
        if first_created_id is not None:
            self.selection_state.set_selection(first_created_id)
        self.update()

    def _layout_children(self, children, rect: QRect, orientation: str, painter: QPainter):
        if not children:
            return

        count = len(children)
        if orientation == "horizontal":
            base = rect.width() // count if count else rect.width()
            x = rect.x()
            for index, child in enumerate(children):
                width = base if index < count - 1 else rect.right() - x + 1
                child_rect = QRect(x, rect.y(), max(width, 1), rect.height())
                self._draw_node(child, child_rect, painter)
                x += base
        else:
            base = rect.height() // count if count else rect.height()
            y = rect.y()
            for index, child in enumerate(children):
                height = base if index < count - 1 else rect.bottom() - y + 1
                child_rect = QRect(rect.x(), y, rect.width(), max(height, 1))
                self._draw_node(child, child_rect, painter)
                y += base

    def _draw_node(self, node, rect: QRect, painter: QPainter):
        inner = rect.adjusted(6, 6, -6, -6)
        self.node_rects[node.id] = inner

        is_selected = self.selection_state.get_selection() == node.id
        pen = QPen(QColor("#0f766e") if is_selected else QColor("#555555"))
        pen.setWidth(3 if is_selected else 1)
        painter.setPen(pen)
        painter.setBrush(QColor("#ccfbf1") if is_selected else QColor("#ffffff"))
        painter.drawRect(inner)
        painter.setPen(QColor("#111111"))
        painter.drawText(
            inner.adjusted(8, 8, -8, -8),
            Qt.AlignmentFlag.AlignTop | Qt.TextWordWrap,
            f"{node.type}\n{node.id}",
        )

        children = self.model.get_children(node.id)
        if not children:
            return

        content_rect = inner.adjusted(12, 36, -12, -12)
        if content_rect.width() <= 0 or content_rect.height() <= 0:
            return

        orientation = "vertical"
        if node.type == "horizontal":
            orientation = "horizontal"
        elif node.type in {"vertical", "container", "document", "panel", "main", "sidebar"}:
            orientation = "vertical"

        self._layout_children(children, content_rect, orientation, painter)
