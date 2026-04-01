# Epic P2: Skill Registry & Capability Discovery

**Priority:** 2 (High)
**Status:** Done
**Ported From:** `claw-code/src/tools.py` (registry, search, filtering, permission integration), `claw-code/src/execution_registry.py` (ExecutionRegistry pattern)
**Integration Target:** `src/verify/skills/framework.py`

## Rationale

magic-agents originally used a bare `SKILL_REGISTRY: dict[str, VerificationSkill]` with no metadata, capability discovery, dependency declaration, or validation. claw-code's tool registry pattern stores rich metadata per tool (name, responsibility, source hint, status), supports search/filtering, and integrates with the permission system. This epic replaces the bare dict with a metadata-rich registry supporting search, validation, dependency declaration, and capability introspection.

---

## Story P2.R1: Descriptor Registration

### EARS Requirement

> The system **shall** associate each registered `VerificationSkill` with a `SkillDescriptor` containing `skill_id`, `name`, `description`, `input_types` (frozenset of requirement types it handles), `output_format`, `framework`, and `version`.

### Design by Contract

**Preconditions:**
- Each `VerificationSkill` subclass declares metadata as class attributes (`skill_id`, `name`, `description`, `input_types`, `output_format`, `framework`, `version`).
- `skill_id` is a non-empty string unique across all registered skills.

**Postconditions:**
- `SKILL_REGISTRY` maps `skill_id` to the `VerificationSkill` instance.
- `SkillDescriptor` is a frozen dataclass built on demand via `_build_descriptor()`.
- Attempting to register a skill with a duplicate `skill_id` raises `ValueError`.

**Invariants:**
- Every entry in `SKILL_REGISTRY` has a valid skill instance with a non-empty `skill_id`.
- `skill_id` values are globally unique within a single process.

### Acceptance Criteria

- [x] `SkillDescriptor` frozen dataclass is defined with all listed fields.
- [x] `register_skill()` rejects duplicate `skill_id` with `ValueError`.
- [x] Existing skills (`PytestSkill`, `CucumberJavaSkill`) carry class-level metadata.
- [x] `get_skill_descriptor(skill_id)` returns a built descriptor or `None`.
- [x] `get_all_descriptors()` returns descriptors for all registered skills.

### How to Test

```python
def test_descriptor_fields():
    desc = get_skill_descriptor("pytest_unit_test")
    assert desc is not None
    assert desc.skill_id == "pytest_unit_test"
    assert "api_behavior" in desc.input_types

def test_duplicate_registration_raises():
    register_skill(mock_skill)
    with pytest.raises(ValueError, match="already registered"):
        register_skill(mock_skill_copy)
```

---

## Story P2.R2: Capability Discovery

### EARS Requirement

> **When** a caller queries the skill registry with a search term or requirement type filter, the system **shall** return only skills whose metadata matches the query (by `skill_id`, `name`, `description`, `framework`) or whose `input_types` contains the given type.

### Design by Contract

**Preconditions:**
- At least one skill is registered in `SKILL_REGISTRY`.
- The query string is non-empty, or a valid requirement type is provided.

**Postconditions:**
- `find_skills(query)` returns `list[tuple[SkillDescriptor, VerificationSkill]]` matching case-insensitively across all text fields.
- `find_skills_by_type(req_type)` returns only skills whose `input_types` contains the given type.
- Empty result is valid when no match is found.

**Invariants:**
- Search is case-insensitive.
- Search never mutates the registry.
- Builtin skills are auto-loaded before any search via `_ensure_builtin_skills_loaded()`.

### Acceptance Criteria

- [x] `find_skills(query)` searches across `skill_id`, `name`, `description`, `framework`.
- [x] `find_skills_by_type(req_type)` filters by `input_types` membership.
- [x] Both return empty lists when no match found.
- [x] Builtin skills lazy-load on first search.

### How to Test

```python
def test_find_skills_by_name():
    results = find_skills("pytest")
    assert any(desc.skill_id == "pytest_unit_test" for desc, _ in results)

def test_find_skills_by_type():
    results = find_skills_by_type("api_behavior")
    assert len(results) >= 1
    for desc, _ in results:
        assert "api_behavior" in desc.input_types

def test_find_skills_no_match():
    assert find_skills("nonexistent_xyz") == []
```

---

## Story P2.R3: Dispatch Validation

### EARS Requirement

> **If** a compiled spec references a `skill` that is not registered or whose `input_types` do not include the requirement's type, **then** the system **shall** raise a `SkillDispatchError` listing every unresolvable `(requirement_id, skill_id)` pair.

### Design by Contract

**Preconditions:**
- A compiled spec has `requirements[].verification[].skill` fields.
- `SKILL_REGISTRY` has been populated.

**Postconditions:**
- `validate_dispatch(spec)` returns a list of human-readable error strings.
- `dispatch_skills()` calls `validate_dispatch()` before generating artifacts and raises `SkillDispatchError` if errors exist.
- ALL missing/incompatible skills are reported in one error (not just the first).

**Invariants:**
- Validation is exhaustive across all requirements.
- Dispatch never proceeds if any requirement lacks a valid skill handler.

### Acceptance Criteria

- [x] `SkillDispatchError` exception class is defined.
- [x] `validate_dispatch(spec)` returns all errors in one pass.
- [x] `dispatch_skills()` raises `SkillDispatchError` when validation fails.
- [x] Error messages include requirement ID and skill ID.

### How to Test

```python
def test_dispatch_missing_skill():
    spec = {"requirements": [{"id": "REQ-001", "verification": [{"skill": "nonexistent"}]}]}
    with pytest.raises(SkillDispatchError, match="nonexistent"):
        dispatch_skills(spec, constitution)

def test_dispatch_reports_all_errors():
    spec = {"requirements": [
        {"id": "REQ-001", "verification": [{"skill": "missing_a"}]},
        {"id": "REQ-002", "verification": [{"skill": "missing_b"}]},
    ]}
    with pytest.raises(SkillDispatchError) as exc_info:
        dispatch_skills(spec, constitution)
    assert "REQ-001" in str(exc_info.value)
    assert "REQ-002" in str(exc_info.value)
```

---

## Story P2.R4: Web Introspection

### EARS Requirement

> The system **shall** expose a `GET /api/skills` endpoint that returns a JSON array of all registered skill descriptors, enabling the web UI to display available verification capabilities.

### Design by Contract

**Preconditions:**
- The FastAPI app is running.
- At least one skill is registered.

**Postconditions:**
- Response is a JSON array of objects, each containing all `SkillDescriptor` fields.
- Response status is 200.
- The array matches the current state of `SKILL_REGISTRY`.

**Invariants:**
- The endpoint is read-only and never modifies the registry.
- `input_types` is serialized as a sorted list (frozenset is not JSON-native).

### Acceptance Criteria

- [x] `GET /api/skills` returns 200 with a JSON array.
- [x] Each entry contains `skill_id`, `name`, `description`, `input_types`, `output_format`, `framework`, `version`.
- [x] Response matches current registry state.

### How to Test

```python
def test_skills_endpoint(client):
    resp = client.get("/api/skills")
    assert resp.status_code == 200
    skills = resp.json()
    assert isinstance(skills, list)
    assert len(skills) >= 1
    assert "skill_id" in skills[0]
    assert "input_types" in skills[0]
```
