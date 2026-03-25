# Pytest Test Templates

## Success Test Template

```python
def test_{req_id}_success(self):
    """[{REQ-ID}.success] Happy path returns expected response."""
    response = requests.{method}(_url(), headers=_auth_headers())
    assert response.status_code == {status}
    body = response.json()
    assert "{field}" in body  # for each required field
```

## Failure Test Template

```python
def test_{req_id}_{fail_id}(self):
    """[{REQ-ID}.{FAIL-ID}] {description}"""
    response = requests.{method}(_url())  # setup varies by violation category
    assert response.status_code == {status}
    body = response.json()
    assert body.get("error") == "{error_key}"
```

## Invariant Test Template

```python
def test_{req_id}_{inv_id}(self):
    """[{REQ-ID}.{INV-ID}] {rule}"""
    response = requests.{method}(_url(), headers=_auth_headers())
    assert response.status_code == 200
    body = response.json()
    assert "{forbidden_field}" not in body  # for each forbidden field
```

## Failure Request Setup by Category

| Category | Setup |
|----------|-------|
| authentication | No auth header |
| authorization | Invalid role token |
| data_existence | Valid auth, nonexistent resource |
| data_state | Valid auth, invalid state resource |
| rate_limit | Burst requests to trigger limit |
