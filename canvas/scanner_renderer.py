from __future__ import annotations

from PySide6.QtCore import QRect, Qt
from PySide6.QtGui import QColor, QPainter, QPen


class ScannerRenderer:
    def __init__(self, canvas):
        self.canvas = canvas
        self.bg = QColor("#f8fafc")
        self.panel = QColor("#ffffff")
        self.panel_alt = QColor("#f1f5f9")
        self.border = QColor("#cbd5e1")
        self.border_strong = QColor("#94a3b8")
        self.header_fill = QColor("#e2e8f0")
        self.header_fill_alt = QColor("#eef2ff")
        self.text = QColor("#0f172a")
        self.text_soft = QColor("#64748b")
        self.text_mid = QColor("#334155")
        self.accent = QColor("#2563eb")
        self.accent_fill = QColor("#dbeafe")
        self.good = QColor("#22c55e")
        self.warn_fill = QColor("#eff6ff")

    def _child_nodes_by_symbol(self, node) -> dict[str, object]:
        children: dict[str, object] = {}
        model = self.canvas.model
        for child_id in getattr(node, "children", []):
            child = model.get_node(child_id)
            if child is None:
                continue
            symbol = str(((getattr(child, "metadata", {}) or {}).get("source", {}) or {}).get("symbol") or "")
            if symbol:
                children[symbol] = child
        return children

    def _source_symbol(self, node) -> str:
        return str(((getattr(node, "metadata", {}) or {}).get("source", {}) or {}).get("symbol") or "")

    def _render_hints(self, node) -> dict[str, object]:
        metadata = getattr(node, "metadata", {}) or {}
        return metadata.get("render_hints", {}) or {}

    def _raw_provider_data(self, node) -> dict[str, object]:
        metadata = getattr(node, "metadata", {}) or {}
        raw = metadata.get("raw", {}) or {}
        return raw.get("provider_data", {}) or {}

    def _is_visible(self, node) -> bool:
        if node is None:
            return True
        return self._render_hints(node).get("visible") is not False

    def _is_enabled(self, node) -> bool:
        if node is None:
            return True
        return self._render_hints(node).get("enabled") is not False

    def _child_nodes(self, node) -> list[object]:
        children: list[object] = []
        model = self.canvas.model
        for child_id in getattr(node, "children", []):
            child = model.get_node(child_id)
            if child is not None:
                children.append(child)
        return children

    def _sorted_children(self, node) -> list[object]:
        def key(child):
            return (
                int(child.properties.get("y", 0) or 0),
                int(child.properties.get("x", 0) or 0),
                str(((getattr(child, "metadata", {}) or {}).get("source", {}) or {}).get("symbol") or child.id),
            )

        return sorted(self._child_nodes(node), key=key)

    def _node_text(self, node, fallback: str = "") -> str:
        if node is None:
            return fallback
        render_hints = self._render_hints(node)
        return str(
            node.properties.get("text")
            or node.properties.get("value")
            or node.properties.get("placeholder")
            or node.properties.get("title")
            or render_hints.get("text")
            or render_hints.get("placeholder")
            or render_hints.get("title")
            or fallback
        )

    def _pretty_key(self, text: str) -> str:
        if not text:
            return ""
        return text.replace("field_inputs_", "").replace("_input", "").replace("_", " ").strip().title()

    def _draw_surface(
        self,
        painter: QPainter,
        rect: QRect,
        *,
        fill: QColor | None = None,
        border: QColor | None = None,
        radius: int = 6,
    ):
        painter.setPen(QPen(border or self.border, 1))
        painter.setBrush(fill or self.panel)
        painter.drawRoundedRect(rect, radius, radius)

    def _draw_section_shell(self, node, inner: QRect, painter: QPainter, *, fill: QColor | None = None):
        self._draw_surface(painter, inner, fill=fill or self.bg, border=self.border_strong, radius=6)
        self.canvas._draw_header_label(node, inner, painter)
        return inner.adjusted(10, 38, -10, -10)

    def _draw_card(
        self,
        painter: QPainter,
        rect: QRect,
        *,
        title: str,
        fill: QColor | None = None,
        header_fill: QColor | None = None,
        node=None,
    ):
        card_fill = fill or self.panel
        card_border = self.border
        if node is not None and not self._is_visible(node):
            card_fill = self.panel_alt
        elif node is not None and not self._is_enabled(node):
            card_fill = QColor("#f8fafc")
        self._draw_surface(painter, rect, fill=card_fill, border=card_border, radius=5)
        header = QRect(rect.x(), rect.y(), rect.width(), min(26, rect.height()))
        painter.fillRect(header, header_fill or self.header_fill)
        painter.setPen(self.text)
        painter.drawText(header.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, title)
        if node is not None and not self._is_visible(node):
            tag = QRect(header.right() - 72, header.y() + 4, 64, max(16, header.height() - 8))
            self._draw_surface(painter, tag, fill=self.panel, border=self.border, radius=4)
            painter.setPen(self.text_soft)
            painter.drawText(tag, Qt.AlignmentFlag.AlignCenter, "Hidden")
        elif node is not None and not self._is_enabled(node):
            tag = QRect(header.right() - 78, header.y() + 4, 70, max(16, header.height() - 8))
            self._draw_surface(painter, tag, fill=self.panel, border=self.border, radius=4)
            painter.setPen(self.text_soft)
            painter.drawText(tag, Qt.AlignmentFlag.AlignCenter, "Disabled")
        return rect.adjusted(10, 32, -10, -10)

    def _draw_chip_row(self, painter: QPainter, rect: QRect, labels: list[str]):
        chip_x = rect.x()
        chip_y = rect.y()
        chip_h = max(18, rect.height())
        for text in labels:
            width = max(46, min(92, 18 + (len(text) * 7)))
            chip = QRect(chip_x, chip_y, width, chip_h)
            if chip.right() > rect.right():
                break
            self._draw_surface(painter, chip, fill=self.panel, border=self.border, radius=4)
            painter.setPen(self.text_mid)
            painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, text)
            chip_x += width + 6

    def _draw_field(self, painter: QPainter, rect: QRect, *, label: str, value: str):
        label_rect = QRect(rect.x(), rect.y(), rect.width(), 14)
        field_rect = QRect(rect.x(), rect.y() + 16, rect.width(), max(24, rect.height() - 16))
        painter.setPen(self.text_soft)
        painter.drawText(label_rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label)
        self._draw_surface(painter, field_rect, fill=self.panel, border=self.border, radius=4)
        painter.setPen(self.text)
        painter.drawText(field_rect.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, value)

    def _draw_button(self, painter: QPainter, rect: QRect, *, label: str, emphasized: bool = False):
        self._draw_surface(
            painter,
            rect,
            fill=self.accent_fill if emphasized else self.panel_alt,
            border=self.accent if emphasized else self.border_strong,
            radius=4,
        )
        painter.setPen(QColor("#1e3a8a") if emphasized else self.text_mid)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_state_button(self, painter: QPainter, rect: QRect, *, label: str, node=None, emphasized: bool = False):
        enabled = self._is_enabled(node)
        fill = self.accent_fill if emphasized and enabled else (self.panel_alt if enabled else QColor("#f8fafc"))
        border = self.accent if emphasized and enabled else (self.border_strong if enabled else self.border)
        text_color = QColor("#1e3a8a") if emphasized and enabled else (self.text_mid if enabled else self.text_soft)
        self._draw_surface(painter, rect, fill=fill, border=border, radius=4)
        painter.setPen(text_color)
        painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, label)

    def _group_rows(self, node) -> list[list[object]]:
        rows: list[list[object]] = []
        for child in self._sorted_children(node):
            y = int(child.properties.get("y", 0) or 0)
            if not rows:
                rows.append([child])
                continue
            last = rows[-1]
            last_y = int(last[0].properties.get("y", 0) or 0)
            if abs(y - last_y) <= 18:
                last.append(child)
            else:
                rows.append([child])
        for row in rows:
            row.sort(key=lambda child: int(child.properties.get("x", 0) or 0))
        return rows

    def _profile_form_specs(self, node) -> list[tuple[str, str, str]]:
        children = self._child_nodes_by_symbol(node)
        specs: list[tuple[str, str, str]] = []
        ordered_symbols = [
            "name_input",
            "field_inputs_price_min",
            "field_inputs_price_max",
            "field_inputs_percent_change_min",
            "field_inputs_relative_volume_min",
            "field_inputs_volume_min",
            "field_inputs_float_max",
            "field_inputs_float_turnover_min",
            "news_required_input",
            "field_inputs_news_lookback_minutes",
            "field_inputs_scan_limit",
            "field_inputs_universe_file",
        ]
        for symbol in ordered_symbols:
            child = children.get(symbol)
            if child is None:
                continue
            if symbol == "news_required_input":
                specs.append(("checkbox", "News Required", self._node_text(child, "news_required")))
            else:
                specs.append(("field", self._pretty_key(symbol), self._node_text(child, self._pretty_key(symbol))))
        return specs

    def _results_headers(self, node) -> list[str]:
        raw = self._raw_provider_data(node)
        headers = (raw.get("column_headers") or [])[:4]
        return [str(header) for header in headers if str(header).strip()]

    def _text_area_summary(self, node, default: str) -> str:
        render_hints = self._render_hints(node)
        placeholder = str(render_hints.get("placeholder") or "").strip()
        text = str(render_hints.get("text") or "").strip()
        if placeholder:
            return placeholder
        if text:
            return text
        return default

    def draw_profile_sidebar(self, node, inner: QRect, painter: QPainter):
        children = self._child_nodes_by_symbol(node)
        content = self._draw_section_shell(node, inner, painter)
        list_rect = QRect(content.x(), content.y() + 16, content.width(), max(120, content.height() - 58))
        actions_rect = QRect(content.x(), list_rect.bottom() + 8, content.width(), max(28, content.height() - list_rect.height() - 8))
        painter.setPen(self.text_soft)
        painter.drawText(
            QRect(content.x(), content.y(), content.width(), 16),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            self._node_text(children.get("label_user_profiles"), "User Profiles"),
        )
        self.draw_list_panel(node, list_rect, painter)
        self._draw_surface(painter, actions_rect, fill=self.panel, border=self.border, radius=4)
        chip_y = actions_rect.y() + 4
        chip_x = actions_rect.x() + 8
        for symbol, fallback, emphasized in [
            ("new_button", "New", False),
            ("clone_button", "Clone", False),
            ("rename_button", "Rename", False),
            ("delete_button", "Delete", False),
            ("save_button", "Save", True),
        ]:
            child = children.get(symbol)
            text = self._node_text(child, fallback)
            width = max(46, min(100, 18 + (len(text) * 7)))
            chip = QRect(chip_x, chip_y, width, max(18, actions_rect.height() - 8))
            if chip.right() > actions_rect.right() - 8:
                break
            self._draw_state_button(painter, chip, label=text, node=child, emphasized=emphasized)
            chip_x += width + 6

    def draw_form_container(self, node, inner: QRect, painter: QPainter):
        form_rect = self._draw_section_shell(node, inner, painter)
        specs = self._profile_form_specs(node)
        if not specs:
            rows = self._group_rows(node)
            specs = []
            for index, row in enumerate(rows):
                label_text = ""
                value_text = ""
                button_labels: list[str] = []
                for child in row:
                    child_type = str(getattr(child, "type", "") or "")
                    if child_type == "text" and not label_text:
                        label_text = self._node_text(child, "")
                    elif child_type in {"input", "button"}:
                        text = self._node_text(child, "")
                        if child_type == "button":
                            button_labels.append(text)
                        elif not value_text:
                            value_text = text
                specs.append(("buttons" if button_labels else "field", label_text or f"Field {index + 1}", ", ".join(button_labels) if button_labels else value_text or "Value"))
        visible_rows = max(1, min(10, len(specs)))
        row_height = max(28, form_rect.height() // visible_rows)
        label_column = max(110, int(form_rect.width() * 0.34))
        painter.setPen(QPen(self.border, 1))
        painter.drawLine(form_rect.x() + label_column, form_rect.y(), form_rect.x() + label_column, form_rect.bottom())
        for index in range(visible_rows):
            row_y = form_rect.y() + (index * row_height)
            row_rect = QRect(form_rect.x(), row_y, form_rect.width(), row_height)
            if index % 2 == 0:
                painter.fillRect(row_rect, self.panel)
            painter.setPen(self.border)
            painter.drawLine(row_rect.left(), row_rect.bottom(), row_rect.right(), row_rect.bottom())
            if index >= len(specs):
                continue
            kind, label_text, value_text = specs[index]
            label_cell = QRect(row_rect.x() + 8, row_rect.y(), label_column - 16, row_rect.height())
            value_cell = QRect(row_rect.x() + label_column + 8, row_rect.y() + 4, row_rect.width() - label_column - 16, row_rect.height() - 8)
            painter.setPen(self.text_soft)
            painter.drawText(label_cell, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, label_text)
            if kind == "buttons":
                self._draw_chip_row(painter, value_cell, [part.strip() for part in value_text.split(",") if part.strip()])
            elif kind == "checkbox":
                box = QRect(value_cell.x(), value_cell.y() + max(0, (value_cell.height() - 18) // 2), 18, 18)
                self._draw_surface(painter, box, fill=self.panel, border=self.border_strong, radius=4)
                painter.fillRect(QRect(box.x() + 4, box.y() + 4, 10, 10), self.good)
                painter.setPen(self.text_mid)
                painter.drawText(value_cell.adjusted(28, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, value_text)
            else:
                self._draw_surface(painter, value_cell, fill=self.panel, border=self.border, radius=4)
                painter.setPen(self.text)
                painter.drawText(value_cell.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, value_text or label_text)
        footer = QRect(form_rect.x(), form_rect.bottom() - 22, min(260, form_rect.width()), 18)
        painter.setPen(self.text_soft)
        painter.drawText(footer, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, "Source-backed form fields from ProfileManagerDialog")

    def draw_controls_container(self, node, inner: QRect, painter: QPainter):
        children = self._child_nodes_by_symbol(node)
        strip = self._draw_section_shell(node, inner, painter)
        row_y = strip.y()
        field_h = 42
        field_y = row_y
        self._draw_field(
            painter,
            QRect(strip.x(), field_y, 196, field_h),
            label=self._node_text(children.get("label_profile"), "Profile"),
            value=self._node_text(children.get("profile_combo"), "Profile"),
        )
        self._draw_field(
            painter,
            QRect(strip.x() + 208, field_y, 84, field_h),
            label=self._node_text(children.get("label_scan_limit"), "Limit"),
            value=self._node_text(children.get("limit_input"), "200"),
        )
        self._draw_field(
            painter,
            QRect(strip.x() + 304, field_y, 244, field_h),
            label=self._node_text(children.get("label_universe_file"), "Universe"),
            value=self._node_text(children.get("universe_path_input"), "Universe"),
        )
        self._draw_state_button(
            painter,
            QRect(strip.x() + 560, field_y + 18, 92, 24),
            label=self._node_text(children.get("debug_checkbox"), "Debug"),
            node=children.get("debug_checkbox"),
        )
        self._draw_state_button(
            painter,
            QRect(strip.x() + 660, field_y + 18, 110, 24),
            label=self._node_text(children.get("run_button"), "Run"),
            node=children.get("run_button"),
            emphasized=True,
        )
        painter.setPen(self.text_soft)
        painter.drawText(
            QRect(strip.x(), field_y + 50, strip.width(), 16),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "Profile and universe settings define the scan workspace",
        )
        utility_labels = [
            self._node_text(children.get("auto_refresh_button"), "Auto Refresh"),
            self._node_text(children.get("manage_profiles_button"), "Profiles"),
            self._node_text(children.get("open_window_button"), "Window"),
        ]
        utility_rect = QRect(strip.x(), field_y + 72, min(strip.width(), 420), 22)
        chip_x = utility_rect.x()
        for symbol, label in [
            ("auto_refresh_button", utility_labels[0] if len(utility_labels) > 0 else ""),
            ("manage_profiles_button", utility_labels[1] if len(utility_labels) > 1 else ""),
            ("open_window_button", utility_labels[2] if len(utility_labels) > 2 else ""),
        ]:
            if not label:
                continue
            width = max(52, min(120, 18 + (len(label) * 7)))
            chip = QRect(chip_x, utility_rect.y(), width, utility_rect.height())
            if chip.right() > utility_rect.right():
                break
            self._draw_state_button(painter, chip, label=label, node=children.get(symbol))
            chip_x += width + 6

    def draw_details_container(self, node, inner: QRect, painter: QPainter):
        children = self._child_nodes_by_symbol(node)
        content = self._draw_section_shell(node, inner, painter)
        top_h = max(58, int(content.height() * 0.34))
        split_w = max(120, (content.width() - 10) // 2)
        fail_rect = QRect(content.x(), content.y(), content.width(), top_h)
        news_rect = QRect(content.x(), fail_rect.bottom() + 10, split_w, max(56, content.height() - top_h - 10))
        debug_rect = QRect(news_rect.right() + 10, fail_rect.bottom() + 10, content.width() - split_w - 10, max(56, content.height() - top_h - 10))
        fail_node = children.get("fail_reason_text")
        news_node = children.get("news_text")
        debug_node = children.get("scan_debug_text")
        self._draw_card(painter, fail_rect, title=self._node_text(fail_node, "Fail Reasons"), node=fail_node)
        self._draw_card(painter, news_rect, title=self._node_text(news_node, "News"), header_fill=self.header_fill_alt, node=news_node)
        self._draw_card(painter, debug_rect, title=self._node_text(debug_node, "Scan Debug"), node=debug_node)
        painter.setPen(self.text_soft)
        painter.drawText(
            fail_rect.adjusted(10, 34, -10, -10),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextWordWrap,
            self._text_area_summary(fail_node, "Why a result failed thresholds or validation."),
        )
        painter.drawText(
            news_rect.adjusted(10, 34, -10, -10),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextWordWrap,
            self._text_area_summary(news_node, "Headline and catalyst context for the selected row."),
        )
        painter.drawText(
            debug_rect.adjusted(10, 34, -10, -10),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextWordWrap,
            self._text_area_summary(debug_node, "Verbose scan output and workflow diagnostics."),
        )
        footer = QRect(content.x(), content.bottom() - 18, content.width(), 16)
        painter.setPen(self.text_soft)
        painter.drawText(footer, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "results selection drives this area")

    def draw_results_container(self, node, inner: QRect, painter: QPainter):
        children = self._child_nodes_by_symbol(node)
        content = self._draw_section_shell(node, inner, painter)
        table_rect = QRect(content.x(), content.y(), content.width(), max(120, content.height() - 44))
        footer_rect = QRect(content.x(), table_rect.bottom() + 8, content.width(), max(28, content.height() - table_rect.height() - 8))
        self._draw_surface(painter, table_rect, fill=self.panel, border=self.border, radius=4)
        table_node = children.get("results_table")
        table_title = self._node_text(table_node, "Results Table")
        header = QRect(table_rect.x(), table_rect.y(), table_rect.width(), 24)
        painter.fillRect(header, self.header_fill)
        painter.setPen(self.text_mid)
        painter.drawText(header.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, table_title)
        summary_rect = QRect(header.right() - 220, header.y(), 212, header.height())
        painter.setPen(self.text_soft)
        painter.drawText(summary_rect, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, "scanner results workspace")
        painter.setPen(self.border)
        for row_y in range(header.bottom(), table_rect.bottom(), 22):
            painter.drawLine(table_rect.x(), row_y, table_rect.right(), row_y)
        self._draw_surface(painter, footer_rect, fill=self.warn_fill, border=self.border, radius=4)
        painter.fillRect(QRect(footer_rect.x() + 8, footer_rect.y() + 7, 10, max(10, footer_rect.height() - 14)), self.good)
        painter.drawText(
            footer_rect.adjusted(26, 0, -8, 0),
            Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
            "Select a result row to inspect news and fail reasons",
        )

    def draw_table_panel(self, node, inner: QRect, painter: QPainter):
        self._draw_surface(painter, inner, fill=self.panel, border=self.border_strong, radius=6)
        header = QRect(inner.x(), inner.y(), inner.width(), min(30, inner.height()))
        painter.fillRect(header, self.header_fill)
        painter.setPen(self.text)
        headers = self._results_headers(node)
        if not headers:
            headers = ["Symbol", "%", "RVOL", "News"]
        if headers:
            column_width = max(40, inner.width() // max(1, len(headers)))
            for index, header_text in enumerate(headers):
                cell = QRect(inner.x() + (index * column_width), header.y(), column_width, header.height())
                painter.drawRect(cell)
                painter.drawText(cell.adjusted(6, 0, -6, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(header_text))
        body = QRect(inner.x(), header.bottom(), inner.width(), max(0, inner.height() - header.height()))
        row_height = 24
        sample_rows = [
            ["NVDA", "+4.2%", "2.1x", "News"],
            ["AAPL", "+2.8%", "1.6x", "Watch"],
            ["AMD", "+3.1%", "1.9x", "News"],
            ["TSLA", "+5.7%", "2.8x", "Hot"],
        ]
        column_width = max(40, inner.width() // max(1, len(headers) or 4))
        for row_index, row_y in enumerate(range(body.y(), body.bottom(), row_height)):
            painter.setPen(self.border)
            if row_index == 0:
                painter.fillRect(QRect(body.x(), row_y, body.width(), row_height), self.warn_fill)
            painter.drawLine(body.x(), row_y, body.right(), row_y)
            row = sample_rows[row_index] if row_index < len(sample_rows) else None
            if row is None:
                continue
            for col_index, cell_text in enumerate(row[: max(1, len(headers) or 4)]):
                cell = QRect(body.x() + (col_index * column_width), row_y, column_width, row_height)
                painter.setPen(self.border)
                painter.drawLine(cell.right(), row_y, cell.right(), row_y + row_height)
                if col_index == len(headers) - 1:
                    chip = QRect(cell.x() + 6, cell.y() + 4, max(44, min(cell.width() - 12, 54)), row_height - 8)
                    chip_fill = self.accent_fill if str(cell_text).lower() == "news" else self.panel_alt
                    chip_pen = self.accent if str(cell_text).lower() == "news" else self.border_strong
                    self._draw_surface(painter, chip, fill=chip_fill, border=chip_pen, radius=4)
                    painter.setPen(self.text_mid)
                    painter.drawText(chip, Qt.AlignmentFlag.AlignCenter, str(cell_text))
                    continue
                painter.setPen(self.text if col_index == 0 else self.text_mid)
                painter.drawText(cell.adjusted(6, 0, -6, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(cell_text))

    def draw_text_area_panel(self, node, inner: QRect, painter: QPainter):
        self._draw_surface(painter, inner, fill=self.panel, border=self.border_strong, radius=6)
        source_symbol = self._source_symbol(node)
        title = {
            "fail_reason_text": "Fail Reasons",
            "news_text": "News",
            "scan_debug_text": "Scan Debug",
        }.get(source_symbol, self._node_text(node, "Text Area"))
        header = QRect(inner.x(), inner.y(), inner.width(), min(26, inner.height()))
        painter.fillRect(header, self.header_fill_alt if source_symbol == "news_text" else self.header_fill)
        painter.setPen(self.text)
        painter.drawText(header.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, str(title))
        content = inner.adjusted(10, 32, -10, -10)
        painter.setPen(self.border)
        for line_y in range(content.y() + 18, content.bottom(), 18):
            painter.drawLine(content.x(), line_y, content.right(), line_y)
        painter.setPen(self.text_soft)
        label = self._text_area_summary(node, "Text Area")
        painter.drawText(content, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop | Qt.TextWordWrap, str(label))

    def draw_list_panel(self, node, inner: QRect, painter: QPainter):
        self._draw_surface(painter, inner, fill=self.panel, border=self.border_strong, radius=4)
        row_height = 24
        source_symbol = self._source_symbol(node)
        item_labels = ["Item A", "Item B", "Item C"]
        if source_symbol == "profile_list":
            item_labels = ["Top Gainers MVP", "Momentum News", "Definition Match"]
        for index, text in enumerate(item_labels):
            row = QRect(inner.x(), inner.y() + (index * row_height), inner.width(), row_height)
            if row.bottom() > inner.bottom():
                break
            if index == 0:
                painter.fillRect(row, self.accent_fill)
            painter.setPen(self.border)
            painter.drawRect(row)
            painter.setPen(self.text)
            painter.drawText(row.adjusted(8, 0, -8, 0), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
