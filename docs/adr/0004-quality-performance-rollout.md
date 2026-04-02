# ADR 0004: UI Quality Gates and Rollout Controls

## Status

Accepted

## Context

By the time the React operator workspace covered epics U1 through U7, the feature set was effectively complete but the ship criteria were still soft. The frontend had strong targeted Vitest coverage, but it lacked an explicit CI-shaped gate, a durable browser journey harness, and a documented way to compare the new React entrypoint with the legacy HTML surface during rollout. The production build also served one main shell chunk with only the inspector analyst view lazy-loaded, which made it too easy for later changes to grow the shipped payload without a recorded threshold.

## Decision

Adopt a three-part rollout and quality model:

- separate frontend verification into `npm run test:ui`, `npm run test:e2e`, and `npm run test:ci` so browser coverage remains optional and independent from the faster component/integration gate
- treat `npm run test:ci` as the baseline contributor gate for UI-only changes, while keeping `npm run test:e2e` additive for release validation, regression investigation, and environments that use the remote Playwright server path
- cap Vitest worker fan-out at `1` for the shared jsdom-heavy UI suite so the non-browser gate stays deterministic on constrained local and Codex-hosted macOS environments
- keep the core operator journey deterministic in Playwright by routing all browser tests through mocked API/SSE fixtures with retained screenshots on failure and opt-in traces via `PW_TRACE=1` or CI
- keep the shell CSS gzip ceiling fixed at `7 kB`, but allow the raw shell CSS budget to rise to `36 kB` when shipped operator chrome grows without materially changing compressed transfer size
- treat the FastAPI root as a reversible rollout boundary by supporting `MAGIC_AGENTS_FRONTEND_MODE=auto|react|legacy` and `/?frontend=react|legacy` overrides while preserving the legacy HTML entrypoint

Add bundle budgets as part of the shipped contract by generating a Vite manifest and checking the entry shell plus lazy-loaded workspace chunks from [`/Users/dannytrevino/development/magic-agents/ui/config/bundle-budgets.json`](/Users/dannytrevino/development/magic-agents/ui/config/bundle-budgets.json). Keep the verification console behind a lazy import so artifact-heavy proof surfaces do not inflate the initial workspace shell.
Treat a budget failure as a regression in the shipped product surface. The default response is to trim shell chrome or split code further; budget increases require an intentional scope change rather than a convenience edit.

Pin the shared Vitest DOM contract in [`/Users/dannytrevino/development/magic-agents/ui/src/test/setup.ts`](/Users/dannytrevino/development/magic-agents/ui/src/test/setup.ts) so observer APIs, media-query APIs, and inert scroll helpers are present across hosts. Component and integration failures should reflect product drift, not missing browser primitives in the local jsdom runtime.

Make the Playwright browser runtime explicit and environment-selectable. Keep Chromium, Firefox, and WebKit available through `PLAYWRIGHT_BROWSER` or dedicated package scripts instead of hard-wiring a single engine into the shared config. Add a supported remote-browser path through `playwright run-server` plus `PW_TEST_CONNECT_WS_ENDPOINT` so Codex-hosted or otherwise restricted environments can still execute the deterministic mocked operator journey without launching browsers locally.
Scope typed linting to tracked source and Playwright config/spec files through [`/Users/dannytrevino/development/magic-agents/ui/tsconfig.eslint.json`](/Users/dannytrevino/development/magic-agents/ui/tsconfig.eslint.json), and ignore generated browser caches and build output so the lint gate fails on product code instead of local tool artifacts.

## Consequences

### Positive

- Frontend regressions now have explicit coverage layers instead of relying on convention.
- Contributors now have a single non-browser gate that remains valid even when local browser launch is restricted and that fails fast on lint/config drift before spending time in build or test steps.
- Shared DOM polyfills now keep the non-browser gate stable across host environments that do not expose every browser primitive by default.
- Browser journeys can be exercised without a live FastAPI or Jira backend because the Playwright suite owns its mocks.
- Browser coverage is the layer that catches rendered workflow copy and selector drift in the intake-to-verification journey when component and integration tests still pass.
- Once the UI-port tracker is fully complete, failing `npm run test:ci`, failing `npm run test:e2e:chromium`, or drift between `progress.json` and the epic markdown files becomes the primary signal that UI work is still unfinished.
- Browser choice no longer blocks diagnosis when one engine is incompatible with the host sandbox.
- Restricted hosts can keep using the same Playwright suite by connecting to a separately launched browser runtime.
- Rollout and rollback decisions no longer require code edits or branch-specific static file shuffling.
- Bundle growth becomes visible in CI before it silently lands in the shipped workspace.

### Tradeoffs

- The browser suite now depends on local Playwright browser installs, and contributors need to know which engine failed before treating the problem as an app regression.
- Remote-browser usage adds one more moving part: the browser server endpoint and, optionally, the app server base URL.
- Local debug runs no longer get Playwright traces automatically; contributors need to opt in with `PW_TRACE=1` when the host can persist trace archives cleanly.
- The shared test-runtime shim needs to stay lean; adding too many browser fallbacks there can hide a real production/runtime mismatch if contributors stop checking whether the app itself relies on unavailable APIs.
- The backend root handler now carries a small amount of rollout logic in addition to asset resolution.
- Build output includes a Vite manifest and another verification script that contributors need to keep aligned with future code-splitting changes.
- ESLint now depends on a dedicated project file for tracked frontend and Playwright sources, so new frontend entrypoints or tooling files need to be added there when they become part of the shipped surface.
