from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QLineEdit, QWidget

from canvas.interaction_controller import InteractionController
from canvas.resize_handles import ResizeHandles
from core.node_resolution import resolve_node_state
from core.scene_resolution import resolve_scene_state
from engine.layout_engine import LayoutEngine


class CanvasWidget(QWidget):
    """World-space canvas that renders the model and forwards edits to the engine."""

    AUTHORED_CANVAS_WIDTH = 8000
    AUTHORED_CANVAS_HEIGHT = 8000
    WHEEL_PAN_STEP = 64
    SUPPORTED_RENDER_ROLES = {
        "button",
        "text",
        "input",
        "toolbar",
        "sidebar",
        "main",
        "panel",
    }

    def __init__(self, layout_model, selection_state):
        super().__init__()
        self.model = layout_model
        self.selection_state = selection_state
        self.controller = InteractionController(layout_model, selection_state)
        self.resize_handles = ResizeHandles(layout_model)
        self.layout_engine = LayoutEngine(layout_model)
        self.node_rects: dict[str, QRect] = {}
        self.screen_rects: dict[str, QRect] = {}
        self.paint_rects: dict[str, QRect] = {}
        self.engine_rects: dict[str, dict[str, int]] = {}
        self.render_profiles: dict[str, dict[str, object]] = {}
        self.dragging_node_id: str | None = None
        self.drag_offset = QPoint(0, 0)
        self.resizing_node_id: str | None = None
        self.resize_handle: str | None = None
        self.resize_start_point = QPoint(0, 0)
        self.resize_start_rect: dict[str, int] | None = None
        self.handle_rects: dict[tuple[str, str], QRect] = {}
        self.camera_x = 0
        self.camera_y = 0
        self.panning = False
        self.pan_start = QPoint(0, 0)
        self.camera_start_x = 0
        self.camera_start_y = 0
        self.focus_node_id: str | None = None
        self.interaction_message: str | None = None
        self.status_listener = None
        self.geometry_tool = self._build_geometry_tool()
        self.setMinimumSize(400, 300)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.model.subscribe(self._handle_model_changed)
        self.destroyed.connect(lambda _obj=None: self.model.unsubscribe(self._handle_model_changed))
        self.selection_state.subscribe(self._handle_selection_changed)

    def paintEvent(self, event):
        """Render the current tree using engine rects plus the camera offset."""
        del event
        self.node_rects = {}
        self.screen_rects = {}
        self.paint_rects = {}
        self.handle_rects = {}
        self.render_profiles = {}
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

        self.engine_rects = self.layout_engine.compute_layout(
            self.model.root_id, self.authored_canvas_rect()
        )
        active_bench_session_id = self.model.get_active_bench_session_id()
        for node_id in self.layout_engine.draw_order:
            node = self.model.get_node(node_id)
            rect = self.engine_rects.get(node_id)
            if node is None or rect is None:
                continue
            if not self._is_visible_in_active_bench_session(node, active_bench_session_id):
                continue
            self._draw_node(node, self.world_to_screen_rect(rect), painter)
        self._refresh_geometry_tool()
        painter.end()

    def mousePressEvent(self, event):
        """Start pan, resize, selection, or drag based on the clicked target."""
        point = event.position().toPoint()
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = True
            self.pan_start = point
            self.camera_start_x = self.camera_x
            self.camera_start_y = self.camera_y
            return

        world_point = self.screen_to_world_point(point)
        selected_id = self.selection_state.get_selection()
        if selected_id is not None:
            handle = self._hit_handle(selected_id, point)
            if handle is not None:
                node = self.model.get_node(selected_id)
                if node is not None:
                    if self._can_edit_geometry(node):
                        self.resizing_node_id = selected_id
                        self.resize_handle = handle
                        self.resize_start_point = world_point
                        rect = self.engine_rects.get(selected_id)
                        self.resize_start_rect = dict(rect) if rect is not None else None
                    else:
                        self._set_blocked_message_for_node(node)
                return

        selected_id = self.layout_engine.hit_test(
            (world_point.x(), world_point.y()),
            self.engine_rects,
            self.layout_engine.draw_order,
        )
        self.selection_state.set_selection(selected_id)
        if selected_id is not None:
            node = self.model.get_node(selected_id)
            if node is not None:
                if self._can_edit_geometry(node):
                    rect = self.engine_rects.get(selected_id)
                    if rect is not None:
                        self.dragging_node_id = selected_id
                        self.drag_offset = world_point - QPoint(rect["x"], rect["y"])
                else:
                    self._set_blocked_message_for_node(node)
            self.update()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Advance the active interaction in world space."""
        point = event.position().toPoint()
        if self.panning:
            delta = point - self.pan_start
            self._set_camera(self.camera_start_x - delta.x(), self.camera_start_y - delta.y())
            self._notify_view_changed()
            self.update()
            return

        world_point = self.screen_to_world_point(point)
        if self.resizing_node_id is not None:
            node = self.model.get_node(self.resizing_node_id)
            if node is not None:
                dx = world_point.x() - self.resize_start_point.x()
                dy = world_point.y() - self.resize_start_point.y()
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
                    world_point.x() - self.drag_offset.x(),
                    world_point.y() - self.drag_offset.y(),
                    self.authored_canvas_rect(),
                )
                self._apply_geometry_result(node, result)
                self.update()
            return

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Clear transient interaction state after mouse release."""
        if event.button() == Qt.MouseButton.MiddleButton:
            self.panning = False
        self.dragging_node_id = None
        self.resizing_node_id = None
        self.resize_handle = None
        self.resize_start_rect = None
        super().mouseReleaseEvent(event)

    def wheelEvent(self, event):
        delta = event.angleDelta()
        if delta.isNull():
            super().wheelEvent(event)
            return
        step_x = 0
        step_y = 0
        if delta.x():
            step_x = -self.WHEEL_PAN_STEP if delta.x() > 0 else self.WHEEL_PAN_STEP
        if delta.y():
            step_y = -self.WHEEL_PAN_STEP if delta.y() > 0 else self.WHEEL_PAN_STEP
        self._set_camera(self.camera_x + step_x, self.camera_y + step_y)
        self._notify_view_changed()
        self.update()
        event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected()
            event.accept()
            return
        super().keyPressEvent(event)

    def is_canvas_empty(self) -> bool:
        return len(self.model.get_children(self.model.root_id)) == 0

    def focus_selected_node(self):
        """Center the camera on the selected node or subtree."""
        selected_id = self.selection_state.get_selection()
        if selected_id is None or selected_id == self.model.root_id:
            return
        if self.model.get_node(selected_id) is None:
            return
        self.focus_node_id = selected_id
        self._center_camera_on_node(selected_id)
        self._notify_view_changed()
        self.update()

    def clear_focus(self):
        """Reset the view to the default top-left world position."""
        self.focus_node_id = None
        self._set_camera(0, 0)
        self._notify_view_changed()
        self.update()

    def focus_parent(self):
        """Move focus up one parent level and recenter there."""
        if self.focus_node_id is None:
            return
        parent = self.model.get_parent(self.focus_node_id)
        if parent is None or parent.id == self.model.root_id:
            self.focus_node_id = None
            self._set_camera(0, 0)
        else:
            self.focus_node_id = parent.id
            self._center_camera_on_node(parent.id)
        self._notify_view_changed()
        self.update()

    def clear_root_children(self):
        """Remove all top-level content so a scaffold can replace the project."""
        if any(self._subtree_contains_protected(child.id) for child in self.model.get_children(self.model.root_id)):
            self._set_interaction_message("Blocked: protected source-backed content cannot be cleared from the root")
            return
        self.clear_focus()
        with self.model.batch_updates():
            for child in list(self.model.get_children(self.model.root_id)):
                self.model.remove_node(child.id)
        self.selection_state.clear_selection()

    def apply_template(self, template_dict, parent_id=None, replace_root=False):
        """Insert a template using the current empty/root-replace rules."""
        if replace_root:
            if any(self._is_protected(child) for child in self.model.get_children(self.model.root_id)):
                self._set_interaction_message("Blocked: protected source-backed root content cannot be replaced by a template")
                return
        else:
            target_parent_id = parent_id or self.selection_state.get_selection() or self.model.root_id
            if target_parent_id == self.model.root_id and not self._allows_root_mutation():
                self._set_interaction_message("Blocked: source scene root does not allow direct design insertion")
                return
            if target_parent_id != self.model.root_id:
                target_parent = self.model.get_node(target_parent_id)
                if target_parent is not None and self._is_protected(target_parent):
                    self._set_blocked_message_for_node(target_parent)
                    return
        first_created_id = self._apply_template_internal(
            template_dict,
            parent_id=parent_id,
            replace_root=replace_root,
        )
        if first_created_id is not None:
            self.selection_state.set_selection(first_created_id)

    def delete_selected(self):
        """Delete the selected node unless it is the synthetic root."""
        node_id = self.selection_state.get_selection()
        if not node_id or node_id == self.model.root_id:
            return
        node = self.model.get_node(node_id)
        if node is not None and self._is_protected(node):
            self._set_blocked_message_for_node(node)
            return
        if self.focus_node_id == node_id:
            parent = self.model.get_parent(node_id)
            self.focus_node_id = None if parent is None or parent.id == self.model.root_id else parent.id
        parent = self.model.get_parent(node_id)
        self.model.remove_node(node_id)
        if parent:
            self.selection_state.set_selection(parent.id)
        else:
            self.selection_state.clear_selection()
        self._notify_view_changed()

    def add_child_to_selected(self, node_type="panel"):
        """Append a new child to the selected node or the root."""
        parent_id = self.selection_state.get_selection() or self.model.root_id
        if parent_id == self.model.root_id and not self._allows_root_mutation():
            self._set_interaction_message("Blocked: source scene root does not allow direct structural edits")
            return
        if parent_id != self.model.root_id:
            parent = self.model.get_node(parent_id)
            if parent is not None and self._is_protected(parent):
                self._set_blocked_message_for_node(parent)
                return
        node = self.model.create_node(node_type, {})
        self.model.add_node(parent_id, node)
        self.selection_state.set_selection(node.id)

    def create_component_node(self, component_type: str, properties: dict):
        """Create a configured component node under the active parent."""
        parent_id = self.selection_state.get_selection() or self.model.root_id
        if parent_id == self.model.root_id and not self._allows_root_mutation():
            self._set_interaction_message("Blocked: source scene root does not allow direct component creation")
            return None
        if parent_id != self.model.root_id:
            parent = self.model.get_node(parent_id)
            if parent is not None and self._is_protected(parent):
                self._set_blocked_message_for_node(parent)
                return None
        node = self.model.create_node(component_type, properties)
        self.model.add_node(parent_id, node)
        self.selection_state.set_selection(node.id)
        return node

    def _apply_template_internal(self, template_dict, parent_id=None, replace_root=False):
        """Handle empty-canvas init, root replacement, and document flattening."""
        if replace_root:
            self.clear_root_children()

        if self.is_canvas_empty():
            return self._insert_template_node(template_dict, self.model.root_id)

        target_parent_id = parent_id or self.selection_state.get_selection() or self.model.root_id
        if template_dict.get("type") == "document":
            return self._insert_template_children(template_dict.get("children", []), target_parent_id)
        return self._insert_template_node(template_dict, target_parent_id)

    def _insert_template_node(self, template_node, target_parent_id):
        """Create one template node and recurse through its children in order."""
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

    def _draw_node(self, node, screen_rect: QRect, painter: QPainter):
        """Draw a node card and cache both world and screen rects for interaction."""
        world_rect = self.engine_rects[node.id]
        self.node_rects[node.id] = self._rect_to_qrect(world_rect)
        self.screen_rects[node.id] = screen_rect
        profile = self._resolve_render_profile(node)
        self.render_profiles[node.id] = profile
        role = str(profile["render_kind"])
        draw_fn = getattr(self, f"_draw_{role}", self._draw_generic_fallback)
        draw_fn(node, screen_rect, profile, painter)

        is_selected = self.selection_state.get_selection() == node.id
        if is_selected:
            self._draw_selection_overlay(screen_rect, painter, node, profile)
        if node.properties.get("locked"):
            self._draw_lock_indicator(screen_rect, painter, profile)
        self._draw_resolution_badge(node, painter)

    def _resolve_render_role(self, node) -> str:
        ui_role = node.properties.get("ui_role")
        if ui_role in self.SUPPORTED_RENDER_ROLES:
            return str(ui_role)
        if node.type in self.SUPPORTED_RENDER_ROLES:
            return str(node.type)
        return "generic_fallback"

    def _resolve_render_profile(self, node) -> dict[str, object]:
        role = self._resolve_render_role(node)
        profiles = {
            "button": {
                "render_kind": "button",
                "fill_style": "button",
                "show_header": False,
                "show_body": False,
                "show_border": True,
                "show_label": True,
                "content_alignment": "center",
                "padding": 10,
                "corner_radius": 6,
                "border_weight": 1,
                "draw_children_inside": False,
                "overlay_layer": False,
                "selection_style": "outline",
                "lock_indicator": True,
            },
            "text": {
                "render_kind": "text",
                "fill_style": "none",
                "show_header": False,
                "show_body": False,
                "show_border": False,
                "show_label": True,
                "content_alignment": "left",
                "padding": 2,
                "corner_radius": 0,
                "border_weight": 0,
                "draw_children_inside": False,
                "overlay_layer": False,
                "selection_style": "outline",
                "lock_indicator": True,
            },
            "input": {
                "render_kind": "input",
                "fill_style": "input",
                "show_header": False,
                "show_body": False,
                "show_border": True,
                "show_label": True,
                "content_alignment": "left",
                "padding": 8,
                "corner_radius": 4,
                "border_weight": 1,
                "draw_children_inside": False,
                "overlay_layer": False,
                "selection_style": "outline",
                "lock_indicator": True,
            },
            "toolbar": {
                "render_kind": "toolbar",
                "fill_style": "toolbar",
                "show_header": False,
                "show_body": False,
                "show_border": True,
                "show_label": False,
                "content_alignment": "left",
                "padding": 8,
                "corner_radius": 0,
                "border_weight": 1,
                "draw_children_inside": True,
                "overlay_layer": False,
                "selection_style": "outline",
                "lock_indicator": True,
            },
            "sidebar": {
                "render_kind": "sidebar",
                "fill_style": "sidebar",
                "show_header": True,
                "show_body": True,
                "show_border": True,
                "show_label": True,
                "content_alignment": "top",
                "padding": 12,
                "corner_radius": 0,
                "border_weight": 1,
                "draw_children_inside": True,
                "overlay_layer": False,
                "selection_style": "outline",
                "lock_indicator": True,
            },
            "main": {
                "render_kind": "main",
                "fill_style": "main",
                "show_header": True,
                "show_body": True,
                "show_border": True,
                "show_label": True,
                "content_alignment": "top",
                "padding": 12,
                "corner_radius": 0,
                "border_weight": 1,
                "draw_children_inside": True,
                "overlay_layer": False,
                "selection_style": "outline",
                "lock_indicator": True,
            },
            "panel": {
                "render_kind": "panel",
                "fill_style": "panel",
                "show_header": True,
                "show_body": True,
                "show_border": True,
                "show_label": True,
                "content_alignment": "top",
                "padding": 10,
                "corner_radius": 6,
                "border_weight": 1,
                "draw_children_inside": True,
                "overlay_layer": False,
                "selection_style": "outline",
                "lock_indicator": True,
            },
            "generic_fallback": {
                "render_kind": "generic_fallback",
                "fill_style": "generic",
                "show_header": True,
                "show_body": True,
                "show_border": True,
                "show_label": True,
                "content_alignment": "top",
                "padding": 8,
                "corner_radius": 2,
                "border_weight": 1,
                "draw_children_inside": True,
                "overlay_layer": False,
                "selection_style": "outline",
                "lock_indicator": True,
            },
        }
        return dict(profiles[role])

    def _inner_rect(self, screen_rect: QRect, inset: int = 6) -> QRect:
        inner = screen_rect.adjusted(inset, inset, -inset, -inset)
        self.paint_rects[self._current_paint_node_id] = inner
        return inner

    def _draw_button(self, node, screen_rect: QRect, profile: dict[str, object], painter: QPainter):
        self._current_paint_node_id = node.id
        inner = self._inner_rect(screen_rect)
        pen = QPen(QColor("#4b5563"))
        pen.setWidth(int(profile["border_weight"]))
        painter.setPen(pen)
        painter.setBrush(QColor("#f3f4f6"))
        painter.drawRoundedRect(inner, int(profile["corner_radius"]), int(profile["corner_radius"]))
        painter.setPen(QColor("#111111"))
        label = node.properties.get("text") or node.properties.get("title") or "Button"
        painter.drawText(inner, Qt.AlignmentFlag.AlignCenter, str(label))

    def _draw_text(self, node, screen_rect: QRect, profile: dict[str, object], painter: QPainter):
        self._current_paint_node_id = node.id
        inner = self._inner_rect(screen_rect, inset=2)
        painter.setPen(QColor("#111111"))
        label = node.properties.get("text") or node.properties.get("value") or node.properties.get("title") or ""
        painter.drawText(inner, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextWordWrap, str(label))

    def _draw_input(self, node, screen_rect: QRect, profile: dict[str, object], painter: QPainter):
        self._current_paint_node_id = node.id
        inner = self._inner_rect(screen_rect)
        pen = QPen(QColor("#6b7280"))
        pen.setWidth(int(profile["border_weight"]))
        painter.setPen(pen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(inner, int(profile["corner_radius"]), int(profile["corner_radius"]))
        painter.setPen(QColor("#6b7280"))
        label = node.properties.get("value") or node.properties.get("placeholder") or node.properties.get("title") or ""
        painter.drawText(inner.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(label))

    def _draw_toolbar(self, node, screen_rect: QRect, profile: dict[str, object], painter: QPainter):
        self._current_paint_node_id = node.id
        inner = self._inner_rect(screen_rect)
        pen = QPen(QColor("#9ca3af"))
        pen.setWidth(int(profile["border_weight"]))
        painter.setPen(pen)
        painter.setBrush(QColor("#e5e7eb"))
        painter.drawRect(inner)

    def _draw_sidebar(self, node, screen_rect: QRect, profile: dict[str, object], painter: QPainter):
        self._current_paint_node_id = node.id
        inner = self._inner_rect(screen_rect)
        pen = QPen(QColor("#9ca3af"))
        pen.setWidth(int(profile["border_weight"]))
        painter.setPen(pen)
        painter.setBrush(QColor("#f1f5f9"))
        painter.drawRect(inner)
        self._draw_header_label(node, inner, painter)

    def _draw_main(self, node, screen_rect: QRect, profile: dict[str, object], painter: QPainter):
        self._current_paint_node_id = node.id
        inner = self._inner_rect(screen_rect)
        pen = QPen(QColor("#cbd5e1"))
        pen.setWidth(int(profile["border_weight"]))
        painter.setPen(pen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRect(inner)
        self._draw_header_label(node, inner, painter)

    def _draw_panel(self, node, screen_rect: QRect, profile: dict[str, object], painter: QPainter):
        self._current_paint_node_id = node.id
        inner = self._inner_rect(screen_rect)
        pen = QPen(QColor("#94a3b8"))
        pen.setWidth(int(profile["border_weight"]))
        painter.setPen(pen)
        painter.setBrush(QColor("#ffffff"))
        painter.drawRoundedRect(inner, int(profile["corner_radius"]), int(profile["corner_radius"]))
        self._draw_header_label(node, inner, painter)

    def _draw_generic_fallback(self, node, screen_rect: QRect, profile: dict[str, object], painter: QPainter):
        self._current_paint_node_id = node.id
        inner = self._inner_rect(screen_rect)
        pen = QPen(QColor("#6b7280"))
        pen.setWidth(int(profile["border_weight"]))
        pen.setStyle(Qt.PenStyle.DashLine)
        painter.setPen(pen)
        painter.setBrush(QColor("#f8fafc"))
        painter.drawRect(inner)
        painter.setPen(QColor("#334155"))
        label = node.properties.get("title") or f"Unknown: {node.type}"
        painter.drawText(inner.adjusted(8, 8, -8, -8), Qt.AlignmentFlag.AlignTop | Qt.TextWordWrap, str(label))

    def _draw_header_label(self, node, rect: QRect, painter: QPainter):
        header = QRect(rect.x(), rect.y(), rect.width(), min(28, rect.height()))
        painter.fillRect(header, QColor("#eef2f7"))
        painter.setPen(QColor("#111111"))
        label = node.properties.get("title") or node.type
        painter.drawText(header.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(label))

    def _draw_selection_overlay(self, screen_rect: QRect, painter: QPainter, node, profile: dict[str, object]):
        inner = self.paint_rects[node.id]
        pen = QPen(QColor("#0f766e"))
        pen.setWidth(3)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        if profile["render_kind"] == "button":
            painter.drawRoundedRect(inner, int(profile["corner_radius"]), int(profile["corner_radius"]))
        else:
            painter.drawRect(inner)
        self._draw_resize_handles(inner, painter, node.id)

    def _draw_lock_indicator(self, screen_rect: QRect, painter: QPainter, profile: dict[str, object]):
        inner = self.paint_rects[self._current_paint_node_id]
        painter.setPen(QColor("#111111"))
        painter.drawText(
            QRect(inner.right() - 24, inner.top() + 4, 20, 16),
            Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop,
            "L",
        )

    def _resolve_node_badge(self, node):
        resolved = resolve_node_state(node, getattr(self.model, "scene_metadata", {}))
        if resolved["editability"] == "forkable":
            return {"text": "SOURCE", "fill": QColor("#fef3c7"), "pen": QColor("#92400e")}
        if resolved["resolved_mode"] == "bench":
            return {"text": "BENCH", "fill": QColor("#dbeafe"), "pen": QColor("#1d4ed8")}
        if resolved["editability"] == "editable" and resolved["origin_node_id"]:
            return {"text": "FORK", "fill": QColor("#dcfce7"), "pen": QColor("#166534")}
        return None

    def _draw_resolution_badge(self, node, painter: QPainter):
        badge = self._resolve_node_badge(node)
        if badge is None:
            return
        rect = self.paint_rects.get(node.id)
        if rect is None or rect.width() < 72 or rect.height() < 32:
            return
        badge_rect = QRect(rect.right() - 78, rect.top() + 6, 72, 18)
        painter.setPen(QPen(badge["pen"]))
        painter.setBrush(badge["fill"])
        painter.drawRoundedRect(badge_rect, 4, 4)
        painter.setPen(badge["pen"])
        painter.drawText(badge_rect, Qt.AlignmentFlag.AlignCenter, str(badge["text"]))

    def _draw_resize_handles(self, rect: QRect, painter: QPainter, node_id: str):
        """Draw the selected node's clickable screen-space resize handles."""
        node = self.model.get_node(node_id)
        if node is not None and node.properties.get("locked"):
            return
        handle_size = 8
        handles = {
            "top_left": QRect(rect.left(), rect.top(), handle_size, handle_size),
            "top": QRect(rect.center().x() - 4, rect.top(), handle_size, handle_size),
            "top_right": QRect(rect.right() - 4, rect.top(), handle_size, handle_size),
            "left": QRect(rect.left(), rect.center().y() - 4, handle_size, handle_size),
            "right": QRect(rect.right() - 4, rect.center().y() - 4, handle_size, handle_size),
            "bottom_left": QRect(rect.left(), rect.bottom() - 4, handle_size, handle_size),
            "bottom": QRect(rect.center().x() - 4, rect.bottom() - 4, handle_size, handle_size),
            "bottom_right": QRect(rect.right() - 4, rect.bottom() - 4, handle_size, handle_size),
        }
        painter.setPen(QColor("#0f766e"))
        painter.setBrush(QColor("#0f766e"))
        for handle_name, handle_rect in handles.items():
            self.handle_rects[(node_id, handle_name)] = handle_rect
            painter.drawRect(handle_rect)

    def _hit_handle(self, node_id: str, point: QPoint):
        for handle_name in (
            "top_left",
            "top",
            "top_right",
            "left",
            "right",
            "bottom_left",
            "bottom",
            "bottom_right",
        ):
            rect = self.handle_rects.get((node_id, handle_name))
            if rect is not None and rect.contains(point):
                return handle_name
        return None

    def _apply_resize(self, node, dx: int, dy: int):
        """Resolve a resize through the engine and write the result back."""
        if node.properties.get("locked") or self.resize_handle is None:
            return
        result = self.layout_engine.resize_node(
            node.id,
            self.resize_handle,
            dx,
            dy,
            self.authored_canvas_rect(),
            base_rect=self.resize_start_rect,
        )
        self._apply_geometry_result(node, result)

    def _apply_geometry_result(self, node, result: dict):
        """Write engine-resolved geometry back into the node properties."""
        node.properties = dict(node.properties)
        node.properties["layout_mode"] = result["layout_mode"]
        node.properties["x"] = result["x"]
        node.properties["y"] = result["y"]
        node.properties["width"] = result["width"]
        node.properties["height"] = result["height"]
        self.model.notify_subscribers()

    def _rect_to_qrect(self, rect: dict[str, int]) -> QRect:
        return QRect(rect["x"], rect["y"], rect["width"], rect["height"])

    def authored_canvas_rect(self) -> dict[str, int]:
        """Return the current world bounds used by the engine."""
        return {
            "x": 0,
            "y": 0,
            "width": self.AUTHORED_CANVAS_WIDTH,
            "height": self.AUTHORED_CANVAS_HEIGHT,
        }

    def get_viewport_state(self) -> dict[str, object]:
        """Expose camera/focus state for export and tests."""
        return {
            "authored_canvas_rect": self.authored_canvas_rect(),
            "camera": {"x": self.camera_x, "y": self.camera_y},
            "focus_node_id": self.focus_node_id,
            "effective_root_id": self.model.root_id,
        }

    def world_to_screen_rect(self, rect: dict[str, int]) -> QRect:
        """Translate a world rect into the current camera-relative screen rect."""
        return QRect(
            rect["x"] - self.camera_x,
            rect["y"] - self.camera_y,
            rect["width"],
            rect["height"],
        )

    def screen_to_world_point(self, point: QPoint) -> QPoint:
        """Translate a screen point into world coordinates."""
        return QPoint(point.x() + self.camera_x, point.y() + self.camera_y)

    def _build_geometry_tool(self):
        """Build the floating numeric geometry editor for the current selection."""
        panel = QFrame()
        panel.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QGridLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setHorizontalSpacing(6)
        layout.setVerticalSpacing(4)
        self.geometry_title = QLabel("No selection", panel)
        layout.addWidget(self.geometry_title, 0, 0, 1, 4)
        self.geometry_fields: dict[str, QLineEdit] = {}
        for index, (field_name, label_text) in enumerate(
            [("x", "X"), ("y", "Y"), ("width", "W"), ("height", "H")],
            start=1,
        ):
            label = QLabel(label_text, panel)
            edit = QLineEdit(panel)
            edit.setFixedWidth(56)
            edit.editingFinished.connect(self._apply_geometry_overlay_edits)
            layout.addWidget(label, index, 0)
            layout.addWidget(edit, index, 1)
            self.geometry_fields[field_name] = edit
        return panel

    def _handle_selection_changed(self, _selected_id):
        self.interaction_message = None
        node_id = self.selection_state.get_selection()
        if node_id is not None and node_id != self.model.root_id:
            node = self.model.get_node(node_id)
            if node is not None:
                resolved = resolve_node_state(node, getattr(self.model, "scene_metadata", {}))
                if resolved["editability"] == "forkable":
                    self.interaction_message = "Inspect only: use Fork Here or Open In Bench to make an editable copy"
                elif resolved["editability"] != "editable":
                    reason = resolved.get("reason") or "Editing is blocked for this node"
                    self.interaction_message = f"Inspect only: {reason}"
        self._refresh_geometry_tool()
        self._notify_view_changed()
        self.update()

    def _handle_model_changed(self):
        self.engine_rects = {}
        self.render_profiles = {}
        self.interaction_message = None
        self._refresh_geometry_tool()
        self._notify_view_changed()
        self.update()

    def _is_visible_in_active_bench_session(self, node, active_bench_session_id: str | None) -> bool:
        if active_bench_session_id is None:
            return True
        bench_session_id = (getattr(node, "metadata", {}) or {}).get("bench_session_id")
        if bench_session_id is None:
            return True
        return str(bench_session_id) == active_bench_session_id

    def _refresh_geometry_tool(self):
        """Sync the geometry editor with the current selection state."""
        node_id = self.selection_state.get_selection()
        if node_id is None or node_id == self.model.root_id:
            self.geometry_title.setText("No selection")
            for field in self.geometry_fields.values():
                field.setText("")
                field.setEnabled(False)
            return
        node = self.model.get_node(node_id)
        rect = self.engine_rects.get(node_id)
        if node is None:
            return
        if rect is None:
            rect = {
                "x": int(node.properties.get("x", 0)),
                "y": int(node.properties.get("y", 0)),
                "width": int(node.properties.get("width", 200)),
                "height": int(node.properties.get("height", 100)),
            }
        self.geometry_title.setText(node_id)
        self.geometry_fields["x"].setText(str(int(rect["x"])))
        self.geometry_fields["y"].setText(str(int(rect["y"])))
        self.geometry_fields["width"].setText(str(int(rect["width"])))
        self.geometry_fields["height"].setText(str(int(rect["height"])))
        locked = bool(node.properties.get("locked"))
        for field in self.geometry_fields.values():
            field.setEnabled(not locked)

    def _apply_geometry_overlay_edits(self):
        """Commit manual geometry edits from the tool panel into the selected node."""
        node_id = self.selection_state.get_selection()
        if node_id is None or node_id == self.model.root_id:
            return
        node = self.model.get_node(node_id)
        if node is None:
            return
        if not self._can_edit_geometry(node):
            self._set_blocked_message_for_node(node)
            return
        current_rect = self.engine_rects.get(node_id)
        if current_rect is None:
            current_rect = {
                "x": int(node.properties.get("x", 0)),
                "y": int(node.properties.get("y", 0)),
                "width": int(node.properties.get("width", 200)),
                "height": int(node.properties.get("height", 100)),
            }

        values = {
            "x": self._parse_overlay_int("x", current_rect["x"]),
            "y": self._parse_overlay_int("y", current_rect["y"]),
            "width": self._parse_overlay_int("width", current_rect["width"]),
            "height": self._parse_overlay_int("height", current_rect["height"]),
        }
        min_width = int(node.properties.get("min_width", 50))
        min_height = int(node.properties.get("min_height", 30))
        node.properties = dict(node.properties)
        node.properties["layout_mode"] = "free"
        node.properties["x"] = values["x"]
        node.properties["y"] = values["y"]
        node.properties["width"] = max(min_width, values["width"])
        node.properties["height"] = max(min_height, values["height"])
        self.model.notify_subscribers()

    def _parse_overlay_int(self, field_name: str, fallback: int) -> int:
        text = self.geometry_fields[field_name].text().strip()
        try:
            return int(text)
        except ValueError:
            return int(fallback)

    def _center_camera_on_node(self, node_id: str):
        """Center the camera on a node or subtree bounds without changing scale."""
        if not self.engine_rects:
            self.engine_rects = self.layout_engine.compute_layout(
                self.model.root_id, self.authored_canvas_rect()
            )
        bounds = self._node_or_subtree_bounds(node_id)
        if bounds is None:
            return
        self._set_camera(
            bounds["x"] + (bounds["width"] // 2) - (self.width() // 2),
            bounds["y"] + (bounds["height"] // 2) - (self.height() // 2),
        )

    def _node_or_subtree_bounds(self, node_id: str):
        """Compute world bounds for a node and all of its descendants."""
        rects: list[dict[str, int]] = []

        def visit(current_id: str):
            rect = self.engine_rects.get(current_id)
            if rect is not None:
                rects.append(rect)
            current = self.model.get_node(current_id)
            if current is None:
                return
            for child_id in current.children:
                visit(child_id)

        visit(node_id)
        if not rects:
            return None
        min_x = min(rect["x"] for rect in rects)
        min_y = min(rect["y"] for rect in rects)
        max_x = max(rect["x"] + rect["width"] for rect in rects)
        max_y = max(rect["y"] + rect["height"] for rect in rects)
        return {
            "x": min_x,
            "y": min_y,
            "width": max_x - min_x,
            "height": max_y - min_y,
        }

    def get_status_text(self) -> str:
        focus = self.focus_node_id or "ALL"
        scene_resolved = resolve_scene_state(getattr(self.model, "scene_metadata", {}))
        bench_suffix = ""
        if scene_resolved["active_bench_session_id"]:
            bench_suffix = f" | BENCH: {scene_resolved['active_bench_session_id']}"
        message_suffix = ""
        if self.interaction_message:
            message_suffix = f" | NOTE: {self.interaction_message}"
        return (
            f"SNAP: ON | GRID: {self.layout_engine.grid_size} | "
            f"SCENE: {scene_resolved['origin']}/{scene_resolved['trust_level']} | "
            f"MODE: {scene_resolved['resolved_mode']} | FOCUS: {focus}{bench_suffix}{message_suffix}"
        )

    def _notify_view_changed(self):
        if callable(self.status_listener):
            self.status_listener(self.get_status_text())

    def _set_camera(self, x: int, y: int):
        max_x = max(0, self.AUTHORED_CANVAS_WIDTH - self.width())
        max_y = max(0, self.AUTHORED_CANVAS_HEIGHT - self.height())
        self.camera_x = max(0, min(int(x), max_x))
        self.camera_y = max(0, min(int(y), max_y))

    def _can_edit_geometry(self, node) -> bool:
        return resolve_node_state(node, getattr(self.model, "scene_metadata", {}))["editability"] == "editable"

    def _is_protected(self, node) -> bool:
        return resolve_node_state(node, getattr(self.model, "scene_metadata", {}))["editability"] != "editable"

    def _subtree_contains_protected(self, node_id: str) -> bool:
        node = self.model.get_node(node_id)
        if node is None:
            return False
        if self._is_protected(node):
            return True
        return any(self._subtree_contains_protected(child_id) for child_id in node.children)

    def _allows_root_mutation(self) -> bool:
        scene_resolved = resolve_scene_state(getattr(self.model, "scene_metadata", {}))
        return scene_resolved["resolved_mode"] == "design"

    def _set_interaction_message(self, message: str) -> None:
        self.interaction_message = str(message)
        self._notify_view_changed()
        self.update()

    def _set_blocked_message_for_node(self, node) -> None:
        resolved = resolve_node_state(node, getattr(self.model, "scene_metadata", {}))
        reason = resolved.get("reason") or "Editing is blocked for this node"
        self._set_interaction_message(f"Blocked: {reason}")
