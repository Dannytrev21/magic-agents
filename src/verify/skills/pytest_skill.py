"""Pytest Unit Test Skill — generates tagged pytest test files from spec contracts.

This skill handles:
- api_behavior requirements → full HTTP endpoint tests
- security_invariant requirements → security-focused tests
- data_constraint requirements → data validation tests

Each generated test function is tagged with its spec ref:
- [REQ-001.success] for happy path
- [REQ-001.FAIL-001] for failure modes
- [REQ-001.INV-001] for invariants
"""

import textwrap

from verify.skills.framework import VerificationSkill, register_skill


@register_skill
class PytestSkill(VerificationSkill):
    """Generates pytest test files from spec contracts.

    Uses template-based generation with constitutional awareness.
    Each test is tagged with its spec ref for traceability.
    """

    skill_id = "pytest_unit_test"
    description = "Generate pytest unit tests from spec contracts"

    def generate(
        self,
        spec: dict,
        requirement: dict,
        constitution: dict,
    ) -> str:
        """Generate a complete pytest test file for the given requirement."""
        req_id = requirement.get("id", "REQ-001")
        req_type = requirement.get("type", "api_behavior")
        contract = requirement.get("contract", {})

        if req_type == "api_behavior":
            return self._generate_api_tests(req_id, contract, constitution)
        elif req_type == "security_invariant":
            return self._generate_security_tests(req_id, contract, constitution)
        elif req_type == "data_constraint":
            return self._generate_data_tests(req_id, contract, constitution)
        else:
            return self._generate_api_tests(req_id, contract, constitution)

    def _generate_api_tests(
        self, req_id: str, contract: dict, constitution: dict
    ) -> str:
        """Generate API behavior tests with success, failure, and invariant cases."""
        interface = contract.get("interface", {})
        method = interface.get("method", "GET").lower()
        path = interface.get("path", "/")
        auth = interface.get("auth", "jwt_bearer")

        # Extract constitution details
        api_config = constitution.get("api", {})
        auth_config = api_config.get("auth", {})
        token_header = auth_config.get("token_header", "Authorization")
        token_prefix = auth_config.get("token_prefix", "Bearer ")
        error_format = api_config.get("error_format", {})

        lines = [
            f'"""Auto-generated pytest verification tests from spec — {req_id}.',
            '',
            f'Skill: pytest_unit_test',
            f'Requirement: {req_id}',
            f'Tags: See [REQ-xxx.yyy] markers in each test docstring.',
            '"""',
            '',
            'import pytest',
            'import requests',
            '',
            '',
            f'# ── Configuration ──',
            '',
            f'BASE_URL = "http://localhost:8080"',
            f'ENDPOINT = "{path}"',
            f'VALID_TOKEN = "{token_prefix}valid-test-token"',
            '',
            '',
            f'def _url(path: str = ENDPOINT) -> str:',
            f'    return f"{{BASE_URL}}{{path}}"',
            '',
            '',
            f'def _auth_headers(token: str = VALID_TOKEN) -> dict:',
            f'    return {{"{token_header}": token}}',
            '',
            '',
        ]

        # ── Success test ──
        success = contract.get("success", {})
        if success:
            status = success.get("status", 200)
            schema = success.get("schema", {})
            required_fields = schema.get("required", [])
            forbidden_fields = schema.get("forbidden_fields", [])

            field_asserts = "\n".join(
                '    assert "{}" in body, "Missing required field: {}"'.format(f, f)
                for f in required_fields
            )

            lines.extend([
                f'class Test{_safe_class(req_id)}Success:',
                f'    """Happy path tests for {req_id}."""',
                '',
                f'    def test_{_safe(req_id)}_success(self):',
                f'        """[{req_id}.success] Happy path returns expected response."""',
                f'        response = requests.{method}(_url(), headers=_auth_headers())',
                f'        assert response.status_code == {status}, (',
                f'            f"Expected {status}, got {{response.status_code}}: {{response.text}}"',
                f'        )',
                f'        body = response.json()',
            ])

            if field_asserts:
                lines.append(field_asserts)

            lines.extend(['', ''])

        # ── Failure tests ──
        failures = contract.get("failures", [])
        if failures:
            lines.extend([
                f'class Test{_safe_class(req_id)}Failures:',
                f'    """Failure mode tests for {req_id}."""',
                '',
            ])

            for failure in failures:
                fid = failure.get("id", "FAIL-001")
                f_status = failure.get("status", 400)
                f_when = failure.get("when", fid)
                f_violates = failure.get("violates", "")
                f_body = failure.get("body", {})

                # Determine request setup based on violation category
                if "PRE-" in f_violates:
                    pre_idx = f_violates  # e.g., PRE-001
                    category = _find_precondition_category(
                        contract.get("preconditions", []), pre_idx
                    )
                else:
                    category = "unknown"

                request_setup = _failure_request_setup(
                    method, category, token_prefix, token_header
                )

                # Error body assertion
                error_key = f_body.get("error", "")
                body_assert = ""
                if error_key:
                    body_assert = (
                        '        body = response.json()\n'
                        '        assert body.get("error") == "{err}", (\n'
                        '            "Expected error: {err}"\n'
                        '        )'.format(err=error_key)
                    )

                lines.extend([
                    f'    def test_{_safe(req_id)}_{_safe(fid)}(self):',
                    f'        """[{req_id}.{fid}] {f_when}"""',
                    request_setup,
                    f'        assert response.status_code == {f_status}, (',
                    f'            f"Expected {f_status}, got {{response.status_code}}: {{response.text}}"',
                    f'        )',
                ])

                if body_assert:
                    lines.append(body_assert)

                lines.extend(['', ''])

        # ── Invariant tests ──
        invariants = contract.get("invariants", [])
        if invariants:
            lines.extend([
                f'class Test{_safe_class(req_id)}Invariants:',
                f'    """Invariant verification tests for {req_id}."""',
                '',
            ])

            for inv in invariants:
                inv_id = inv.get("id", "INV-001")
                rule = inv.get("rule", inv_id)
                inv_type = inv.get("type", "security")

                if inv_type == "security":
                    # Check forbidden fields
                    forbidden = success.get("schema", {}).get("forbidden_fields", [])
                    if forbidden:
                        forbidden_checks = "\n".join(
                            '        assert "{}" not in body, "Forbidden field found: {}"'.format(f, f)
                            for f in forbidden
                        )
                    else:
                        forbidden_checks = f'        # Verify: {rule}'

                    lines.extend([
                        f'    def test_{_safe(req_id)}_{_safe(inv_id)}(self):',
                        f'        """[{req_id}.{inv_id}] {rule}"""',
                        f'        response = requests.{method}(_url(), headers=_auth_headers())',
                        f'        assert response.status_code == 200',
                        f'        body = response.json()',
                        forbidden_checks,
                        '',
                        '',
                    ])
                else:
                    lines.extend([
                        f'    def test_{_safe(req_id)}_{_safe(inv_id)}(self):',
                        f'        """[{req_id}.{inv_id}] {rule}"""',
                        f'        response = requests.{method}(_url(), headers=_auth_headers())',
                        f'        assert response.status_code == 200',
                        f'        # Invariant check: {rule}',
                        '',
                        '',
                    ])

        return "\n".join(lines)

    def _generate_security_tests(
        self, req_id: str, contract: dict, constitution: dict
    ) -> str:
        """Generate security invariant tests."""
        invariants = contract.get("invariants", [])
        api_config = constitution.get("api", {})
        base_path = api_config.get("base_path", "/api/v1")

        lines = [
            f'"""Security invariant tests — {req_id}."""',
            '',
            'import pytest',
            'import requests',
            '',
            f'BASE_URL = "http://localhost:8080"',
            '',
        ]

        for inv in invariants:
            inv_id = inv.get("id", "INV-001")
            rule = inv.get("rule", "")

            lines.extend([
                f'def test_{_safe(req_id)}_{_safe(inv_id)}():',
                f'    """[{req_id}.{inv_id}] {rule}"""',
                f'    # Security invariant: {rule}',
                f'    response = requests.get(f"{{BASE_URL}}{base_path}", headers={{"Authorization": "Bearer test-token"}})',
                f'    assert response.status_code in [200, 401, 403]',
                f'    if response.status_code == 200:',
                f'        body = response.json()',
                f'        # Verify invariant holds in response',
                '',
                '',
            ])

        return "\n".join(lines)

    def _generate_data_tests(
        self, req_id: str, contract: dict, constitution: dict
    ) -> str:
        """Generate data constraint tests."""
        invariants = contract.get("invariants", [])
        preconditions = contract.get("preconditions", [])

        lines = [
            f'"""Data constraint tests — {req_id}."""',
            '',
            'import pytest',
            'import requests',
            '',
            f'BASE_URL = "http://localhost:8080"',
            '',
        ]

        for inv in invariants:
            inv_id = inv.get("id", "INV-001")
            rule = inv.get("rule", "")

            lines.extend([
                f'def test_{_safe(req_id)}_{_safe(inv_id)}():',
                f'    """[{req_id}.{inv_id}] {rule}"""',
                f'    # Data constraint: {rule}',
                f'    pass  # TODO: implement data constraint verification',
                '',
                '',
            ])

        return "\n".join(lines)


# ── Helpers ──


def _safe(name: str) -> str:
    """Convert REQ-001 or FAIL-001 to valid Python identifier."""
    return name.replace("-", "_")


def _safe_class(name: str) -> str:
    """Convert REQ-001 to a class name like Req001."""
    return name.replace("-", "").title().replace("_", "")


def _find_precondition_category(preconditions: list[dict], pre_id: str) -> str:
    """Find the category of a precondition by ID."""
    for pre in preconditions:
        if pre.get("id") == pre_id:
            return pre.get("category", "unknown")
    return "unknown"


def _failure_request_setup(
    method: str, category: str, token_prefix: str, token_header: str
) -> str:
    """Generate the request setup for a failure test based on violation category."""
    if category == "authentication":
        return f'        response = requests.{method}(_url())  # No auth header'
    elif category == "authorization":
        return (
            f'        response = requests.{method}(\n'
            f'            _url(),\n'
            f'            headers={{"{token_header}": "{token_prefix}unauthorized-user-token"}},\n'
            f'        )'
        )
    elif category == "data_existence":
        return (
            f'        response = requests.{method}(\n'
            f'            _url(),\n'
            f'            headers=_auth_headers(),\n'
            f'        )  # Target resource does not exist'
        )
    elif category == "data_state":
        return (
            f'        response = requests.{method}(\n'
            f'            _url(),\n'
            f'            headers=_auth_headers(),\n'
            f'        )  # Target resource in invalid state'
        )
    elif category == "rate_limit":
        return (
            f'        # Send enough requests to trigger rate limit\n'
            f'        for _ in range(100):\n'
            f'            requests.{method}(_url(), headers=_auth_headers())\n'
            f'        response = requests.{method}(_url(), headers=_auth_headers())'
        )
    else:
        return f'        response = requests.{method}(_url(), headers=_auth_headers())'
