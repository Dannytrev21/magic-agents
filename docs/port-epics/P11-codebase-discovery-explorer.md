# Epic P11: Codebase Discovery & Explore Agent

**Priority:** 2.5 (High — slotted between P2 and P3; foundational for all negotiation quality)
**Ported From:** `claw-code/src/port_manifest.py` (workspace introspection), `claw-code/src/context.py` (PortContext build), `claw-code/src/setup.py` (environment detection), Claude Code "Explore" agent pattern (scan → understand → index)
**Integration Target:** `magic-agents/src/verify/scanner.py` (currently Java-only), `magic-agents/constitution.yaml` (currently hand-written)

## Rationale

Claude Code ships with **Explore agents** — lightweight sub-agents that scan a repository to understand its structure, language, framework, patterns, and conventions before any task execution. This gives Claude grounded context instead of guessing. magic-agents has a `scanner.py` module, but it is hardcoded to Java/Spring Boot (regex-based annotation scanning). The `constitution.yaml` — which every negotiation phase and verification skill consumes — is entirely hand-written. This means:

1. Onboarding a new repo requires a human to author the constitution from scratch.
2. The scanner cannot handle Python, TypeScript, Go, or any non-Spring-Boot project.
3. Negotiation phases receive no codebase context unless someone manually feeds it.

This epic creates a **general-purpose codebase explorer** that auto-detects language, framework, patterns, and conventions from any repository, then generates a draft constitution. It is the single highest-leverage improvement for negotiation quality because every downstream phase benefits from grounded codebase context.

### Relationship to Existing Epics

- **Depends on:** None (foundational)
- **Feeds into:** P1 (constitution `budget` section auto-discovered), P2 (skills matched to detected framework), P4 (routing informed by detected stack)

---

## Story P11.1: Language & Framework Auto-Detection

### EARS Requirement

> **When** the explore agent is given a directory path, the system **shall** detect the primary language, framework, build tool, and runtime version by analyzing file extensions, manifest files (package.json, pom.xml, build.gradle, Cargo.toml, pyproject.toml, go.mod), and framework-specific markers, and return a `StackProfile` dataclass with these fields populated.

### Design by Contract

**Preconditions:**
- The directory path exists and is readable.
- At least one source file or manifest file is present in the directory tree.

**Postconditions:**
- `StackProfile` is returned with: `language` (e.g., "java", "python", "typescript"), `framework` (e.g., "spring-boot", "fastapi", "nextjs", "express"), `build_tool` (e.g., "gradle", "npm", "poetry"), `runtime_version` (e.g., "17", "3.11", "20"), and `confidence` (float 0.0–1.0).
- If multiple languages are detected, `secondary_languages` lists them ranked by file count.
- If no framework is detected, `framework` is `"unknown"` and `confidence` is below 0.5.

**Invariants:**
- Detection is 100% deterministic — zero AI. Same directory always produces the same `StackProfile`.
- Detection completes in < 5 seconds for repositories with up to 50,000 files.
- Detection never writes to the filesystem.

### Acceptance Criteria

- [ ] `StackProfile` dataclass is defined with all listed fields.
- [ ] `detect_stack(path: str) -> StackProfile` function is implemented.
- [ ] Detects at minimum: Java/Spring Boot, Python/FastAPI, Python/Django, TypeScript/Next.js, TypeScript/Express, Go/stdlib, Rust/Actix.
- [ ] Returns `confidence < 0.5` when framework cannot be determined.
- [ ] Handles monorepos by detecting the primary stack at root and per-subdirectory.

### How to Test

```python
# Unit test: detect Java/Spring Boot
def test_detect_spring_boot(tmp_path):
    (tmp_path / "build.gradle").write_text("plugins { id 'org.springframework.boot' }")
    (tmp_path / "src/main/java/App.java").mkdir(parents=True)
    profile = detect_stack(str(tmp_path))
    assert profile.language == "java"
    assert profile.framework == "spring-boot"
    assert profile.build_tool == "gradle"
    assert profile.confidence >= 0.8

# Unit test: detect Python/FastAPI
def test_detect_fastapi(tmp_path):
    (tmp_path / "pyproject.toml").write_text('[project]\ndependencies = ["fastapi"]')
    (tmp_path / "main.py").write_text("from fastapi import FastAPI")
    profile = detect_stack(str(tmp_path))
    assert profile.language == "python"
    assert profile.framework == "fastapi"

# Unit test: unknown framework
def test_detect_unknown(tmp_path):
    (tmp_path / "script.sh").write_text("#!/bin/bash")
    profile = detect_stack(str(tmp_path))
    assert profile.confidence < 0.5

# Integration test: real dog-service repo
def test_detect_dog_service():
    profile = detect_stack("dog-service")
    assert profile.language == "java"
    assert profile.framework == "spring-boot"
    assert profile.build_tool == "gradle"

# Performance test: large repo completes in time
def test_detect_performance(large_repo_path):
    import time
    start = time.time()
    detect_stack(large_repo_path)
    assert time.time() - start < 5.0
```

---

## Story P11.2: Structural Index Builder (Multi-Language)

### EARS Requirement

> **When** a `StackProfile` has been produced, the system **shall** scan the repository and build a `CodebaseIndex` containing discovered API endpoints, data models/entities, DTOs/schemas, test patterns, configuration files, and directory structure — using language-appropriate scanners dispatched based on the detected stack.

### Design by Contract

**Preconditions:**
- A valid `StackProfile` has been produced for the target directory.
- Language-specific scanner plugins are registered for the detected language.

**Postconditions:**
- `CodebaseIndex` is returned with: `endpoints` (list of HTTP routes with method, path, handler), `models` (entities/structs/classes with fields), `schemas` (DTOs, request/response types), `test_patterns` (discovered test files with framework, naming conventions), `config_files` (application configs, env files), and `directory_tree` (top-level structure summary).
- Each discovered item includes its `file_path` for traceability.
- The index includes a `coverage_report` indicating what percentage of source files were successfully parsed.

**Invariants:**
- Scanning is deterministic and read-only.
- Partial failures (unparseable files) are logged but do not abort the scan.
- The index for any repo with < 10,000 source files completes in < 30 seconds.
- Language scanners are pluggable: adding a new language does not require modifying the core scanner.

### Acceptance Criteria

- [ ] `build_codebase_index(profile: StackProfile, path: str) -> CodebaseIndex` is implemented.
- [ ] Java scanner extracts: `@RestController` endpoints, `@Entity` models, DTOs by naming convention, `@WebMvcTest`/`@SpringBootTest` patterns.
- [ ] Python scanner extracts: FastAPI/Flask route decorators, Pydantic models, SQLAlchemy models, pytest fixtures/markers.
- [ ] TypeScript scanner extracts: Express/Next.js routes, TypeScript interfaces/types, Jest/Vitest test files.
- [ ] Unparseable files are logged at DEBUG and counted in `coverage_report`.

### How to Test

```python
# Unit test: Java endpoint discovery
def test_java_endpoints():
    index = build_codebase_index(java_profile, "dog-service")
    assert len(index.endpoints) >= 4  # GET/POST/PUT/DELETE /api/v1/dogs
    assert any(e.method == "GET" and "/dogs" in e.path for e in index.endpoints)

# Unit test: Python model discovery
def test_python_models(tmp_path):
    (tmp_path / "models.py").write_text("class User(Base):\n    __tablename__ = 'users'\n    id = Column(Integer)")
    index = build_codebase_index(python_profile, str(tmp_path))
    assert any(m.class_name == "User" for m in index.models)

# Unit test: partial failure handling
def test_partial_failure(tmp_path):
    (tmp_path / "good.py").write_text("from fastapi import APIRouter")
    (tmp_path / "bad.py").write_bytes(b"\x00\x01\x02")  # binary garbage
    index = build_codebase_index(python_profile, str(tmp_path))
    assert index.coverage_report["parsed_files"] >= 1
    assert index.coverage_report["failed_files"] >= 1

# Unit test: scanner plugin dispatch
def test_scanner_dispatch():
    java_profile = StackProfile(language="java", ...)
    python_profile = StackProfile(language="python", ...)
    # Each should dispatch to its language scanner
    j_index = build_codebase_index(java_profile, "dog-service")
    assert j_index.endpoints  # Java scanner ran
```

---

## Story P11.3: Auto-Generate Draft Constitution from Index

### EARS Requirement

> **When** a `CodebaseIndex` and `StackProfile` are available, the system **shall** generate a draft `constitution.yaml` file populated with the detected project metadata, source structure, testing patterns, API conventions, and security markers — formatted identically to the existing hand-written constitution schema.

### Design by Contract

**Preconditions:**
- A valid `StackProfile` and `CodebaseIndex` have been produced.
- The target output path is writable.

**Postconditions:**
- A `constitution.yaml` file is written to `.verify/constitution.yaml` (or a specified path).
- The file includes all sections: `project`, `source_structure`, `testing`, `api`, `observability` (if detectable), `conventions`, `verification_standards`.
- Fields that could not be auto-detected are marked with a `# TODO: verify` comment.
- The file is valid YAML and parseable by the existing constitution loader.

**Invariants:**
- Generation is deterministic: same index + profile = same constitution output.
- The generated constitution never overwrites an existing file without explicit confirmation (returns the draft as a string if the file exists).
- All `# TODO: verify` markers are counted and reported in the generation summary.

### Acceptance Criteria

- [ ] `generate_constitution(profile, index, output_path=None) -> ConstitutionDraft` is implemented.
- [ ] `ConstitutionDraft` contains `yaml_content` (string), `todo_count` (int), `sections_populated` (list of section names).
- [ ] Generated YAML matches the schema of the existing `constitution.yaml`.
- [ ] Unknown fields get `# TODO: verify` comments.
- [ ] Existing constitution files are never silently overwritten.

### How to Test

```python
# Unit test: generates valid YAML
def test_generates_valid_yaml():
    draft = generate_constitution(java_profile, java_index)
    parsed = yaml.safe_load(draft.yaml_content)
    assert "project" in parsed
    assert parsed["project"]["language"] == "java"
    assert parsed["project"]["framework"] == "spring-boot"

# Unit test: testing patterns populated
def test_testing_patterns():
    draft = generate_constitution(java_profile, java_index)
    parsed = yaml.safe_load(draft.yaml_content)
    assert "testing" in parsed
    assert parsed["testing"]["unit_framework"] in ("junit5", "junit4")

# Unit test: TODO markers for unknown fields
def test_todo_markers():
    draft = generate_constitution(minimal_profile, minimal_index)
    assert draft.todo_count > 0
    assert "# TODO: verify" in draft.yaml_content

# Unit test: does not overwrite existing
def test_no_overwrite(tmp_path):
    existing = tmp_path / "constitution.yaml"
    existing.write_text("project:\n  name: existing")
    draft = generate_constitution(java_profile, java_index, output_path=str(existing))
    # Should return draft without writing
    assert existing.read_text().startswith("project:\n  name: existing")
    assert draft.yaml_content != existing.read_text()

# Integration test: roundtrip with real repo
def test_roundtrip_dog_service():
    profile = detect_stack("dog-service")
    index = build_codebase_index(profile, "dog-service")
    draft = generate_constitution(profile, index)
    parsed = yaml.safe_load(draft.yaml_content)
    assert parsed["project"]["name"] == "dog-service"
    assert parsed["source_structure"]["main"] is not None
```

---

## Story P11.4: Explore Agent CLI & Web Endpoint

### EARS Requirement

> The system **shall** expose the codebase explorer as both a CLI command (`python -m verify.explorer <path>`) that prints the `StackProfile`, `CodebaseIndex` summary, and draft constitution to stdout, and as a `POST /api/explore` web endpoint that accepts a `path` parameter and returns the full exploration result as JSON.

### Design by Contract

**Preconditions:**
- The target path exists and is readable.
- For the web endpoint, the FastAPI app is running.

**Postconditions:**
- CLI: Prints a formatted report including stack detection results, index summary (endpoint count, model count, test pattern count), and the draft constitution YAML.
- Web: Returns a JSON response with `stack_profile`, `codebase_index` (serialized), `constitution_draft` (YAML string), and `todo_count`.
- Both entry points return the same underlying data.

**Invariants:**
- The CLI and web endpoint produce equivalent results for the same input path.
- The endpoint is idempotent and read-only.
- Response time is bounded by Story P11.1 + P11.2 constraints (< 35 seconds total).

### Acceptance Criteria

- [ ] `python -m verify.explorer dog-service` prints stack, index summary, and draft constitution.
- [ ] `POST /api/explore {"path": "dog-service"}` returns 200 with full JSON result.
- [ ] `POST /api/explore {"path": "/nonexistent"}` returns 400 with a clear error.
- [ ] CLI output includes color formatting for readability.
- [ ] Web response includes `duration_seconds` for performance monitoring.

### How to Test

```python
# CLI test: runs without error
def test_explorer_cli():
    result = subprocess.run(
        ["python", "-m", "verify.explorer", "dog-service"],
        capture_output=True, text=True
    )
    assert result.returncode == 0
    assert "spring-boot" in result.stdout
    assert "endpoints" in result.stdout.lower()

# Integration test: web endpoint
def test_explore_endpoint(client):
    resp = client.post("/api/explore", json={"path": "dog-service"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["stack_profile"]["language"] == "java"
    assert data["stack_profile"]["framework"] == "spring-boot"
    assert "constitution_draft" in data
    assert data["duration_seconds"] < 35

# Integration test: invalid path
def test_explore_invalid_path(client):
    resp = client.post("/api/explore", json={"path": "/nonexistent"})
    assert resp.status_code == 400

# Equivalence test: CLI and web produce same data
def test_cli_web_equivalence(client):
    cli = subprocess.run(["python", "-m", "verify.explorer", "dog-service", "--json"],
                         capture_output=True, text=True)
    web = client.post("/api/explore", json={"path": "dog-service"}).json()
    cli_data = json.loads(cli.stdout)
    assert cli_data["stack_profile"] == web["stack_profile"]
```

---

## Story P11.5: Inject Codebase Context into Negotiation Phases

### EARS Requirement

> **When** a negotiation session starts and a `CodebaseIndex` is available for the target repository, the system **shall** inject the index summary into the system prompt of every negotiation phase, enabling the LLM to reference actual endpoints, models, and patterns instead of hallucinating them.

### Design by Contract

**Preconditions:**
- A `CodebaseIndex` has been built (either from auto-scan or cached from a previous run).
- The `NegotiationHarness` is initializing a new session.

**Postconditions:**
- The `VerificationContext` includes a `codebase_index` field with the serialized index.
- Each phase's system prompt includes a `## Codebase Context` section with the index summary (endpoints, models, test patterns).
- The context injection is bounded to 2,000 tokens maximum (truncated if necessary with a note).

**Invariants:**
- If no index is available, phases proceed without codebase context (graceful degradation).
- The injected context is read-only — phases cannot modify the index.
- Context injection does not change the phase's constitutional rules or validation logic.

### Acceptance Criteria

- [ ] `VerificationContext` has an optional `codebase_index: dict` field.
- [ ] Phase system prompts include `## Codebase Context` when index is available.
- [ ] Context is truncated to 2,000 tokens with a `[truncated — N items omitted]` note.
- [ ] Phases work normally when no index is provided.
- [ ] The web UI session creation endpoint accepts an optional `explore_path` that triggers auto-scan.

### How to Test

```python
# Unit test: context injection
def test_context_injected_into_phase():
    index = build_codebase_index(java_profile, "dog-service")
    context = VerificationContext(jira_key="TEST-1", codebase_index=index.to_dict())
    prompt = build_phase1_system_prompt(context)
    assert "## Codebase Context" in prompt
    assert "GET /api/v1/dogs" in prompt

# Unit test: graceful degradation
def test_no_index_graceful():
    context = VerificationContext(jira_key="TEST-1")
    prompt = build_phase1_system_prompt(context)
    assert "## Codebase Context" not in prompt  # Section omitted

# Unit test: truncation
def test_context_truncation():
    huge_index = {"endpoints": [{"path": f"/api/{i}"} for i in range(500)]}
    context = VerificationContext(jira_key="TEST-1", codebase_index=huge_index)
    prompt = build_phase1_system_prompt(context)
    assert "[truncated" in prompt
    # Prompt should not exceed reasonable size
    assert len(prompt) < 20_000

# Integration test: session with explore_path
def test_session_with_explore(client):
    resp = client.post("/api/session/start", json={
        "jira_key": "TEST-1",
        "explore_path": "dog-service"
    })
    assert resp.status_code == 200
    session = resp.json()
    assert session["codebase_detected"] is True
```
