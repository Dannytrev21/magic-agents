"""Test runner and JUnit XML parser for the verification pipeline."""

import json
import os
import re
import subprocess
import sys
import xml.etree.ElementTree as ET


def run_gradle_tests(project_dir: str, results_dir: str) -> str:
    """Run Gradle tests in a project directory and copy JUnit XML results.

    Returns the path to the JUnit XML results file.
    """
    os.makedirs(results_dir, exist_ok=True)

    gradlew = os.path.join(project_dir, "gradlew")
    result = subprocess.run(
        [gradlew, "test"],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )

    if result.returncode not in (0, 1):
        print(f"gradle test stderr:\n{result.stderr}", file=sys.stderr)

    # Find JUnit XML results from Gradle's output directory
    gradle_results_dir = os.path.join(project_dir, "build", "test-results", "test")
    xml_path = os.path.join(results_dir, "results.xml")

    if os.path.isdir(gradle_results_dir):
        # Merge all XML files from Gradle into one
        import glob
        xml_files = glob.glob(os.path.join(gradle_results_dir, "*.xml"))
        if xml_files:
            # Use the first XML file or merge multiple
            import shutil
            shutil.copy2(xml_files[0], xml_path)

    return xml_path


def run_tests(test_path: str, results_dir: str) -> str:
    """Run pytest on a test file and produce JUnit XML results.

    Returns the path to the JUnit XML results file.
    """
    os.makedirs(results_dir, exist_ok=True)
    xml_path = os.path.join(results_dir, "results.xml")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", test_path, f"--junitxml={xml_path}", "-v"],
        capture_output=True,
        text=True,
    )

    if result.returncode not in (0, 1):
        # 0 = all passed, 1 = some failed, anything else is an error
        print(f"pytest stderr:\n{result.stderr}", file=sys.stderr)

    return xml_path


def parse_junit_xml(xml_path: str) -> list[dict]:
    """Parse JUnit XML into a unified list of test case dicts.

    Each dict has: name, tags, status, failure_message.
    Tags are extracted from [REQ-001.FAIL-002] patterns in the test name or docstring.
    """
    tree = ET.parse(xml_path)
    cases = []

    for testcase in tree.iter("testcase"):
        name = testcase.get("name", "")
        classname = testcase.get("classname", "")

        # Extract spec ref tags from the test name
        tags = _extract_tags(name)

        # Also check properties for tags (JUnit 5 style)
        for prop in testcase.iter("property"):
            if prop.get("name") == "tag":
                tags.append(prop.get("value", ""))

        # Determine status
        failure = testcase.find("failure")
        error = testcase.find("error")
        skipped = testcase.find("skipped")

        if failure is not None:
            status = "failed"
            failure_msg = failure.get("message", "")
        elif error is not None:
            status = "errored"
            failure_msg = error.get("message", "")
        elif skipped is not None:
            status = "skipped"
            failure_msg = ""
        else:
            status = "passed"
            failure_msg = ""

        cases.append({
            "name": name,
            "classname": classname,
            "tags": tags,
            "status": status,
            "failure_message": failure_msg,
        })

    return cases


def run_and_parse(test_path: str, results_dir: str) -> dict:
    """Run tests and parse results in one call.

    Returns {"test_cases": [...]}.
    """
    xml_path = run_tests(test_path, results_dir)
    cases = parse_junit_xml(xml_path)

    result = {"test_cases": cases}

    # Write parsed results as JSON for debugging
    parsed_path = os.path.join(results_dir, "parsed_results.json")
    with open(parsed_path, "w") as f:
        json.dump(result, f, indent=2)

    return result


def merge_results(paths: list[str]) -> dict:
    """Merge test results from multiple files into a single unified dict.

    Auto-detects format: .xml → JUnit, .json → Jest/parsed.
    """
    all_cases = []

    for path in paths:
        if path.endswith(".xml"):
            all_cases.extend(parse_junit_xml(path))
        elif path.endswith(".json"):
            with open(path) as f:
                content = json.load(f)
            if "test_cases" in content:
                all_cases.extend(content["test_cases"])
            elif "testResults" in content:
                all_cases.extend(_parse_jest_json(content))

    return {"test_cases": all_cases}


def _extract_tags(text: str) -> list[str]:
    """Extract spec ref tags from text.

    Looks for patterns like:
      [REQ-001.success]       → REQ-001.success
      [REQ-001.FAIL-001]      → REQ-001.FAIL-001
      test_REQ_001_FAIL_001   → REQ-001.FAIL-001
    """
    tags = []

    # Pattern 1: bracket-enclosed refs like [REQ-001.success]
    bracket_matches = re.findall(r"\[([A-Z]+-\d+\.\S+?)\]", text)
    tags.extend(bracket_matches)

    # Pattern 2: underscore-based refs in function names like test_REQ_001_FAIL_001
    # Convert REQ_001_success → REQ-001.success
    # Convert REQ_001_FAIL_001 → REQ-001.FAIL-001
    underscore_matches = re.findall(
        r"(REQ_\d+)_(success|FAIL_\d+|INV_\d+)", text
    )
    for req_part, element_part in underscore_matches:
        req_ref = req_part.replace("_", "-")  # REQ_001 → REQ-001
        element_ref = element_part.replace("_", "-")  # FAIL_001 → FAIL-001
        tag = f"{req_ref}.{element_ref}"
        if tag not in tags:
            tags.append(tag)

    return tags


def _parse_jest_json(content: dict) -> list[dict]:
    """Parse Jest JSON output into unified test case format."""
    cases = []

    for suite in content.get("testResults", []):
        for test in suite.get("assertionResults", []):
            name = test.get("fullName", "") or test.get("title", "")
            tags = _extract_tags(name)

            for ancestor in test.get("ancestorTitles", []):
                tags.extend(_extract_tags(ancestor))

            cases.append({
                "name": name,
                "classname": "",
                "tags": tags,
                "status": test.get("status", "failed"),
                "failure_message": "\n".join(test.get("failureMessages", [])),
            })

    return cases
