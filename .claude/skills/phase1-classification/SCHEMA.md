# Phase 1 Output Schema

## Classification object

| Field | Type | Required | Allowed values |
|-------|------|----------|----------------|
| `ac_index` | int | yes | 0-based index matching `raw_acceptance_criteria` |
| `type` | string | yes | `api_behavior`, `performance_sla`, `security_invariant`, `observability`, `compliance`, `data_constraint` |
| `actor` | string | yes | `authenticated_user`, `admin`, `system`, `anonymous_user`, `api_client` |
| `interface` | object or null | yes if type=api_behavior | `{"method": "GET", "path": "/api/v1/..."}` |

## Type descriptions

| Type | When to use | Downstream path |
|------|-------------|-----------------|
| `api_behavior` | AC describes an HTTP endpoint interaction | Phase 2 (postconditions) → Phase 3 (preconditions) → Phase 4 (failure modes) |
| `performance_sla` | AC specifies latency, throughput, or capacity targets | Verification routing to load test skill |
| `security_invariant` | AC describes what must never happen (data leakage, unauthorized access) | Extracted as cross-cutting invariant |
| `observability` | AC requires logging, metrics, or alerting | Verification routing to observability skill |
| `compliance` | AC references regulatory or policy requirements | Verification routing to compliance check skill |
| `data_constraint` | AC specifies data validation rules, format constraints | Verification routing to schema validation |

## Validation rules

Run `python -c "from verify.negotiation.validate import validate_classifications; ..."` to check output.
