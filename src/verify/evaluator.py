"""Evaluation engine — maps spec refs to test results and produces AC checkbox verdicts.

This module is 100% deterministic. Zero AI.
"""

import yaml


# ── Evaluation strategies per verification type ──

EVALUATION_STRATEGIES = {}


def strategy(ver_type):
    """Decorator to register evaluation strategies."""
    def decorator(fn):
        EVALUATION_STRATEGIES[ver_type] = fn
        return fn
    return decorator


@strategy("test_result")
def eval_test_result(ref, test_results, check_details=None):
    """Match a spec ref to a tagged test in the parsed test results."""
    for test_case in test_results.get("test_cases", []):
        tags = test_case.get("tags", [])
        name = test_case.get("name", "")

        if ref in tags or ref in name:
            passed = test_case["status"] == "passed"
            return {
                "passed": passed,
                "details": (
                    f"Test '{test_case['name']}' {test_case['status']}"
                    + (f": {test_case.get('failure_message', '')}" if not passed else "")
                ),
            }

    return {
        "passed": False,
        "details": f"No test found with tag matching '{ref}'",
    }


@strategy("deployment_check")
def eval_deployment_check(ref, test_results, check_details=None):
    """Verify that a generated artifact file exists and is structurally valid."""
    import json
    import os

    check_details = check_details or {}
    file_path = check_details.get("file", "")

    if not os.path.exists(file_path):
        return {"passed": False, "details": f"Expected file not found: {file_path}"}

    try:
        with open(file_path) as f:
            if file_path.endswith(".json"):
                json.load(f)
            elif file_path.endswith((".yaml", ".yml")):
                yaml.safe_load(f)
            else:
                f.read()
    except Exception as e:
        return {"passed": False, "details": f"File exists but is not parseable: {e}"}

    return {"passed": True, "details": f"File exists and is valid: {file_path}"}


@strategy("config_validation")
def eval_config_validation(ref, test_results, check_details=None):
    """Validate that a config file contains required entries."""
    import json
    import os

    check_details = check_details or {}
    file_path = check_details.get("file", "")
    required_entries = check_details.get(
        "required_spans", check_details.get("required_entries", [])
    )

    if not os.path.exists(file_path):
        return {"passed": False, "details": f"Config file not found: {file_path}"}

    try:
        with open(file_path) as f:
            content = (
                yaml.safe_load(f) if file_path.endswith((".yaml", ".yml"))
                else json.load(f)
            )
    except Exception as e:
        return {"passed": False, "details": f"Config not parseable: {e}"}

    content_str = json.dumps(content)
    missing = [entry for entry in required_entries if entry not in content_str]

    if missing:
        return {"passed": False, "details": f"Config missing required entries: {missing}"}

    return {
        "passed": True,
        "details": f"Config valid with all {len(required_entries)} required entries",
    }


def evaluate_pass_condition(condition, results, threshold=None):
    """Evaluate whether an AC checkbox should be ticked."""
    if not results:
        return False

    if condition == "ALL_PASS":
        return all(r["passed"] for r in results)
    elif condition == "ANY_PASS":
        return any(r["passed"] for r in results)
    elif condition == "PERCENTAGE":
        pass_rate = sum(1 for r in results if r["passed"]) / len(results) * 100
        return pass_rate >= (threshold or 100)

    return False


def evaluate_spec(spec_path: str, test_results: dict) -> list[dict]:
    """Master evaluation function.

    Reads the spec's traceability map and test results.
    Returns a verdict for each AC checkbox.
    """
    with open(spec_path) as f:
        spec = yaml.safe_load(f)

    verdicts = []

    for mapping in spec["traceability"]["ac_mappings"]:
        checkbox_results = []

        for req_ver in mapping["required_verifications"]:
            ref = req_ver["ref"]
            ver_type = req_ver["verification_type"]

            eval_fn = EVALUATION_STRATEGIES.get(ver_type)
            if eval_fn is None:
                result = {
                    "passed": False,
                    "details": f"Unknown verification type: {ver_type}",
                }
            else:
                result = eval_fn(
                    ref=ref,
                    test_results=test_results,
                    check_details=req_ver.get("check_details"),
                )

            checkbox_results.append({
                "ref": ref,
                "description": req_ver.get("description", ""),
                "verification_type": ver_type,
                "passed": result["passed"],
                "details": result.get("details", ""),
            })

        passed_count = sum(1 for r in checkbox_results if r["passed"])
        total_count = len(checkbox_results)

        verdict = evaluate_pass_condition(
            condition=mapping["pass_condition"],
            results=checkbox_results,
            threshold=mapping.get("threshold"),
        )

        verdicts.append({
            "ac_checkbox": mapping["ac_checkbox"],
            "ac_text": mapping["ac_text"],
            "passed": verdict,
            "pass_condition": mapping["pass_condition"],
            "summary": f"{passed_count}/{total_count} verifications passed",
            "evidence": checkbox_results,
        })

    return verdicts
