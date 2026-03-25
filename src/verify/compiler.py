"""Spec Compiler — transforms a populated VerificationContext into a YAML spec file.

The output format matches DEMO-001.yaml and is consumed by generator.py and evaluator.py.
This module is 100% deterministic — zero AI.
"""

import os
from datetime import datetime, timezone

import yaml

from verify.context import VerificationContext

# ------------------------------------------------------------------
# Verification Routing Table — deterministic dispatch, no AI
# Maps requirement type → (skill ID, output file extension)
# ------------------------------------------------------------------

ROUTING_TABLE: dict[str, dict] = {
    "api_behavior": {
        "skill": "cucumber_java",
        "framework": "cucumber",
        "output_pattern": "dog-service/src/test/resources/features/{key}.feature",
    },
    "performance_sla": {
        "skill": "newrelic_alert_config",
        "framework": "newrelic",
        "output_pattern": ".verify/generated/{key}_alerts.json",
    },
    "security_invariant": {
        "skill": "pytest_unit_test",
        "framework": "pytest",
        "output_pattern": ".verify/generated/test_{key}_security.py",
    },
    "observability": {
        "skill": "otel_config",
        "framework": "opentelemetry",
        "output_pattern": ".verify/generated/{key}_otel.yaml",
    },
    "compliance": {
        "skill": "gherkin_scenario",
        "framework": "behave",
        "output_pattern": ".verify/generated/{key}_compliance.feature",
    },
    "data_constraint": {
        "skill": "pytest_unit_test",
        "framework": "pytest",
        "output_pattern": ".verify/generated/test_{key}_data.py",
    },
}

DEFAULT_ROUTE = {
    "skill": "cucumber_java",
    "framework": "cucumber",
    "output_pattern": "dog-service/src/test/resources/features/{key}.feature",
}


def get_route(requirement_type: str) -> dict:
    """Look up the verification route for a requirement type."""
    return ROUTING_TABLE.get(requirement_type, DEFAULT_ROUTE)


def compile_spec(context: VerificationContext) -> dict:
    """Compile a VerificationContext into a spec dict matching the YAML schema."""
    requirements = _build_requirements(context)

    # Store routing decisions on the context for downstream use
    context.verification_routing = {
        req["id"]: {
            "skill": req["verification"][0]["skill"],
            "output": req["verification"][0]["output"],
            "type": req["type"],
        }
        for req in requirements
    }

    # Build traceability from compiled requirements (routing-aware)
    traceability = _build_traceability(context, requirements)
    context.traceability_map = traceability

    return {
        "meta": _build_meta(context),
        "requirements": requirements,
        "traceability": traceability,
    }


def write_spec(spec: dict, output_dir: str = ".verify/specs") -> str:
    """Write a compiled spec dict to a YAML file. Returns the output path."""
    jira_key = spec["meta"]["jira_key"]
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, f"{jira_key}.yaml")
    with open(output_path, "w") as f:
        yaml.dump(spec, f, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return output_path


def compile_and_write(
    context: VerificationContext, output_dir: str = ".verify/specs",
) -> str:
    """Compile and write in one step. Sets context.spec_path. Returns file path."""
    spec = compile_spec(context)
    path = write_spec(spec, output_dir)
    context.spec_path = path
    return path


# ------------------------------------------------------------------
# Private helpers
# ------------------------------------------------------------------


def _build_meta(ctx: VerificationContext) -> dict:
    now = datetime.now(timezone.utc).isoformat()
    return {
        "spec_version": "1.0",
        "jira_key": ctx.jira_key,
        "jira_summary": ctx.jira_summary,
        "generated_at": now,
        "approved_at": ctx.approved_at or now,
        "approved_by": ctx.approved_by or "auto",
        "status": "approved" if ctx.approved else "draft",
    }


def _build_requirements(ctx: VerificationContext) -> list[dict]:
    requirements = []
    jira_key_lower = ctx.jira_key.lower().replace("-", "_")

    for classification in ctx.classifications:
        ac_index = classification["ac_index"]
        req_id = f"REQ-{ac_index + 1:03d}"
        ac_text = _get_ac_text(ctx, ac_index)
        req_type = classification.get("type", "api_behavior")
        postcondition = _find_postcondition(ctx, ac_index)

        # Build contract based on requirement type
        if req_type == "api_behavior":
            contract = {
                "interface": _build_interface(classification.get("interface", {}), ctx),
                "preconditions": _build_preconditions(ctx),
                "success": _build_success(postcondition),
                "failures": _build_failures(ctx),
                "invariants": _build_invariants(ctx, postcondition),
            }
        else:
            # Non-API types: include invariants and any available contract elements
            contract = {
                "invariants": _build_invariants(ctx, postcondition),
            }
            if ctx.preconditions:
                contract["preconditions"] = _build_preconditions(ctx)

        # Route via the routing table — deterministic lookup
        route = get_route(req_type)
        output_path = route["output_pattern"].format(key=jira_key_lower)

        requirements.append({
            "id": req_id,
            "ac_checkbox": ac_index,
            "ac_text": ac_text,
            "title": ac_text,
            "type": req_type,
            "contract": contract,
            "verification": [
                {
                    "refs": _build_verification_refs(ctx),
                    "skill": route["skill"],
                    "output": output_path,
                }
            ],
        })

    return requirements


def _get_ac_text(ctx: VerificationContext, ac_index: int) -> str:
    for ac in ctx.raw_acceptance_criteria:
        if ac["index"] == ac_index:
            return ac["text"]
    return ""


def _find_postcondition(ctx: VerificationContext, ac_index: int) -> dict:
    for p in ctx.postconditions:
        if p.get("ac_index") == ac_index:
            return p
    return {}


def _build_interface(interface: dict, ctx: VerificationContext) -> dict:
    auth = (
        ctx.constitution
        .get("api", {})
        .get("auth", {})
        .get("mechanism", "jwt_bearer")
    )
    return {
        "method": interface.get("method", "GET"),
        "path": interface.get("path", "/"),
        "auth": auth,
    }


def _build_preconditions(ctx: VerificationContext) -> list[dict]:
    return [
        {
            "id": p["id"],
            "description": p["description"],
            "formal": p.get("formal", ""),
            "category": p.get("category", ""),
        }
        for p in ctx.preconditions
    ]


def _build_success(postcondition: dict) -> dict:
    schema_raw = postcondition.get("schema", {})

    # Restructure: {field: {type, required}} → {type, required[], properties{}, forbidden_fields[]}
    required_fields = []
    properties = {}
    for field_name, field_def in schema_raw.items():
        if isinstance(field_def, dict):
            if field_def.get("required", False):
                required_fields.append(field_name)
            properties[field_name] = {k: v for k, v in field_def.items() if k != "required"}
        else:
            properties[field_name] = field_def

    return {
        "status": postcondition.get("status", 200),
        "content_type": postcondition.get("content_type", "application/json"),
        "schema": {
            "type": "object",
            "required": required_fields,
            "properties": properties,
            "forbidden_fields": postcondition.get("forbidden_fields", []),
        },
    }


def _build_failures(ctx: VerificationContext) -> list[dict]:
    return [
        {
            "id": fm["id"],
            "when": fm["description"],
            "violates": fm["violates"],
            "status": fm["status"],
            "body": fm.get("body", {}),
        }
        for fm in ctx.failure_modes
    ]


def _build_invariants(ctx: VerificationContext, postcondition: dict) -> list[dict]:
    forbidden = postcondition.get("forbidden_fields", [])
    return [
        {
            "id": inv["id"],
            "type": inv.get("category", "security"),
            "rule": inv["description"],
            "formal": _derive_formal(inv, forbidden),
        }
        for inv in ctx.invariants
    ]


def _derive_formal(invariant: dict, forbidden_fields: list[str]) -> str:
    """Derive a semi-formal expression for an invariant."""
    desc = invariant.get("description", "")
    if "MUST NOT contain" in desc and forbidden_fields:
        return " AND ".join(f"'{f}' not in response.keys()" for f in forbidden_fields)
    return desc


def _build_verification_refs(ctx: VerificationContext) -> list[str]:
    refs = ["success"]
    refs.extend(fm["id"] for fm in ctx.failure_modes)
    refs.extend(inv["id"] for inv in ctx.invariants)
    return refs


# ------------------------------------------------------------------
# Traceability map — built from compiled requirements
# ------------------------------------------------------------------

# Maps skill ID to the verification_type used in traceability refs
SKILL_TO_VERIFICATION_TYPE: dict[str, str] = {
    "pytest_unit_test": "test_result",
    "newrelic_alert_config": "config_validation",
    "otel_config": "deployment_check",
    "gherkin_scenario": "test_result",
}


def _build_traceability(
    ctx: VerificationContext, requirements: list[dict],
) -> dict:
    """Build traceability ac_mappings from compiled requirements.

    Each AC gets refs from its requirement's contract elements.
    Invariants are cross-cutting — they appear in every AC mapping (many-to-many).
    """
    # Index requirements by ac_checkbox for lookup
    req_by_ac: dict[int, dict] = {}
    for req in requirements:
        req_by_ac[req["ac_checkbox"]] = req

    # Collect cross-cutting invariant refs (apply to all ACs)
    cross_cutting_inv_refs: list[dict] = []
    for inv in ctx.invariants:
        cross_cutting_inv_refs.append({
            "id": inv["id"],
            "description": inv.get("description", ""),
        })

    ac_mappings: list[dict] = []
    for ac in ctx.raw_acceptance_criteria:
        ac_idx = ac["index"]
        req = req_by_ac.get(ac_idx)
        verifications: list[dict] = []

        if req:
            req_id = req["id"]
            skill = req["verification"][0]["skill"]
            ver_type = SKILL_TO_VERIFICATION_TYPE.get(skill, "test_result")
            contract = req.get("contract", {})

            # Success ref (only for api_behavior with a success block)
            if "success" in contract:
                verifications.append({
                    "ref": f"{req_id}.success",
                    "description": f"Happy path: HTTP {contract['success'].get('status', '?')}",
                    "verification_type": ver_type,
                })

            # Failure mode refs
            for fm in contract.get("failures", []):
                verifications.append({
                    "ref": f"{req_id}.{fm['id']}",
                    "description": f"Failure: {fm.get('when', fm['id'])}",
                    "verification_type": ver_type,
                })

            # Invariant refs from this requirement's contract
            for inv in contract.get("invariants", []):
                verifications.append({
                    "ref": f"{req_id}.{inv['id']}",
                    "description": f"Invariant: {inv.get('rule', inv['id'])}",
                    "verification_type": ver_type,
                })
        else:
            # AC has no requirement — still link cross-cutting invariants
            req_prefix = f"REQ-{ac_idx + 1:03d}"
            for inv in cross_cutting_inv_refs:
                verifications.append({
                    "ref": f"{req_prefix}.{inv['id']}",
                    "description": f"Invariant: {inv['description']}",
                    "verification_type": "test_result",
                })

        ac_mappings.append({
            "ac_checkbox": ac_idx,
            "ac_text": ac["text"],
            "pass_condition": "ALL_PASS",
            "required_verifications": verifications,
        })

    return {"ac_mappings": ac_mappings}
