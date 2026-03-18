from __future__ import annotations

from PySide6.QtCore import QRect, QPoint, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QWidget

from canvas.interaction_controller import InteractionController
from canvas.resize_handles import ResizeHandles
from engine.layout_engine import LayoutEngine


class CanvasWidget(QWidget):
    def __init__(self, layout_model, selection_state):
        super().__init__()
        self.model = layout_model
        self.selection_state = selection_state
        self.controller = InteractionController(layout_model, selection_state)
        self.resize_handles = ResizeHandles(layout_model)
        self.layout_engine = LayoutEngine(layout_model)
        self.node_rects: dict[str, QRect] = {}
        self.paint_rects: dict[str, QRect] = {}
        self.engine_rects: dict[str, dict[str, int]] = {}
        self.dragging_node_id: str | None = None
        self.drag_offset = QPoint(0, 0)
        self.resizing_node_id: str | None = None
        self.resize_handle: str | None = None
        self.resize_start_point = QPoint(0, 0)
        self.handle_rects: dict[tuple[str, str], QRect] = {}
        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

    def paintEvent(self, event):
        del event
        self.node_rects = {}
        self.paint_rects = {}
        self.handle_rects = {}
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
        canvas_rect = self._qrect_to_rect(content_rect)
        self.engine_rects = self.layout_engine.compute_layout(self.model.root_id, canvas_rect)
        for node_id in self.layout_engine.draw_order:
            node = self.model.get_node(node_id)
            rect = self.engine_rects.get(node_id)
            if node is None or rect is None:
                continue
            self._draw_node(node, self._rect_to_qrect(rect), painter)
        painter.end()

    def mousePressEvent(self, event):
        point = event.position().toPoint()
        selected_id = self.selection_state.get_selection()
        if selected_id is not None:
            handle = self._hit_handle(selected_id, point)
            if handle is not None:
                node = self.model.get_node(selected_id)
                if node is not None and not node.properties.get("locked"):
                    self.resizing_node_id = selected_id
                    self.resize_handle = handle
                    self.resize_start_point = point
                return

        selected_id = self.layout_engine.hit_test((point.x(), point.y()), self.engine_rects, self.layout_engine.draw_order)
        self.selection_state.set_selection(selected_id)
        if selected_id is not None:
            node = self.model.get_node(selected_id)
            if node is not None and not node.properties.get("locked"):
                rect = self.engine_rects.get(selected_id)
                if rect is not None:
                    self.dragging_node_id = selected_id
                    self.drag_offset = point - QPoint(rect["x"], rect["y"])
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        point = event.position().toPoint()
        if self.resizing_node_id is not None:
            node = self.model.get_node(self.resizing_node_id)
            if node is not None:
                dx = point.x() - self.resize_start_point.x()
                dy = point.y() - self.resize_start_point.y()
                self._apply_resize(node, dx, dy)
                self.update()
            return

        if self.dragging_node_id is not None:
            node = self.model.get_node(self.dragging_node_id)
            if node is not None:
                if node.properties.get("locked"):
                    return
                result = self.layout_engine.move_node(
                    self.dragging_node_id,
                    point.x() - self.drag_offset.x(),
                    point.y() - self.drag_offset.y(),
                    self._qrect_to_rect(self.rect().adjusted(8, 8, -8, -8)),
                )
                self._apply_geometry_result(node, result)
                self.update()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        self.dragging_node_id = None
        self.resizing_node_id = None
        self.resize_handle = None
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
            event.accept()
            return
        super().keyPressEvent(event)

    def is_canvas_empty(self) -> bool:
        return len(self.model.get_children(self.model.root_id)) == 0

    def clear_root_children(self):
        for child in list(self.model.get_children(self.model.root_id)):
            self.model.remove_node(child.id)
        self.selection_state.clear_selection()
        self.update()

    def apply_template(self, template_dict, parent_id=None, replace_root=False):
        first_created_id = self._apply_template_internal(
            template_dict,
            parent_id=parent_id,
            replace_root=replace_root,
        )
        if first_created_id is not None:
            self.selection_state.set_selection(first_created_id)
        self.update()

    def delete_selected(self):
        node_id = self.selection_state.get_selection()
        if not node_id or node_id == self.model.root_id:
            return
        parent = self.model.get_parent(node_id)
        self.model.remove_node(node_id)
        if parent:
            self.selection_state.set_selection(parent.id)
        else:
            self.selection_state.clear_selection()
        self.update()

    def add_child_to_selected(self, node_type="panel"):
        parent_id = self.selection_state.get_selection() or self.model.root_id
        node = self.model.create_node(node_type, {})
        self.model.add_node(parent_id, node)
        self.selection_state.set_selection(node.id)
        self.update()

    def create_component_node(self, component_type: str, properties: dict):
        parent_id = self.selection_state.get_selection() or self.model.root_id
        node = self.model.create_node(component_type, properties)
        self.model.add_node(parent_id, node)
        self.selection_state.set_selection(node.id)
        self.update()
        return node

    def _apply_template_internal(self, template_dict, parent_id=None, replace_root=False):
        if replace_root:
            self.clear_root_children()

        if self.is_canvas_empty():
            return self._insert_template_node(template_dict, self.model.root_id)

        target_parent_id = parent_id or self.selection_state.get_selection() or self.model.root_id
        if template_dict.get("type") == "document":
            return self._insert_template_children(template_dict.get("children", []), target_parent_id)
        return self._insert_template_node(template_dict, target_parent_id)

    def _insert_template_node(self, template_node, target_parent_id):
        properties = dict(template_node.get("properties", {}))
        node = self.model.create_node(template_node["type"], properties)
        self.model.add_node(target_parent_id, node)
        first_created_id = node.id
        for child_template in template_node.get("children", []):
            self._insert_template_node(child_template, node.id)
        return first_created_id

    def _insert_template_children(self, template_children, target_parent_id):
        first_created_id = None
        for child_template in template_children:
            created_id = self._insert_template_node(child_template, target_parent_id)
            if first_created_id is None:
                first_created_id = created_id
        return first_created_id

    def _draw_node(self, node, rect: QRect, painter: QPainter):
        inner = rect.adjusted(6, 6, -6, -6)
        self.node_rects[node.id] = rect
        self.paint_rects[node.id] = inner

        is_selected = self.selection_state.get_selection() == node.id
        pen = QPen(QColor("#0f766e") if is_selected else QColor("#555555"))
        pen.setWidth(3 if is_selected else 1)
        if node.properties.get("locked"):
            pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QColor("#ccfbf1") if is_selected else QColor("#ffffff"))
        painter.drawRect(inner)
        painter.setPen(QColor("#111111"))
        title = node.properties.get("title") or node.type
        description = node.properties.get("description") or ""
        text = f"{title}\n{node.id}"
        if description:
            text += f"\n{description}"
        painter.drawText(
            inner.adjusted(8, 8, -8, -8),
            Qt.AlignmentFlag.AlignTop | Qt.TextWordWrap,
            text,
        )

        if is_selected:
            self._draw_resize_handles(inner, painter, node.id)
        if node.properties.get("locked"):
            painter.setPen(QColor("#111111"))
            painter.drawText(
                QRect(inner.right() - 24, inner.top() + 4, 20, 16),
                Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
                "L",
            )

    def _draw_resize_handles(self, rect: QRect, painter: QPainter, node_id: str):
        node = self.model.get_node(node_id)
        if node is not None and node.properties.get("locked"):
            return
        handle_size = 8
        handles = {
            "right": QRect(rect.right() - 4, rect.center().y() - 4, handle_size, handle_size),
            "bottom": QRect(rect.center().x() - 4, rect.bottom() - 4, handle_size, handle_size),
            "bottom_right": QRect(rect.right() - 4, rect.bottom() - 4, handle_size, handle_size),
        }
        painter.setPen(QColor("#0f766e"))
        painter.setBrush(QColor("#0f766e"))
        for handle_name, handle_rect in handles.items():
            self.handle_rects[(node_id, handle_name)] = handle_rect
            painter.drawRect(handle_rect)

    def _hit_handle(self, node_id: str, point: QPoint):
        for handle_name in ("right", "bottom", "bottom_right"):
            rect = self.handle_rects.get((node_id, handle_name))
            if rect is not None and rect.contains(point):
                return handle_name
        return None

    def _apply_resize(self, node, dx: int, dy: int):
        if node.properties.get("locked") or self.resize_handle is None:
            return
        result = self.layout_engine.resize_node(
            node.id,
            self.resize_handle,
            dx,
            dy,
            self._qrect_to_rect(self.rect().adjusted(8, 8, -8, -8)),
        )
        self._apply_geometry_result(node, result)

    def _apply_geometry_result(self, node, result: dict):
        node.properties = dict(node.properties)
        node.properties["layout_mode"] = result["layout_mode"]
        node.properties["x"] = result["x"]
        node.properties["y"] = result["y"]
        node.properties["width"] = result["width"]
        node.properties["height"] = result["height"]

    def _qrect_to_rect(self, rect: QRect) -> dict[str, int]:
        return {
            "x": rect.x(),
            "y": rect.y(),
            "width": rect.width(),
            "height": rect.height(),
        }

    def _rect_to_qrect(self, rect: dict[str, int]) -> QRect:
        return QRect(rect["x"], rect["y"], rect["width"], rect["height"])
