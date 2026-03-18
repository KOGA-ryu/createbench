# Build Rules

All code must follow these rules:

## 1. Follow .md specs exactly
- Each file has a contract
- Do not deviate

## 2. No hidden behavior
- No side effects outside defined flow

## 3. No cross-layer violations
- UI does not mutate structure directly
- Core does not depend on UI

## 4. Determinism required
- Same input = same output

## 5. No silent fixes
- Invalid states must be visible

## 6. Schema is the source of truth
- Do not hardcode property logic

## 7. Keep systems isolated
- layout_model -> structure
- inspector -> editing
- checklist -> validation
- export -> output

## 8. No overengineering
- MVP simplicity preferred
