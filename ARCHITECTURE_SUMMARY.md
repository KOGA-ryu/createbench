# Architecture Summary

## Core Systems

### property_registry
- schema compiler
- inheritance + defaults
- validation

### layout_model
- tree structure
- node storage
- id generation

### tree_manager
- structural operations
- no business logic

### selection_state
- current selection
- event notifications

### checklist_engine
- validation layer
- issue generation

### dsl_builder
- deterministic export
- DSL + JSON

## UI Systems

### canvas
- visual layout
- direct manipulation

### inspector
- schema-driven editing

### checklist_panel
- validation display

### main_window
- layout assembly only

## Data Flow

user -> canvas/inspector -> layout_model -> checklist -> export

## Key Guarantees

- deterministic output
- explicit state
- schema-driven behavior
- no hidden coupling
