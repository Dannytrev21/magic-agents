"""Tag Contract Enforcement — validates spec ref coverage in generated tests.

Scans generated test content for spec ref patterns and compares against
expected refs from the spec's verification entries.

This implements Epic 4.3 of the Intent-to-Verification pipeline.
"""

import re


def validate_tags(generated_content: str, expected_refs: list[str]) -> dict:
    """Validate that generated test content covers all expected spec refs.

    Scans for refs in two formats:
    1. Bracket-enclosed: [REQ-001.success], [REQ-001.FAIL-001]
    2. Underscore-based in function names: test_REQ_001_FAIL_001

    Args:
        generated_content: The generated test file content
        expected_refs: List of expected spec refs (e.g., ["REQ-001.success", "REQ-001.FAIL-001"])

    Returns:
        Dict with keys: covered, missing, extra
    """
    found_refs = _extract_all_refs(generated_content)

    expected_set = set(expected_refs)
    found_set = set(found_refs)

    covered = sorted(expected_set & found_set)
    missing = sorted(expected_set - found_set)
    extra = sorted(found_set - expected_set)

    return {
        "covered": covered,
        "missing": missing,
        "extra": extra,
    }


def _extract_all_refs(text: str) -> list[str]:
    """Extract all spec ref tags from text.

    Looks for patterns like:
      [REQ-001.success]       → REQ-001.success
      [REQ-001.FAIL-001]      → REQ-001.FAIL-001
      test_REQ_001_FAIL_001   → REQ-001.FAIL-001
      test_REQ_001_success    → REQ-001.success
      test_REQ_001_INV_001    → REQ-001.INV-001
    """
    refs = set()

    # Pattern 1: bracket-enclosed refs like [REQ-001.success]
    bracket_matches = re.findall(r"\[([A-Z]+-\d+\.\S+?)\]", text)
    refs.update(bracket_matches)

    # Pattern 2: underscore-based refs in function names
    # Convert REQ_001_success → REQ-001.success
    # Convert REQ_001_FAIL_001 → REQ-001.FAIL-001
    underscore_matches = re.findall(
        r"(REQ_\d+)_(success|FAIL_\d+|INV_\d+)", text
    )
    for req_part, element_part in underscore_matches:
        req_ref = req_part.replace("_", "-")
        element_ref = element_part.replace("_", "-")
        ref = f"{req_ref}.{element_ref}"
        refs.add(ref)

    return sorted(refs)
