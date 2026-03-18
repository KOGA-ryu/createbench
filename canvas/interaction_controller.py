class InteractionController:
    def __init__(self, layout_model, selection_state):
        self.model = layout_model
        self.selection_state = selection_state
        self.active_drag_id = None

    def start_drag(self, node_id):
        self.active_drag_id = node_id

    def end_drag(self, target_node_id, position):
        self.active_drag_id = None
