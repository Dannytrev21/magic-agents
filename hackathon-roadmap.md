# Hackathon Feature Roadmap: Bullet Tracer → Production Spec

## Context

Hackathon day rebuild. The bullet tracer (hardcoded story, single Claude call for spec, single Claude call for tests, Jira update) is the foundation — it's always the working demo. Every feature below builds on it incrementally, moving toward the full production design in `specify-production-spec.md`. Ranked by **hackathon impact** (what wows the audience / proves the thesis) and **effort** (can we build it in 30-60 min vs half a day).

The bullet tracer gives you: hardcoded story → one-shot spec → Java tests → Gradle → Jira checkbox ticked. Everything below extends that.

---

## Tier 1: High Impact, Low-Medium Effort (Do These First)

These get you from "cool demo" to "this is a real product."

| # | Feature | Effort | Impact | What It Adds |
|---|---------|--------|--------|-------------|
| **1** | **Live Jira Ticket Input** | ~30 min | HIGH | Replace hardcoded story with real Jira fetch. User types ticket key → API pulls AC + metadata. Proves it works on any ticket, not just a canned one. The Jira client code already exists. |
| **2** | **Multi-AC Support** | ~45 min | HIGH | Handle tickets with 2-5 acceptance criteria (not just one). Each AC gets its own classification → contract → test methods → verdict. The traceability map links each AC to its tests. This is the core value prop — one ticket, many ACs, all verified. |
| **3** | **Interactive Negotiation (4-Phase)** | ~2 hr | VERY HIGH | Replace single-shot spec with the 4-phase negotiation loop: classify → postconditions → preconditions → failure modes. Developer can provide feedback at each phase to refine. This is the "AI negotiation" demo moment — the AI asks smart questions, the developer shapes the spec. |
| **4** | **Web UI: Negotiation Chat View** | ~2 hr | VERY HIGH | Split-pane UI: chat conversation (left) + live spec preview (right). Phase progress dots at top. Approve/feedback input at bottom. This is what people see — the bullet tracer can run headless, but the demo needs a face. |
| **5** | **Evidence Comment on Jira** | ~20 min | HIGH | After evaluation, post a formatted evidence table as a Jira comment: per-AC verdict, per-ref pass/fail, spec path. The `format_evidence_comment()` method already exists. Two lines of integration. Huge demo moment — "look at the Jira ticket, it updated itself." |
| **6** | **Constitution File Loading** | ~30 min | MEDIUM | Load `constitution.yaml` from the target repo instead of hardcoding it. The constitution steers everything — test patterns, auth mechanism, error format, security invariants. Makes the demo feel real for any repo. |

**Tier 1 gets you to:** Real Jira tickets → AI negotiation with developer feedback → formal spec → generated tests → verdicts → Jira updated with evidence. This is ~80% of the demo story.

---

## Tier 2: High Impact, Medium Effort (Core Differentiators)

These are what make SPECify different from "yet another test generator."

| # | Feature | Effort | Impact | What It Adds |
|---|---------|--------|--------|-------------|
| **7** | **EARS Statement Summary + Approval Gate** | ~1 hr | HIGH | After Phase 4, synthesize all contracts into EARS statements (WHEN/SHALL/IF/THEN). Display to developer as a readable summary before spec emission. "Here's what we agreed to in plain English — approve?" This is the bridge between AI negotiation and deterministic execution. |
| **8** | **Codebase Pre-Scanner (Java/Spring)** | ~2 hr | VERY HIGH | Scan target repo for `@GetMapping`, `@Entity`, `@ControllerAdvice`, DTOs, security config. Feed the structural index to negotiation phases. The AI now says "I found your `UserEntity` with 9 fields — your DTO exposes 6" instead of guessing. Transforms negotiation quality. |
| **9** | **Gherkin Scenario Generation** | ~1.5 hr | HIGH | New skill: EARS statements → `.feature` files with `@REQ-001.FAIL-002` tags. Produces human-readable BDD scenarios from the spec. A different, complementary angle on verification — proves "one spec, many output formats." |
| **10** | **Multiple Verification Skills (pytest + JUnit + Gherkin)** | ~2 hr | HIGH | Route different requirement types to different skills: `api_behavior` → JUnit, `security_invariant` → pytest security tests, `compliance` → Gherkin scenarios. The routing table exists in compiler.py. This proves the "one spec, many verification types" thesis. |
| **11** | **SSE Streaming for Pipeline Execution** | ~1.5 hr | HIGH | Stream pipeline progress to the UI via Server-Sent Events: "Generating tests... Running gradle... Evaluating... Updating Jira..." Real-time feedback instead of a loading spinner. Makes the deterministic zone feel alive. |
| **12** | **Ticket Transition (→ Done)** | ~15 min | MEDIUM | After all ACs pass, transition the Jira ticket to "Done." `transition_ticket()` exists. One line. But the demo moment of watching the ticket go green is worth it. |

**Tier 2 gets you to:** Codebase-aware AI negotiation → EARS approval → multi-skill generation (JUnit + Gherkin) → streaming execution → Jira ticket Done. This is ~90% of the production vision's core loop.

---

## Tier 3: Extend the Platform (Medium Effort, High Value)

These widen SPECify's reach beyond unit tests.

| # | Feature | Effort | Impact | What It Adds |
|---|---------|--------|--------|-------------|
| **13** | **Agent SDK for Generation (Parallel Subagents)** | ~3 hr | HIGH | Replace single Claude API call for test gen with Agent SDK orchestrator that spawns parallel subagents per skill (JUnit, NRQL, Gherkin). Each subagent has isolated context + SKILL.md. Production spec Section 5.3. |
| **14** | **New Relic Alert Config Generation** | ~1.5 hr | MEDIUM | New skill: `performance_sla` requirements → NRQL alert condition JSON. Proves verification goes beyond unit tests into infrastructure. |
| **15** | **Deep Reads (AI-Requested File Reads)** | ~1.5 hr | HIGH | During negotiation, the AI can request reads of specific files from the codebase index. "I need to see `UserController.java` to confirm the endpoint." Constrained: max 10 reads, 100 lines each, allowlisted extensions. Two-pass phase execution. |
| **16** | **Context Curator (Per-Phase Context Engineering)** | ~2 hr | HIGH | Each phase sees ONLY the context it needs. Phase 4 sees preconditions + error format, NOT Phase 1 classifications. Prevents context rot, improves output quality, reduces token cost. Production spec Section 4.2. |
| **17** | **Spec Diff on Re-negotiation** | ~1 hr | MEDIUM | When re-running negotiation on a ticket that already has a spec, show what changed. Side-by-side YAML diff. Proves specs are living documents, not throwaway. |
| **18** | **Drift Detection Layer 1-2** | ~1.5 hr | MEDIUM | Spec fingerprinting: hash the contract, embed in test file header. CI check compares fingerprints. "Spec changed but tests are stale." Layer 1 is free (tagged tests already catch regressions). |

---

## Tier 4: Production Hardening + Stretch Goals

Build these if you're ahead of schedule or for post-hackathon.

| # | Feature | Effort | Impact | What It Adds |
|---|---------|--------|--------|-------------|
| **19** | **Checkpointing + Resume** | ~1.5 hr | MEDIUM | After each phase, persist context to `.verify/checkpoints/`. On startup, offer to resume from where you left off. Critical for reliability — if the API call fails at Phase 4, you don't re-run Phases 1-3. |
| **20** | **Back-Pressure Controller** | ~1 hr | MEDIUM | Hard limits: max 50 API calls, 500K tokens, 10 min wall clock, 3 retries per phase. Prevents runaway sessions. Soft limits warn the developer. Production spec Section 4.4. |
| **21** | **Structured Observability (JSONL Harness Log)** | ~1 hr | MEDIUM | Every harness event logged as structured JSON: phase_started, llm_called, validation_result, developer_interaction, phase_completed. The audit trail for the Jira evidence comment and for debugging. |
| **22** | **Spec JSON Schema Validation** | ~1 hr | MEDIUM | Validate emitted specs against a JSON Schema (`spec.schema.json`). Catches structural issues before they propagate to skills/evaluator. Production spec Section 8.2. |
| **23** | **CLI Interface (`specify` commands)** | ~2 hr | MEDIUM | `specify PROJ-1234`, `specify init`, `specify negotiate`, `specify execute`, `specify check`. Makes SPECify a real developer tool, not just a web UI. |
| **24** | **Multi-Language Scanners (Node/Python)** | ~3 hr | MEDIUM | Add codebase scanners for Express.js and FastAPI alongside the Java/Spring scanner. Proves language-agnostic thesis. |
| **25** | **Drift Detection Layer 3-4** | ~4 hr | MEDIUM | Source-spec cross-reference in CI (Layer 3). AI-assisted `specify amend` for targeted spec updates from git diffs (Layer 4). The full drift detection stack. |
| **26** | **Alpine.js + Prism.js UI Rewrite** | ~3 hr | MEDIUM | Production-grade UI with Alpine.js for reactivity and Prism.js for YAML syntax highlighting. Three views: Negotiation, Execution, Results. Replaces the current vanilla JS single-page app. |

---

## The 80% Line

**Features 1-12 get you ~90% of the production vision's core loop.** Specifically:

- Real Jira ticket input (not hardcoded)
- Multi-AC traceability
- 4-phase interactive negotiation with developer feedback
- EARS approval gate
- Codebase-aware negotiation
- Multi-skill verification (JUnit + Gherkin)
- Streaming pipeline execution
- Per-AC verdicts with evidence
- Jira checkboxes ticked + evidence comment + ticket transitioned

**Features 13-18** extend the platform (Agent SDK subagents, NRQL alerts, deep reads, context curation, drift detection).

**Features 19-26** are production hardening + stretch (checkpointing, back-pressure, observability, CLI, multi-language scanners, UI rewrite).

---

## Suggested Hackathon Day Sequence

1. Build the bullet tracer first (~2 hr) — always have a working demo
2. Features 1-2 (~1 hr) — live Jira + multi-AC
3. Features 3-4 (~3 hr) — negotiation + web UI (this is the demo centerpiece)
4. Features 5-6 (~45 min) — Jira evidence + constitution loading
5. Features 7-9 (~4.5 hr) — EARS summary + codebase scanner + Gherkin (if time)
6. Features 10-12 (~3.5 hr) — multi-skill routing + streaming + ticket transition (if time)
7. Anything in Tier 3-4 is bonus
