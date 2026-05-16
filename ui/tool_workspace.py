from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)


class ToolWorkspace:
    def __init__(self, parent, sections: dict[str, QWidget], section_display_names: dict[str, str]):
        self.parent = parent
        self.sections = sections
        self.section_display_names = section_display_names
        self.section_toggle_buttons: dict[str, QToolButton] = {}
        self.section_cards: dict[str, QFrame] = {}
        self.active_sections: list[str] = []
        self.workspace_window = self._build_workspace_window()
        self.tool_rail_widget = self._build_left_toolbar()

    @staticmethod
    def build_project_group(title: str, object_name: str, *widgets: QWidget) -> QFrame:
        group = QFrame()
        group.setObjectName(object_name)
        group.setFrameShape(QFrame.Shape.StyledPanel)
        group.setStyleSheet(ToolWorkspace.project_group_style(object_name))
        layout = QVBoxLayout(group)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)
        title_label = QLabel(title)
        title_label.setObjectName(f"{object_name}_title")
        title_label.setStyleSheet(ToolWorkspace.project_group_title_style(object_name))
        layout.addWidget(title_label)
        for widget in widgets:
            layout.addWidget(widget)
        return group

    @staticmethod
    def project_group_title_style(object_name: str) -> str:
        if object_name == "project_scene_actions_group":
            return "font-weight: 700; color: #111827;"
        return "font-weight: 600; color: #374151; font-size: 11px;"

    @staticmethod
    def project_group_style(object_name: str) -> str:
        if object_name == "project_scene_actions_group":
            return "QFrame { background: #f8fafc; border: 1px solid #cbd5e1; }"
        return "QFrame { background: #ffffff; border: 1px solid #e5e7eb; }"

    @staticmethod
    def project_input_style() -> str:
        return (
            "color: #111827;"
            "background: #ffffff;"
            "selection-background-color: #bfdbfe;"
            "selection-color: #111827;"
        )

    def _build_workspace_window(self):
        window = QWidget(self.parent, Qt.WindowType.Tool)
        window.setWindowTitle("Tool Workspace")
        layout = QVBoxLayout(window)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        content = QWidget()
        self.left_tool_stack = QVBoxLayout(content)
        self.left_tool_stack.setContentsMargins(0, 0, 0, 0)
        self.left_tool_stack.setSpacing(8)
        self.left_tool_stack.addStretch()
        scroll.setWidget(content)
        layout.addWidget(scroll, 1)
        window.resize(340, 720)
        return window

    def _build_left_toolbar(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        layout.addWidget(QLabel("Tools"))
        for section_name in [
            "Geometry",
            "Components",
            "Templates",
            "Structure",
            "View",
            "Validation",
            "Project",
        ]:
            button = QToolButton()
            button.setText(self.section_display_names[section_name])
            button.setCheckable(True)
            button.setChecked(False)
            button.setArrowType(Qt.ArrowType.RightArrow)
            button.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
            button.toggled.connect(
                lambda checked, name=section_name: self.toggle_section(name, checked)
            )
            self.section_toggle_buttons[section_name] = button
            layout.addWidget(button)
        layout.addStretch()
        return panel

    def toggle_section(self, section_name: str, checked: bool):
        button = self.section_toggle_buttons[section_name]
        button.setArrowType(Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow)
        if checked:
            if section_name not in self.active_sections:
                self.active_sections.append(section_name)
        else:
            if section_name in self.active_sections:
                self.active_sections.remove(section_name)
        self.rebuild_stack()

    def rebuild_stack(self):
        while self.left_tool_stack.count() > 1:
            item = self.left_tool_stack.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)

        for section_name in self.active_sections:
            card = self.section_cards.get(section_name)
            if card is None:
                card = self._make_section_card(section_name, self.sections[section_name])
                self.section_cards[section_name] = card
            self.left_tool_stack.insertWidget(self.left_tool_stack.count() - 1, card)
        if self.active_sections:
            self.workspace_window.show()
            self.workspace_window.raise_()

    def _make_section_card(self, title: str, content_widget: QWidget):
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        header = QLabel(self.section_display_names.get(title, title))
        layout.addWidget(header)
        content_widget.setParent(card)
        layout.addWidget(content_widget)
        return card
