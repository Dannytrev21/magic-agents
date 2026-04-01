# Epic P03: Negotiation Transcript Compaction

**Priority:** 3 (High)  
**Ported From:** `claw-code/src/transcript.py`, `claw-code/src/query_engine.py`  
**Integration Target:** `src/verify/negotiation/harness.py`, `src/verify/context.py`

## Rationale

`magic-agents` currently appends every negotiation log entry to `VerificationContext.negotiation_log` and never compacts it. Long approval and revision loops can push early phase decisions far back into the session payload and checkpoint files, even though later phases mostly need a durable summary plus recent verbatim entries.

`claw-code` already carries the useful shape for this feature:

- a transcript store with explicit compaction
- a runtime trigger that compacts after a configurable number of turns

This port keeps the same operational value, but upgrades the representation for `magic-agents` by producing a structured summary entry instead of blindly trimming old records.

## Story P03.1: Structured Transcript Compactor

### EARS Requirement

> **When** a negotiation transcript grows beyond a configurable threshold, the system **shall** replace the oldest transcript window with a single `compaction_summary` entry while preserving the most recent verbatim entries.

### Design By Contract

**Preconditions**

- The transcript is a list of dict entries.
- Each non-summary entry contains at least `phase`, `role`, `content`, and `timestamp`.
- `keep_recent` is greater than zero.

**Postconditions**

- If the transcript length is less than or equal to `compaction_threshold`, the transcript is unchanged.
- If the transcript length is greater than `compaction_threshold`, the result begins with exactly one summary entry.
- The summary entry records:
  - compacted entry count
  - phase names covered by the compacted window
  - per-phase counts
  - a short human-readable summary string
- The most recent `keep_recent` entries remain verbatim and in order.

**Invariants**

- Compaction is deterministic for the same input transcript.
- Compaction never removes the newest `keep_recent` entries.
- Re-running compaction on an unchanged already-compacted transcript produces no further change.
- The summary payload remains JSON-serializable.

### Acceptance Criteria

- [ ] A `TranscriptCompactor` type exists with configurable `compaction_threshold` and `keep_recent`.
- [ ] Compaction emits a single `compaction_summary` entry instead of naive truncation.
- [ ] The summary content includes phase coverage and compacted counts.
- [ ] Repeated compaction does not stack multiple summary entries at the front.

## Story P03.2: Harness-Level Integration

### EARS Requirement

> **When** `NegotiationHarness.add_to_log()` appends an entry that pushes the transcript beyond the compaction threshold, the system **shall** compact `VerificationContext.negotiation_log` automatically before returning.

### Design By Contract

**Preconditions**

- `NegotiationHarness` has a valid `VerificationContext`.
- `NegotiationHarness` has a `TranscriptCompactor`.

**Postconditions**

- The new log entry is present in `context.negotiation_log`.
- If the threshold is crossed, older entries are replaced by one summary entry.
- The newest entries remain verbatim and checkpoint-safe.

**Invariants**

- `add_to_log()` remains append-oriented from the caller’s perspective.
- Existing checkpoint serialization continues to work without schema changes outside the log payload.
- Transcript compaction is an optimization and must not mutate phase outputs, approvals, or traceability state.

### Acceptance Criteria

- [ ] `NegotiationHarness` accepts an optional compactor dependency.
- [ ] `add_to_log()` compacts automatically after append.
- [ ] Existing checkpoint save/load behavior still round-trips compacted logs.
- [ ] Focused tests cover compactor behavior and harness integration.

## Red-Green Plan

1. Add failing unit tests for standalone compaction behavior.
2. Add a failing integration test for `NegotiationHarness.add_to_log()`.
3. Implement the compactor.
4. Wire the compactor into the harness.
5. Run focused tests for the compactor and checkpoint round-trip.
