# ADR 0004: UI Quality Gates and Rollout Controls

## Status

Accepted

## Context

By the time the React operator workspace covered epics U1 through U7, the feature set was effectively complete but the ship criteria were still soft. The frontend had strong targeted Vitest coverage, but it lacked an explicit CI-shaped gate, a durable browser journey harness, and a documented way to compare the new React entrypoint with the legacy HTML surface during rollout. The production build also served one main shell chunk with only the inspector analyst view lazy-loaded, which made it too easy for later changes to grow the shipped payload without a recorded threshold.

## Decision

Adopt a three-part rollout and quality model:

- separate frontend verification into `npm run test:ui`, `npm run test:e2e`, and `npm run test:ci` so browser coverage remains optional and independent from the faster component/integration gate
- keep the core operator journey deterministic in Playwright by routing all browser tests through mocked API/SSE fixtures with retained traces and screenshots on failure
- treat the FastAPI root as a reversible rollout boundary by supporting `MAGIC_AGENTS_FRONTEND_MODE=auto|react|legacy` and `/?frontend=react|legacy` overrides while preserving the legacy HTML entrypoint

Add bundle budgets as part of the shipped contract by generating a Vite manifest and checking the entry shell plus lazy-loaded workspace chunks from [`/Users/dannytrevino/development/magic-agents/ui/config/bundle-budgets.json`](/Users/dannytrevino/development/magic-agents/ui/config/bundle-budgets.json). Keep the verification console behind a lazy import so artifact-heavy proof surfaces do not inflate the initial workspace shell.

## Consequences

### Positive

- Frontend regressions now have explicit coverage layers instead of relying on convention.
- Browser journeys can be exercised without a live FastAPI or Jira backend because the Playwright suite owns its mocks.
- Rollout and rollback decisions no longer require code edits or branch-specific static file shuffling.
- Bundle growth becomes visible in CI before it silently lands in the shipped workspace.

### Tradeoffs

- The browser suite now depends on a local Playwright browser install and can still be blocked by platform sandbox restrictions even when the tests themselves are valid.
- The backend root handler now carries a small amount of rollout logic in addition to asset resolution.
- Build output includes a Vite manifest and another verification script that contributors need to keep aligned with future code-splitting changes.
