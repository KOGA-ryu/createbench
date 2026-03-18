# File: engine/lock_manager.py

## Purpose

Defines the central lock policy for engine-driven interactions. Acts as the single source of truth for whether a node may move or resize.

## Responsibilities

* decide whether a node can move
* decide whether a node can resize

## Inputs

* node objects with geometry-related properties

## Outputs

* bool move permission
* bool resize permission

## Public API

* `can_move(node) -> bool`
* `can_resize(node) -> bool`

## Lock Rules

* `locked = true` blocks move
* `locked = true` blocks resize
* locked nodes remain selectable
* semantic property editing remains allowed
* no lock inheritance in MVP

## Internal Logic

* reads `locked` from node properties
* defaults to unlocked if property is missing
* contains no side effects

## Dependencies

* none

## Constraints

* must NOT mutate node state
* must NOT manage selection
* must NOT import Qt
* must remain tiny and deterministic

## Edge Cases

* missing `locked` property
* non-bool `locked` values from legacy states

## Tests

1. locked node cannot move
2. locked node cannot resize
3. unlocked node can move
4. unlocked node can resize

## Decisions Locked

* lock policy is explicit and local to the node
* selection is never blocked by locking
* no inherited locking in MVP
