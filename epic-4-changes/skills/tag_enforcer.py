"""Tag Contract Enforcement — validates spec ref coverage in generated tests.

Implements Feature 4.3: Every generated test method must be tagged with its
spec ref in a consistent format, and coverage is validated.

Following Block Principle 1: This is deterministic validation — no AI.
"""

import re


def validate_tags(
    generated_content: str,
    expected_refs: list[str],
) -> dict[str, list[str]]:
    """Validate that generated test content covers all expected spec refs.

    Scans the generated content for spec ref patterns in brackets [REQ-001.success],
    markers, test names, or docstrings.

    Args:
        generated_content: The generated test file content as a string.
        expected_refs: List of expected spec refs (e.g., ["REQ-001.success", "REQ-001.FAIL-001"]).

    Returns:
        Dict with keys:
            - "covered": refs found in the content
            - "missing": expected refs not found
            - "extra": refs found but not in expected list
    """
    # Extract all refs from the content using bracket notation [REQ-XXX.YYY]
    found_refs = set()

    # Pattern 1: [REQ-NNN.something] in docstrings/comments
    bracket_pattern = re.compile(r"\[(REQ-\d+\.[\w-]+)\]")
    found_refs.update(bracket_pattern.findall(generated_content))

    # Pattern 2: pytest.mark.spec("REQ-NNN.something")
    marker_pattern = re.compile(r'pytest\.mark\.spec\(["\']([^"\']+)["\']\)')
    found_refs.update(marker_pattern.findall(generated_content))

    # Pattern 3: test name contains REQ_NNN_something (underscored form)
    # Convert back to dash form for comparison
    name_pattern = re.compile(r"def test_\w*?(REQ_\d+)_(\w+)")
    for match in name_pattern.finditer(generated_content):
        req = match.group(1).replace("_", "-")
        ref_suffix = match.group(2).replace("_", "-")
        found_refs.add(f"{req}.{ref_suffix}")

    expected_set = set(expected_refs)

    covered = sorted(found_refs & expected_set)
    missing = sorted(expected_set - found_refs)
    extra = sorted(found_refs - expected_set)

    return {
        "covered": covered,
        "missing": missing,
        "extra": extra,
    }
