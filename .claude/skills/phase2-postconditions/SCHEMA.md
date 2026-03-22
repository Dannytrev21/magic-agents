# Phase 2 Output Schema

## Postcondition object

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `ac_index` | int | yes | Links to the classified AC |
| `status` | int | yes | HTTP success status code (100-599) |
| `content_type` | string | yes | Response MIME type |
| `schema` | object | yes | Field name → `{type, required}` mapping |
| `constraints` | list[string] | yes | Cross-field relationships |
| `forbidden_fields` | list[string] | yes | Fields that must never appear |

## Constraint patterns

| Pattern | Example | What it prevents |
|---------|---------|-----------------|
| Field equality | `response.id == jwt.sub` | Cross-user data leakage |
| Format validation | `response.email matches RFC 5322` | Invalid data exposure |
| Derived field | `response.display_name == first_name + " " + last_name` | Stale computed fields |
| Temporal | `response.updated_at >= request.timestamp` | Stale cache serving |
