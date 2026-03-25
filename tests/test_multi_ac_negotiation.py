"""RED tests for multi-AC negotiation end-to-end flow.

Tests that multiple acceptance criteria flow correctly through all 4 phases,
synthesis, compilation, and produce proper traceability.

TDD: Write these tests FIRST (RED), then implement if any fail (GREEN).
"""

import os
import tempfile

import pytest
import yaml


@pytest.fixture(autouse=True)
def ensure_mock_mode(monkeypatch):
    """Ensure LLM_MOCK is set for all tests in this module."""
    monkeypatch.setenv("LLM_MOCK", "true")


class TestMultiACNegotiation:
    """Tests for Feature 2: Multi-AC Support.

    Ensures tickets with 2-5 ACs each get their own classification,
    postcondition, and that traceability links each AC to its tests.
    """

    def test_phase1_classifies_multiple_acs(self):
        """Each AC in a multi-AC ticket should get its own classification."""
        from verify.context import VerificationContext
        from verify.llm_client import LLMClient
        from verify.negotiation.phase1 import run_phase1

        ctx = VerificationContext(
            jira_key="MULTI-001",
            jira_summary="Dog CRUD API",
            raw_acceptance_criteria=[
                {"index": 0, "text": "User can create a dog via POST /api/v1/dogs", "checked": False},
                {"index": 1, "text": "User can retrieve a dog via GET /api/v1/dogs/{id}", "checked": False},
                {"index": 2, "text": "User can delete a dog via DELETE /api/v1/dogs/{id}", "checked": False},
            ],
            constitution={"project": {"framework": "spring-boot"}, "api": {"base_path": "/api/v1"}},
        )
        llm = LLMClient()
        classifications = run_phase1(ctx, llm)

        assert len(classifications) >= 3, f"Expected 3+ classifications, got {len(classifications)}"
        ac_indices = {c.get("ac_index") for c in classifications}
        assert len(ac_indices) >= 2, "Multiple ACs should produce distinct ac_index values"

    def test_synthesis_multi_ac_traceability(self):
        """Synthesis should produce one traceability mapping per AC."""
        from verify.context import VerificationContext
        from verify.negotiation.synthesis import run_synthesis

        ctx = VerificationContext(
            jira_key="MULTI-002",
            jira_summary="Multi-AC Dog API",
            raw_acceptance_criteria=[
                {"index": 0, "text": "Create a dog", "checked": False},
                {"index": 1, "text": "Retrieve a dog", "checked": False},
            ],
            constitution={},
        )
        ctx.classifications = [
            {"ac_index": 0, "type": "api_behavior", "actor": "authenticated_user",
             "interface": {"method": "POST", "path": "/api/v1/dogs"}},
            {"ac_index": 1, "type": "api_behavior", "actor": "authenticated_user",
             "interface": {"method": "GET", "path": "/api/v1/dogs/{id}"}},
        ]
        ctx.postconditions = [
            {"ac_index": 0, "status": 201, "schema": {}},
            {"ac_index": 1, "status": 200, "schema": {}},
        ]
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Valid auth", "category": "authentication"},
        ]
        ctx.failure_modes = [
            {"id": "FAIL-001", "violates": "PRE-001", "status": 401, "description": "No auth", "body": {}},
        ]

        run_synthesis(ctx)

        assert len(ctx.traceability_map["ac_mappings"]) == 2
        assert ctx.traceability_map["ac_mappings"][0]["ac_checkbox"] == 0
        assert ctx.traceability_map["ac_mappings"][1]["ac_checkbox"] == 1

        # Each AC mapping should have refs
        for mapping in ctx.traceability_map["ac_mappings"]:
            assert len(mapping["required_verifications"]) > 0

    def test_compiler_multi_ac_produces_multiple_requirements(self):
        """Compiler should produce one requirement per classified AC."""
        from verify.compiler import compile_spec
        from verify.context import VerificationContext

        ctx = VerificationContext(
            jira_key="MULTI-003",
            jira_summary="Multi-AC",
            raw_acceptance_criteria=[
                {"index": 0, "text": "AC-0", "checked": False},
                {"index": 1, "text": "AC-1", "checked": False},
            ],
            constitution={},
        )
        ctx.classifications = [
            {"ac_index": 0, "type": "api_behavior", "actor": "user",
             "interface": {"method": "POST", "path": "/dogs"}},
            {"ac_index": 1, "type": "api_behavior", "actor": "user",
             "interface": {"method": "GET", "path": "/dogs/{id}"}},
        ]
        ctx.postconditions = [
            {"ac_index": 0, "status": 201, "schema": {}},
            {"ac_index": 1, "status": 200, "schema": {}},
        ]
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Auth", "category": "authentication", "formal": "jwt != null"},
        ]
        ctx.failure_modes = [
            {"id": "FAIL-001", "violates": "PRE-001", "status": 401, "body": {}, "description": "no auth"},
        ]
        ctx.approved = True
        ctx.approved_by = "test"

        spec = compile_spec(ctx)
        assert len(spec["requirements"]) == 2, f"Expected 2 requirements, got {len(spec['requirements'])}"
        assert spec["requirements"][0]["id"] == "REQ-001"
        assert spec["requirements"][1]["id"] == "REQ-002"

    def test_full_negotiation_to_spec_multi_ac(self):
        """Full flow: multi-AC context → synthesis → compile → write → load."""
        from verify.compiler import compile_and_write
        from verify.context import VerificationContext
        from verify.negotiation.synthesis import run_synthesis

        ctx = VerificationContext(
            jira_key="E2E-MULTI",
            jira_summary="End-to-end multi-AC",
            raw_acceptance_criteria=[
                {"index": 0, "text": "Create dog", "checked": False},
                {"index": 1, "text": "Get dog", "checked": False},
                {"index": 2, "text": "Delete dog", "checked": False},
            ],
            constitution={"verification_standards": {"security_invariants": ["No password in response"]}},
        )
        ctx.classifications = [
            {"ac_index": 0, "type": "api_behavior", "actor": "user",
             "interface": {"method": "POST", "path": "/api/v1/dogs"}},
            {"ac_index": 1, "type": "api_behavior", "actor": "user",
             "interface": {"method": "GET", "path": "/api/v1/dogs/{id}"}},
            {"ac_index": 2, "type": "api_behavior", "actor": "user",
             "interface": {"method": "DELETE", "path": "/api/v1/dogs/{id}"}},
        ]
        ctx.postconditions = [
            {"ac_index": 0, "status": 201, "schema": {"name": {"type": "string", "required": True}}},
            {"ac_index": 1, "status": 200, "schema": {"id": {"type": "integer", "required": True}}},
            {"ac_index": 2, "status": 204, "schema": {}},
        ]
        ctx.preconditions = [
            {"id": "PRE-001", "description": "Valid JWT", "category": "authentication", "formal": "jwt != null"},
            {"id": "PRE-002", "description": "Dog exists", "category": "data_existence", "formal": "dog.id exists"},
        ]
        ctx.failure_modes = [
            {"id": "FAIL-001", "violates": "PRE-001", "status": 401, "body": {"error": "Unauthorized"}, "description": "Missing auth"},
            {"id": "FAIL-002", "violates": "PRE-002", "status": 404, "body": {"error": "Not found"}, "description": "Dog not found"},
        ]

        run_synthesis(ctx)
        assert len(ctx.ears_statements) >= 3  # At least one per postcondition + failure modes
        assert len(ctx.traceability_map["ac_mappings"]) == 3

        ctx.approved = True
        ctx.approved_by = "tester"

        with tempfile.TemporaryDirectory() as tmpdir:
            path = compile_and_write(ctx, output_dir=tmpdir)
            assert os.path.exists(path)

            with open(path) as f:
                spec = yaml.safe_load(f)

            assert len(spec["requirements"]) == 3
            assert len(spec["traceability"]["ac_mappings"]) == 3

            # Verify traceability refs include success and failure refs
            all_refs = []
            for mapping in spec["traceability"]["ac_mappings"]:
                for v in mapping["required_verifications"]:
                    all_refs.append(v["ref"])

            assert any("success" in r for r in all_refs), "Missing success refs"
            assert any("FAIL" in r for r in all_refs), "Missing failure refs"


class TestMultiACEvaluation:
    """Tests for multi-AC evaluation producing per-AC verdicts."""

    def test_evaluate_spec_per_ac_verdicts(self):
        """Evaluator should produce one verdict per AC in the traceability map."""
        from verify.evaluator import evaluate_spec

        spec = {
            "traceability": {
                "ac_mappings": [
                    {
                        "ac_checkbox": 0,
                        "ac_text": "Create dog",
                        "pass_condition": "ALL_PASS",
                        "required_verifications": [
                            {"ref": "REQ-001.success", "verification_type": "test_result", "description": "Happy path"},
                        ],
                    },
                    {
                        "ac_checkbox": 1,
                        "ac_text": "Get dog",
                        "pass_condition": "ALL_PASS",
                        "required_verifications": [
                            {"ref": "REQ-002.success", "verification_type": "test_result", "description": "Happy path"},
                        ],
                    },
                ]
            }
        }

        test_results = {
            "test_cases": [
                {"name": "test [REQ-001.success]", "tags": ["REQ-001.success"], "status": "passed", "failure_message": ""},
                {"name": "test [REQ-002.success]", "tags": ["REQ-002.success"], "status": "failed", "failure_message": "404 not 200"},
            ]
        }

        # Write spec to temp file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(spec, f)
            spec_path = f.name

        try:
            verdicts = evaluate_spec(spec_path, test_results)
            assert len(verdicts) == 2
            assert verdicts[0]["passed"] is True   # AC 0 → REQ-001.success passed
            assert verdicts[1]["passed"] is False   # AC 1 → REQ-002.success failed
            assert verdicts[0]["ac_text"] == "Create dog"
            assert verdicts[1]["ac_text"] == "Get dog"
        finally:
            os.unlink(spec_path)


class TestNegotiationFeedbackLoop:
    """Tests for multi-turn feedback during negotiation phases."""

    def test_phase_rerun_with_feedback(self):
        """Phases should accept feedback param for revision."""
        from verify.context import VerificationContext
        from verify.llm_client import LLMClient
        from verify.negotiation.phase1 import run_phase1

        ctx = VerificationContext(
            jira_key="FB-001",
            jira_summary="Feedback test",
            raw_acceptance_criteria=[
                {"index": 0, "text": "User can view profile", "checked": False},
            ],
            constitution={"project": {"framework": "spring-boot"}, "api": {"base_path": "/api/v1"}},
        )
        llm = LLMClient()

        # First run
        result1 = run_phase1(ctx, llm)
        assert len(result1) >= 1

        # Re-run with feedback
        result2 = run_phase1(ctx, llm, feedback="The type should be security_invariant not api_behavior")
        assert len(result2) >= 1
