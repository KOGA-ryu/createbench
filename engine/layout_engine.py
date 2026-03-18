from __future__ import annotations

from engine.constraints import validate_move, validate_resize
from engine.geometry import apply_resize, detect_resize_handle, point_in_rect
from engine.lock_manager import can_move, can_resize
from engine.snap_engine import resolve_snap


class LayoutEngine:
    def __init__(self, layout_model, grid_size: int = 8):
        self.model = layout_model
        self.grid_size = grid_size
        self.rect_map: dict[str, dict[str, int]] = {}
        self.draw_order: list[str] = []
        self.last_canvas_rect: dict[str, int] | None = None

    def compute_layout(self, root_id, canvas_rect) -> dict[str, dict[str, int]]:
        if self.model.get_node(root_id) is None:
            raise ValueError(f"Node not found: {root_id}")
        self.rect_map = {}
        self.draw_order = []
        self.last_canvas_rect = dict(canvas_rect)

        root_children = self.model.get_children(root_id)
        auto_children = [
            child for child in root_children if child.properties.get("layout_mode", "free") != "free"
        ]
        auto_rects = self._split_rect(canvas_rect, len(auto_children), "vertical")

        auto_index = 0
        for child in root_children:
            if child.properties.get("layout_mode", "free") == "free":
                rect = self._resolved_free_rect(child, None, canvas_rect)
            else:
                rect = auto_rects[auto_index]
                auto_index += 1
            self._compute_node(child, rect, canvas_rect)

        assert len(self.rect_map) == len(set(self.rect_map)), "Rect map contains duplicate node ownership"
        assert len(self.draw_order) == len(set(self.draw_order)), "Draw order contains duplicate node ids"
        return dict(self.rect_map)

    def hit_test(self, point, rect_map=None, draw_order=None) -> str | None:
        active_rect_map = rect_map or self.rect_map
        active_draw_order = draw_order or self.draw_order
        px, py = point
        for node_id in reversed(active_draw_order):
            rect = active_rect_map.get(node_id)
            if rect is not None and point_in_rect(px, py, rect):
                return node_id
        return None

    def get_resize_handle(self, point, node_id, rect_map=None) -> str | None:
        active_rect_map = rect_map or self.rect_map
        rect = active_rect_map.get(node_id)
        if rect is None:
            return None
        return detect_resize_handle(point, rect)

    def move_node(self, node_id, proposed_x, proposed_y, canvas_rect) -> dict:
        node = self.model.get_node(node_id)
        if node is None:
            raise ValueError(f"Node not found: {node_id}")
        if node_id == self.model.root_id:
            raise ValueError("Root cannot be moved")
        current_rect = self._ensure_current_rect(node_id, canvas_rect)
        if not can_move(node):
            return self._result_from_rect(current_rect, node.properties.get("layout_mode", "free"), blocked=True)

        layout_mode = node.properties.get("layout_mode", "free")
        if layout_mode != "free":
            layout_mode = "free"

        proposed_rect = {
            "x": int(proposed_x),
            "y": int(proposed_y),
            "width": current_rect["width"],
            "height": current_rect["height"],
        }
        parent_rect = self._parent_rect(node, canvas_rect)
        sibling_rects = self._sibling_rects(node)
        resolved = validate_move(proposed_rect, node, parent_rect, canvas_rect)
        resolved = resolve_snap(resolved, parent_rect, sibling_rects, grid_size=self.grid_size)
        resolved = validate_move(resolved, node, parent_rect, canvas_rect)
        return self._result_from_rect(resolved, layout_mode)

    def resize_node(self, node_id, handle, dx, dy, canvas_rect) -> dict:
        node = self.model.get_node(node_id)
        if node is None:
            raise ValueError(f"Node not found: {node_id}")
        if node_id == self.model.root_id:
            raise ValueError("Root cannot be resized")
        current_rect = self._ensure_current_rect(node_id, canvas_rect)
        if not can_resize(node):
            return self._result_from_rect(current_rect, node.properties.get("layout_mode", "free"), blocked=True)

        layout_mode = node.properties.get("layout_mode", "free")
        if layout_mode != "free":
            layout_mode = "free"

        resized = apply_resize(
            current_rect,
            handle,
            dx,
            dy,
            node.properties.get("min_width", 50),
            node.properties.get("min_height", 30),
            node.properties.get("max_width"),
            node.properties.get("max_height"),
        )
        parent_rect = self._parent_rect(node, canvas_rect)
        sibling_rects = self._sibling_rects(node)
        resolved = validate_resize(resized, node, parent_rect, canvas_rect)
        resolved = resolve_snap(resolved, parent_rect, sibling_rects, grid_size=self.grid_size)
        resolved = self._preserve_resize_anchor(current_rect, resolved, handle)
        resolved = validate_resize(resolved, node, parent_rect, canvas_rect)
        return self._result_from_rect(resolved, layout_mode)

    def get_node_rect(self, node_id):
        if node_id == self.model.root_id:
            return self.last_canvas_rect
        return self.rect_map.get(node_id)

    def _compute_node(self, node, assigned_rect, canvas_rect):
        if node.properties.get("layout_mode", "free") == "free":
            rect = self._resolved_free_rect(node, assigned_rect, canvas_rect)
        else:
            rect = dict(assigned_rect)

        self._assert_valid_geometry(node, rect)
        self.rect_map[node.id] = rect
        self.draw_order.append(node.id)

        children = self.model.get_children(node.id)
        if not children:
            return

        orientation = self._orientation_for(node)
        auto_children = [child for child in children if child.properties.get("layout_mode", "free") != "free"]
        auto_rects = self._split_rect(rect, len(auto_children), orientation)

        auto_index = 0
        for child in children:
            if child.properties.get("layout_mode", "free") == "free":
                child_rect = self._resolved_free_rect(child, rect, canvas_rect)
            else:
                child_rect = auto_rects[auto_index]
                auto_index += 1
            self._compute_node(child, child_rect, canvas_rect)

    def _resolved_free_rect(self, node, parent_rect, canvas_rect):
        proposed_rect = {
            "x": int(node.properties.get("x", 0)),
            "y": int(node.properties.get("y", 0)),
            "width": int(node.properties.get("width", 200)),
            "height": int(node.properties.get("height", 100)),
        }
        return validate_move(proposed_rect, node, parent_rect, canvas_rect)

    def _split_rect(self, rect, count: int, orientation: str) -> list[dict[str, int]]:
        if count <= 0:
            return []

        pieces: list[dict[str, int]] = []
        if orientation == "horizontal":
            base = rect["width"] // count if count else rect["width"]
            x = rect["x"]
            for index in range(count):
                width = base if index < count - 1 else rect["x"] + rect["width"] - x
                pieces.append(
                    {
                        "x": x,
                        "y": rect["y"],
                        "width": max(width, 1),
                        "height": rect["height"],
                    }
                )
                x += base
            return pieces

        base = rect["height"] // count if count else rect["height"]
        y = rect["y"]
        for index in range(count):
            height = base if index < count - 1 else rect["y"] + rect["height"] - y
            pieces.append(
                {
                    "x": rect["x"],
                    "y": y,
                    "width": rect["width"],
                    "height": max(height, 1),
                }
            )
            y += base
        return pieces

    def _orientation_for(self, node) -> str:
        if node.type == "horizontal":
            return "horizontal"
        return "vertical"

    def _ensure_current_rect(self, node_id, canvas_rect):
        if self.model.get_node(node_id) is None:
            raise ValueError(f"Node not found: {node_id}")
        if self.last_canvas_rect != canvas_rect or node_id not in self.rect_map:
            self.compute_layout(self.model.root_id, canvas_rect)
        rect = self.rect_map.get(node_id)
        if rect is None:
            raise ValueError(f"No rect available for node: {node_id}")
        return rect

    def _parent_rect(self, node, canvas_rect):
        if node.parent_id in (None, self.model.root_id):
            return None
        return self.rect_map.get(node.parent_id) or self._ensure_current_rect(node.parent_id, canvas_rect)

    def _sibling_rects(self, node):
        if node.parent_id is None:
            return []
        parent = self.model.get_node(node.parent_id)
        if parent is None:
            return []
        rects = []
        for sibling_id in parent.children:
            if sibling_id == node.id:
                continue
            rect = self.rect_map.get(sibling_id)
            if rect is not None:
                rects.append(rect)
        return rects

    def _result_from_rect(self, rect, layout_mode, blocked: bool = False):
        if rect["width"] <= 0 or rect["height"] <= 0:
            raise AssertionError("Engine emitted non-positive geometry")
        return {
            "x": rect["x"],
            "y": rect["y"],
            "width": rect["width"],
            "height": rect["height"],
            "layout_mode": layout_mode,
            "blocked": blocked,
        }

    def _preserve_resize_anchor(self, original_rect, resolved_rect, handle):
        anchored = dict(resolved_rect)
        if handle in {"right", "bottom_right"}:
            anchored["width"] = max(1, resolved_rect["x"] + resolved_rect["width"] - original_rect["x"])
            anchored["x"] = original_rect["x"]
        if handle in {"bottom", "bottom_right"}:
            anchored["height"] = max(1, resolved_rect["y"] + resolved_rect["height"] - original_rect["y"])
            anchored["y"] = original_rect["y"]
        return anchored

    def _assert_valid_geometry(self, node, rect):
        min_width = int(node.properties.get("min_width", 1))
        min_height = int(node.properties.get("min_height", 1))
        assert rect["width"] >= min_width, f"Node {node.id} width below minimum"
        assert rect["height"] >= min_height, f"Node {node.id} height below minimum"
        assert rect["width"] > 0, f"Node {node.id} width must be positive"
        assert rect["height"] > 0, f"Node {node.id} height must be positive"
