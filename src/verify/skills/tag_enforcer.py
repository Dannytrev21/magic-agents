"""Tag Contract Enforcement — validates that generated tests cover all spec refs.

This is Block Principle 1: deterministic validation for things agents shouldn't decide.
The tag enforcer scans generated test content for spec ref patterns and compares
against the expected refs from the spec's verification blocks.

Coverage is a hard requirement — if a spec ref is missing from the generated tests,
the traceability chain is broken and the evaluator can't produce verdicts.
"""

import re


def validate_tags(
    generated_content: str,
    expected_refs: list[str],
) -> dict:
    """Validate that generated test content covers all expected spec refs.

    Scans for spec ref patterns in test content:
    - Bracket-enclosed: [REQ-001.success], [REQ-001.FAIL-001]
    - Underscore-based: test_REQ_001_success, test_REQ_001_FAIL_001
    - Marker-based: pytest.mark.spec("REQ-001.success")

    Args:
        generated_content: The full text of the generated test file.
        expected_refs: List of expected spec refs (e.g., ["REQ-001.success", "REQ-001.FAIL-001"]).

    Returns:
        Dict with keys:
        - "covered": list of refs found in the content
        - "missing": list of refs NOT found in the content
        - "extra": list of refs found in content but not in expected_refs
        - "coverage_pct": float percentage of expected refs covered
    """
    found_refs = extract_refs(generated_content)

    expected_set = set(expected_refs)
    found_set = set(found_refs)

    covered = sorted(expected_set & found_set)
    missing = sorted(expected_set - found_set)
    extra = sorted(found_set - expected_set)

    total = len(expected_set)
    coverage_pct = (len(covered) / total * 100) if total > 0 else 100.0

    return {
        "covered": covered,
        "missing": missing,
        "extra": extra,
        "coverage_pct": coverage_pct,
    }


def extract_refs(content: str) -> list[str]:
    """Extract all spec ref tags from generated test content.

    Recognizes three patterns:
    1. Bracket-enclosed: [REQ-001.success], [REQ-001.FAIL-001]
    2. pytest marker: pytest.mark.spec("REQ-001.success")
    3. Underscore-based in function names: test_REQ_001_FAIL_001 → REQ-001.FAIL-001

    Returns deduplicated list of refs.
    """
    refs: set[str] = set()

    # Pattern 1: bracket-enclosed refs
    bracket_matches = re.findall(r"\[([A-Z]+-\d+\.\S+?)\]", content)
    refs.update(bracket_matches)

    # Pattern 2: pytest.mark.spec("REQ-001.success")
    marker_matches = re.findall(r'pytest\.mark\.spec\(["\']([^"\']+)["\']\)', content)
    refs.update(marker_matches)

    # Pattern 3: underscore-based refs in function/method names
    # test_REQ_001_success → REQ-001.success
    # test_REQ_001_FAIL_001 → REQ-001.FAIL-001
    # test_REQ_001_INV_001 → REQ-001.INV-001
    underscore_matches = re.findall(
        r"(REQ_\d+)_(success|FAIL_\d+|INV_\d+)", content
    )
    for req_part, element_part in underscore_matches:
        req_ref = req_part.replace("_", "-")
        element_ref = element_part.replace("_", "-")
        refs.add(f"{req_ref}.{element_ref}")

    return sorted(refs)


def enforce_coverage(
    generated_content: str,
    expected_refs: list[str],
    min_coverage_pct: float = 100.0,
) -> tuple[bool, dict]:
    """Enforce minimum tag coverage. Returns (passed, validation_result).

    Args:
        generated_content: The generated test file content.
        expected_refs: Expected spec refs.
        min_coverage_pct: Minimum coverage percentage required (default: 100%).

    Returns:
        Tuple of (passed: bool, result: dict with coverage details).
    """
    result = validate_tags(generated_content, expected_refs)
    passed = result["coverage_pct"] >= min_coverage_pct
    return passed, result
