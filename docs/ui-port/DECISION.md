# UI Port Decision Record

## Problem

Choose the stronger implementation plan between `docs/ui-port` and `docs/ui-port-claude`, then produce one final plan in `docs/ui-port`.

## Tree of Thought Summary

### Root

Which plan gives Magic Agents the best path to a real Operator Workspace for the current backend and product shape?

### Branch A: Keep `docs/ui-port` as-is

**Thought:** This plan is already aligned to the current FastAPI app, the existing endpoints, and the React + TypeScript + Vite direction.

**Evaluation:**
- Feasibility: sure
- Estimated complexity: medium
- Confidence: 8/10

**Strengths:**
- Correctly centers the product on operator workflow instead of generic dashboard styling.
- Strong on backend compatibility, typed API boundaries, rollout, and testing.
- Uses better React architecture defaults and acknowledges current API reality.

**Weaknesses:**
- Some stories are too broad and leave important UI behaviors under-specified.
- Missing several concrete interaction details that would help implementation quality.

**Status:** EXPLORE

### Branch B: Replace with `docs/ui-port-claude`

**Thought:** This set is more concrete in shell behavior, panel behavior, and view-level interactions.

**Evaluation:**
- Feasibility: maybe
- Estimated complexity: medium-high
- Confidence: 5/10

**Strengths:**
- Stronger on exact panel behavior, top bar details, timeline ideas, transcript rendering, and results presentation.
- Better micro-interaction specificity.

**Weaknesses:**
- Drifts from the real backend in several places.
- Assumes endpoints and telemetry that do not exist yet.
- Uses React 18 instead of the current React 19 recommendation.
- Leans harder on card-based rendering than the chosen visual direction warrants.

**Status:** PRUNE as the primary base

### Branch C: Hybrid

**Thought:** Keep `docs/ui-port` as the base architecture and merge in the concrete workflow details from `docs/ui-port-claude`, rewriting any mismatched API or product assumptions.

**Evaluation:**
- Feasibility: sure
- Estimated complexity: medium
- Confidence: 9/10

**Why this branch wins:**
- Preserves the stronger backend-aware plan.
- Improves implementation quality by importing the stronger UI specifics.
- Avoids adopting wrong technical assumptions from the Claude draft.

## Selected Features from `ui-port-claude`

- Design tokens, font rules, and UI primitives
- Top bar with session context
- Panel collapse and responsive panel behavior
- Left-rail AC checklist
- Left-rail phase timeline
- Session health telemetry as a conditional story tied to backend usage data
- Active-phase transcript view
- Sticky phase mini-rail and breadcrumb context
- Spec contract viewer
- Richer results summary and empty/error handling

## Rejected or Rewritten Features

- Replace React 18 assumptions with React 19
- Rewrite endpoint assumptions to match current FastAPI routes or mark them as backend dependencies
- Remove any default drift toward card mosaics or boxed dashboard composition
- Treat generic SSE/event-store work as dependent on backend structured event support rather than assuming it already exists

## Final Decision

The final plan in `docs/ui-port` is a hybrid:

- `docs/ui-port` remains the canonical plan
- `docs/ui-port-claude` contributes concrete interaction details
- all imported features are rewritten to fit the actual Magic Agents backend, UI thesis, and React/Vite architecture

## Implemented U5 Decisions

- Keep inspector work session-scoped and subordinate to the selected story and AC instead of introducing a parallel route tree.
- Use on-demand inspector actions for planner, critique, spec diff, compile, and scan work so the center pane never resets during evidence inspection.
- Return parsed requirement and traceability data from `/api/compile` so the contract viewer stays structured without adding client-side YAML parsing complexity.
- Share acceptance-criterion selection between the left rail, center pane, and inspector so traceability and structured spec requirements can cross-highlight the same proof chain.
