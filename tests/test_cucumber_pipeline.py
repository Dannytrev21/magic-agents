"""Tests for Cucumber/Gherkin runner integration in the verification pipeline.

RED phase — tests for parsing Cucumber JUnit XML results and extracting spec ref
tags from Gherkin scenario names/tags for the evaluation engine.
"""

import json
import os
import tempfile
import pytest

os.environ["LLM_MOCK"] = "true"

from verify.runner import parse_junit_xml, merge_results, _extract_tags


# ─── Tag extraction from Gherkin scenarios ───────────────────────────────


class TestCucumberTagExtraction:
    def test_extract_from_scenario_tag(self):
        """Cucumber scenario names contain spec ref tags like @REQ-001.success"""
        tags = _extract_tags("Successfully retrieve a dog by ID[REQ-001.success]")
        assert "REQ-001.success" in tags

    def test_extract_from_failure_tag(self):
        tags = _extract_tags("Reject request without auth token[REQ-001.FAIL-001]")
        assert "REQ-001.FAIL-001" in tags

    def test_extract_from_invariant_tag(self):
        tags = _extract_tags("Response never exposes forbidden fields[REQ-001.INV-001]")
        assert "REQ-001.INV-001" in tags

    def test_extract_multiple_tags(self):
        tags = _extract_tags("[REQ-001.success] and also [REQ-001.INV-001]")
        assert "REQ-001.success" in tags
        assert "REQ-001.INV-001" in tags


# ─── Cucumber JUnit XML parsing ──────────────────────────────────────────


class TestCucumberJunitParsing:
    @pytest.fixture
    def cucumber_xml(self, tmp_path):
        """Create a JUnit XML file similar to what Cucumber/Gradle produces."""
        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="Dog CRUD API verification" tests="5" failures="1" errors="0" skipped="0" time="2.345">
  <testcase name="Successfully retrieve a dog by ID" classname="Dog CRUD API verification" time="0.456">
    <system-out>@REQ-001.success @DEV-17</system-out>
  </testcase>
  <testcase name="Reject request without auth token[REQ-001.FAIL-001]" classname="Dog CRUD API verification" time="0.123">
  </testcase>
  <testcase name="Reject request with expired token[REQ-001.FAIL-002]" classname="Dog CRUD API verification" time="0.098">
  </testcase>
  <testcase name="Return 404 for non-existent dog[REQ-001.FAIL-003]" classname="Dog CRUD API verification" time="0.087">
    <failure message="Expected 404 but got 500">
      java.lang.AssertionError: Expected 404 but got 500
    </failure>
  </testcase>
  <testcase name="Response never exposes forbidden fields[REQ-001.INV-001]" classname="Dog CRUD API verification" time="0.134">
  </testcase>
</testsuite>"""
        xml_path = tmp_path / "cucumber_results.xml"
        xml_path.write_text(xml_content)
        return str(xml_path)

    def test_parses_cucumber_results(self, cucumber_xml):
        cases = parse_junit_xml(cucumber_xml)
        assert len(cases) == 5

    def test_extracts_tags_from_test_names(self, cucumber_xml):
        cases = parse_junit_xml(cucumber_xml)
        # Test with bracket-style tag
        fail_001 = next(c for c in cases if "FAIL-001" in c["name"])
        assert "REQ-001.FAIL-001" in fail_001["tags"]

    def test_detects_passed_and_failed(self, cucumber_xml):
        cases = parse_junit_xml(cucumber_xml)
        passed = [c for c in cases if c["status"] == "passed"]
        failed = [c for c in cases if c["status"] == "failed"]
        assert len(passed) == 4
        assert len(failed) == 1

    def test_failed_test_has_message(self, cucumber_xml):
        cases = parse_junit_xml(cucumber_xml)
        failed = next(c for c in cases if c["status"] == "failed")
        assert "404" in failed["failure_message"] or "500" in failed["failure_message"]


# ─── Merge results from multiple formats ─────────────────────────────────


class TestMergeResults:
    @pytest.fixture
    def junit_xml(self, tmp_path):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="tests" tests="1">
  <testcase name="test_REQ_001_success" classname="tests.test_api" time="0.1"/>
</testsuite>"""
        path = tmp_path / "junit.xml"
        path.write_text(xml)
        return str(path)

    @pytest.fixture
    def cucumber_xml(self, tmp_path):
        xml = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="cucumber" tests="1">
  <testcase name="Happy path[REQ-001.success]" classname="Dog API" time="0.2"/>
</testsuite>"""
        path = tmp_path / "cucumber.xml"
        path.write_text(xml)
        return str(path)

    def test_merge_two_xml_files(self, junit_xml, cucumber_xml):
        merged = merge_results([junit_xml, cucumber_xml])
        assert len(merged["test_cases"]) == 2

    def test_merge_preserves_tags(self, junit_xml, cucumber_xml):
        merged = merge_results([junit_xml, cucumber_xml])
        all_tags = []
        for case in merged["test_cases"]:
            all_tags.extend(case["tags"])
        assert "REQ-001.success" in all_tags


# ─── Pipeline integration (evaluator uses Cucumber results) ──────────────


class TestCucumberEvaluation:
    def test_evaluator_matches_cucumber_tags(self, tmp_path):
        """The evaluator should match spec refs in Cucumber test names."""
        from verify.evaluator import evaluate_spec

        # Create a minimal spec
        spec = {
            "meta": {"jira_key": "DEV-17"},
            "requirements": [],
            "traceability": {
                "ac_mappings": [
                    {
                        "ac_checkbox": 0,
                        "ac_text": "Dog can be retrieved by ID",
                        "pass_condition": "ALL_PASS",
                        "required_verifications": [
                            {"ref": "REQ-001.success", "description": "Happy path",
                             "verification_type": "test_result"},
                            {"ref": "REQ-001.FAIL-001", "description": "No auth",
                             "verification_type": "test_result"},
                        ],
                    }
                ]
            },
        }
        import yaml
        spec_path = str(tmp_path / "spec.yaml")
        with open(spec_path, "w") as f:
            yaml.dump(spec, f)

        # Simulate Cucumber test results
        test_results = {
            "test_cases": [
                {"name": "Successfully retrieve a dog by ID[REQ-001.success]",
                 "classname": "Dog API", "tags": ["REQ-001.success"],
                 "status": "passed", "failure_message": ""},
                {"name": "Reject without auth[REQ-001.FAIL-001]",
                 "classname": "Dog API", "tags": ["REQ-001.FAIL-001"],
                 "status": "passed", "failure_message": ""},
            ]
        }

        verdicts = evaluate_spec(spec_path, test_results)
        assert len(verdicts) == 1
        assert verdicts[0]["passed"] is True
        assert verdicts[0]["ac_checkbox"] == 0

    def test_evaluator_catches_cucumber_failure(self, tmp_path):
        """A failed Cucumber scenario should cause the verdict to fail."""
        from verify.evaluator import evaluate_spec
        import yaml

        spec = {
            "meta": {"jira_key": "DEV-17"},
            "requirements": [],
            "traceability": {
                "ac_mappings": [
                    {
                        "ac_checkbox": 0,
                        "ac_text": "Dog can be retrieved by ID",
                        "pass_condition": "ALL_PASS",
                        "required_verifications": [
                            {"ref": "REQ-001.success", "description": "Happy path",
                             "verification_type": "test_result"},
                        ],
                    }
                ]
            },
        }
        spec_path = str(tmp_path / "spec.yaml")
        with open(spec_path, "w") as f:
            yaml.dump(spec, f)

        test_results = {
            "test_cases": [
                {"name": "Retrieve dog[REQ-001.success]",
                 "classname": "Dog API", "tags": ["REQ-001.success"],
                 "status": "failed", "failure_message": "Expected 200 got 500"},
            ]
        }

        verdicts = evaluate_spec(spec_path, test_results)
        assert verdicts[0]["passed"] is False
