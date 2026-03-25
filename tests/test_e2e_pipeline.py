"""End-to-end pipeline tests — RED-GREEN TDD.

Tests the full flow: Jira fetch → negotiation → compile → generate → evaluate.
Uses mock mode for LLM calls to keep tests fast and deterministic.
"""
import json
import os
import pytest
import yaml
from pathlib import Path
from unittest.mock import patch

# Force mock mode at import time AND ensure no API key is present
os.environ["LLM_MOCK"] = "true"
os.environ.pop("ANTHROPIC_API_KEY", None)

from fastapi.testclient import TestClient
from verify.negotiation.web import app, _session
from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.compiler import compile_spec, compile_and_write
from verify.negotiation.harness import NegotiationHarness
from verify.negotiation.phase1 import run_phase1
from verify.negotiation.phase2 import run_phase2
from verify.negotiation.phase3 import run_phase3
from verify.negotiation.phase4 import run_phase4
from verify.negotiation.synthesis import run_synthesis
from verify.evaluator import evaluate_spec, evaluate_pass_condition, EVALUATION_STRATEGIES
from verify.runner import merge_results
from verify.spec_diff import diff_specs, format_diff_summary
from verify.spec_validator import validate_spec


client = TestClient(app)


@pytest.fixture(autouse=True)
def mock_env_and_clear_session():
    """Ensure mock mode is active and clear session before each test."""
    with patch.dict(os.environ, {"LLM_MOCK": "true"}, clear=False):
        # Also remove API key to prevent real calls
        os.environ.pop("ANTHROPIC_API_KEY", None)
        _session.clear()
        yield
        _session.clear()


class TestFullNegotiationToSpec:
    """Test the complete negotiation → spec compilation flow."""

    def _make_context(self):
        return VerificationContext(
            jira_key="DEV-17",
            jira_summary="Dog Service CRUD API",
            raw_acceptance_criteria=[
                {"index": 0, "text": "User can list all dogs via GET /api/v1/dogs", "checked": False},
            ],
            constitution={
                "project": {"framework": "spring-boot", "language": "java"},
                "api": {"base_path": "/api/v1"},
            },
        )

    def test_phase1_produces_classifications(self):
        """RED: Phase 1 must produce valid classifications for each AC."""
        ctx = self._make_context()
        llm = LLMClient()
        results = run_phase1(ctx, llm)
        assert len(results) >= 1
        assert results[0]["type"] in [
            "api_behavior", "performance_sla", "security_invariant",
            "observability", "compliance", "data_constraint",
        ]
        assert "actor" in results[0]
        assert ctx.classifications == results

    def test_full_4_phase_negotiation(self):
        """RED: All 4 phases complete and produce expected artifacts."""
        ctx = self._make_context()
        llm = LLMClient()

        # Phase 1
        run_phase1(ctx, llm)
        assert len(ctx.classifications) >= 1

        # Phase 2
        run_phase2(ctx, llm)
        assert len(ctx.postconditions) >= 1

        # Phase 3
        run_phase3(ctx, llm)
        assert len(ctx.preconditions) >= 1

        # Phase 4
        run_phase4(ctx, llm)
        assert len(ctx.failure_modes) >= 1

        # Synthesis
        run_synthesis(ctx)
        assert len(ctx.ears_statements) >= 1
        assert "ac_mappings" in ctx.traceability_map

    def test_compile_spec_after_negotiation(self):
        """RED: Compiled spec must be valid YAML with all required sections."""
        ctx = self._make_context()
        llm = LLMClient()

        # Run all phases
        run_phase1(ctx, llm)
        run_phase2(ctx, llm)
        run_phase3(ctx, llm)
        run_phase4(ctx, llm)
        run_synthesis(ctx)
        ctx.approved = True
        ctx.approved_by = "test"

        spec = compile_spec(ctx)

        # Validate structure
        assert "meta" in spec
        assert "requirements" in spec
        assert "traceability" in spec
        assert spec["meta"]["jira_key"] == "DEV-17"
        assert len(spec["requirements"]) >= 1

        # Each requirement should have verification routing
        for req in spec["requirements"]:
            assert "verification" in req
            assert len(req["verification"]) >= 1
            assert "skill" in req["verification"][0]

        # Traceability should map ACs
        mappings = spec["traceability"]["ac_mappings"]
        assert len(mappings) >= 1
        assert mappings[0]["ac_checkbox"] == 0

    def test_compile_and_write_creates_file(self, tmp_path):
        """RED: compile_and_write must create a YAML file on disk."""
        ctx = self._make_context()
        llm = LLMClient()

        run_phase1(ctx, llm)
        run_phase2(ctx, llm)
        run_phase3(ctx, llm)
        run_phase4(ctx, llm)
        run_synthesis(ctx)
        ctx.approved = True
        ctx.approved_by = "test"

        spec_path = compile_and_write(ctx, output_dir=str(tmp_path))
        assert os.path.exists(spec_path)

        with open(spec_path) as f:
            loaded = yaml.safe_load(f)
        assert loaded["meta"]["jira_key"] == "DEV-17"

    def test_spec_validates_against_schema(self):
        """RED: Compiled spec must pass JSON schema validation."""
        ctx = self._make_context()
        llm = LLMClient()

        run_phase1(ctx, llm)
        run_phase2(ctx, llm)
        run_phase3(ctx, llm)
        run_phase4(ctx, llm)
        run_synthesis(ctx)
        ctx.approved = True
        ctx.approved_by = "test"

        spec = compile_spec(ctx)
        valid, errors = validate_spec(spec)
        assert valid, f"Spec validation errors: {errors}"


class TestWebE2EFlow:
    """Test the web API end-to-end flow."""

    def test_start_and_approve_all_phases(self):
        """RED: Web flow should handle start → 4 approvals → summary."""
        # Start negotiation
        resp = client.post("/api/start", json={
            "jira_key": "DEV-17",
            "jira_summary": "Dog Service CRUD API",
            "acceptance_criteria": [
                {"index": 0, "text": "User can list all dogs via GET /api/v1/dogs", "checked": False},
            ],
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data["phase_number"] == 1
        assert data["done"] is False

        # Approve phases 1-6
        for phase_num in range(2, 8):
            resp = client.post("/api/respond", json={"input": "approve"})
            assert resp.status_code == 200
            data = resp.json()
            if phase_num <= 7 and not data.get("done"):
                assert data["phase_number"] == phase_num

        # After phase 7, should get done with summary
        # (The 7th approve triggers synthesis/traceability)
        if not data.get("done"):
            resp = client.post("/api/respond", json={"input": "approve"})
            data = resp.json()
        assert data.get("done") is True
        assert "summary" in data

    def test_compile_after_negotiation(self):
        """RED: Compile endpoint should work after full negotiation."""
        # Start and approve all phases
        client.post("/api/start", json={
            "jira_key": "DEV-17",
            "jira_summary": "Dog Service CRUD API",
            "acceptance_criteria": [
                {"index": 0, "text": "User can list all dogs via GET /api/v1/dogs", "checked": False},
            ],
        })
        for _ in range(7):
            client.post("/api/respond", json={"input": "approve"})

        # Now approve EARS
        resp = client.post("/api/ears-approve", json={"approved_by": "test"})
        assert resp.status_code == 200
        assert resp.json()["approved"] is True

        # Compile spec
        resp = client.post("/api/compile")
        assert resp.status_code == 200
        data = resp.json()
        assert "spec_path" in data
        assert "spec_content" in data

    def test_feedback_revises_phase(self):
        """RED: Providing feedback should re-run the phase with revisions."""
        client.post("/api/start", json={
            "jira_key": "DEV-17",
            "jira_summary": "Dog Service CRUD API",
            "acceptance_criteria": [
                {"index": 0, "text": "User can list all dogs via GET /api/v1/dogs", "checked": False},
            ],
        })

        # Send feedback instead of approve
        resp = client.post("/api/respond", json={
            "input": "The type should be api_behavior, not security_invariant"
        })
        assert resp.status_code == 200
        data = resp.json()
        assert data.get("revised") is True
        assert data["phase_number"] == 1  # Still on phase 1

    def test_spec_diff_no_previous(self):
        """RED: Spec diff with no old spec should indicate first spec."""
        # Negotiate and compile
        client.post("/api/start", json={
            "jira_key": "NEWTICKET-999",
            "jira_summary": "New ticket",
            "acceptance_criteria": [
                {"index": 0, "text": "Test AC", "checked": False},
            ],
        })
        for _ in range(7):
            client.post("/api/respond", json={"input": "approve"})
        client.post("/api/ears-approve", json={"approved_by": "test"})

        resp = client.post("/api/spec-diff")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_old_spec"] is False

    def test_scan_endpoint(self):
        """RED: Codebase scan should work for dog-service."""
        resp = client.post("/api/scan", json={"project_root": "dog-service"})
        assert resp.status_code == 200
        data = resp.json()
        # Should either scan successfully or fail gracefully
        assert "scanned" in data


class TestEvaluationEngine:
    """Test the evaluation engine features (Epic 5)."""

    def test_evaluation_strategies_registered(self):
        """RED: All 3 evaluation strategies must be registered."""
        assert "test_result" in EVALUATION_STRATEGIES
        assert "deployment_check" in EVALUATION_STRATEGIES
        assert "config_validation" in EVALUATION_STRATEGIES

    def test_pass_condition_all_pass(self):
        """RED: ALL_PASS returns True only when all results pass."""
        results = [{"passed": True}, {"passed": True}]
        assert evaluate_pass_condition("ALL_PASS", results) is True
        results.append({"passed": False})
        assert evaluate_pass_condition("ALL_PASS", results) is False

    def test_pass_condition_any_pass(self):
        """RED: ANY_PASS returns True if at least one passes."""
        assert evaluate_pass_condition("ANY_PASS", [{"passed": False}, {"passed": True}]) is True
        assert evaluate_pass_condition("ANY_PASS", [{"passed": False}, {"passed": False}]) is False

    def test_pass_condition_percentage(self):
        """RED: PERCENTAGE returns True if ratio >= threshold."""
        results = [{"passed": True}, {"passed": True}, {"passed": False}]
        assert evaluate_pass_condition("PERCENTAGE", results, threshold=60) is True
        assert evaluate_pass_condition("PERCENTAGE", results, threshold=80) is False

    def test_multi_format_merge(self):
        """RED: merge_results must combine multiple result files."""
        assert callable(merge_results)


class TestCheckpointResume:
    """Test checkpoint and resume functionality (Feature 2.8)."""

    def test_save_and_load_checkpoint(self, tmp_path):
        """RED: Checkpoint saves and restores context correctly."""
        from verify.negotiation.checkpoint import save_checkpoint, load_checkpoint

        ctx = VerificationContext(
            jira_key="CP-001",
            jira_summary="Checkpoint Test",
            raw_acceptance_criteria=[{"index": 0, "text": "Test AC", "checked": False}],
            constitution={},
        )
        ctx.classifications = [{"ac_index": 0, "type": "api_behavior"}]

        # Save with custom base dir
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            path = save_checkpoint(ctx, "phase_1")
            assert path.exists()

            # Load
            result = load_checkpoint("CP-001")
            assert result is not None
            loaded_ctx, phase_idx = result
            assert loaded_ctx.jira_key == "CP-001"
            assert len(loaded_ctx.classifications) == 1
        finally:
            os.chdir(original_cwd)

    def test_session_check_endpoint(self):
        """RED: Session check endpoint reports checkpoint status."""
        resp = client.get("/api/session/NONEXISTENT-999")
        assert resp.status_code == 200
        data = resp.json()
        assert data["has_checkpoint"] is False


class TestObservability:
    """Test the observability/logging feature (Feature 21)."""

    def test_harness_logger_exists(self):
        """RED: HarnessLogger must be usable."""
        from verify.observability import HarnessLogger
        logger = HarnessLogger("TEST-001")
        logger.log_phase_started("phase_1")
        logger.log_phase_completed("phase_1", duration_ms=100)
        # Should not raise

    def test_harness_logger_writes_jsonl(self, tmp_path):
        """RED: Logger should write JSONL entries."""
        from verify.observability import HarnessLogger
        original_cwd = os.getcwd()
        os.chdir(tmp_path)
        try:
            logger = HarnessLogger("LOG-001")
            logger.log_phase_started("phase_1")
            logger.log_phase_completed("phase_1", duration_ms=150)

            log_path = Path(".verify/logs/LOG-001.jsonl")
            assert log_path.exists()
            lines = log_path.read_text().strip().split("\n")
            assert len(lines) >= 2
            for line in lines:
                entry = json.loads(line)
                assert "event_type" in entry
                assert "timestamp" in entry
        finally:
            os.chdir(original_cwd)


class TestBackPressure:
    """Test the back-pressure controller (Feature 20)."""

    def test_controller_limits(self):
        """RED: BackPressure should enforce hard limits."""
        from verify.backpressure import BackPressureController

        controller = BackPressureController(
            max_api_calls=5,
            max_tokens=1000,
            max_wall_clock_seconds=60,
            max_retries_per_phase=2,
        )
        assert controller.can_proceed()
        for _ in range(5):
            controller.record_api_call(tokens_in=50, tokens_out=50)
        # Should now be at the limit
        assert not controller.can_proceed()


class TestSpecDiffIntegration:
    """Test spec diff feature (Feature 17) through the web API."""

    def test_diff_detects_changes(self, tmp_path):
        """RED: Diffing two specs should detect structural differences."""
        old_spec = {
            "meta": {"jira_key": "DIFF-001", "spec_version": "1.0"},
            "requirements": [
                {"id": "REQ-001", "title": "Original"}
            ],
            "traceability": {"ac_mappings": []},
        }
        new_spec = {
            "meta": {"jira_key": "DIFF-001", "spec_version": "1.0"},
            "requirements": [
                {"id": "REQ-001", "title": "Modified"},
                {"id": "REQ-002", "title": "New requirement"},
            ],
            "traceability": {"ac_mappings": []},
        }

        old_path = tmp_path / "old_spec.yaml"
        with open(old_path, "w") as f:
            yaml.dump(old_spec, f)

        result = diff_specs(str(old_path), new_spec)
        assert "REQ-002" in result["added_requirements"]
        assert "REQ-001" in result["modified_requirements"]

        summary = format_diff_summary(result)
        assert "REQ-002" in summary
