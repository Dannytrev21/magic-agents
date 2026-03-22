## Epic 7: Constitution & Repo Awareness [STRETCH]

> **Design references:** The constitution concept comes from GitHub Spec Kit and AWS Kiro — a repo-level file capturing organizational conventions, tech stack, and testing patterns. All spec generation and negotiation is steered by this context. See `ac-to-specs-plan.md` §1.2 and [reference-library.md §4](reference-library.md#4-bmad--agent-as-code-agile-development-framework) for BMAD's context-engineered development approach.

**Note:** The constitution is already used throughout the pipeline — Phase 1 prompts use `constitution.api.base_path` and `constitution.api.auth.mechanism`, Phase 2 uses `constitution.verification_standards.security_invariants`, and the compiler uses `constitution.api.auth.mechanism` for the interface auth field. Currently the constitution is passed in manually. This epic auto-generates it from repo analysis.

**Implementation pattern:** Each scanner is a deterministic script (not an Agent Skill) because repo scanning is mechanical, not context-dependent. Following Block Principle 1: agents should NOT decide what framework a repo uses — that's a `pyproject.toml` parse.

### Feature 7.1: Repo Scanner — Stack Detection

**Story:** Auto-detect language, framework, build tool from repo files.
**Implementation:** Parse `pyproject.toml`/`package.json`/`pom.xml`/`build.gradle` to detect stack. Populate `constitution.project` section (`language`, `framework`, `build_tool`, `package_manager`). Present for developer confirmation. This is a deterministic script, not an LLM call.

### Feature 7.2: Test Pattern Discovery

**Story:** Sample existing test files and extract patterns.
**Implementation:** Find test files via glob (`test_*.py`, `*Test.java`, `*.test.js`), extract imports/annotations/assertion styles. Classify as `controller_test`, `service_test`, `integration_test`. Store in `constitution.testing.patterns`. This information steers the Pytest Skill (Epic 4) to generate tests matching the repo's existing conventions (import style, assertion style, fixture patterns).

### Feature 7.3: API Convention Discovery

**Story:** Detect base paths, auth mechanism, error format.
**Implementation:** Scan route/controller files for patterns. Detect auth from decorators/middleware (e.g., `@jwt_required`, `Depends(get_current_user)`). Parse error handlers for response format (e.g., `{"error": str, "message": str}`). Populate `constitution.api` with `base_path`, `auth.mechanism`, `auth.claims`, `error_format.example`, `common_status_codes`. These fields are used by all 4 negotiation phase prompts for constitution-steered classification and contract proposals.

### Feature 7.4: Code-Grounded Negotiation / RAG [MEDIUM PRIORITY]

**Agentic Pattern:** Code-Grounded Negotiation

**Problem:** During negotiation, the AI proposes schemas and error codes based on convention, but the actual codebase may already implement things differently. The developer has to manually correct every mismatch between what the AI proposes and what the code actually does.

**Pattern:** During phases 2-4, the LLM can call a `read_source(path, lines)` tool to inspect actual endpoint code, error handlers, and model definitions. Proposals are grounded in what's already implemented rather than guessed from conventions.

**Implementation:**
- Extend `LLMClient` with Claude's tool-use API — define a `code_search` tool the LLM can call during negotiation
- Add a `CodeSearchTool` that accepts file path + optional line range, reads the source, returns relevant snippets
- The constitution (Features 7.1-7.3) provides the index of relevant files; the tool provides the content
- Tool results are injected as tool-use messages in the conversation, not into the system prompt (respects instruction budget)
- Phase 2 (postconditions) benefits most: "Here's the actual endpoint handler — propose postconditions that match the implementation"
- Phase 4 (failure modes) benefits from reading error handlers: "Here's how errors are actually raised — enumerate failure modes from the code"
- Maps to harness engineering's "tools & dispatch" pattern ([reference-library.md §3](../../reference-library.md#3-harness-engineering--structuring-agent-environments-for-reliability))

**Depends on:** Features 7.1-7.3 (constitution provides the file index to search)

---

