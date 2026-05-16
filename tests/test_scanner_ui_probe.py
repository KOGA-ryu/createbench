import sys
import tempfile
import importlib.util
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QFormLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QStatusBar,
    QVBoxLayout,
    QWidget,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scanner_ui_probe import validate_scanner_repo_root
from scanner_ui_probe import build_scanner_main_window_packet
from scanner_ui_probe import build_scanner_profile_manager_packet


_RUNTIME_MODULE_PATH = PROJECT_ROOT / "io" / "scanner_ui_probe_runtime.py"
_RUNTIME_SPEC = importlib.util.spec_from_file_location(
    "_createbench_scanner_ui_probe_runtime",
    _RUNTIME_MODULE_PATH,
)
_RUNTIME_MODULE = importlib.util.module_from_spec(_RUNTIME_SPEC)
assert _RUNTIME_SPEC is not None and _RUNTIME_SPEC.loader is not None
_RUNTIME_SPEC.loader.exec_module(_RUNTIME_MODULE)
build_packet_for_window = _RUNTIME_MODULE.build_packet_for_window
build_packet_for_profile_manager = _RUNTIME_MODULE.build_packet_for_profile_manager


APP = QApplication.instance() or QApplication([])


class FakeWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Fake Scanner")
        self.resize(640, 420)
        central = QWidget(self)
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.addWidget(QLabel("Profile"))
        self.profile_input = QLineEdit()
        self.profile_input.setPlaceholderText("Choose profile")
        layout.addWidget(self.profile_input)
        self.run_button = QPushButton("Run")
        layout.addWidget(self.run_button)
        self.status = QStatusBar(self)
        self.setStatusBar(self.status)
        self.status.showMessage("Ready")


class FakeProfileManager(QDialog):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Profile Manager")
        self.resize(700, 420)
        layout = QFormLayout(self)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Profile name")
        self.save_button = QPushButton("Save")
        layout.addRow("Name", self.name_input)
        layout.addRow(self.save_button)


def validate_scanner_repo_root_accepts_expected_structure():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "ui" / "views").mkdir(parents=True)
        (root / ".venv" / "bin").mkdir(parents=True)
        (root / "ui" / "views" / "main_window.py").write_text("", encoding="utf-8")
        (root / "ui" / "views" / "profile_manager.py").write_text("", encoding="utf-8")
        (root / "ui" / "app.py").write_text("", encoding="utf-8")
        (root / ".venv" / "bin" / "python").write_text("", encoding="utf-8")

        validated = validate_scanner_repo_root(root)

    assert validated == root.resolve()


def validate_scanner_repo_root_rejects_missing_structure():
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        try:
            validate_scanner_repo_root(root)
        except ValueError as exc:
            assert "Scanner repo missing required paths" in str(exc)
        else:
            raise AssertionError("Expected ValueError for missing scanner repo structure")


def scanner_runtime_packet_maps_named_widgets():
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = Path(tmp)
        window = FakeWindow()
        window.show()
        APP.processEvents()
        packet = build_packet_for_window(window, repo_root=repo_root)
        window.close()
        APP.processEvents()

    node_ids = {node["id"] for node in packet["nodes"]}
    nodes_by_id = {node["id"]: node for node in packet["nodes"]}

    assert packet["source_provider"] == "scanner_qt_runtime_probe"
    assert packet["trust_level"] == "partial"
    assert packet["roots"] == ["scanner_main_window"]
    assert "scanner_main_window" in node_ids
    assert "profile_input" in node_ids
    assert "run_button" in node_ids
    assert nodes_by_id["scanner_main_window"]["ui_role"] == "tool_window"
    assert nodes_by_id["profile_input"]["type"] == "input"
    assert nodes_by_id["run_button"]["type"] == "button"
    assert nodes_by_id["run_button"]["render_hints"]["text"] == "Run"


def scanner_profile_manager_packet_maps_dialog_root():
    with tempfile.TemporaryDirectory() as tmp:
        repo_root = Path(tmp)
        dialog = FakeProfileManager()
        dialog.show()
        APP.processEvents()
        packet = build_packet_for_profile_manager(dialog, repo_root=repo_root)
        dialog.close()
        APP.processEvents()

    node_ids = {node["id"] for node in packet["nodes"]}
    nodes_by_id = {node["id"]: node for node in packet["nodes"]}

    assert packet["roots"] == ["scanner_profile_manager_dialog"]
    assert "scanner_profile_manager_dialog" in node_ids
    assert "name_input" in node_ids
    assert "save_button" in node_ids
    assert nodes_by_id["scanner_profile_manager_dialog"]["ui_role"] == "dialog"
    assert nodes_by_id["scanner_profile_manager_dialog"]["source"]["symbol"] == "ProfileManagerDialog"
    assert nodes_by_id["save_button"]["render_hints"]["text"] == "Save"


def real_scanner_main_window_packet_recovers_source_ranges():
    packet = build_scanner_main_window_packet("/Users/kogaryu/dev/scanner")
    nodes_by_id = {node["id"]: node for node in packet["nodes"]}

    assert nodes_by_id["scanner_main_window"]["source"]["line_start"] is not None
    assert nodes_by_id["central_widget"]["children"] == [
        "scanner_controls_region",
        "scanner_results_region",
        "scanner_details_region",
    ]
    assert nodes_by_id["profile_combo"]["source"]["line_start"] is not None
    assert nodes_by_id["run_button"]["source"]["line_start"] is not None
    assert nodes_by_id["central_widget"]["type"] == "container"
    assert nodes_by_id["results_table"]["ui_role"] == "main"
    assert nodes_by_id["scanner_controls_region"]["ui_role"] == "toolbar"
    assert nodes_by_id["scanner_results_region"]["ui_role"] == "main"
    assert nodes_by_id["profile_combo"]["parent"] == "scanner_controls_region"
    assert nodes_by_id["results_table"]["parent"] == "scanner_results_region"
    assert nodes_by_id["news_text"]["parent"] == "scanner_details_region"
    assert int(nodes_by_id["central_widget"]["layout_hints"]["width"] or 0) > 500
    assert int(nodes_by_id["profile_combo"]["layout_hints"]["width"] or 0) < int(
        nodes_by_id["scanner_controls_region"]["layout_hints"]["width"] or 0
    )
    assert int(nodes_by_id["results_table"]["layout_hints"]["height"] or 0) > 100
    assert int(nodes_by_id["profile_combo"]["layout_hints"]["x"] or 0) >= 0
    assert int(nodes_by_id["profile_combo"]["layout_hints"]["y"] or 0) >= 0
    assert int(nodes_by_id["results_table"]["layout_hints"]["x"] or 0) >= 0
    assert int(nodes_by_id["results_table"]["layout_hints"]["y"] or 0) >= 0
    assert "ui_role inferred from scanner main window semantics" in nodes_by_id["results_table"]["trust"]["warnings"]


def real_scanner_profile_manager_packet_recovers_source_ranges():
    packet = build_scanner_profile_manager_packet("/Users/kogaryu/dev/scanner")
    nodes_by_id = {node["id"]: node for node in packet["nodes"]}

    assert nodes_by_id["scanner_profile_manager_dialog"]["source"]["line_start"] is not None
    assert nodes_by_id["scanner_profile_manager_dialog"]["children"] == [
        "profile_manager_sidebar_region",
        "profile_manager_form_region",
    ]
    assert nodes_by_id["name_input"]["source"]["line_start"] is not None
    assert nodes_by_id["save_button"]["source"]["line_start"] is not None
    assert nodes_by_id["field_inputs_price_min"]["source"]["line_start"] is not None
    assert nodes_by_id["field_inputs_news_lookback_minutes"]["type"] == "input"
    assert nodes_by_id["profile_manager_sidebar_region"]["type"] == "container"
    assert nodes_by_id["profile_manager_sidebar_region"]["ui_role"] == "sidebar"
    assert nodes_by_id["profile_list"]["parent"] == "profile_manager_sidebar_region"
    assert nodes_by_id["name_input"]["parent"] == "profile_manager_form_region"
    assert int(nodes_by_id["scanner_profile_manager_dialog"]["layout_hints"]["width"] or 0) > 500
    assert int(nodes_by_id["profile_list"]["layout_hints"]["width"] or 0) <= int(
        nodes_by_id["profile_manager_sidebar_region"]["layout_hints"]["width"] or 0
    )
    assert int(nodes_by_id["name_input"]["layout_hints"]["width"] or 0) < int(
        nodes_by_id["profile_manager_form_region"]["layout_hints"]["width"] or 0
    )
    assert int(nodes_by_id["profile_list"]["layout_hints"]["x"] or 0) >= 0
    assert int(nodes_by_id["profile_list"]["layout_hints"]["y"] or 0) >= 0
    assert int(nodes_by_id["name_input"]["layout_hints"]["x"] or 0) >= 0
    assert int(nodes_by_id["name_input"]["layout_hints"]["y"] or 0) >= 0
    assert nodes_by_id["profile_list"]["ui_role"] == "sidebar"
    assert "ui_role inferred from scanner profile manager semantics" in nodes_by_id["profile_list"]["trust"]["warnings"]


def run_all_tests():
    tests = [
        validate_scanner_repo_root_accepts_expected_structure,
        validate_scanner_repo_root_rejects_missing_structure,
        scanner_runtime_packet_maps_named_widgets,
        scanner_profile_manager_packet_maps_dialog_root,
        real_scanner_main_window_packet_recovers_source_ranges,
        real_scanner_profile_manager_packet_recovers_source_ranges,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            APP.processEvents()
            passed += 1
            print(f"PASS {test.__name__}")
        except Exception as exc:
            failed += 1
            print(f"FAIL {test.__name__}: {exc}")

    print(f"\nResult: {passed} passed, {failed} failed")

    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    run_all_tests()
