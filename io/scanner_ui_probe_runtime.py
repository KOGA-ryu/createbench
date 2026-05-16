from __future__ import annotations

import json
import re
import sys
import ast
from pathlib import Path

try:
    from PyQt6.QtCore import QPoint
    from PyQt6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QSpinBox,
        QStatusBar,
        QTableWidget,
        QTextEdit,
        QWidget,
    )
    QT_FRAMEWORK = "pyqt6"
except ImportError:
    from PySide6.QtCore import QPoint
    from PySide6.QtWidgets import (
        QApplication,
        QCheckBox,
        QComboBox,
        QDialog,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QSpinBox,
        QStatusBar,
        QTableWidget,
        QTextEdit,
        QWidget,
    )
    QT_FRAMEWORK = "pyside6"


def _slug(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    return slug or "widget"


def _source_assignment_index(source_path: Path) -> dict[str, tuple[int | None, int | None]]:
    if not source_path.exists():
        return {}
    try:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
    except Exception:
        return {}

    assignments: dict[str, tuple[int | None, int | None]] = {}
    for node in ast.walk(tree):
        targets: list[ast.Attribute] = []
        value_node = None
        if isinstance(node, ast.Assign):
            targets = [
                target
                for target in node.targets
                if isinstance(target, ast.Attribute)
                and isinstance(target.value, ast.Name)
                and target.value.id == "self"
            ]
            value_node = node.value
        elif isinstance(node, ast.AnnAssign):
            if (
                isinstance(node.target, ast.Attribute)
                and isinstance(node.target.value, ast.Name)
                and node.target.value.id == "self"
            ):
                targets = [node.target]
                value_node = node.value
        if not targets:
            continue
        for target in targets:
            assignments[target.attr] = (
                getattr(node, "lineno", None),
                getattr(node, "end_lineno", getattr(node, "lineno", None)),
            )
            if isinstance(value_node, ast.Dict):
                for key_node, dict_value_node in zip(value_node.keys, value_node.values):
                    if not isinstance(key_node, ast.Constant) or not isinstance(key_node.value, str):
                        continue
                    dict_key = str(key_node.value)
                    assignments[f"{target.attr}_{dict_key}"] = (
                        getattr(dict_value_node, "lineno", getattr(node, "lineno", None)),
                        getattr(
                            dict_value_node,
                            "end_lineno",
                            getattr(dict_value_node, "lineno", getattr(node, "lineno", None)),
                        ),
                    )
    return assignments


def _class_source_range(source_path: Path, class_name: str) -> tuple[int | None, int | None]:
    if not source_path.exists():
        return (None, None)
    try:
        tree = ast.parse(source_path.read_text(encoding="utf-8"))
    except Exception:
        return (None, None)
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return (
                getattr(node, "lineno", None),
                getattr(node, "end_lineno", getattr(node, "lineno", None)),
            )
    return (None, None)


def _node_type_and_role(widget: QWidget) -> tuple[str, str | None]:
    if isinstance(widget, QMainWindow):
        return "panel", "tool_window"
    if isinstance(widget, QDialog):
        return "panel", "dialog"
    if isinstance(widget, QStatusBar):
        return "toolbar", "toolbar"
    if isinstance(widget, QLabel):
        return "text", None
    if isinstance(widget, QPushButton):
        return "button", None
    if isinstance(widget, (QLineEdit, QComboBox, QCheckBox, QSpinBox)):
        return "input", None
    if isinstance(widget, (QTextEdit, QTableWidget)):
        return "panel", None
    return "panel", None


def _scanner_semantic_override(
    *,
    root_node_id: str,
    source_symbol: str | None,
    node_type: str,
    ui_role: str | None,
) -> tuple[str, str | None, list[str]]:
    warnings: list[str] = []
    if root_node_id == "scanner_main_window":
        if source_symbol == "central_widget":
            node_type = "container"
            warnings.append("type inferred from scanner main window semantics")
        elif source_symbol == "results_table":
            ui_role = "main"
            warnings.append("ui_role inferred from scanner main window semantics")
    elif root_node_id == "scanner_profile_manager_dialog":
        if source_symbol == "profile_list":
            ui_role = "sidebar"
            warnings.append("ui_role inferred from scanner profile manager semantics")
    return node_type, ui_role, warnings


def _render_hints(widget: QWidget) -> dict[str, object]:
    text = None
    title = None
    placeholder = None
    if isinstance(widget, QLabel):
        text = widget.text().strip() or None
    elif isinstance(widget, QPushButton):
        text = widget.text().strip() or None
    elif isinstance(widget, QLineEdit):
        placeholder = widget.placeholderText().strip() or None
        text = widget.text().strip() or None
    elif isinstance(widget, QComboBox):
        text = widget.currentText().strip() or None
    elif isinstance(widget, QCheckBox):
        text = widget.text().strip() or None
    elif isinstance(widget, QSpinBox):
        text = widget.text().strip() or None
    elif isinstance(widget, QTextEdit):
        placeholder = widget.placeholderText().strip() or None
        text = widget.toPlainText().strip() or None
    elif isinstance(widget, (QMainWindow, QDialog)):
        title = widget.windowTitle().strip() or None
    elif isinstance(widget, QStatusBar):
        text = widget.currentMessage().strip() or None
    return {
        "title": title,
        "text": text,
        "placeholder": placeholder,
        "icon": None,
        "visible": bool(widget.isVisible()),
        "enabled": bool(widget.isEnabled()),
        "window_mode": "window" if isinstance(widget, (QMainWindow, QDialog)) else None,
    }


def _source_info(
    widget_id: str,
    *,
    source_file: str,
    symbol: str | None,
    line_start: int | None = None,
    line_end: int | None = None,
) -> dict[str, object]:
    return {
        "file": source_file,
        "symbol": symbol,
        "line_start": line_start,
        "line_end": line_end,
        "source_id": widget_id,
    }


def _named_widgets(root_widget: QWidget) -> dict[QWidget, str]:
    names: dict[QWidget, str] = {}
    for attr_name, value in vars(root_widget).items():
        if isinstance(value, QWidget):
            names[value] = attr_name
        elif isinstance(value, dict):
            for key, child in value.items():
                if isinstance(key, str) and isinstance(child, QWidget):
                    names[child] = f"{attr_name}_{key}"
    if isinstance(root_widget, QMainWindow):
        central = root_widget.centralWidget()
        if isinstance(central, QWidget):
            names.setdefault(central, "central_widget")
        status = root_widget.statusBar()
        if isinstance(status, QWidget):
            names.setdefault(status, "status_bar")
    return names


def _meaningful_widgets(root_widget: QWidget) -> tuple[list[QWidget], dict[QWidget, str]]:
    named = _named_widgets(root_widget)
    widgets: set[QWidget] = {root_widget}
    widgets.update(named.keys())

    label_counts: dict[str, int] = {}
    for label in root_widget.findChildren(QLabel):
        if label in widgets:
            continue
        if label.objectName().startswith("qt_"):
            continue
        text = label.text().strip()
        if not text:
            continue
        widgets.add(label)
        slug = _slug(text)
        label_counts[slug] = label_counts.get(slug, 0) + 1
        suffix = "" if label_counts[slug] == 1 else f"_{label_counts[slug]}"
        named[label] = f"label_{slug}{suffix}"

    def sort_key(widget: QWidget) -> tuple[int, int, str]:
        pos = widget.mapTo(root_widget, QPoint(0, 0))
        name = named.get(widget) or widget.metaObject().className()
        return (pos.y(), pos.x(), str(name))

    ordered = sorted(widgets, key=sort_key)
    return ordered, named


def _region_bounds(packet_nodes: list[dict[str, object]], child_ids: list[str], fallback: dict[str, int]) -> dict[str, int]:
    nodes_by_id = {node["id"]: node for node in packet_nodes}
    xs: list[int] = []
    ys: list[int] = []
    rights: list[int] = []
    bottoms: list[int] = []
    for child_id in child_ids:
        node = nodes_by_id.get(child_id)
        if node is None:
            continue
        layout_hints = node["layout_hints"]
        x = int(layout_hints.get("x") or 0)
        y = int(layout_hints.get("y") or 0)
        width = int(layout_hints.get("width") or 0)
        height = int(layout_hints.get("height") or 0)
        xs.append(x)
        ys.append(y)
        rights.append(x + width)
        bottoms.append(y + height)
    if not xs:
        return dict(fallback)
    return {
        "x": min(xs),
        "y": min(ys),
        "width": max(rights) - min(xs),
        "height": max(bottoms) - min(ys),
    }


def _append_inferred_region(
    packet: dict[str, object],
    *,
    region_id: str,
    title: str,
    child_ids: list[str],
    ui_role: str | None,
    bounds: dict[str, int],
    source_file: str,
) -> None:
    nodes_by_id = {node["id"]: node for node in packet["nodes"]}
    for child_id in child_ids:
        if child_id in nodes_by_id:
            child = nodes_by_id[child_id]
            child["parent"] = region_id
            child_layout_hints = child["layout_hints"]
            child_x = int(child_layout_hints.get("x") or 0)
            child_y = int(child_layout_hints.get("y") or 0)
            child_layout_hints["x"] = child_x - int(bounds["x"])
            child_layout_hints["y"] = child_y - int(bounds["y"])

    region_node = {
        "id": region_id,
        "type": "container",
        "ui_role": ui_role,
        "parent": "scanner_profile_manager_dialog",
        "children": [child_id for child_id in child_ids if child_id in nodes_by_id],
        "source": {
            "file": source_file,
            "symbol": region_id,
            "line_start": None,
            "line_end": None,
            "source_id": region_id,
        },
        "layout_hints": {
            "layout_mode": "free",
            "layout_direction": None,
            "preferred_width": bounds["width"],
            "preferred_height": bounds["height"],
            "min_width": None,
            "min_height": None,
            "max_width": None,
            "max_height": None,
            "x": bounds["x"],
            "y": bounds["y"],
            "width": bounds["width"],
            "height": bounds["height"],
        },
        "render_hints": {
            "title": title,
            "text": None,
            "placeholder": None,
            "icon": None,
            "visible": True,
            "enabled": True,
            "window_mode": None,
        },
        "relationships": {
            "communicates_to": [],
            "depends_on": [],
            "updated_by": [],
            "triggered_by": [],
        },
        "trust": {
            "trust_level": "partial",
            "representation_origin": "adapter",
            "warnings": [
                "synthetic container inferred from scanner profile manager semantics",
            ],
        },
        "raw": {
            "provider_type": "synthetic_region",
            "provider_data": {"region_title": title},
            "unresolved_fields": ["source.line_start", "source.line_end"],
        },
    }
    packet["nodes"].append(region_node)


def _apply_main_window_regions(packet: dict[str, object]) -> dict[str, object]:
    nodes_by_id = {node["id"]: node for node in packet["nodes"]}
    root = nodes_by_id.get("scanner_main_window")
    if root is None:
        return packet

    controls_children = [
        "profile_combo",
        "label_profile",
        "limit_input",
        "label_scan_limit",
        "universe_path_input",
        "label_universe_file",
        "debug_checkbox",
        "run_button",
        "auto_refresh_button",
        "manage_profiles_button",
        "open_window_button",
    ]
    results_children = ["results_table"]
    detail_children = [
        child_id
        for child_id in list(nodes_by_id.get("central_widget", {}).get("children", []))
        if child_id not in controls_children and child_id not in results_children
    ]

    central = nodes_by_id.get("central_widget")
    if central is None:
        return packet
    central_bounds = central["layout_hints"]
    central_width = int(central_bounds.get("width") or 0)
    central_height = int(central_bounds.get("height") or 0)

    controls_bounds = _region_bounds(
        packet["nodes"],
        controls_children,
        {
            "x": 24,
            "y": 24,
            "width": max(400, central_width - 48),
            "height": 140,
        },
    )
    results_bounds = _region_bounds(
        packet["nodes"],
        results_children,
        {
            "x": 24,
            "y": controls_bounds["y"] + controls_bounds["height"] + 16,
            "width": max(500, central_width - 48),
            "height": 240,
        },
    )
    details_bounds = _region_bounds(
        packet["nodes"],
        detail_children,
        {
            "x": 24,
            "y": results_bounds["y"] + results_bounds["height"] + 16,
            "width": max(500, central_width - 48),
            "height": max(160, central_height - (results_bounds["y"] + results_bounds["height"] + 40)),
        },
    )

    source_file = str(root["source"]["file"])
    _append_inferred_region(
        packet,
        region_id="scanner_controls_region",
        title="Controls",
        child_ids=controls_children,
        ui_role="toolbar",
        bounds=controls_bounds,
        source_file=source_file,
    )
    _append_inferred_region(
        packet,
        region_id="scanner_results_region",
        title="Results",
        child_ids=results_children,
        ui_role="main",
        bounds=results_bounds,
        source_file=source_file,
    )
    _append_inferred_region(
        packet,
        region_id="scanner_details_region",
        title="Details",
        child_ids=detail_children,
        ui_role=None,
        bounds=details_bounds,
        source_file=source_file,
    )

    central["children"] = [
        "scanner_controls_region",
        "scanner_results_region",
        "scanner_details_region",
    ]
    for region_id in central["children"]:
        nodes_by_id[region_id] = next(
            node for node in packet["nodes"] if node["id"] == region_id
        )
        nodes_by_id[region_id]["parent"] = "central_widget"
    return packet


def _apply_profile_manager_regions(packet: dict[str, object]) -> dict[str, object]:
    nodes_by_id = {node["id"]: node for node in packet["nodes"]}
    root = nodes_by_id.get("scanner_profile_manager_dialog")
    if root is None:
        return packet

    left_children = [
        "label_user_profiles",
        "profile_list",
        "new_button",
        "clone_button",
        "rename_button",
        "delete_button",
        "save_button",
    ]
    right_children = [
        child_id
        for child_id in list(root["children"])
        if child_id not in left_children
    ]

    root_bounds = root["layout_hints"]
    root_width = int(root_bounds.get("width") or 0)
    root_height = int(root_bounds.get("height") or 0)
    left_bounds = _region_bounds(
        packet["nodes"],
        left_children,
        {
            "x": 24,
            "y": 24,
            "width": max(240, int(root_width * 0.34)),
            "height": max(320, root_height - 48),
        },
    )
    right_bounds = _region_bounds(
        packet["nodes"],
        right_children,
        {
            "x": left_bounds["x"] + left_bounds["width"] + 24,
            "y": 24,
            "width": max(320, root_width - (left_bounds["x"] + left_bounds["width"] + 48)),
            "height": max(320, root_height - 48),
        },
    )

    source_file = str(root["source"]["file"])
    _append_inferred_region(
        packet,
        region_id="profile_manager_sidebar_region",
        title="Profiles",
        child_ids=left_children,
        ui_role="sidebar",
        bounds=left_bounds,
        source_file=source_file,
    )
    _append_inferred_region(
        packet,
        region_id="profile_manager_form_region",
        title="Profile Form",
        child_ids=right_children,
        ui_role=None,
        bounds=right_bounds,
        source_file=source_file,
    )

    root["children"] = [
        "profile_manager_sidebar_region",
        "profile_manager_form_region",
    ]
    return packet


def build_packet_for_widget(
    root_widget: QWidget,
    *,
    repo_root: Path,
    source_file_relative: str,
    root_node_id: str,
    root_symbol: str,
    source_provider: str = "scanner_qt_runtime_probe",
) -> dict[str, object]:
    widgets, names = _meaningful_widgets(root_widget)
    source_path = (repo_root / source_file_relative).resolve()
    source_file = str(source_path)
    source_assignments = _source_assignment_index(source_path)
    root_line_start, root_line_end = _class_source_range(source_path, root_symbol)
    widget_ids = {
        widget: (root_node_id if widget is root_widget else names[widget])
        for widget in widgets
    }
    included = set(widgets)

    def nearest_included_parent(widget: QWidget) -> QWidget | None:
        parent = widget.parentWidget()
        while parent is not None:
            if parent in included:
                return parent
            parent = parent.parentWidget()
        return None

    def relative_geometry(widget: QWidget, parent: QWidget | None) -> tuple[int, int, int, int]:
        if parent is None:
            return 0, 0, int(widget.width()), int(widget.height())
        child_pos = widget.mapTo(root_widget, QPoint(0, 0))
        parent_pos = parent.mapTo(root_widget, QPoint(0, 0))
        return (
            int(child_pos.x() - parent_pos.x()),
            int(child_pos.y() - parent_pos.y()),
            int(widget.width()),
            int(widget.height()),
        )

    children_by_parent: dict[str, list[str]] = {}
    nodes: list[dict[str, object]] = []

    for widget in widgets:
        node_id = widget_ids[widget]
        parent_widget = nearest_included_parent(widget)
        parent_id = None if parent_widget is None else widget_ids[parent_widget]
        children_by_parent.setdefault(node_id, [])
        if parent_id is not None:
            children_by_parent.setdefault(parent_id, []).append(node_id)

        x, y, width, height = relative_geometry(widget, parent_widget)
        node_type, ui_role = _node_type_and_role(widget)
        source_symbol = root_symbol if widget is root_widget else names.get(widget)
        node_type, ui_role, semantic_warnings = _scanner_semantic_override(
            root_node_id=root_node_id,
            source_symbol=source_symbol,
            node_type=node_type,
            ui_role=ui_role,
        )
        source_line_start = None
        source_line_end = None
        if widget is root_widget:
            source_line_start = root_line_start
            source_line_end = root_line_end
        elif source_symbol in source_assignments:
            source_line_start, source_line_end = source_assignments[source_symbol]
        raw_provider_data = {
            "qt_class": widget.metaObject().className(),
            "attribute_name": names.get(widget),
            "object_name": widget.objectName() or None,
        }
        if isinstance(widget, QTableWidget):
            raw_provider_data["column_headers"] = [
                widget.horizontalHeaderItem(index).text()
                if widget.horizontalHeaderItem(index) is not None
                else ""
                for index in range(widget.columnCount())
            ]
        unresolved: list[str] = []
        if source_line_start is None:
            unresolved.append("source.line_start")
        if source_line_end is None:
            unresolved.append("source.line_end")
        if ui_role is None:
            unresolved.append("ui_role")
        trust_warnings = list(semantic_warnings)
        nodes.append(
            {
                "id": node_id,
                "type": node_type,
                "ui_role": ui_role,
                "parent": parent_id,
                "children": [],
                "source": _source_info(
                    node_id,
                    source_file=source_file,
                    symbol=source_symbol,
                    line_start=source_line_start,
                    line_end=source_line_end,
                ),
                "layout_hints": {
                    "layout_mode": "free",
                    "layout_direction": None,
                    "preferred_width": width,
                    "preferred_height": height,
                    "min_width": None,
                    "min_height": None,
                    "max_width": None,
                    "max_height": None,
                    "x": x,
                    "y": y,
                    "width": width,
                    "height": height,
                },
                "render_hints": _render_hints(widget),
                "relationships": {
                    "communicates_to": [],
                    "depends_on": [],
                    "updated_by": [],
                    "triggered_by": [],
                },
                "trust": {
                    "trust_level": "partial",
                    "representation_origin": "adapter",
                    "warnings": trust_warnings,
                },
                "raw": {
                    "provider_type": "qt_widget",
                    "provider_data": raw_provider_data,
                    "unresolved_fields": unresolved,
                },
            }
        )

    nodes_by_id = {node["id"]: node for node in nodes}
    for parent_id, children in children_by_parent.items():
        children.sort(
            key=lambda child_id: (
                nodes_by_id[child_id]["layout_hints"]["y"],
                nodes_by_id[child_id]["layout_hints"]["x"],
                child_id,
            )
        )
        nodes_by_id[parent_id]["children"] = children

    return {
        "packet_version": "1",
        "source_framework": QT_FRAMEWORK,
        "source_provider": source_provider,
        "trust_level": "partial",
        "roots": [root_node_id],
        "nodes": nodes,
        "warnings": [
            "Runtime Qt probe provides partial source mapping and generic role inference.",
        ],
    }


def build_packet_for_window(window: QMainWindow, *, repo_root: Path) -> dict[str, object]:
    packet = build_packet_for_widget(
        window,
        repo_root=repo_root,
        source_file_relative="ui/views/main_window.py",
        root_node_id="scanner_main_window",
        root_symbol="MainWindow",
    )
    return _apply_main_window_regions(packet)


def build_packet_for_profile_manager(dialog: QDialog, *, repo_root: Path) -> dict[str, object]:
    packet = build_packet_for_widget(
        dialog,
        repo_root=repo_root,
        source_file_relative="ui/views/profile_manager.py",
        root_node_id="scanner_profile_manager_dialog",
        root_symbol="ProfileManagerDialog",
    )
    return _apply_profile_manager_regions(packet)


def _main(argv: list[str]) -> int:
    if len(argv) != 3:
        raise SystemExit("Usage: scanner_ui_probe_runtime.py <scanner_repo_root> <target>")
    repo_root = Path(argv[1]).resolve()
    target = str(argv[2]).strip()
    if str(repo_root.parent) not in sys.path:
        sys.path.insert(0, str(repo_root.parent))

    from scanner.ui.views.main_window import MainWindow
    from scanner.ui.views.profile_manager import ProfileManagerDialog

    app = QApplication.instance() or QApplication([])
    widget: QWidget
    if target == "main_window":
        widget = MainWindow()
    elif target == "profile_manager":
        widget = ProfileManagerDialog()
    else:
        raise SystemExit(f"Unsupported scanner probe target: {target}")
    widget.show()
    app.processEvents()
    if target == "main_window":
        packet = build_packet_for_window(widget, repo_root=repo_root)
    else:
        packet = build_packet_for_profile_manager(widget, repo_root=repo_root)
    print(json.dumps(packet, indent=2, sort_keys=True))
    widget.close()
    app.processEvents()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main(sys.argv))
