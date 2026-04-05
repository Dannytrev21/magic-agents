# ADR 0003: UI Design System, Accessibility, and Motion

## Status

Accepted

## Context

The React operator workspace reached feature-complete coverage for the core workflow in epics U1 through U6, but the UI polish layer was still under-specified. Tokens lived only in CSS, focus management existed only for pane swaps, and pipeline/session status changes were visible but not announced. That made it too easy for future changes to drift into card-heavy styling, inconsistent motion timing, or inaccessible state transitions.

## Decision

Adopt a typed UI design-system module at [`/Users/dannytrevino/development/magic-agents/ui/src/styles/system.ts`](/Users/dannytrevino/development/magic-agents/ui/src/styles/system.ts) as the canonical source for:

- the visual thesis and surface map
- shared color, spacing, radius, material, shadow, and motion tokens
- the reduced-motion baseline for the workspace

Mirror the cross-cutting token values into [`/Users/dannytrevino/development/magic-agents/ui/src/styles/tokens.css`](/Users/dannytrevino/development/magic-agents/ui/src/styles/tokens.css) so CSS Modules can consume them without local magic numbers.

Standardize accessibility and motion behavior around these rules:

- major session, phase, and pipeline transitions announce through a polite live region
- focus returns to the active workspace after session start, phase advancement, and pipeline completion
- workspace and verification surfaces expose explicit busy/log semantics during in-place updates
- motion uses shared timing tokens and must degrade cleanly under `prefers-reduced-motion`

## Consequences

### Positive

- UI polish decisions now have a durable home instead of being spread across unrelated CSS files.
- New frontend work can extend the existing graphite/bone/signal visual language without re-deriving it.
- Accessibility requirements are enforced at the shell/workspace level rather than depending on ad hoc component behavior.
- Motion changes are less likely to regress performance or become ornamental because they share one vocabulary.

### Tradeoffs

- New global tokens now require a small amount of duplication between TypeScript and CSS.
- Live announcements introduce another state channel in the shell, so new major transitions should update it intentionally instead of ignoring it.
