"""Tests for the pipeline module — Jira feedback loop, constitution loading, and update_jira."""

import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest
import yaml


class TestConstitutionLoading:
    """Tests for load_constitution (Feature 6: Constitution File Loading)."""

    def test_load_constitution_from_explicit_path(self):
        from verify.pipeline import load_constitution

        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump({"project": {"name": "test"}}, f)
            path = f.name

        try:
            result = load_constitution(path)
            assert result["project"]["name"] == "test"
        finally:
            os.unlink(path)

    def test_load_constitution_nonexistent_falls_through(self):
        """When explicit path doesn't exist, falls through to search paths."""
        from verify.pipeline import load_constitution
        import os

        # If constitution.yaml exists in cwd, it will find it via fallback
        result = load_constitution("/nonexistent/path/constitution.yaml")
        if os.path.exists("constitution.yaml"):
            assert isinstance(result, dict)
        else:
            assert result == {}

    def test_load_constitution_searches_cwd(self):
        from verify.pipeline import load_constitution

        # Should find constitution.yaml in the project root
        if os.path.exists("constitution.yaml"):
            result = load_constitution()
            assert isinstance(result, dict)


class TestUpdateJira:
    """Tests for update_jira (Epic 6: Jira Feedback Loop)."""

    def test_update_jira_function_exists(self):
        from verify.pipeline import update_jira
        assert callable(update_jira)

    def test_run_pipeline_with_jira_function_exists(self):
        from verify.pipeline import run_pipeline_with_jira
        assert callable(run_pipeline_with_jira)

    def test_update_jira_ticks_passing_checkboxes(self):
        """update_jira should tick checkboxes for passing verdicts."""
        from verify.pipeline import update_jira

        with patch("verify.jira_client.JiraClient") as MockClientCls:
            mock_client = MagicMock()
            MockClientCls.return_value = mock_client
            MockClientCls.format_evidence_comment = MagicMock(return_value="evidence text")

            verdicts = [
                {"ac_checkbox": 0, "ac_text": "AC 0", "passed": True, "summary": "1/1",
                 "pass_condition": "ALL_PASS", "evidence": []},
                {"ac_checkbox": 1, "ac_text": "AC 1", "passed": False, "summary": "0/1",
                 "pass_condition": "ALL_PASS", "evidence": []},
            ]

            result = update_jira("TEST-001", verdicts, "spec.yaml", transition_on_pass=False)

            # Should have ticked checkbox 0 but not 1
            mock_client.tick_checkboxes.assert_called_once_with("TEST-001", [0])

    def test_update_jira_returns_result_dict(self):
        """update_jira returns a summary dict."""
        from verify.pipeline import update_jira

        with patch("verify.jira_client.JiraClient") as MockClient:
            mock_client = MagicMock()
            MockClient.return_value = mock_client
            MockClient.format_evidence_comment = MagicMock(return_value="evidence")

            verdicts = [
                {"ac_checkbox": 0, "ac_text": "AC 0", "passed": True, "summary": "1/1",
                 "pass_condition": "ALL_PASS", "evidence": []},
            ]

            result = update_jira("TEST-001", verdicts, "spec.yaml", transition_on_pass=False)
            assert "checkboxes_ticked" in result
            assert "comment_posted" in result
            assert "all_passed" in result


class TestEvaluator:
    """Tests for evaluation strategies and pass conditions (Epic 5)."""

    def test_evaluation_strategies_registered(self):
        from verify.evaluator import EVALUATION_STRATEGIES
        assert "test_result" in EVALUATION_STRATEGIES
        assert "deployment_check" in EVALUATION_STRATEGIES
        assert "config_validation" in EVALUATION_STRATEGIES

    def test_evaluate_pass_condition_all_pass(self):
        from verify.evaluator import evaluate_pass_condition

        assert evaluate_pass_condition("ALL_PASS", [{"passed": True}, {"passed": True}]) is True
        assert evaluate_pass_condition("ALL_PASS", [{"passed": True}, {"passed": False}]) is False

    def test_evaluate_pass_condition_any_pass(self):
        from verify.evaluator import evaluate_pass_condition

        assert evaluate_pass_condition("ANY_PASS", [{"passed": False}, {"passed": True}]) is True
        assert evaluate_pass_condition("ANY_PASS", [{"passed": False}, {"passed": False}]) is False

    def test_evaluate_pass_condition_percentage(self):
        from verify.evaluator import evaluate_pass_condition

        results = [{"passed": True}, {"passed": True}, {"passed": False}]
        assert evaluate_pass_condition("PERCENTAGE", results, threshold=60) is True
        assert evaluate_pass_condition("PERCENTAGE", results, threshold=80) is False

    def test_evaluate_pass_condition_empty_results(self):
        from verify.evaluator import evaluate_pass_condition
        assert evaluate_pass_condition("ALL_PASS", []) is False

    def test_deployment_check_file_exists(self):
        from verify.evaluator import EVALUATION_STRATEGIES

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"key": "value"}')
            path = f.name

        try:
            result = EVALUATION_STRATEGIES["deployment_check"](
                "REQ-001", {}, {"file": path}
            )
            assert result["passed"] is True
        finally:
            os.unlink(path)

    def test_deployment_check_file_missing(self):
        from verify.evaluator import EVALUATION_STRATEGIES

        result = EVALUATION_STRATEGIES["deployment_check"](
            "REQ-001", {}, {"file": "/nonexistent/file.json"}
        )
        assert result["passed"] is False

    def test_config_validation_with_entries(self):
        from verify.evaluator import EVALUATION_STRATEGIES

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write('{"alert_name": "test", "threshold": 100}')
            path = f.name

        try:
            result = EVALUATION_STRATEGIES["config_validation"](
                "REQ-001", {}, {"file": path, "required_entries": ["alert_name", "threshold"]}
            )
            assert result["passed"] is True
        finally:
            os.unlink(path)


class TestRunner:
    """Tests for the multi-format test result parser (Feature 5.1)."""

    def test_merge_results_function_exists(self):
        from verify.runner import merge_results
        assert callable(merge_results)

    def test_parse_junit_xml(self):
        from verify.runner import parse_junit_xml

        xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<testsuite name="tests" tests="2" failures="1">
    <testcase name="test_REQ_001_success [REQ-001.success]" classname="test_demo">
    </testcase>
    <testcase name="test_REQ_001_FAIL_001 [REQ-001.FAIL-001]" classname="test_demo">
        <failure message="AssertionError">expected 401 got 500</failure>
    </testcase>
</testsuite>"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".xml", delete=False) as f:
            f.write(xml_content)
            path = f.name

        try:
            cases = parse_junit_xml(path)
            assert len(cases) == 2
            assert cases[0]["status"] == "passed"
            assert cases[1]["status"] == "failed"
            assert "REQ-001.success" in cases[0]["tags"]
            assert "REQ-001.FAIL-001" in cases[1]["tags"]
        finally:
            os.unlink(path)

    def test_extract_tags_bracket_pattern(self):
        from verify.runner import _extract_tags

        tags = _extract_tags("[REQ-001.success] and [REQ-001.FAIL-001]")
        assert "REQ-001.success" in tags
        assert "REQ-001.FAIL-001" in tags

    def test_extract_tags_underscore_pattern(self):
        from verify.runner import _extract_tags

        tags = _extract_tags("test_REQ_001_success_case")
        assert "REQ-001.success" in tags


class TestWebEndpoints:
    """Tests for new web API endpoints."""

    def test_web_app_importable(self):
        from verify.negotiation.web import app
        assert app is not None

    def test_ears_approve_endpoint_exists(self):
        """The /api/ears-approve endpoint is registered."""
        from verify.negotiation.web import app
        routes = [r.path for r in app.routes]
        assert "/api/ears-approve" in routes

    def test_pipeline_stream_endpoint_exists(self):
        """The /api/pipeline/stream endpoint is registered."""
        from verify.negotiation.web import app
        routes = [r.path for r in app.routes]
        assert "/api/pipeline/stream" in routes

    def test_run_tests_endpoint_exists(self):
        from verify.negotiation.web import app
        routes = [r.path for r in app.routes]
        assert "/api/run-tests" in routes

    def test_evaluate_endpoint_exists(self):
        from verify.negotiation.web import app
        routes = [r.path for r in app.routes]
        assert "/api/evaluate" in routes

    def test_jira_update_endpoint_exists(self):
        from verify.negotiation.web import app
        routes = [r.path for r in app.routes]
        assert "/api/jira-update" in routes

    def test_constitution_endpoint_exists(self):
        from verify.negotiation.web import app
        routes = [r.path for r in app.routes]
        assert "/api/constitution" in routes


class TestCompiler:
    """Tests for the spec compiler and routing table."""

    def test_routing_table_complete(self):
        from verify.compiler import ROUTING_TABLE
        expected_types = ["api_behavior", "performance_sla", "security_invariant",
                          "observability", "compliance", "data_constraint"]
        for t in expected_types:
            assert t in ROUTING_TABLE, f"Missing routing for {t}"

    def test_compile_spec_produces_traceability(self):
        from verify.compiler import compile_spec
        from verify.context import VerificationContext

        ctx = VerificationContext(
            jira_key="TEST-001", jira_summary="Test",
            raw_acceptance_criteria=[{"index": 0, "text": "AC text", "checked": False}],
            constitution={},
        )
        ctx.classifications = [{"ac_index": 0, "type": "api_behavior", "actor": "user",
                                "interface": {"method": "GET", "path": "/test"}}]
        ctx.postconditions = [{"ac_index": 0, "status": 200, "schema": {}}]
        ctx.preconditions = [{"id": "PRE-001", "description": "Auth", "category": "authentication", "formal": "x"}]
        ctx.failure_modes = [{"id": "FAIL-001", "violates": "PRE-001", "status": 401, "body": {}, "description": "no auth"}]
        ctx.approved = True
        ctx.approved_by = "test"

        spec = compile_spec(ctx)
        assert "traceability" in spec
        assert len(spec["traceability"]["ac_mappings"]) == 1
        assert spec["traceability"]["ac_mappings"][0]["pass_condition"] == "ALL_PASS"

    def test_compile_and_write_creates_file(self):
        from verify.compiler import compile_and_write
        from verify.context import VerificationContext

        ctx = VerificationContext(
            jira_key="TEST-WRITE", jira_summary="Test",
            raw_acceptance_criteria=[{"index": 0, "text": "AC", "checked": False}],
            constitution={},
        )
        ctx.classifications = [{"ac_index": 0, "type": "api_behavior", "actor": "user",
                                "interface": {"method": "GET", "path": "/t"}}]
        ctx.postconditions = [{"ac_index": 0, "status": 200, "schema": {}}]
        ctx.preconditions = [{"id": "P1", "description": "a", "category": "authentication", "formal": "x"}]
        ctx.failure_modes = [{"id": "F1", "violates": "P1", "status": 401, "body": {}, "description": "d"}]
        ctx.approved = True
        ctx.approved_by = "test"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = compile_and_write(ctx, output_dir=tmpdir)
            assert os.path.exists(path)
            assert ctx.spec_path == path

            with open(path) as f:
                loaded = yaml.safe_load(f)
            assert loaded["meta"]["jira_key"] == "TEST-WRITE"


class TestNegotiationSynthesis:
    """Tests for post-negotiation synthesis."""

    def test_run_synthesis_populates_context(self):
        from verify.context import VerificationContext
        from verify.negotiation.synthesis import run_synthesis

        ctx = VerificationContext(
            jira_key="TEST-001", jira_summary="Test",
            raw_acceptance_criteria=[{"index": 0, "text": "User can view profile", "checked": False}],
            constitution={"verification_standards": {"security_invariants": ["No password in response"]}},
        )
        ctx.classifications = [{"ac_index": 0, "type": "api_behavior", "actor": "user",
                                "interface": {"method": "GET", "path": "/api/v1/users/me"}}]
        ctx.postconditions = [{"ac_index": 0, "status": 200, "schema": {}, "forbidden_fields": ["password"]}]
        ctx.preconditions = [{"id": "PRE-001", "description": "Auth", "category": "authentication"}]
        ctx.failure_modes = [{"id": "FAIL-001", "violates": "PRE-001", "status": 401, "description": "No auth"}]

        run_synthesis(ctx)

        assert len(ctx.invariants) >= 1
        assert len(ctx.ears_statements) >= 1
        assert "ac_mappings" in ctx.traceability_map
        assert len(ctx.traceability_map["ac_mappings"]) == 1

    def test_ears_statements_include_when_then(self):
        from verify.context import VerificationContext
        from verify.negotiation.synthesis import generate_ears_statements

        ctx = VerificationContext(
            jira_key="TEST-001", jira_summary="Test",
            raw_acceptance_criteria=[{"index": 0, "text": "AC", "checked": False}],
            constitution={},
        )
        ctx.classifications = [{"ac_index": 0, "type": "api_behavior", "actor": "user",
                                "interface": {"method": "GET", "path": "/api/v1/test"}}]
        ctx.postconditions = [{"ac_index": 0, "status": 200}]
        ctx.failure_modes = [{"id": "FAIL-001", "violates": "PRE-001", "status": 401, "description": "No auth token"}]
        ctx.invariants = []

        ears = generate_ears_statements(ctx)
        assert any("WHEN" in e and "SHALL" in e for e in ears), "Missing WHEN/SHALL pattern"
        assert any("IF" in e and "THEN" in e for e in ears), "Missing IF/THEN pattern"
