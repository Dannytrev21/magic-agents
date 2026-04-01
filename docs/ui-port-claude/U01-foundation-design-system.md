# Epic U01: Foundation & Design System

**Priority:** 1 (Critical — everything else builds on this)
**Stack:** React 18 + TypeScript + Vite
**Design Direction:** Operator Workspace — calm, high-trust product UI

## Visual Thesis

Graphite (`#2B2B2B`), bone (`#F2EDE8`), and one sharp signal color (electric amber `#F59E0B`) as the sole accent. Sans-serif for product copy (Instrument Sans or similar), monospace only for requirement IDs, spec refs, and code snippets. No gradients, no shadows heavier than `0 1px 2px`. Confidence expressed through restraint.

---

## Story U01.1: Vite + React + TypeScript Project Scaffold

### EARS Requirement

> The system **shall** provide a Vite-based React + TypeScript project at `ui/` within the magic-agents repository, configured with path aliases (`@/`), strict TypeScript, ESLint, and a `dev` script that serves on port 5173 with API proxy to the FastAPI backend on port 8000.

### Design by Contract

**Preconditions:**
- Node.js >= 18 and npm are available on the developer's machine.
- The FastAPI backend is running on `localhost:8000`.

**Postconditions:**
- `npm run dev` starts the Vite dev server on port 5173.
- API calls to `/api/*` are proxied to `localhost:8000`.
- TypeScript strict mode is enabled (`strict: true` in `tsconfig.json`).
- Path aliases resolve `@/components/Foo` to `ui/src/components/Foo.tsx`.
- ESLint is configured with `@typescript-eslint` and React rules.

**Invariants:**
- Hot module replacement works for all `.tsx` and `.css` files.
- Build (`npm run build`) produces a `dist/` folder with zero TypeScript errors.

### Acceptance Criteria

- [ ] `ui/package.json` exists with `react`, `react-dom`, `typescript`, `vite` dependencies.
- [ ] `npm run dev` serves the app and proxies `/api` to port 8000.
- [ ] `npm run build` completes with zero errors.
- [ ] `@/` path alias resolves correctly in imports.

### How to Test

```bash
cd ui && npm install && npm run build  # Must exit 0
npm run dev &  # Must serve on 5173
curl http://localhost:5173/  # Must return HTML
```

---

## Story U01.2: Design Token System (CSS Custom Properties)

### EARS Requirement

> The system **shall** define a design token layer as CSS custom properties on `:root`, covering color palette (graphite, bone, signal, semantic), typography scale (5 sizes), spacing scale (4px base), border radii, and transition durations, and every component **shall** reference tokens exclusively — no hardcoded values.

### Design by Contract

**Preconditions:**
- The Vite project exists (from U01.1).

**Postconditions:**
- `ui/src/styles/tokens.css` defines all tokens under `:root`.
- Color tokens: `--color-graphite-900` through `--color-graphite-100`, `--color-bone`, `--color-signal`, `--color-signal-muted`, `--color-success`, `--color-error`, `--color-warning`.
- Typography tokens: `--font-sans`, `--font-mono`, `--text-xs` through `--text-xl`, `--leading-tight`, `--leading-normal`.
- Spacing tokens: `--space-1` (4px) through `--space-16` (64px).
- Transition tokens: `--transition-fast` (120ms), `--transition-normal` (200ms), `--transition-slow` (350ms).
- No component CSS file contains a raw hex color, pixel font-size, or hardcoded margin.

**Invariants:**
- Token names follow `--{category}-{variant}` convention.
- All color tokens meet WCAG AA contrast against their intended background.

### Acceptance Criteria

- [ ] `tokens.css` is loaded globally and all tokens are accessible.
- [ ] A grep for raw hex colors (`#[0-9a-fA-F]{3,8}`) in component `.css`/`.tsx` files returns zero results (outside `tokens.css`).
- [ ] Signal color (`--color-signal`) has ≥ 4.5:1 contrast ratio against `--color-bone`.

### How to Test

```bash
# Lint for hardcoded values (should return 0 matches outside tokens.css)
grep -rn '#[0-9a-fA-F]\{3,8\}' ui/src/components/ --include='*.css' --include='*.tsx'

# Visual test: open Storybook/dev and verify token usage
```

---

## Story U01.3: Typography & Font Loading

### EARS Requirement

> The system **shall** load two font families — a sans-serif for product copy and a monospace for IDs/refs — via `@font-face` declarations with `font-display: swap`, and define a typographic scale with `--text-xs` (12px), `--text-sm` (14px), `--text-base` (16px), `--text-lg` (20px), `--text-xl` (28px).

### Design by Contract

**Preconditions:**
- Font files are bundled locally in `ui/src/assets/fonts/` (no CDN dependency).

**Postconditions:**
- `--font-sans` resolves to the chosen sans-serif family with system fallbacks.
- `--font-mono` resolves to a monospace family (JetBrains Mono, IBM Plex Mono, or equivalent).
- All `@font-face` declarations use `font-display: swap` to prevent FOIT.
- Body text defaults to `--font-sans` at `--text-base`.
- Requirement IDs (`REQ-001`), spec refs, and code blocks use `--font-mono`.

**Invariants:**
- No layout shift occurs during font loading (swap ensures fallback renders immediately).
- Font files total < 300KB (subset to latin if needed).

### Acceptance Criteria

- [ ] Sans-serif and monospace fonts load without FOIT.
- [ ] Body text uses sans-serif; IDs and code use monospace.
- [ ] Total font payload < 300KB.
- [ ] Typographic scale produces visually distinct sizes at each step.

### How to Test

```typescript
// Visual regression: capture screenshots at each text size
// Performance: check network tab for font file sizes
// Verify: inspect computed font-family on body vs code elements
```

---

## Story U01.4: Base Component Primitives

### EARS Requirement

> The system **shall** provide reusable primitive components — `Button`, `Badge`, `Card`, `Text`, `Mono`, `Divider`, and `Skeleton` — styled exclusively with design tokens and accepting variant props for visual differentiation.

### Design by Contract

**Preconditions:**
- Design tokens are loaded (from U01.2).
- Components are authored in TypeScript with explicit prop types.

**Postconditions:**
- `Button` supports variants: `primary` (signal color fill), `secondary` (graphite outline), `ghost` (text-only), `danger` (error color).
- `Badge` supports: `info`, `success`, `warning`, `error`, `neutral` variants.
- `Card` renders a container with `--color-bone` background, 1px graphite-200 border, `--space-4` padding.
- `Text` renders with `--font-sans` and accepts `size` prop mapping to the typographic scale.
- `Mono` renders with `--font-mono` for IDs and refs.
- `Skeleton` renders a pulsing placeholder matching the component it replaces.
- `Divider` renders a 1px `--color-graphite-200` horizontal rule.

**Invariants:**
- All primitives accept a `className` prop for composition.
- All interactive primitives have `:focus-visible` styles for keyboard navigation.
- All primitives use `forwardRef` for ref forwarding.

### Acceptance Criteria

- [ ] Each primitive renders correctly with all variant combinations.
- [ ] Keyboard focus is visible on interactive elements.
- [ ] No raw HTML elements (`<button>`, `<span>`) are used directly in feature components — only primitives.

### How to Test

```typescript
// Unit test: Button renders all variants
test("Button renders primary variant", () => {
  render(<Button variant="primary">Click</Button>);
  expect(screen.getByRole("button")).toHaveClass("button--primary");
});

// Unit test: Badge renders correct colors
test("Badge success variant", () => {
  render(<Badge variant="success">Passed</Badge>);
  expect(screen.getByText("Passed")).toBeInTheDocument();
});

// Accessibility test: focus visible
test("Button has focus-visible styles", () => {
  render(<Button>Test</Button>);
  const btn = screen.getByRole("button");
  btn.focus();
  expect(btn).toHaveFocus();
});
```
