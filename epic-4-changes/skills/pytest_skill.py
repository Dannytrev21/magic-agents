"""Pytest Unit Test Skill — generates tagged pytest tests from spec contracts.

Implements Feature 4.2: Reads spec contract (success, failures, invariants)
and generates a complete pytest test file with tagged methods.

Each test function includes the spec ref in its docstring: [REQ-001.success],
[REQ-001.FAIL-001], etc. for traceability back to the spec.
"""

import textwrap

from verify.skills.framework import VerificationSkill, register_skill


class PytestSkill(VerificationSkill):
    """Generates pytest tests from spec contracts for api_behavior requirements."""

    skill_id = "pytest_unit_test"

    def generate(self, spec: dict, requirement: dict, constitution: dict) -> str:
        """Generate a complete pytest test file from the requirement's contract.

        Args:
            spec: Full spec dict.
            requirement: The requirement dict with contract, id, type, etc.
            constitution: Repository constitution (unused for now, template-based).

        Returns:
            Complete Python test file content as a string.
        """
        contract = requirement.get("contract", {})
        req_id = requirement.get("id", "REQ-001")
        req_type = requirement.get("type", "api_behavior")

        lines = [
            '"""Auto-generated verification tests from spec via PytestSkill."""',
            "",
            "from fastapi.testclient import TestClient",
            "",
            "from dummy_app.main import app",
            "",
            "client = TestClient(app)",
            "",
        ]

        if req_type == "api_behavior" and "interface" in contract:
            lines.extend(self._generate_api_tests(contract, req_id))
        else:
            # Fallback: generate invariant-only tests
            lines.extend(self._generate_invariant_only_tests(contract, req_id))

        return "\n".join(lines)

    def output_path(self, spec: dict, requirement: dict) -> str:
        """Return the output path from the requirement's verification block."""
        for v in requirement.get("verification", []):
            if v.get("output"):
                return v["output"]

        # Fallback: derive from spec key
        jira_key = spec.get("meta", {}).get("jira_key", "unknown")
        safe_key = jira_key.lower().replace("-", "_")
        return f".verify/generated/test_{safe_key}.py"

    # ------------------------------------------------------------------
    # Private generators
    # ------------------------------------------------------------------

    def _generate_api_tests(self, contract: dict, req_id: str) -> list[str]:
        """Generate tests for an api_behavior requirement."""
        lines = []
        interface = contract["interface"]
        method = interface.get("method", "GET").upper()
        path = interface.get("path", "/")
        auth = interface.get("auth", "")

        # --- Success test ---
        success = contract.get("success", {})
        if success:
            lines.extend(self._generate_success_test(
                method, path, auth, success, req_id
            ))

        # --- Failure tests ---
        for failure in contract.get("failures", []):
            lines.extend(self._generate_failure_test(
                method, path, failure, req_id, contract
            ))

        # --- Invariant tests ---
        for invariant in contract.get("invariants", []):
            lines.extend(self._generate_invariant_test(
                method, path, auth, invariant, req_id, success
            ))

        return lines

    def _generate_success_test(
        self, method: str, path: str, auth: str,
        success: dict, req_id: str,
    ) -> list[str]:
        """Generate the happy-path success test."""
        status = success.get("status", 200)
        schema = success.get("schema", {})
        required_fields = schema.get("required", [])

        fields_check = " and ".join(
            [f'"{f}" in body' for f in required_fields]
        ) if required_fields else "True"

        safe_id = _safe(req_id)
        headers = self._auth_headers(auth)

        return [
            textwrap.dedent(f'''\
            def test_{safe_id}_success():
                """[{req_id}.success] Happy path returns correct response."""
                response = client.{method.lower()}("{path}", headers={headers})
                assert response.status_code == {status}, (
                    f"Expected {status}, got {{response.status_code}}"
                )
                body = response.json()
                assert {fields_check}, f"Missing required fields in {{body}}"
            '''),
        ]

    def _generate_failure_test(
        self, method: str, path: str,
        failure: dict, req_id: str, contract: dict,
    ) -> list[str]:
        """Generate a failure mode test."""
        fid = failure["id"]
        status = failure["status"]
        violates = failure.get("violates", "")
        body = failure.get("body", {})
        error_key = body.get("error", "")

        safe_id = _safe(req_id)
        safe_fid = _safe(fid)

        # Determine request shape based on which precondition is violated
        headers, description = self._failure_request(violates, method, contract)

        error_lines = ""
        if error_key:
            error_lines = (
                f"\n    body = response.json()"
                f"\n    detail = body.get(\"detail\", body)"
                f"\n    if isinstance(detail, dict):"
                f"\n        assert detail.get(\"error\") == \"{error_key}\", ("
                f"\n            f\"Expected error '{error_key}', got {{detail}}\""
                f"\n        )"
            )

        when = failure.get("when", description)
        test_code = (
            f"def test_{safe_id}_{safe_fid}():\n"
            f"    \"\"\"[{req_id}.{fid}] {when}\"\"\"\n"
            f"    response = client.{method.lower()}(\"{path}\"{headers})\n"
            f"    assert response.status_code == {status}, (\n"
            f"        f\"Expected {status}, got {{response.status_code}}\"\n"
            f"    ){error_lines}\n"
        )

        return [test_code]

    def _generate_invariant_test(
        self, method: str, path: str, auth: str,
        invariant: dict, req_id: str, success: dict,
    ) -> list[str]:
        """Generate an invariant test."""
        inv_id = invariant["id"]
        rule = invariant.get("rule", "")
        safe_id = _safe(req_id)
        safe_inv = _safe(inv_id)
        headers = self._auth_headers(auth)

        # Build assertion from invariant type
        schema = success.get("schema", {})
        forbidden = schema.get("forbidden_fields", [])

        if forbidden:
            forbidden_checks = " and ".join(
                [f'"{f}" not in body' for f in forbidden]
            )
            assertion = f'assert {forbidden_checks}, f"Forbidden fields found in response: {{body.keys()}}"'
        else:
            assertion = f'# Invariant: {rule}\n    pass'

        return [
            textwrap.dedent(f'''\
            def test_{safe_id}_{safe_inv}():
                """[{req_id}.{inv_id}] {rule}"""
                response = client.{method.lower()}("{path}", headers={headers})
                assert response.status_code == 200
                body = response.json()
                {assertion}
            '''),
        ]

    def _generate_invariant_only_tests(self, contract: dict, req_id: str) -> list[str]:
        """Generate tests for non-API requirements (invariants only)."""
        lines = []
        for invariant in contract.get("invariants", []):
            inv_id = invariant["id"]
            rule = invariant.get("rule", "")
            safe_id = _safe(req_id)
            safe_inv = _safe(inv_id)
            lines.append(
                textwrap.dedent(f'''\
                def test_{safe_id}_{safe_inv}():
                    """[{req_id}.{inv_id}] {rule}"""
                    # TODO: Implement invariant check
                    pass
                ''')
            )
        return lines

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _auth_headers(auth: str) -> str:
        """Return a headers dict string for the given auth mechanism."""
        if auth in ("jwt_bearer", "bearer"):
            return '{"Authorization": "Bearer valid-token"}'
        return "{}"

    @staticmethod
    def _failure_request(
        violates: str, method: str, contract: dict,
    ) -> tuple[str, str]:
        """Determine the request headers/params for a failure test.

        Returns (headers_arg, description) tuple.
        """
        # Find the violated precondition's category
        category = ""
        for pre in contract.get("preconditions", []):
            if pre["id"] == violates:
                category = pre.get("category", "")
                break

        if category == "authentication" or violates == "PRE-001":
            # No auth header
            return "", "Missing authentication"
        elif category == "data_existence" or violates == "PRE-002":
            # Auth with a not-found user token
            return ', headers={"Authorization": "Bearer not-found-user"}', "Resource not found"
        elif category == "data_state":
            return ', headers={"Authorization": "Bearer inactive-user"}', "Invalid resource state"
        else:
            # Default: send with auth
            return ', headers={"Authorization": "Bearer valid-token"}', "Precondition violated"


def _safe(name: str) -> str:
    """Convert a spec ref like REQ-001 or FAIL-001 to a valid Python identifier."""
    return name.replace("-", "_")


# Auto-register on import
_instance = PytestSkill()
register_skill(_instance)
