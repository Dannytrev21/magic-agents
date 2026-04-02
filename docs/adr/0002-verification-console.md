# ADR 0002: Center-Pane Verification Console

## Status

Accepted

## Context

After U1 through U5, the React workspace could negotiate specs and inspect evidence, but the operator still had to cross an architectural seam to compile specs, generate proof artifacts, monitor execution, and post Jira feedback. The older contract also treated EARS approval as mostly a frontend concern, which left compile and pipeline endpoints callable even when the UI correctly showed them as locked.

## Decision

- Keep verification work in the center pane as a session-scoped console instead of introducing a separate route or modal workflow.
- Persist approval metadata, artifact viewers, pipeline events, and Jira feedback state per session so operators can move between workspace tabs without losing verification context.
- Use the existing FastAPI contract with additive fields for compiled specs, generated tests, and SSE pipeline events instead of inventing client-side YAML parsing or synthetic run state.
- Enforce the EARS approval gate on the server for compile, generate-tests, run-tests, evaluate, and pipeline-stream endpoints so disabled controls cannot be bypassed with direct requests.
- Treat the post-run surface as a first-class operator view: summary first, per-AC evidence second, Jira update last.

## Consequences

- Negotiation and proof-of-correctness now share one dominant workspace, which keeps the product aligned with the operator workflow described in the production spec.
- The frontend can revisit compiled YAML, generated tests, and live pipeline output without introducing a global store or route churn.
- Backend changes stay additive for existing consumers while tightening correctness around approval gating.
- Future rollout and accessibility work should refine this console in place rather than splitting execution into a detached UI flow.
