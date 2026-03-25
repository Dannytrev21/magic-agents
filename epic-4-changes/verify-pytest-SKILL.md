---
name: verify-pytest
description: Generate pytest unit tests from verification spec contracts
skill_id: pytest_unit_test
trigger_terms: [pytest, unit test, test generation, api test, verification test]
version: "1.0"
---

# Pytest Verification Skill

Generates complete pytest test files from spec contracts. Each generated test is tagged
with its spec ref for end-to-end traceability from AC checkbox to test verdict.

## Input

- **Spec YAML** with requirements containing `contract` blocks (interface, preconditions, success, failures, invariants)
- **Constitution** (optional) with coding conventions for the target project

## Output

- pytest test file with tagged test functions
- Each test includes `[REQ-NNN.ref]` in its docstring
- Tests use `fastapi.testclient.TestClient` for API behavior requirements

## Constitutional Rules

### MUST
- Every test function MUST include the spec ref in its docstring: `[REQ-001.success]`
- Success tests MUST assert the exact HTTP status code from the spec
- Success tests MUST verify all required fields are present in the response
- Failure tests MUST use the appropriate request shape to trigger each failure mode
- Invariant tests MUST verify forbidden fields are absent from responses

### FORBIDDEN
- FORBIDDEN: Generating tests that don't map to a spec ref
- FORBIDDEN: Hardcoding test data that contradicts the spec contract
- FORBIDDEN: Skipping failure modes listed in the spec

## Test Patterns

### Success Test
```python
def test_REQ_001_success():
    """[REQ-001.success] Happy path returns correct response."""
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer valid-token"})
    assert response.status_code == 200
    body = response.json()
    assert "id" in body and "email" in body
```

### Failure Test (Auth)
```python
def test_REQ_001_FAIL_001():
    """[REQ-001.FAIL-001] Missing auth returns 401."""
    response = client.get("/api/v1/users/me")
    assert response.status_code == 401
```

### Invariant Test
```python
def test_REQ_001_INV_001():
    """[REQ-001.INV-001] Forbidden fields never in response."""
    response = client.get("/api/v1/users/me", headers={"Authorization": "Bearer valid-token"})
    body = response.json()
    assert "password" not in body and "ssn" not in body
```
