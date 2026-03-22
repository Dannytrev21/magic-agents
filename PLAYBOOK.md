# Claude Code Implementation Playbook
## Project: Intent-to-Verification Spec Engine ("Magic Agents")

**Stack:** Python 3.11+ / FastAPI / pytest / Claude API
**MVP Scope:** Epics 0-4 + Stories 6.1-6.2
**Design Overview:** [`docs/DESIGN.md`](docs/DESIGN.md) — architecture diagrams, data flows, epic dependencies

**Core principle:** The entire pipeline — from spec generation to proof-of-correctness generation — is powered by [Claude Agent Skills](https://agentskills.io) following the SKILL.md open standard. Negotiation phase skills (`.claude/skills/phase*-*/`) produce the spec; verification skills (`.claude/skills/verify-*/`) produce the tests, configs, and scenarios that prove correctness.

### Reference Documents

| Document | Purpose |
|----------|---------|
| [docs/DESIGN.md](docs/DESIGN.md) | High-level architecture with Mermaid diagrams |
| [reference-library.md](reference-library.md) | Sherpa, Agent Skills, Harness Engineering, BMAD |
| [agent-skills-reference.md](agent-skills-reference.md) | Agent Skills open standard + API skills reference |
| [ac-to-specs-plan.md](ac-to-specs-plan.md) | Detailed design plan with spec schema |
| [user-stories.md](user-stories.md) | Epic/story breakdown with acceptance criteria |

---

### How to Use This Playbook

Work through features **sequentially within each epic**. Each feature has:
1. **Prerequisites** — run these checks before starting; if any fail, the dependency isn't ready
2. **Implementation Steps** — each with an inline `Verify` block containing an executable command
3. **Definition of Done** — a smoke-test script that re-verifies everything for the feature

Check off `- [ ]` boxes as you complete each step. Do not skip verification steps.

---

### Epic Playbooks

| Epic | Name | Features | Status | Playbook |
|------|------|----------|--------|----------|
| 0 | Bullet Tracer | 6 | Foundation | [epic-0-bullet-tracer](docs/epic-0-bullet-tracer/PLAYBOOK.md) |
| 1 | Jira Integration | 4 | Foundation | [epic-1-jira-integration](docs/epic-1-jira-integration/PLAYBOOK.md) |
| 2 | AI Negotiation | 10 | Core complete, patterns pending | [epic-2-ai-negotiation](docs/epic-2-ai-negotiation/PLAYBOOK.md) |
| 3 | Formal Spec Emission | 3 | Complete | [epic-3-formal-spec](docs/epic-3-formal-spec/PLAYBOOK.md) |
| 4 | Verification Agent Skills | 3 | **MVP Next** | [epic-4-skill-routing](docs/epic-4-skill-routing/PLAYBOOK.md) |
| 5 | Evaluation Engine | 3 | MVP | [epic-5-evaluation](docs/epic-5-evaluation/PLAYBOOK.md) |
| 6 | Jira Feedback Loop | 3 | MVP | [epic-6-jira-feedback](docs/epic-6-jira-feedback/PLAYBOOK.md) |
| 7 | Constitution & RAG | 4 | Stretch | [epic-7-constitution](docs/epic-7-constitution/PLAYBOOK.md) |
| 8 | Advanced Negotiation | 4 | Stretch | [epic-8-advanced-negotiation](docs/epic-8-advanced-negotiation/PLAYBOOK.md) |
| 9 | Beyond-Code Verification Skills | 3 | Stretch | [epic-9-verification-skills](docs/epic-9-verification-skills/PLAYBOOK.md) |
| 10 | CI/CD & PR Automation | 3 | Stretch | [epic-10-cicd](docs/epic-10-cicd/PLAYBOOK.md) |

---

### Quick Start

```sh
# Run the web UI (Jira story picker + negotiation + traceability)
source .venv/bin/activate
python3 run_web.py

# Run the full pipeline against a compiled spec
python3 -m verify.pipeline .verify/specs/DEMO-001.yaml

# Run negotiation in mock mode (no API key needed)
LLM_MOCK=true python3 run_negotiation.py
```
