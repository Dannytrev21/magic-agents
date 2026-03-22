# Agent Skills Reference — Magic Agents Project

> Comprehensive reference for implementing Agent Skills in the Intent-to-Verification Spec Engine. Covers both the Claude Code SKILL.md standard (for our negotiation phases and verification skill agents) and the Anthropic API Skills system (for potential API-driven document generation).

---

## 1. What Agent Skills Are

Skills are **modular capability packages** that extend Claude with domain-specific expertise. They combine instructions, executable code, resources, and helper scripts into composable expertise packages. Unlike fine-tuning (which modifies model weights permanently), skills are **runtime knowledge and workflows** that can be updated instantly without retraining.

**Key characteristics:**

- Higher-level than individual tools — combine instructions, code, and resources
- Composable — multiple skills work together seamlessly
- Efficient — progressive disclosure means you only pay for what you use
- Include proven code — tested helper scripts reduce errors
- Portable — the same skill works across Claude Code, VS Code, Cursor, Codex, and 13+ other platforms

**Open standard:** Agent Skills follow the [Agent Skills](https://agentskills.io) open standard, published December 2025.

---

## 2. Progressive Disclosure — The Core Architecture

Progressive disclosure is the defining design principle. Like a well-organized manual, skills let Claude load information only as needed.

### Three-Tier Loading Model

| Level | Content | Token Cost | When Loaded |
|-------|---------|-----------|-------------|
| **1: Metadata** | `name` and `description` from YAML frontmatter | ~100 tokens per skill | Always (at startup, in system prompt) |
| **2: Instructions** | SKILL.md body + any referenced .md files | <5k tokens recommended | When skill becomes relevant |
| **3: Resources** | Scripts, templates, data files | Variable (effectively unlimited) | During execution, as needed |

**Token optimization:** You can install many skills without context penalty. Claude only knows each skill exists and when to use it. Full instructions load only when triggered. Scripts execute via bash and only their *output* enters context — the code itself never loads.

### How Loading Works in Practice

```
1. Startup → System prompt includes: "pdf-processing: Extract text and tables from PDF files"
2. User request → "Extract the text from this PDF and summarize it"
3. Claude triggers → reads SKILL.md from filesystem → instructions enter context
4. Claude determines → form filling not needed → FORMS.md is NOT read
5. Claude executes → uses instructions from SKILL.md to complete the task
```

### The Instruction Budget

Every element in the system prompt — tool descriptions, skill metadata, examples — consumes the finite "instruction budget." This reduces space for actual task reasoning.

**Implication for our project:** Each negotiation phase skill and each verification generator skill should be as concise as possible. Move detailed reference material (like prompt templates, schema examples) to separate files that load only when that specific phase executes.

---

## 3. SKILL.md Format — The Complete Specification

### Required Structure

Every skill needs a `SKILL.md` file with YAML frontmatter and markdown body:

```yaml
---
name: lowercase-with-hyphens    # Required. Max 64 chars. Lowercase letters, numbers, hyphens only.
description: What and when       # Required. Max 1024 chars. What the skill does AND when to use it.
---

# Skill Instructions

Clear guidance for Claude, examples, constraints, and rules.
Recommended: Keep under 500 lines / 5,000 tokens total.
```

### Metadata Field Rules

**`name`:**
- Maximum 64 characters
- Must contain only lowercase letters, numbers, and hyphens
- Cannot contain XML tags
- Cannot contain reserved words: "anthropic", "claude"
- Becomes the `/slash-command` in Claude Code

**`description`:**
- Must be non-empty, maximum 1024 characters
- Cannot contain XML tags
- **Must include both what the skill does AND when to use it**
- Write in third person (injected into system prompt)
- Include key trigger terms for discovery

### Claude Code Extended Frontmatter

Claude Code extends the standard with additional fields:

| Field | Required | Description |
|-------|----------|-------------|
| `name` | No (defaults to directory name) | Display name, becomes `/slash-command` |
| `description` | Recommended | What and when. Claude uses this for auto-discovery |
| `argument-hint` | No | Hint during autocomplete: `[issue-number]` |
| `disable-model-invocation` | No | `true` = only user can invoke (prevents auto-trigger) |
| `user-invocable` | No | `false` = only Claude can invoke (background knowledge) |
| `allowed-tools` | No | Tools Claude can use without permission when skill active |
| `model` | No | Override model when skill is active |
| `effort` | No | Override effort level: `low`, `medium`, `high`, `max` |
| `context` | No | `fork` = run in isolated subagent context |
| `agent` | No | Which subagent type to use with `context: fork` |
| `hooks` | No | Hooks scoped to this skill's lifecycle |

### String Substitutions

| Variable | Description |
|----------|-------------|
| `$ARGUMENTS` | All arguments passed when invoking |
| `$ARGUMENTS[N]` / `$N` | Specific argument by 0-based index |
| `${CLAUDE_SESSION_ID}` | Current session ID |
| `${CLAUDE_SKILL_DIR}` | Directory containing this SKILL.md |

### Dynamic Context Injection

The `` !`<command>` `` syntax runs shell commands *before* skill content is sent to Claude:

```yaml
---
name: pr-summary
context: fork
agent: Explore
---

## Pull request context
- PR diff: !`gh pr diff`
- PR comments: !`gh pr view --comments`

## Your task
Summarize this pull request...
```

---

## 4. Directory Structure & File Organization

### Basic Skill

```
my-skill/
├── SKILL.md           # Required: main instructions
```

### Full Skill with Supporting Files

```
my-skill/
├── SKILL.md              # Main instructions (required, <500 lines)
├── REFERENCE.md          # API reference (loaded as needed)
├── EXAMPLES.md           # Usage examples (loaded as needed)
├── TROUBLESHOOTING.md    # Common issues (loaded as needed)
├── scripts/
│   ├── main_logic.py     # Utility script (executed, not loaded into context)
│   ├── validate.py       # Validation script
│   └── utils.py          # Shared utilities
└── resources/
    ├── templates/
    │   └── template.xlsx  # Template files
    └── data/
        └── benchmarks.json  # Reference data
```

### Key Rules

1. **SKILL.md is the ONLY required file** — everything else is optional
2. **All .md files are available** to Claude when the skill loads
3. **Reference files from SKILL.md** so Claude knows what they contain:
   ```markdown
   ## Additional resources
   - For complete API details, see [reference.md](reference.md)
   - For usage examples, see [examples.md](examples.md)
   ```
4. **Keep references one level deep** — don't chain SKILL.md → advanced.md → details.md
5. **Add table of contents** to reference files >100 lines
6. **Use forward slashes** in all file paths (not backslashes)
7. **Name files descriptively**: `form_validation_rules.md`, not `doc2.md`

### Where Skills Live (Claude Code)

| Scope | Path | Applies To |
|-------|------|-----------|
| Enterprise | Managed settings | All org users |
| Personal | `~/.claude/skills/<name>/SKILL.md` | All your projects |
| Project | `.claude/skills/<name>/SKILL.md` | This project only |
| Plugin | `<plugin>/skills/<name>/SKILL.md` | Where plugin enabled |

Priority: enterprise > personal > project. Plugin skills use `plugin-name:skill-name` namespace.

---

## 5. Writing Effective Skills — Best Practices

### Core Authoring Principles

**1. Concise is Key**

The context window is a public good. Claude is already very smart — only add context it doesn't already have.

```markdown
# Good: ~50 tokens
## Extract PDF text
Use pdfplumber for text extraction:
```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

# Bad: ~150 tokens (explaining what PDFs are)
```

**2. Set Appropriate Degrees of Freedom**

| Freedom Level | When to Use | Example |
|---------------|-------------|---------|
| **High** (text instructions) | Multiple approaches valid, context-dependent | Code review guidelines |
| **Medium** (pseudocode/parameterized) | Preferred pattern exists, some variation OK | Report generation template |
| **Low** (exact scripts, no params) | Fragile operations, consistency critical | Database migration commands |

Analogy: narrow bridge with cliffs = low freedom (exact instructions). Open field = high freedom (general direction).

**3. Write Effective Descriptions**

The description is critical for skill selection — Claude uses it to choose from potentially 100+ available skills.

```yaml
# Good: specific, includes trigger terms
description: Extract text and tables from PDF files, fill forms, merge documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.

# Bad: vague
description: Helps with documents
```

**Always write in third person** — descriptions are injected into the system prompt.

**4. Provide Defaults, Not Options**

```markdown
# Bad: too many choices
"You can use pypdf, or pdfplumber, or PyMuPDF, or..."

# Good: one default with escape hatch
"Use pdfplumber for text extraction.
For scanned PDFs requiring OCR, use pdf2image with pytesseract instead."
```

### Workflow Patterns

**Checklist Pattern** — For multi-step operations:

````markdown
## Form filling workflow

Copy this checklist and track your progress:

```
Task Progress:
- [ ] Step 1: Analyze the form (run analyze_form.py)
- [ ] Step 2: Create field mapping (edit fields.json)
- [ ] Step 3: Validate mapping (run validate_fields.py)
- [ ] Step 4: Fill the form (run fill_form.py)
- [ ] Step 5: Verify output (run verify_output.py)
```
````

**Feedback Loop Pattern** — Run validator → fix errors → repeat:

```markdown
1. Make your edits
2. **Validate immediately**: `python scripts/validate.py`
3. If validation fails:
   - Review the error message
   - Fix the issues
   - Run validation again
4. **Only proceed when validation passes**
```

**Conditional Workflow Pattern** — Guide through decision points:

```markdown
1. Determine the type:
   **Creating new?** → Follow "Creation workflow"
   **Editing existing?** → Follow "Editing workflow"
```

### Script Best Practices

**Solve, don't punt** — Handle errors in scripts rather than failing and hoping Claude figures it out:

```python
def process_file(path):
    try:
        with open(path) as f:
            return f.read()
    except FileNotFoundError:
        print(f"File {path} not found, creating default")
        with open(path, "w") as f:
            f.write("")
        return ""
```

**Justify constants** — No magic numbers:

```python
# Good: self-documenting
REQUEST_TIMEOUT = 30  # HTTP requests typically complete within 30 seconds
MAX_RETRIES = 3       # Most intermittent failures resolve by second retry

# Bad: magic numbers
TIMEOUT = 47  # Why 47?
```

**Create verifiable intermediate outputs** — The plan-validate-execute pattern:

```
analyze → create plan file (JSON) → validate plan (script) → execute → verify
```

This catches errors early, provides machine-verifiable checkpoints, and enables Claude to iterate on the plan without touching originals.

---

## 6. Application to Our Project

### Negotiation Phase Skills (Epic 2)

Each negotiation phase maps to a skill. Following the architecture:

```
src/verify/negotiation/
├── skills/
│   ├── phase1-classification/
│   │   ├── SKILL.md              # Instructions + prompt template
│   │   ├── SCHEMA.md             # Output schema reference
│   │   └── scripts/
│   │       └── validate_output.py # Validate classification structure
│   ├── phase2-postconditions/
│   │   ├── SKILL.md
│   │   ├── SCHEMA.md
│   │   └── scripts/
│   │       └── validate_output.py
│   ├── phase3-preconditions/
│   │   └── ...
│   └── phase4-failure-modes/
│       └── ...
```

**SKILL.md for Phase 1 (example):**

```yaml
---
name: phase1-classification
description: Classify acceptance criteria by type, actor, and interface. Use when starting negotiation on a new Jira ticket's AC items. Probes the Actors and Boundaries dimensions of ambiguity.
---

# Phase 1: Interface & Actor Discovery

## Input
- `context.raw_acceptance_criteria` — list of AC items from Jira
- `context.constitution` — project conventions (framework, API patterns)

## Task
For each AC item, determine:
- **type**: api_behavior | performance_sla | security_invariant | observability | compliance | data_constraint
- **actor**: authenticated_user | admin | system | anonymous_user | api_client
- **interface**: For API behaviors, propose HTTP method + endpoint path

## Output Schema
See [SCHEMA.md](SCHEMA.md) for the exact output structure.

## Constitutional Rules
- NEVER guess the interface if the AC doesn't mention API behavior — classify as the appropriate non-API type
- ALWAYS propose clarifying questions when actor is ambiguous
- Use the constitution's API conventions (base_path, auth mechanism) to inform interface proposals

## Validation
Run: `python scripts/validate_output.py`
```

### Verification Generator Skills (Epic 4)

Each verification generator follows the same pattern:

```
src/verify/skills/
├── pytest-unit-test/
│   ├── SKILL.md              # How to generate pytest tests from spec contracts
│   ├── TEMPLATES.md          # Test templates for different contract elements
│   └── scripts/
│       └── validate_tags.py  # Ensure all spec refs are tagged
├── newrelic-alert-config/
│   ├── SKILL.md
│   └── TEMPLATES.md
├── gherkin-scenario/
│   ├── SKILL.md
│   └── TEMPLATES.md
└── otel-config/
    ├── SKILL.md
    └── TEMPLATES.md
```

### Block's 3 Principles Applied to Our Skills

**Principle 1: What agents should NOT decide**
- Spec schema validation → deterministic scripts (`validate_output.py`)
- Tag coverage checks → deterministic scripts (`validate_tags.py`)
- Pass condition evaluation → code (`ALL_PASS`, `ANY_PASS`, `PERCENTAGE`)
- Routing table lookups → code (`ROUTING_TABLE` dict)

**Principle 2: What agents SHOULD decide**
- Interpreting ambiguous AC text
- Generating clarifying questions
- Proposing interface designs from vague descriptions
- Adapting test templates to specific contract shapes

**Principle 3: Constitutional rules, not suggestions**
- "NEVER skip the validation step"
- "ALWAYS include spec refs in test names"
- "The script is the single source of truth for all scores"
- Explicit constraints prevent agents from softening outputs

### Two-Zone Architecture

```
┌─────────────────────────────────────────────┐
│                  AI ZONE                      │
│  (fuzzy-to-formal translation)               │
│                                               │
│  Negotiation phases: interpret AC,            │
│  generate questions, propose contracts        │
├───────────────── SPEC BOUNDARY ──────────────┤
│                DETERMINISTIC ZONE             │
│  (mechanical translation of spec)             │
│                                               │
│  Routing table, test generation templates,    │
│  tag enforcement, evaluation, Jira updates    │
└─────────────────────────────────────────────┘
```

---

## 7. Anthropic API Skills (Cloud-Based)

For potential API-driven document generation (evidence reports, spec PDFs), the Anthropic API offers a separate skills system.

### API Usage Pattern

```python
from anthropic import Anthropic

client = Anthropic(api_key=API_KEY)

response = client.beta.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=4096,
    container={
        "skills": [
            {"type": "anthropic", "skill_id": "pdf", "version": "latest"}
        ]
    },
    tools=[{"type": "code_execution_20250825", "name": "code_execution"}],
    messages=[{"role": "user", "content": "Generate evidence report..."}],
    betas=[
        "code-execution-2025-08-25",
        "files-api-2025-04-14",
        "skills-2025-10-02"
    ]
)
```

### Required Betas

```python
betas=[
    "code-execution-2025-08-25",    # Code execution environment
    "files-api-2025-04-14",          # File upload/download
    "skills-2025-10-02"              # Skills functionality
]
```

### Available Pre-Built Skills

| Skill ID | Purpose | Generation Time |
|----------|---------|-----------------|
| `xlsx` | Excel spreadsheets | ~2 minutes |
| `pptx` | PowerPoint presentations | ~1-2 minutes |
| `pdf` | PDF documents | ~40-60 seconds |
| `docx` | Word documents | ~1-2 minutes |

### Custom Skills via API

```python
from anthropic.lib import files_from_dir

# Create
skill = client.beta.skills.create(
    display_title="Evidence Report Generator",
    files=files_from_dir("path/to/skill")
)

# Use
response = client.beta.messages.create(
    container={"skills": [
        {"type": "custom", "skill_id": skill.id, "version": "latest"}
    ]},
    # ...
)

# Version
new_version = client.beta.skills.versions.create(
    skill_id=skill.id,
    files=files_from_dir("path/to/updated_skill")
)
```

---

## 8. Evaluation & Iteration

### Build Evaluations First

Create evaluations BEFORE writing extensive documentation:

1. **Identify gaps:** Run Claude on representative tasks without a skill. Document specific failures
2. **Create evaluations:** Build 3+ scenarios testing those gaps
3. **Establish baseline:** Measure performance without the skill
4. **Write minimal instructions:** Just enough to address gaps and pass evaluations
5. **Iterate:** Execute, compare, refine

### Evaluation Structure

```json
{
  "skills": ["phase1-classification"],
  "query": "Classify this AC: 'User can view their profile'",
  "files": ["test-context.json"],
  "expected_behavior": [
    "Classifies as api_behavior type",
    "Identifies authenticated_user as actor",
    "Proposes GET /api/v1/users/me as interface",
    "Generates clarifying question about authorization scope"
  ]
}
```

### The Two-Claude Pattern

1. **Claude A** (skill author) — helps design and refine skill instructions
2. **Claude B** (skill user) — tests the skill on real tasks in a fresh context
3. Observe Claude B's behavior, bring insights back to Claude A
4. Iterate until Claude B consistently produces correct output

### Checklist for Effective Skills

**Core quality:**
- [ ] Description is specific and includes trigger terms
- [ ] SKILL.md body is under 500 lines
- [ ] Additional details in separate files
- [ ] No time-sensitive information
- [ ] Consistent terminology throughout
- [ ] Concrete examples, not abstract
- [ ] File references one level deep
- [ ] Workflows have clear steps

**Code and scripts:**
- [ ] Scripts solve problems rather than punt
- [ ] Error handling is explicit and helpful
- [ ] No magic constants
- [ ] Required packages listed and verified
- [ ] No Windows-style paths
- [ ] Validation steps for critical operations
- [ ] Feedback loops for quality-critical tasks

**Testing:**
- [ ] At least 3 evaluations created
- [ ] Tested with target model(s)
- [ ] Tested with real usage scenarios

---

## 9. Security Considerations

- **Only use skills from trusted sources** — skills can direct Claude to invoke tools or execute code
- **Audit all bundled files** — look for unexpected network calls, file access patterns
- **External URL fetching is risky** — fetched content may contain malicious instructions
- **Never hardcode credentials** in skill files
- **Validate all inputs** in scripts
- **Skills are workspace-specific** (API) or directory-scoped (Claude Code)

---

## 10. Sources

**Official Documentation:**
- [Agent Skills Overview](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview)
- [Skill Authoring Best Practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices)
- [Claude Code Skills Docs](https://code.claude.com/docs/en/skills)
- [Anthropic Engineering Blog: Equipping Agents with Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills)

**Cookbook & Tutorials:**
- [Skills Introduction Cookbook](https://platform.claude.com/cookbook/skills-notebooks-01-skills-introduction)
- [Building Custom Skills Cookbook](https://platform.claude.com/cookbook/skills-notebooks-03-skills-custom-development)
- [The Complete Guide to Building Skills for Claude (PDF)](https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf)

**Community & Ecosystem:**
- [Anthropic Skills GitHub](https://github.com/anthropics/skills)
- [Agent Skills Open Standard](https://agentskills.io)
- [Block Engineering: 3 Principles for Designing Agent Skills](https://engineering.block.xyz/blog/3-principles-for-designing-agent-skills)
- [Lee Hanchung: Claude Skills Deep Dive](https://leehanchung.github.io/blogs/2025/10/26/claude-skills-deep-dive/)
- [Awesome Agent Skills (heilcheng)](https://github.com/heilcheng/awesome-agent-skills)
- [Awesome Agent Skills (skillmatic-ai)](https://github.com/skillmatic-ai/awesome-agent-skills)
