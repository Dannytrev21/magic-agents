## Epic 9: Beyond-Code Verification Skills [STRETCH]

> **Design references:** Each new skill follows the `VerificationSkill` base class and registers in `SKILL_REGISTRY`. The progressive disclosure pattern from the [Agent Skills standard](https://agentskills.io) means these skills only load when the routing table points to them — you can install many skills without context penalty. See [agent-skills-reference.md §2](agent-skills-reference.md) for the three-tier loading model and [reference-library.md §2](reference-library.md#2-agent-skills--modular-discoverable-capability-packages) for Block's design principles.

### Feature 9.1: New Relic Alert Config Skill

**Story:** Generate NRQL alert configurations from performance invariants.
**Implementation:** Create `.claude/skills/verify-newrelic/SKILL.md` (Agent Skill definition) + `src/verify/skills/newrelic_skill.py` (Python runner). The SKILL.md defines constitutional rules for generating NRQL alert configs: query patterns, threshold formats, notification channels. The Python runner reads the SKILL.md instructions and generates NRQL JSON from `type: performance_sla` requirements. Register as `newrelic_alert_config` in SKILL_REGISTRY. The routing table already maps `performance_sla` → `newrelic_alert_config` with output pattern `.verify/generated/{key}_alerts.json`. Verification type: `config_validation`.

**SKILL.md at `.claude/skills/verify-newrelic/SKILL.md`:**
```yaml
---
name: verify-newrelic
description: Generate New Relic NRQL alert configurations from performance SLA requirements in spec contracts. Use when the routing table dispatches a performance_sla requirement. This is a proof-of-correctness skill that produces config artifacts, not test code.
---
```

### Feature 9.2: Gherkin Scenario Skill

**Story:** Generate .feature files from spec contracts.
**Implementation:** Create `.claude/skills/verify-gherkin/SKILL.md` + `src/verify/skills/gherkin_skill.py`. The SKILL.md defines how to translate spec contracts into Given/When/Then scenarios with `@TAG` annotations referencing spec refs. Register as `gherkin_scenario`. The routing table maps `compliance` → `gherkin_scenario` with output pattern `.verify/generated/{key}_compliance.feature`. Verification type: `test_result` (Behave/Cucumber runner).

### Feature 9.3: OpenTelemetry Instrumentation Skill

**Story:** Generate OTel span configs for monitored endpoints.
**Implementation:** Create `.claude/skills/verify-otel/SKILL.md` + `src/verify/skills/otel_skill.py`. The SKILL.md defines OTel collector config patterns for each observed endpoint. Register as `otel_config`. The routing table maps `observability` → `otel_config` with output pattern `.verify/generated/{key}_otel.yaml`. Verification type: `deployment_check` (file exists + valid YAML).

---

