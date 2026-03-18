from PySide6.QtWidgets import QApplication
import sys
from pathlib import Path

from engine.layout_engine import LayoutEngine
from export.dsl_builder import DSLBuilder
from state.app_state import AppState
from ui.main_window import MainWindow


PROJECT_ROOT = Path(__file__).resolve().parent
CORE_SCHEMAS = str(PROJECT_ROOT / "schemas" / "core")


def main():
    if "--export-test" in sys.argv:
        state = AppState(CORE_SCHEMAS)
        document = state.layout_model.create_node("document", {})
        container = state.layout_model.create_node("container", {})
        button = state.layout_model.create_node("button", {"text": "Save"})
        state.layout_model.add_node(state.layout_model.root_id, document)
        state.layout_model.add_node(document.id, container)
        state.layout_model.add_node(container.id, button)
        builder = DSLBuilder(
            state.layout_model, state.property_registry, state.checklist_engine
        )
        print(builder.build_dsl())
        sys.exit(0)

    if "--engine-smoke" in sys.argv:
        state = AppState(CORE_SCHEMAS)
        engine = LayoutEngine(state.layout_model)
        document = state.layout_model.create_node("document", {"layout_mode": "auto"})
        toolbar = state.layout_model.create_node("panel", {"layout_mode": "auto", "title": "Toolbar"})
        horizontal = state.layout_model.create_node("horizontal", {"layout_mode": "auto"})
        sidebar = state.layout_model.create_node("sidebar", {"layout_mode": "auto"})
        main = state.layout_model.create_node("main", {"layout_mode": "auto"})
        free_panel = state.layout_model.create_node(
            "panel",
            {"layout_mode": "free", "x": 420, "y": 160, "width": 240, "height": 160, "title": "Free Panel"},
        )
        state.layout_model.add_node(state.layout_model.root_id, document)
        state.layout_model.add_node(document.id, toolbar)
        state.layout_model.add_node(document.id, horizontal)
        state.layout_model.add_node(document.id, free_panel)
        state.layout_model.add_node(horizontal.id, sidebar)
        state.layout_model.add_node(horizontal.id, main)
        rect_map = engine.compute_layout(state.layout_model.root_id, {"x": 0, "y": 0, "width": 1200, "height": 800})
        checklist = state.checklist_engine.run()
        print("ENGINE_SMOKE_RECT_MAP")
        for node_id in engine.draw_order:
            print(node_id, rect_map[node_id])
        print("ENGINE_SMOKE_CHECKLIST")
        print(checklist["summary"])
        sys.exit(0)

    app = QApplication(sys.argv)

    state = AppState(CORE_SCHEMAS)

    window = MainWindow(state)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
