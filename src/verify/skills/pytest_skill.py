"""Pytest Unit Test Skill — generates pytest test files from spec contracts.

Reads the contract (interface, success, failures, invariants) and produces
a complete, tagged pytest file that can be run against the target application.

This implements Epic 4.2 of the Intent-to-Verification pipeline.
"""

import textwrap

from verify.skills.framework import VerificationSkill, register_skill


class PytestSkill(VerificationSkill):
    """Generates pytest test files from spec contracts.

    Each generated test function is tagged with its spec ref for traceability:
    - [REQ-001.success] in the docstring
    - REQ_001_success in the function name
    """

    skill_id = "pytest_unit_test"
    name = "Pytest Unit Test Generator"
    description = "Generates tagged pytest verification artifacts from spec contracts."
    input_types = frozenset({"api_behavior", "security_invariant", "data_constraint"})
    output_format = ".py"
    framework = "pytest"
    version = "1.0.0"

    def generate(self, spec: dict, requirement: dict, constitution: dict) -> str:
        """Generate a complete pytest test file from a spec requirement."""
        contract = requirement.get("contract", {})
        req_id = requirement.get("id", "REQ-001")
        interface = contract.get("interface", {})
        method = interface.get("method", "GET").upper()
        path = interface.get("path", "/")

        lines = [
            '"""Auto-generated verification tests from spec.',
            f'Requirement: {req_id}',
            f'Endpoint: {method} {path}',
            '"""',
            "",
            "from fastapi.testclient import TestClient",
            "",
            "from dummy_app.main import app",
            "",
            "client = TestClient(app)",
            "",
        ]

        # ── Success test ──
        success = contract.get("success", {})
        if success:
            lines.append(self._generate_success_test(req_id, method, path, success))

        # ── Failure tests ──
        for failure in contract.get("failures", []):
            lines.append(self._generate_failure_test(req_id, method, path, failure))

        # ── Invariant tests ──
        for invariant in contract.get("invariants", []):
            forbidden_fields = success.get("schema", {}).get("forbidden_fields", [])
            lines.append(self._generate_invariant_test(
                req_id, method, path, invariant, forbidden_fields
            ))

        return "\n".join(lines)

    def output_path(self, spec: dict, requirement: dict) -> str:
        """Return the output path from the verification entry or construct one."""
        for ver in requirement.get("verification", []):
            if ver.get("skill") == self.skill_id:
                return ver.get("output", "")

        # Fallback: construct from spec meta
        jira_key = spec.get("meta", {}).get("jira_key", "UNKNOWN")
        safe_key = jira_key.replace("-", "_")
        return f".verify/generated/test_{safe_key}.py"

    # ── Private generators ──

    def _generate_success_test(self, req_id: str, method: str, path: str, success: dict) -> str:
        status = success.get("status", 200)
        schema = success.get("schema", {})
        required_fields = schema.get("required", [])

        fields_check = " and ".join([f'"{f}" in body' for f in required_fields]) or "True"

        method_call = self._method_call(method, path, auth=True)

        return textwrap.dedent(f'''\
            def test_{_safe(req_id)}_success():
                """[{req_id}.success] Happy path returns {status}."""
                response = {method_call}
                assert response.status_code == {status}, (
                    f"Expected {status}, got {{response.status_code}}"
                )
                body = response.json()
                assert {fields_check}, f"Missing required fields in {{body}}"

        ''')

    def _generate_failure_test(self, req_id: str, method: str, path: str, failure: dict) -> str:
        fid = failure.get("id", "FAIL-XXX")
        status = failure.get("status", 400)
        when = failure.get("when", "Failure condition")
        violates = failure.get("violates", "")
        body = failure.get("body", {})
        error_key = body.get("error", "unknown_error")

        # Determine auth strategy based on what precondition is violated
        if "authentication" in violates.lower() or violates == "PRE-001":
            method_call = self._method_call(method, path, auth=False)
        elif "data_existence" in violates.lower() or violates == "PRE-002":
            method_call = self._method_call(method, path, auth=True, token="not-found-user")
        else:
            method_call = self._method_call(method, path, auth=True, token="invalid-state")

        return textwrap.dedent(f'''\
            def test_{_safe(req_id)}_{_safe(fid)}():
                """[{req_id}.{fid}] {when}"""
                response = {method_call}
                assert response.status_code == {status}, (
                    f"Expected {status}, got {{response.status_code}}"
                )
                body = response.json()
                assert body.get("detail", {{}}).get("error") == "{error_key}", (
                    f"Expected error '{error_key}', got {{body}}"
                )

        ''')

    def _generate_invariant_test(
        self, req_id: str, method: str, path: str,
        invariant: dict, forbidden_fields: list[str]
    ) -> str:
        inv_id = invariant.get("id", "INV-XXX")
        rule = invariant.get("rule", "Invariant check")

        method_call = self._method_call(method, path, auth=True)

        if forbidden_fields:
            checks = " and ".join([f'"{f}" not in body' for f in forbidden_fields])
            assertion = f'assert {checks}, f"Forbidden fields found in response: {{body.keys()}}"'
        else:
            assertion = 'pass  # No forbidden fields specified'

        return textwrap.dedent(f'''\
            def test_{_safe(req_id)}_{_safe(inv_id)}():
                """[{req_id}.{inv_id}] {rule}"""
                response = {method_call}
                assert response.status_code == 200
                body = response.json()
                {assertion}

        ''')

    def _method_call(self, method: str, path: str, auth: bool = True, token: str = "valid-token") -> str:
        """Generate the HTTP client call string."""
        method_lower = method.lower()
        if auth:
            return f'client.{method_lower}("{path}", headers={{"Authorization": "Bearer {token}"}})'
        else:
            return f'client.{method_lower}("{path}")'


def _safe(name: str) -> str:
    """Convert REQ-001 or FAIL-001 to valid Python identifier."""
    return name.replace("-", "_")


# Auto-register on import
_skill = PytestSkill()
register_skill(_skill)
