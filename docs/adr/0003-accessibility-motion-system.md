# ADR 0003: Workspace Accessibility and Motion System

## Status

Accepted

## Context

After U1 through U6, the React workspace had the right product structure, but it still looked and behaved like an intermediate port: dark-first tokens, weak distinction between persistent state and transient announcements, and only partial semantics for the active workspace surfaces. U7 needed to establish a durable visual and accessibility baseline before Epic U8 adds more testing and rollout work.

## Decision

- Reframe the shared UI system around a light graphite/bone palette with one amber signal accent and keep mono typography restricted to references, IDs, paths, and artifact-like text.
- Treat the app shell as the accessibility backbone for the operator workflow by adding named workspace status and announcement regions instead of relying on unlabeled status text.
- Wire the active center-pane, inspector, and verification-artifact views as semantic tabpanels so keyboard and assistive-technology users can understand which workspace surface is active.
- Move focus intentionally after major workflow transitions such as session start, successful phase actions, and pipeline completion.
- Keep motion CSS-first with shared timing tokens and a global `prefers-reduced-motion` fallback that strips nonessential animation and smooth scrolling.
- Add snapshot and axe-backed tests around the shell, negotiation workspace, and verification console to guard the design/accessibility system as a product surface, not just a style layer.

## Consequences

- Future UI work inherits one clear visual direction and can extend the workspace without re-litigating palette, typography, or motion defaults.
- Accessibility regressions in shell state, announcements, and active-panel semantics are now easier to catch in the frontend test suite.
- Motion remains lightweight and easier to reason about because it does not depend on extra client state or a dedicated animation framework.
- U8 can focus on broader coverage, performance, and rollout because the core operator workspace now has a stable visual and accessibility foundation.
