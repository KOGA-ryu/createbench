from __future__ import annotations

from engine.constraints import validate_move, validate_resize
from engine.geometry import apply_resize, detect_resize_handle, point_in_rect
from engine.intrinsic_size import get_intrinsic_size
from engine.lock_manager import can_move, can_resize
from engine.snap_engine import resolve_snap


class LayoutEngine:
    """Compute deterministic world-space rects and resolve direct manipulation."""

    def __init__(self, layout_model, grid_size: int = 8):
        self.model = layout_model
        self.grid_size = grid_size
        self.rect_map: dict[str, dict[str, int]] = {}
        self.draw_order: list[str] = []
        self.last_canvas_rect: dict[str, int] | None = None

    SUPPORTED_LAYOUT_ROLES = {
        "document",
        "container",
        "horizontal",
        "vertical",
        "button",
        "text",
        "input",
        "toolbar",
        "sidebar",
        "main",
        "panel",
        "dialog",
        "popup",
        "tool_window",
    }

    def compute_layout(self, root_id, canvas_rect) -> dict[str, dict[str, int]]:
        """Build a rect map for the current tree using one measure/layout pass."""
        if self.model.get_node(root_id) is None:
            raise ValueError(f"Node not found: {root_id}")
        self.rect_map = {}
        self.draw_order = []
        self.last_canvas_rect = dict(canvas_rect)

        root_children = self.model.get_children(root_id)
        child_rects = self._layout_auto_children(root_children, canvas_rect, "vertical", canvas_rect)
        for child in root_children:
            self._compute_node(child, child_rects[child.id], canvas_rect)

        assert len(self.rect_map) == len(set(self.rect_map)), "Rect map contains duplicate node ownership"
        assert len(self.draw_order) == len(set(self.draw_order)), "Draw order contains duplicate node ids"
        return dict(self.rect_map)

    def hit_test(self, point, rect_map=None, draw_order=None) -> str | None:
        """Return the topmost node at a world-space point."""
        active_rect_map = rect_map or self.rect_map
        active_draw_order = draw_order or self.draw_order
        px, py = point
        for node_id in reversed(active_draw_order):
            rect = active_rect_map.get(node_id)
            if rect is not None and point_in_rect(px, py, rect):
                return node_id
        return None

    def get_resize_handle(self, point, node_id, rect_map=None) -> str | None:
        """Resolve which resize handle a world-space point is touching."""
        active_rect_map = rect_map or self.rect_map
        rect = active_rect_map.get(node_id)
        if rect is None:
            return None
        return detect_resize_handle(point, rect)

    def move_node(self, node_id, proposed_x, proposed_y, canvas_rect) -> dict:
        """Resolve a move request without mutating the model directly."""
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

    def resize_node(self, node_id, handle, dx, dy, canvas_rect, base_rect=None) -> dict:
        """Resolve a resize request without mutating the model directly."""
        node = self.model.get_node(node_id)
        if node is None:
            raise ValueError(f"Node not found: {node_id}")
        if node_id == self.model.root_id:
            raise ValueError("Root cannot be resized")
        current_rect = self._ensure_current_rect(node_id, canvas_rect)
        resize_base_rect = dict(base_rect) if base_rect is not None else current_rect
        if not can_resize(node):
            return self._result_from_rect(current_rect, node.properties.get("layout_mode", "free"), blocked=True)

        layout_mode = node.properties.get("layout_mode", "free")
        if layout_mode != "free":
            layout_mode = "free"

        resized = apply_resize(
            resize_base_rect,
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
        resolved = self._preserve_resize_anchor(resize_base_rect, resolved, handle)
        resolved = validate_resize(resolved, node, parent_rect, canvas_rect)
        return self._result_from_rect(resolved, layout_mode)

    def get_node_rect(self, node_id):
        if node_id == self.model.root_id:
            return self.last_canvas_rect
        return self.rect_map.get(node_id)

    def _compute_node(self, node, assigned_rect, canvas_rect):
        """Store the node rect, then recursively lay out any children."""
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
        child_rects = self._layout_auto_children(children, rect, orientation, canvas_rect)

        for child in children:
            child_rect = child_rects[child.id]
            self._compute_node(child, child_rect, canvas_rect)

    def _resolved_free_rect(self, node, parent_rect, canvas_rect):
        """Turn explicit free-layout properties into a validated rect."""
        proposed_rect = {
            "x": int(node.properties.get("x", 0)),
            "y": int(node.properties.get("y", 0)),
            "width": int(node.properties.get("width", 200)),
            "height": int(node.properties.get("height", 100)),
        }
        return validate_move(proposed_rect, node, parent_rect, canvas_rect)

    def _split_rect(self, rect, count: int, orientation: str) -> list[dict[str, int]]:
        """Fallback equal-split policy for node types without intrinsic sizing rules."""
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
        """Map the parent node type to the auto-layout axis it uses."""
        if node.type == "horizontal":
            return "horizontal"
        return "vertical"

    def _layout_auto_children(self, children, parent_rect, orientation: str, canvas_rect):
        """Lay out children using explicit preferred/fill policy without implicit stretching."""
        if not children:
            return {}

        resolved_policies: dict[str, dict[str, object]] = {}
        free_children = {child.id for child in children if child.properties.get("layout_mode", "free") == "free"}
        primary_axis = "height" if orientation == "vertical" else "width"
        primary_policy_key = f"{primary_axis}_policy"
        total_axis = parent_rect[primary_axis]
        fixed_total = 0
        fill_children = []

        for child in children:
            if child.id in free_children:
                continue
            policy = self._resolve_layout_policy(child)
            resolved_policies[child.id] = policy
            if self._is_fill_policy(policy, primary_axis):
                fill_children.append(child)
                continue
            fixed_total += self._resolve_axis_size(child, policy, primary_axis)

        remaining = max(0, total_axis - fixed_total)
        fill_count = len(fill_children)
        fill_share = remaining // fill_count if fill_count else 0
        fill_remainder = remaining % fill_count if fill_count else 0

        cursor_x = parent_rect["x"]
        cursor_y = parent_rect["y"]
        rects = {}
        seen_fill = 0
        for child in children:
            if child.id in free_children:
                rects[child.id] = self._resolved_free_rect(child, parent_rect, canvas_rect)
                continue

            policy = resolved_policies[child.id]

            if orientation == "vertical":
                width = self._resolve_cross_axis_size(child, policy, parent_rect, "width")
                if self._is_fill_policy(policy, "height"):
                    seen_fill += 1
                    height = fill_share + (fill_remainder if seen_fill == fill_count else 0)
                else:
                    height = self._resolve_axis_size(child, policy, "height")
                rects[child.id] = {
                    "x": parent_rect["x"],
                    "y": cursor_y,
                    "width": width,
                    "height": height,
                }
                cursor_y += height
            else:
                height = self._resolve_cross_axis_size(child, policy, parent_rect, "height")
                if self._is_fill_policy(policy, "width"):
                    seen_fill += 1
                    width = fill_share + (fill_remainder if seen_fill == fill_count else 0)
                else:
                    width = self._resolve_axis_size(child, policy, "width")
                rects[child.id] = {
                    "x": cursor_x,
                    "y": parent_rect["y"],
                    "width": width,
                    "height": height,
                }
                cursor_x += width
        return rects

    def _resolve_layout_role(self, node) -> str:
        ui_role = node.properties.get("ui_role")
        if ui_role in self.SUPPORTED_LAYOUT_ROLES:
            return str(ui_role)
        if node.type in self.SUPPORTED_LAYOUT_ROLES:
            return str(node.type)
        return "generic"

    def _resolve_layout_policy(self, node) -> dict[str, object]:
        role = self._resolve_layout_role(node)
        intrinsic = get_intrinsic_size(node) or {}
        properties = node.properties
        preferred_width = int(properties.get("width", intrinsic.get("width", 200)))
        preferred_height = int(properties.get("height", intrinsic.get("height", 100)))

        if role in {"document", "container", "horizontal", "vertical"}:
            preferred_width = int(properties.get("width", intrinsic.get("width", preferred_width)))
            preferred_height = int(properties.get("height", intrinsic.get("height", preferred_height)))
            width_policy = "fill"
            height_policy = "fill"
        elif role == "button":
            preferred_width = max(preferred_width, int(intrinsic.get("width", preferred_width)))
            preferred_height = int(intrinsic.get("height", preferred_height))
            width_policy = "preferred"
            height_policy = "preferred"
        elif role == "text":
            preferred_width = int(properties.get("width", intrinsic.get("width", preferred_width)))
            preferred_height = int(intrinsic.get("height", preferred_height))
            width_policy = "preferred"
            height_policy = "preferred"
        elif role == "input":
            preferred_width = int(properties.get("width", intrinsic.get("width", preferred_width)))
            preferred_height = int(intrinsic.get("height", preferred_height))
            width_policy = "preferred"
            height_policy = "preferred"
        elif role == "toolbar":
            preferred_width = int(properties.get("width", intrinsic.get("width", preferred_width)))
            preferred_height = int(properties.get("height", intrinsic.get("height", preferred_height)))
            width_policy = "fill"
            height_policy = "preferred"
        elif role == "sidebar":
            preferred_width = int(properties.get("width", intrinsic.get("width", preferred_width)))
            preferred_height = int(properties.get("height", intrinsic.get("height", preferred_height)))
            width_policy = "preferred"
            height_policy = "fill"
        elif role == "main":
            preferred_width = int(properties.get("width", intrinsic.get("width", preferred_width)))
            preferred_height = int(properties.get("height", intrinsic.get("height", preferred_height)))
            width_policy = "preferred"
            height_policy = "preferred"
        elif role == "panel":
            preferred_width = int(properties.get("width", intrinsic.get("width", preferred_width)))
            preferred_height = int(properties.get("height", intrinsic.get("height", preferred_height)))
            width_policy = "preferred"
            height_policy = "preferred"
        elif role in {"dialog", "popup", "tool_window"}:
            preferred_width = int(properties.get("width", intrinsic.get("width", preferred_width)))
            preferred_height = int(properties.get("height", intrinsic.get("height", preferred_height)))
            width_policy = "preferred"
            height_policy = "preferred"
        else:
            width_policy = "preferred"
            height_policy = "preferred"

        return {
            "role": role,
            "width_policy": width_policy,
            "height_policy": height_policy,
            "preferred_width": preferred_width,
            "preferred_height": preferred_height,
            "min_width": int(properties.get("min_width", 50)),
            "min_height": int(properties.get("min_height", 30)),
            "max_width": properties.get("max_width"),
            "max_height": properties.get("max_height"),
            "align_x": "left",
            "align_y": "top",
        }

    def _resolve_axis_size(self, child, policy: dict[str, object], axis: str) -> int:
        preferred_key = f"preferred_{axis}"
        min_key = f"min_{axis}"
        max_key = f"max_{axis}"
        value = int(policy[preferred_key])
        minimum = int(policy[min_key])
        maximum = policy[max_key]
        value = max(minimum, value)
        if maximum is not None:
            value = min(value, int(maximum))
        return value

    def _resolve_cross_axis_size(self, child, policy: dict[str, object], parent_rect, axis: str) -> int:
        if self._is_fill_policy(policy, axis):
            return int(parent_rect[axis])
        return self._resolve_axis_size(child, policy, axis)

    def _is_fill_policy(self, policy: dict[str, object], axis: str) -> bool:
        return str(policy[f"{axis}_policy"]) == "fill"

    def _ensure_current_rect(self, node_id, canvas_rect):
        """Recompute layout when cached rects are missing or stale."""
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
        """Normalize engine output for the canvas write-back path."""
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
        """Keep right/bottom anchored handles from drifting the fixed edge."""
        anchored = dict(resolved_rect)
        original_right = original_rect["x"] + original_rect["width"]
        original_bottom = original_rect["y"] + original_rect["height"]
        resolved_right = resolved_rect["x"] + resolved_rect["width"]
        resolved_bottom = resolved_rect["y"] + resolved_rect["height"]
        if handle in {"left", "top_left", "bottom_left"}:
            anchored["x"] = original_right - resolved_rect["width"]
        if handle in {"top", "top_left", "top_right"}:
            anchored["y"] = original_bottom - resolved_rect["height"]
        if handle in {"right", "bottom_right"}:
            anchored["width"] = max(1, resolved_right - original_rect["x"])
            anchored["x"] = original_rect["x"]
        if handle in {"top_right"}:
            anchored["width"] = max(1, resolved_right - original_rect["x"])
            anchored["x"] = original_rect["x"]
        if handle in {"bottom", "bottom_right"}:
            anchored["height"] = max(1, resolved_bottom - original_rect["y"])
            anchored["y"] = original_rect["y"]
        if handle in {"bottom_left"}:
            anchored["height"] = max(1, resolved_bottom - original_rect["y"])
            anchored["y"] = original_rect["y"]
        return anchored

    def _assert_valid_geometry(self, node, rect):
        """Fail fast if the engine emits impossible geometry."""
        min_width = int(node.properties.get("min_width", 1))
        min_height = int(node.properties.get("min_height", 1))
        assert rect["width"] >= min_width, f"Node {node.id} width below minimum"
        assert rect["height"] >= min_height, f"Node {node.id} height below minimum"
        assert rect["width"] > 0, f"Node {node.id} width must be positive"
        assert rect["height"] > 0, f"Node {node.id} height must be positive"
