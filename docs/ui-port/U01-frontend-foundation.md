# Epic U1: Frontend Foundation and App Shell

**Priority:** 1 (Critical)  
**Implementation Target:** new `ui/` React + TypeScript + Vite workspace integrated with FastAPI static serving  
**Current Replacement Surface:** `static/index.html`, `src/verify/negotiation/web.py`

## Rationale

The current frontend is a single HTML file with inline CSS and JavaScript. That is fast for prototyping but too brittle for the Operator Workspace direction. Before layout or feature work matters, the project needs a typed frontend boundary, a predictable build pipeline, and a reusable shell that can host the three-pane workspace without turning state management into ad hoc DOM mutation.

---

## Story U1.1: Scaffold the React + TypeScript + Vite frontend

### EARS Requirement

> **When** a developer builds the UI, the system **shall** produce a versioned static frontend bundle that FastAPI can serve without changing any existing API routes.

### Design by Contract

**Preconditions:**
- Node and the package manager are installed in the dev environment.
- FastAPI continues to own all `/api/*` routes.

**Postconditions:**
- A build command outputs static assets for the Operator Workspace.
- The backend serves the built app in development and production-compatible modes.
- Existing web API endpoints remain unchanged.

**Invariants:**
- API ownership stays in Python.
- Frontend assets are fingerprinted for cache safety.
- The React app boots without requiring backend template rendering.

### Acceptance Criteria

- [ ] A `ui/` workspace exists with React, TypeScript, Vite, linting, and formatting configured.
- [ ] Local development supports a proxy from the Vite dev server to FastAPI.
- [ ] Production build output is served by FastAPI.
- [ ] No existing `/api/*` route signatures are changed as part of the scaffold.

### How to Test

- Run the UI dev server and confirm API calls proxy correctly to FastAPI.
- Run the production build and verify FastAPI serves the compiled app.
- Re-run existing backend web tests to confirm the API surface did not regress.

---

## Story U1.2: Establish a typed API client and query layer

### EARS Requirement

> **When** the frontend reads or mutates negotiation state, the system **shall** do so through typed API functions and query hooks rather than inline `fetch()` calls scattered across components.

### Design by Contract

**Preconditions:**
- The FastAPI endpoints for stories, sessions, negotiation, scan, compile, and pipeline execution are reachable.
- The frontend shell provides a query client provider.

**Postconditions:**
- Each UI workflow action maps to a typed request and response shape.
- Query invalidation rules are explicit for mutations that change session state.
- SSE and long-running pipeline interactions have dedicated adapters.

**Invariants:**
- Components do not build URLs by hand.
- Server state remains normalized at the API-layer boundary.
- Independent requests can be started in parallel.

### Acceptance Criteria

- [ ] A dedicated API module defines typed functions for the current FastAPI endpoints.
- [ ] TanStack Query manages read and mutation lifecycles for story intake and session workflows.
- [ ] SSE pipeline streaming is wrapped in a reusable client adapter.
- [ ] Direct `fetch()` usage in presentational components is forbidden by convention.

### How to Test

- Add unit tests for the API client request/response adapters.
- Add React tests that mock query results and verify loading, success, and failure states.
- Manually confirm parallel fetches do not block the workspace shell unnecessarily.

---

## Story U1.3: Build the application shell and provider stack

### EARS Requirement

> **While** the Operator Workspace is active, the system **shall** render a stable application shell that owns global providers, layout primitives, and top-level navigation state.

### Design by Contract

**Preconditions:**
- The frontend entrypoint is mounted.
- Query, router, and theme providers are available.

**Postconditions:**
- The shell exposes slots for the left rail, center workspace, and right inspector.
- Global errors and empty initialization states can render without crashing child views.
- Top-level navigation state is owned by React rather than direct DOM mutation.

**Invariants:**
- No inline component definitions inside render bodies for shell primitives.
- Shell layout primitives are reusable across screens and test fixtures.
- Non-urgent shell changes use transitions when they would otherwise block input.

### Acceptance Criteria

- [ ] The app has a single root shell with provider composition.
- [ ] Layout primitives exist for rails, inspectors, sections, and artifact panels.
- [ ] Top-level error boundary and not-found fallback are present.
- [ ] The shell can host a placeholder three-pane layout before feature surfaces are ported.

### How to Test

- Render the app shell in unit tests with mocked providers.
- Trigger a simulated API failure and verify the shell displays a controlled error state.
- Verify keyboard navigation reaches the primary shell regions in a predictable order.

---

## Story U1.4: Establish the tokenized visual system and typography rules

### EARS Requirement

> **When** any Operator Workspace surface renders, the system **shall** use a tokenized visual system for color, spacing, typography, radius, and motion timing so the interface stays visually consistent and easy to evolve.

### Design by Contract

**Preconditions:**
- The frontend scaffold exists.
- Global styles can be loaded once by the app shell.

**Postconditions:**
- Design tokens are defined centrally and consumed across the app.
- Product copy uses the primary sans-serif family.
- IDs, refs, paths, and code-like content use the mono family.
- Font loading uses non-blocking behavior appropriate for app UI.

**Invariants:**
- Routine feature components do not hardcode their own color system.
- Accent color remains reserved for action, state, and emphasis.
- The visual language supports dense operator workflows without looking decorative.

### Acceptance Criteria

- [ ] Global tokens cover color, spacing, typography, radius, and motion durations.
- [ ] The workspace defaults to sans-serif product copy and mono for IDs/refs.
- [ ] Hardcoded visual values are avoided outside the token definitions or narrowly justified exceptions.
- [ ] Font loading does not block first paint.

### How to Test

- Add style-level checks or lint rules for token usage in shared surfaces.
- Verify computed font families for body copy versus IDs and refs.
- Capture visual snapshots of the shell and key panes to confirm token consistency.

---

## Story U1.5: Build accessible UI primitives for the workspace

### EARS Requirement

> **When** feature teams build workspace surfaces, the system **shall** provide typed, reusable UI primitives for the most common controls and layout patterns instead of recreating them ad hoc.

### Design by Contract

**Preconditions:**
- Design tokens and global typography rules are in place.
- The React app supports a shared component library.

**Postconditions:**
- Shared primitives exist for buttons, badges, section headers, dividers, skeletons, mono text, and artifact/panel containers.
- Primitives are typed and composable.
- Interactive primitives expose accessible names, states, and visible focus.

**Invariants:**
- Primitives prefer layout and section structure over ornamental box styling.
- Shared controls can be composed without forcing a card-heavy UI.
- Feature components can extend primitives without bypassing accessibility behavior.

### Acceptance Criteria

- [ ] A shared primitive set exists for common interactive and display needs.
- [ ] Interactive primitives support keyboard focus and disabled/loading states.
- [ ] Shared text primitives distinguish product copy from IDs and refs.
- [ ] Skeleton and empty-state primitives exist for async loading surfaces.

### How to Test

- Add unit tests for the primitive variants and focus behavior.
- Run accessibility checks against shared controls.
- Verify feature surfaces can be assembled without reintroducing raw, inconsistent control styling.
