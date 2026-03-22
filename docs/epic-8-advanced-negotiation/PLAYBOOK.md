## Epic 8: Advanced Negotiation [STRETCH]

> **Design references:** These phases complete the six dimensions of ambiguity from `ac-to-specs-plan.md` §1.3. Phase 7's EARS formalization uses WHEN/SHALL/IF-THEN/WHILE patterns — each maps to exactly one verifiable assertion. See [reference-library.md §1](reference-library.md#1-sherpa--model-driven-agent-orchestration-via-state-machines) for how Sherpa's composite states handle complex multi-phase workflows.

**Note:** `synthesis.py` already generates basic invariants and EARS statements deterministically after Phase 4. These stretch phases add LLM-powered depth — the AI discovers invariants the developer didn't think of, runs a completeness sweep, and formats EARS statements for human approval. Each phase follows the same Agent Skills pattern as Phases 1-4: a SKILL.md in `.claude/skills/` with constitutional rules, a Python module in `src/verify/negotiation/`, and deterministic validation of outputs.

### Feature 8.1: Phase 5 — Invariant Extraction

**Story:** Extract universal properties from AC, constitution, and data model.
**Implementation:** Create `src/verify/negotiation/phase5.py` + `.claude/skills/phase5-invariants/SKILL.md`. Extract invariants from three sources: AC text (security-related ACs), constitution `verification_standards.security_invariants`, and inferred from data model (e.g., if schema has `email` field, add format validation invariant). Each has ID (INV-NNN), type (`security`, `performance`, `data_integrity`, `compliance`, `idempotency`, `observability`), rule, and formal expression. Validate with `validate.py`. The harness guard condition for Phase 3 (`_phase_3_ok`) already checks for invariants — this phase populates them via AI rather than the current deterministic extraction.

### Feature 8.2: Phase 6 — Completeness Sweep

**Story:** Run a checklist of dimensions and flag gaps.
**Implementation:** Create `src/verify/negotiation/phase6.py` + `.claude/skills/phase6-completeness/SKILL.md`. Standard checklist of 11 dimensions: authentication, authorization, input validation, schema compliance, error handling, rate limiting, pagination, caching, observability, security, data classification. For each dimension, the AI marks: `COVERED` (spec addresses it), `DEFERRED` (acknowledged but out of scope), `NOT ADDRESSED` (gap). The LLM prompt includes all postconditions, preconditions, failure modes, and invariants so it can assess coverage. Output stored in `context.verification_routing` with routing decisions per dimension.

### Feature 8.3: Phase 7 — EARS Formalization & Approval

**Story:** Synthesize everything into EARS statements for final approval.
**Implementation:** Create `src/verify/negotiation/phase7.py` + `.claude/skills/phase7-ears/SKILL.md`. The AI generates EARS statements from all contract elements using four patterns:
- `WHEN {event} THEN {system} SHALL {action}` (event-driven)
- `IF {condition} THEN {response}` (unwanted behavior)
- `WHILE {state} {system} SHALL {property}` (state-driven)
- `{system} SHALL {property}` (ubiquitous)

Each EARS statement maps to exactly one verifiable assertion. Present the full list for developer approval. On approve → `context.approved = True`, spec freezes. On reject → harness re-enters the relevant earlier phase (feedback loop). The synthesis module currently generates basic EARS from postconditions/failures — this phase refines them with LLM reasoning and developer confirmation.

---

