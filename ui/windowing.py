from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QVBoxLayout, QWidget


SELECTION_WINDOW_OFFSET_X = 210
SELECTION_WINDOW_OFFSET_Y = 80
TOOL_WORKSPACE_OFFSET_X = 250
TOOL_WORKSPACE_OFFSET_Y = 80


def build_selection_window(parent, inspector_panel: QWidget) -> QWidget:
    window = QWidget(parent, Qt.WindowType.Tool)
    window.setWindowTitle("Selection")
    layout = QVBoxLayout(window)
    layout.setContentsMargins(8, 8, 8, 8)
    layout.setSpacing(8)
    inspector_panel.setParent(window)
    layout.addWidget(inspector_panel)
    window.resize(360, 760)
    return window


def position_selection_window(main_window, selection_window) -> None:
    if selection_window is None:
        return
    frame = main_window.frameGeometry()
    selection_window.move(
        frame.topLeft().x() + SELECTION_WINDOW_OFFSET_X,
        frame.topLeft().y() + SELECTION_WINDOW_OFFSET_Y,
    )


def position_tool_workspace_window(main_window, tool_workspace_window) -> None:
    if tool_workspace_window is None:
        return
    frame = main_window.frameGeometry()
    tool_workspace_window.move(
        frame.topLeft().x() + TOOL_WORKSPACE_OFFSET_X,
        frame.topLeft().y() + TOOL_WORKSPACE_OFFSET_Y,
    )


def sync_floating_windows(main_window, selection_window, tool_workspace_window) -> None:
    if selection_window is not None and not selection_window.isHidden():
        position_selection_window(main_window, selection_window)
    if tool_workspace_window is not None and not tool_workspace_window.isHidden():
        position_tool_workspace_window(main_window, tool_workspace_window)


def close_floating_windows(selection_window, tool_workspace_window) -> None:
    if selection_window is not None:
        selection_window.close()
    if tool_workspace_window is not None:
        tool_workspace_window.close()


def close_selection_window(selection_window) -> bool:
    if selection_window is None or not selection_window.isVisible():
        return False
    selection_window.close()
    return True


def focus_selection_window(main_window, selection_window, inspector_panel) -> bool:
    if selection_window is None:
        return False
    if selection_window.isHidden():
        selection_window.show()
        position_selection_window(main_window, selection_window)
    selection_window.raise_()
    selection_window.activateWindow()
    if inspector_panel is not None:
        inspector_panel.setFocus(Qt.FocusReason.ShortcutFocusReason)
    else:
        selection_window.setFocus(Qt.FocusReason.ShortcutFocusReason)
    return True
