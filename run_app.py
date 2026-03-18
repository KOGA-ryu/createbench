from PySide6.QtWidgets import QApplication
import sys

from export.dsl_builder import DSLBuilder
from state.app_state import AppState
from ui.main_window import MainWindow


def main():
    if "--export-test" in sys.argv:
        state = AppState("createbench/schemas/core")
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

    app = QApplication(sys.argv)

    state = AppState("createbench/schemas/core")

    window = MainWindow(state)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
