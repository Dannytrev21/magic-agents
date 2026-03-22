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

---

