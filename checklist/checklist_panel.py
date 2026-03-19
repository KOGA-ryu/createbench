from __future__ import annotations

from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout, QWidget


class ChecklistPanel(QWidget):
    def __init__(self, layout_model, checklist_engine, selection_state):
        super().__init__()
        self.model = layout_model
        self.engine = checklist_engine
        self.selection_state = selection_state

        layout = QVBoxLayout(self)
        self.summary_label = QLabel("Errors: 0 | Warnings: 0 | Info: 0")
        self.selected_label = QLabel("Selected Node Issues")
        self.selected_list = QListWidget()
        self.other_label = QLabel("Other Issues")
        self.other_list = QListWidget()

        layout.addWidget(self.summary_label)
        layout.addWidget(self.selected_label)
        layout.addWidget(self.selected_list)
        layout.addWidget(self.other_label)
        layout.addWidget(self.other_list)

        self.model.subscribe(self.update_checklist)
        self.destroyed.connect(lambda _obj=None: self.model.unsubscribe(self.update_checklist))
        self.selection_state.subscribe(lambda _selected_id: self.update_checklist())

    def update_checklist(self):
        result = self.engine.run()
        summary = result["summary"]
        self.summary_label.setText(
            f"Errors: {summary['errors']} | Warnings: {summary['warnings']} | Info: {summary['info']}"
        )

        selected_id = self.selection_state.get_selection()
        selected_issues = []
        other_issues = []
        for issue in result["issues"]:
            if selected_id is not None and issue["node_id"] == selected_id:
                selected_issues.append(issue)
            else:
                other_issues.append(issue)

        self._populate_list(self.selected_list, selected_issues)
        self._populate_list(self.other_list, other_issues)

    def _populate_list(self, widget: QListWidget, issues: list[dict]):
        widget.clear()
        for issue in issues:
            item = QListWidgetItem(self._format_issue(issue))
            color = {
                "error": QColor("#dc2626"),
                "warning": QColor("#ca8a04"),
                "info": QColor("#6b7280"),
            }[issue["severity"]]
            item.setForeground(color)
            widget.addItem(item)

    def _format_issue(self, issue: dict) -> str:
        prefix = {"error": "[E]", "warning": "[W]", "info": "[I]"}[issue["severity"]]
        location = issue["node_id"]
        if issue["property"]:
            location = f"{location}.{issue['property']}"
        return f"{prefix} {location}: {issue['message']}"
