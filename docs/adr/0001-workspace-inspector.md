# ADR 0001: Session-Scoped Workspace Inspector

## Status

Accepted

## Context

The React workspace needs a right-side inspector that can surface proof-of-correctness artifacts while the operator continues the phase-by-phase negotiation flow. The backend already exposes additive endpoints for scan status, scan execution, planning, critique, spec diff, and compiled specs, but the older UI patterns hid those surfaces behind separate screens or raw endpoints.

## Decision

- Keep the inspector mounted inside the three-pane workspace and subordinate to the selected session and acceptance criterion.
- Trigger scan, planner, critique, spec-diff, and compile work from the inspector via TanStack Query mutations instead of route changes.
- Share acceptance-criterion selection between the left rail, center pane, and inspector so traceability and contract views can cross-highlight the same proof chain.
- Extend `/api/compile` with parsed `requirements` and `traceability` fields so the UI can render a structured contract viewer without adding client-side YAML parsing.
- Keep raw YAML available beside the structured contract so operators can compare the human-readable artifact and the rendered requirement view.

## Consequences

- Inspector actions do not wipe center-pane draft state or force the operator onto a secondary workflow.
- The UI can render per-AC traceability, matrix scanning, and contract routing details from stable backend-generated identifiers.
- Backend changes remain additive and low-risk for existing consumers.
- Future inspector work should continue treating evidence surfaces as secondary tools around the main negotiation loop, not as primary navigation destinations.
