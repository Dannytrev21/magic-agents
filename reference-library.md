# Reference Library: Intent-to-Verification Spec Engine

> Compiled knowledge base for the hackathon project — transforming fuzzy Jira Acceptance Criteria into formal, machine-verifiable specifications using AI-driven negotiation, state machines, agent skills, and harness engineering.

---

## 1. Sherpa — Model-Driven Agent Orchestration via State Machines

### What It Is

Sherpa is an open-source Python framework (MIT license) developed by Aggregate Intellect in collaboration with McGill University. It structures LLM execution using **hierarchical state machines**, enabling fine-grained control over agent behavior through rules or ML-driven decisions. The core insight: treat state machines as **configurable data**, not fixed code, allowing rapid experimentation and encoding domain best practices directly into agent architecture.

### Core Architecture

**State Machines as Data Structures:** Unlike conventional agent frameworks that rely on prompt chaining or purely emergent behavior, Sherpa defines workflows as hierarchical state machines with composite states, guard conditions, and structured transitions. Each state machine encodes domain-specific best practices that guide the LLM through predetermined workflows while maintaining flexibility for ML-based decisions.

**Three-Layer Component Stack:**

- **State Machines** — Tasks, transitions, guards, actions. Complex workflows decompose into manageable substeps using composite states.
- **Policies** — Each transition can use either deterministic rule-based logic or LLM-guided decisions. Automatic optimization reduces API calls by ~50% when only one valid transition exists.
- **Belief System** — Agent-specific belief states track execution history (trajectory history, action logs, task data) while shared memory pools enable cross-agent collaboration through vector stores and document repositories.

**Multi-Agent Orchestration:** Specialized AI agents collaborate on problems while maintaining shared memory and coordinated decision-making. Agent-specific belief states track execution history while shared memory pools enable cross-agent collaboration.

### Key Capabilities

- Hierarchical task decomposition via composite states
- Rule-based AND LLM-driven transition policies
- Agent persistence across sessions
- Cost tracking for LLM operations
- Asynchronous multi-agent execution
- Citation validation and self-consistency via Pydantic objects
- Event-driven architecture

### Research Backing

**Paper:** "SHERPA: A Model-Driven Framework for Large Language Model Execution"
**Authors:** Boqi Chen, Kua Chen, José Antonio Hernández López, Gunter Mussbacher, Dániel Varró, Amir Feizpour
**Published:** arXiv:2509.00272, presented at MODELS 2025

The paper demonstrates that integrating well-designed state machines significantly improves LLM output quality, particularly for complex tasks where human best practices exist but training data is sparse. Evaluated on code generation, class name generation, and question answering tasks across multiple LLMs.

### Relevance to This Project

The negotiation loop in our spec engine IS a hierarchical state machine — each phase (Actors, Boundaries, Preconditions, Failure Modes, Invariants, Non-Functional) is a composite state with transitions that are either rule-based (phase completion checks) or LLM-driven (clarification questions). Sherpa's belief system maps directly to our context/belief object that flows through the pipeline.

### Sources

- Documentation: https://docs.ai.science/en/latest/
- Product Page: https://ai.science/products-services/sherpa
- Paper: https://arxiv.org/abs/2509.00272
- GitHub: https://github.com/Aggregate-Intellect/sherpa

---

## 2. Agent Skills — Modular, Discoverable Capability Packages

### What Agent Skills Are

Agent Skills are **modular, standardized `SKILL.md` packages** that provide on-demand capabilities through progressive disclosure. They function as "recipe cards" that agents consult when needed — instructions rather than executable code, interpreted by agents similarly to how humans read procedural guides.

**Key architectural principle:** Lightweight metadata loads early, full instructions load only when relevant, and supporting resources are accessed when needed. This differs fundamentally from fine-tuning (which modifies model weights permanently) — skills are **runtime knowledge and workflows** that can be updated instantly without retraining.

### Three-Stage Loading Mechanism

1. **Browse** — Agent accesses a catalog of available skills with brief descriptions
2. **Load** — When relevant, agent retrieves complete instructions
3. **Use** — Agent executes the skill and accesses supporting materials

### Skill Structure

A `SKILL.md` file follows this format:

```markdown
---
name: skill-identifier
description: When and why to use this skill
---

Detailed instructions and guidelines
```

The metadata frontmatter helps agents determine relevance. The body contains step-by-step procedures, examples, and best practices. Supporting files may include scripts, templates, MCP servers, and configurations.

### Block Engineering's 3 Principles for Designing Skills

Block maintains 100+ internal skills for domain-specific workflows (POS crash investigation, feature flag setup, oncall protocols). Their three design principles:

**Principle 1: Identify What Agents Should NOT Decide**
Move variable decisions into deterministic scripts. LLMs produce inconsistent evaluations when asked to score subjectively. Use bash scripts with binary pass/fail checks and fixed point values. The skill instructs: *"The script is the single source of truth for all scores. Never override, adjust, or recalculate any score from the script's output."*

**Principle 2: Identify What Agents SHOULD Decide**
Agents excel at interpretation (explaining why checks failed), action generation (creating tailored documentation from codebase analysis), and conversation (recommending prioritization based on constraints). This creates a **two-zone architecture**: scripts handle reproducible operations; agents handle context-dependent reasoning.

**Principle 3: Write Constitutional Rules, Not Suggestions**
LLMs naturally soften results and add caveats. Explicit constraints in `SKILL.md` prevent agents from skipping steps, adjusting outputs, or taking unauthorized actions. Specificity drives consistency.

**Bonus — Design for the Arc:** The strongest skills create conversation continuity where initial output becomes input for subsequent agent actions, enabling follow-up questions and refinements within the same session.

### Supported Platforms

Skills have been adopted across 13+ platforms: Claude Code, VS Code, Cursor, GitHub Copilot, OpenAI Codex, Gemini CLI, Mistral Vibe, Manus, Kiro, Roo Code, and others.

### Discovery & Distribution

- **Official catalogs:** Anthropic, OpenAI, Microsoft, Google, Hugging Face
- **Marketplaces:** agentskill.sh (44k+ skills), SkillsMP, SkillStore
- **Community repos:** GitHub collections organized by domain
- **CLI tools:** Installation utilities aggregating 177+ skills from 24 providers

### Skills vs. MCP (Model Context Protocol)

Skills focus on **workflows and capabilities**; MCP emphasizes **secure, structured data and tool access**. They are complementary.

### Relevance to This Project

Each negotiation phase and each downstream generator in our system is a self-contained skill with a SKILL.md defining its prompt template, input/output contract, and trigger conditions. Skills are loaded on demand (progressive disclosure), not all at once. The two-zone architecture (deterministic scripts + agent reasoning) maps directly to our design principle: *"AI handles the fuzzy-to-formal translation. Everything downstream of the spec is deterministic."*

### Sources

- Block Engineering Blog: https://engineering.block.xyz/blog/3-principles-for-designing-agent-skills
- Awesome Agent Skills (heilcheng): https://github.com/heilcheng/awesome-agent-skills
- Awesome Agent Skills (skillmatic-ai): https://github.com/skillmatic-ai/awesome-agent-skills

---

## 3. Harness Engineering — Structuring Agent Environments for Reliability

### What a Harness Is

A harness is the **operational framework** that enables AI agents to function effectively, especially over extended periods and across multiple context windows. The fundamental insight: **"An agent is a model. Not a framework. Not a prompt chain."** The intelligence resides in the trained model; the harness provides the environment where that intelligence operates.

**Formula:** `coding agent = AI model(s) + harness`

**Three nested layers:**
- **Prompt engineering** (innermost): How to write individual instructions
- **Context engineering** (middle): What information the model should carry
- **Harness engineering** (outer): The structure of work itself — "being good at prompts matters less than being able to build structures for reproducibility"

### The Agent Loop (Foundation)

```
User → messages[] → LLM → response
                      ↓
              stop_reason == "tool_use"?
                    ↙        ↘
                 yes          no
                  ↓            ↓
            execute tools   return text
            append results
            loop back ────→ messages[]
```

This loop is immutable. The model decides when to invoke tools; the harness executes those decisions.

### Five Essential Harness Components

**1. Tools & Dispatch**
Atomic, composable tools (bash execution, file I/O, network calls, database queries). Each tool registers in a dispatch map: `name → handler`.

**2. Context Management**
Three-layer compression strategy prevents token overflow:
- Layer 1: Summarize old messages
- Layer 2: Compress intermediate history
- Layer 3: Archive completed tasks

Critical concept — **The "Dumb Zone"**: Models perform worse at longer context lengths, especially with low semantic similarity between queries and relevant information. Each intermediate tool call acts as a distractor compounding performance degradation. Long-context extensions provide mathematical tricks, not genuine capacity increases.

**3. Knowledge Loading (Skills)**
Load knowledge when needed, not upfront. Skills load on-demand via `tool_result` injection, keeping context clean. This respects the agent's finite **"instruction budget"** — every element in system prompts consumes space for actual task reasoning.

**4. Planning & Persistence**
- **TodoManager** forces explicit planning before execution
- **Task System** organizes goals in dependency graphs persisted to disk, surviving session boundaries
- **Subagents** isolate complex subtasks with independent message histories, preventing context pollution

**5. Team Coordination**
- Persistent teammates maintain async mailboxes (JSONL-based message queues)
- Shared protocol: request-response FSM for negotiation
- Autonomous cycle: agents scan task board, claim work, execute independently
- **Worktree isolation** confines each agent to dedicated directories

### Sub-Agents as Context Firewalls

Sub-agents encapsulate discrete tasks in isolated agent sessions. The parent agent sees only the prompt and final result, preventing intermediate noise accumulation. They are a "particularly powerful lever for hard problems that require many context windows to solve."

**Use cases:** Locating code definitions, analyzing codebase patterns, tracing information flow across services, research/investigation tasks.

**Cost optimization:** Deploy expensive models (Opus) at parent level; cheaper models (Sonnet, Haiku) for sub-agents handling smaller tasks.

### Four Critical Documents for Long-Running Agents

From muraco.ai's harness engineering guide:

1. **design.md** — Captures the design approach and procedural workflow
2. **task_checklist.md** — Breaks work into phases with acceptance criteria
3. **session_handoff.md** — Records recent progress and decision rationale
4. **AGENTS.md** — Documents operational rules that persist across sessions

### Anthropic's Long-Running Agent Patterns

The Anthropic engineering blog describes a two-part harness architecture:

**Initializer Agent:** First session establishes the environment — init.sh scripts, progress files (claude-progress.txt), initial git commits creating a baseline state.

**Coding Agent:** Subsequent sessions follow structured startup protocol:
1. Confirm working directory
2. Read git logs and progress files for context recovery
3. Review feature list and select highest-priority incomplete work
4. Start dev server via init.sh
5. Run end-to-end tests before beginning new work

**Key principle:** Incremental progress beats exponential progress. Tiny steps compound faster than overloaded agents. Break large projects into manageable increments to prevent context exhaustion mid-implementation.

### Harness Configuration Levers (HumanLayer)

**CLAUDE.md / AGENTS.md Files:**
- Keep under 60 lines — brevity matters
- Avoid auto-generation; craft by hand
- Use progressive disclosure
- Include only universally applicable instructions
- Omit codebase overviews (agents discover structure independently)

**MCP Servers (for Tools):**
- Never connect to untrusted servers (prompt injection risk via tool descriptions)
- Minimize tool count; excessive tools flood context
- Prefer established CLIs over MCP duplicates when training data covers them

**Hooks (Event-Driven Automation):**
- Notifications (sound alerts on completion)
- Auto-approval/denial rules for tool calls
- Integrations (Slack, GitHub PRs, preview environments)
- Verification (typecheck/build with silent success, verbose error output)

**Back-Pressure Mechanisms:**
- Typechecks, builds, unit/integration tests, coverage reporting
- Make verification context-efficient — swallow success output, surface errors only

### Key Takeaway

*"The next time your coding agent isn't performing as expected, check the harness before blaming the model."* — HumanLayer

### Relevance to This Project

Our orchestrator IS a harness, not an agent. It manages context windows, enforces phase transitions, and provides the belief/context object that flows through the pipeline. The AI operates within the harness, not above it. The four critical documents map to our system's state management, and the sub-agent pattern applies to our skill dispatcher invoking downstream generator agents.

### Sources

- Anthropic Engineering: https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents
- Learn Claude Code (shareAI): https://github.com/shareAI-lab/learn-claude-code
- HumanLayer Blog: https://www.humanlayer.dev/blog/skill-issue-harness-engineering-for-coding-agents
- Muraco.ai Guide: https://muraco.ai/en/articles/harness-engineering-claude-code-codex/
- Paul Fruitful (Medium): https://medium.com/@fruitful2007/agent-harness-understanding-claude-codes-superpower-engine-85e35a7ec764

---

## 4. BMAD — Agent-as-Code Agile Development Framework

### What It Is

BMAD stands for **"Breakthrough Method of Agile AI-Driven Development."** It's a lightweight, team-shaped framework that gives AI collaboration structure, accountability, and context so outputs become repeatable, readable, and useful. Free and open-source, designed for minimal adoption friction.

### Core Problem It Solves

Unstructured AI conversations lead to lost context and unpredictable outputs. Without systematic structure, "the AI behaves like a different teammate every time." BMAD tackles this by enforcing **documentation-driven development** and **agent specialization**.

### Two Key Innovations

**1. Agentic Planning**
Specialized planning agents — Analyst, Product Manager, Architect, UX Designer, Product Owner — collaborate to generate structured outputs: Product Requirement Documents, architecture specs, UX guidance. Through advanced prompt engineering, iterative design, and human-in-the-loop refinement, BMAD creates robust, real-world plans.

**2. Context-Engineered Development**
Once planning completes, the Scrum Master agent generates detailed story files containing full architectural context, implementation guidelines, embedded reasoning (what, why, and how to build it), and testing criteria. These story files ARE the context — no information is lost in handoff.

### Agent-as-Code Approach

The defining feature: **agents are self-contained markdown files with embedded YAML configurations**. Each role-based AI persona has documented expertise, responsibilities, constraints, and expected outputs. This makes specialized AI expertise as portable and manageable as any other piece of software — versionable, diffable, and auditable.

**LLM Personas defined as Markdown:**
- Product Manager
- Architect
- Developer
- Scrum Master
- UX Designer
- QA Agent

Each has explicit responsibilities, constraints, and output contracts, preventing context loss between interactions.

### Four-Phase Workflow

1. **Analysis** — Create a one-page PRD capturing the problem and constraints. Analyst conducts optional brainstorming and market research.
2. **Planning** — PM develops prioritized user stories with explicit acceptance criteria. UX Expert generates front-end specs.
3. **Solutioning** — Architect produces minimal design with system architecture. PO validates alignment.
4. **Implementation** — Documents sharded into story files. Dev Agent implements code and writes tests. SM coordinates workflow and quality gates. QA reviews and reports bugs. Iterative fix cycles.

### Technical Framework

- **BMad-CORE:** Engine handling agent coordination, workflow execution, IDE support
- **BMB (BMad Builder):** Toolkit for building custom agents, workflows, and modules
- **CIS (Creative Intelligence Suite):** Tools supporting creative exploration across domains
- **Codebase Flattener:** Converts projects into AI-optimized XML format respecting .gitignore
- **Expansion Packs:** Domain-specific modules for creative writing, business, health, education
- **Supported Models:** OpenAI, Qwen3, DeepSeek, Claude, and more
- **Installation:** `npx bmad-method install` (Node.js v20+ required)

### Key Benefits

- **Hallucination Reduction:** Clear specifications minimize AI fabrication. "Specs become the contract, not your latest chat message."
- **Context Preservation:** Structured handoffs between specialized agents maintain project coherence across all development phases.
- **Predictable Incremental Progress:** Fewer rewrites, reduced debugging, faster onboarding through artifact-driven documentation.

### Relevance to This Project

Each negotiation phase agent and each generator skill in our system is defined as a markdown file with a persona, responsibilities, and output contract — directly following the BMAD agent-as-code pattern. The four-phase workflow (Analysis → Planning → Solutioning → Implementation) mirrors our pipeline (Negotiation → Spec Generation → Artifact Generation → Execution). The documentation-first approach aligns with our spec-driven development philosophy.

### Sources

- Official Site: https://bmadcodes.com/
- Documentation: https://docs.bmad-method.org/
- Dev.to Article: https://dev.to/extinctsion/bmad-the-agile-framework-that-makes-ai-actually-predictable-5fe7
- Vishal Mysore (Medium): https://medium.com/@visrow/bmad-method-building-custom-ai-agents-with-bmb-and-google-antigravity-54ac96024e94
- Agent-as-Code Article: https://medium.com/@visrow/bmad-method-agent-as-code-to-democratizing-ai-expertise-904cc52cfe98

---

## 5. Cross-Cutting Patterns & Synthesis

### How These Four Pillars Work Together in Our System

| Component | Sherpa | Agent Skills | Harness Engineering | BMAD |
|-----------|--------|-------------|--------------------|----- |
| **Negotiation Loop** | Hierarchical state machine with composite states per phase | Each phase is a self-contained skill with SKILL.md | Orchestrator is a harness managing context and transitions | Phase agents defined as markdown with personas |
| **Spec Generation** | Belief system accumulates context across phases | Skill trigger conditions determine when to activate | Context compression prevents token overflow | PRD/architecture artifacts feed downstream |
| **Downstream Routing** | Rule-based transitions (deterministic) | Skill dispatcher matches spec dimensions to generators | Back-pressure mechanisms verify outputs | Story files carry full context to implementors |
| **Quality Assurance** | Guard conditions prevent invalid transitions | Constitutional rules prevent agent deviation | Hooks run verification at lifecycle points | QA agent reviews with iterative fix cycles |

### Shared Design Principles

1. **Intelligence Boundary:** AI handles fuzzy-to-formal translation; everything else is deterministic.
2. **Progressive Disclosure:** Load only what's needed, when it's needed. Respect the instruction budget.
3. **Structured Persistence:** Documents, specs, and artifacts survive session boundaries — not conversation history.
4. **Two-Zone Architecture:** Scripts/rules for reproducible operations; agents for context-dependent reasoning.
5. **Incremental Compounding:** Small, verified steps compound faster than overloaded monolithic attempts.

### Key Design Vocabulary

| Term | Definition |
|------|-----------|
| **Belief Object** | Accumulated context (Sherpa) flowing through pipeline states |
| **Skill** | Self-contained capability package with SKILL.md, loaded on demand |
| **Harness** | Operational framework managing tools, context, and agent boundaries |
| **Agent-as-Code** | Agents defined as versionable markdown files with embedded config |
| **Context Firewall** | Sub-agent isolation preventing intermediate noise accumulation |
| **Constitutional Rules** | Explicit constraints preventing agent deviation from prescribed behavior |
| **Back-Pressure** | Verification mechanisms enabling agents to validate their own work |
| **Instruction Budget** | Finite system prompt capacity consumed by tools, skills, and examples |
| **Dumb Zone** | Performance degradation at longer context lengths with low-relevance content |
| **EARS Notation** | WHEN/SHALL/IF-THEN/WHILE sentence patterns for unambiguous requirements |

---

## 6. Additional Related Resources (Discovered During Research)

These were not in the original list but are highly relevant to the project:

- **Martin Fowler on Harness Engineering:** https://martinfowler.com/articles/exploring-gen-ai/harness-engineering.html
- **OpenAI Harness Engineering:** https://openai.com/index/harness-engineering/
- **LangChain — Anatomy of an Agent Harness:** https://blog.langchain.com/the-anatomy-of-an-agent-harness/
- **LangChain — Improving Deep Agents with Harness Engineering:** https://blog.langchain.com/improving-deep-agents-with-harness-engineering/
- **HumanLayer — Writing a Good CLAUDE.md:** https://www.humanlayer.dev/blog/writing-a-good-claude-md
- **HumanLayer — Advanced Context Engineering for Coding Agents (GitHub):** https://github.com/humanlayer/advanced-context-engineering-for-coding-agents
- **Vishal Mysore — Comprehensive Guide to Spec-Driven Development (Kiro, GitHub Spec Kit, BMAD):** https://medium.com/@visrow/comprehensive-guide-to-spec-driven-development-kiro-github-spec-kit-and-bmad-method-5d28ff61b9b1
- **Vishal Mysore — BMAD Guardrails for Autonomous Systems:** https://medium.com/@visrow/bmad-method-how-ai-guardrails-can-keep-autonomous-systems-safe-8c709238c2f2
- **Applied BMAD — Reclaiming Control in AI Dev:** https://bennycheung.github.io/bmad-reclaiming-control-in-ai-dev
- **obra/superpowers — Agentic Skills Framework & Methodology:** https://github.com/obra/superpowers
