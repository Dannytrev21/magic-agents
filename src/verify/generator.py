"""Template-based test generator that reads a spec YAML and emits a tagged pytest file."""

import os
import textwrap

import yaml


def generate_tests(spec_path: str) -> str:
    """Read a spec YAML and generate a pytest test file as a string.

    Each generated test function is tagged with its spec ref so the evaluator
    can match test results back to AC checkboxes.
    """
    with open(spec_path) as f:
        spec = yaml.safe_load(f)

    req = spec["requirements"][0]
    contract = req["contract"]
    req_id = req["id"]
    method = contract["interface"]["method"]
    path = contract["interface"]["path"]

    lines = [
        '"""Auto-generated verification tests from spec."""',
        "",
        "from fastapi.testclient import TestClient",
        "",
        "from dummy_app.main import app",
        "",
        "client = TestClient(app)",
        "",
    ]

    # --- Success test ---
    success = contract["success"]
    required_fields = success["schema"]["required"]
    fields_check = " and ".join(
        [f'"{f}" in body' for f in required_fields]
    )
    lines.append(
        textwrap.dedent(f'''\
        def test_{_safe(req_id)}_success():
            """[{req_id}.success] Happy path returns correct profile data."""
            response = client.get("{path}", headers={{"Authorization": "Bearer valid-token"}})
            assert response.status_code == {success["status"]}, (
                f"Expected {success["status"]}, got {{response.status_code}}"
            )
            body = response.json()
            assert {fields_check}, f"Missing required fields in {{body}}"
        ''')
    )

    # --- Failure tests ---
    for failure in contract["failures"]:
        fid = failure["id"]
        status = failure["status"]
        error_key = failure["body"]["error"]

        if failure["violates"] == "PRE-001":
            # Auth failure — send request without auth header
            lines.append(
                textwrap.dedent(f'''\
                def test_{_safe(req_id)}_{_safe(fid)}():
                    """[{req_id}.{fid}] {failure["when"]}"""
                    response = client.get("{path}")
                    assert response.status_code == {status}, (
                        f"Expected {status}, got {{response.status_code}}"
                    )
                    body = response.json()
                    assert body["detail"]["error"] == "{error_key}", (
                        f"Expected error '{error_key}', got {{body}}"
                    )
                ''')
            )
        elif failure["violates"] == "PRE-002":
            # Data existence failure — send with not-found-user token
            lines.append(
                textwrap.dedent(f'''\
                def test_{_safe(req_id)}_{_safe(fid)}():
                    """[{req_id}.{fid}] {failure["when"]}"""
                    response = client.get("{path}", headers={{"Authorization": "Bearer not-found-user"}})
                    assert response.status_code == {status}, (
                        f"Expected {status}, got {{response.status_code}}"
                    )
                    body = response.json()
                    assert body["detail"]["error"] == "{error_key}", (
                        f"Expected error '{error_key}', got {{body}}"
                    )
                ''')
            )

    # --- Invariant tests ---
    for inv in contract["invariants"]:
        inv_id = inv["id"]
        forbidden = success["schema"].get("forbidden_fields", [])
        forbidden_checks = " and ".join(
            [f'"{f}" not in body' for f in forbidden]
        )
        lines.append(
            textwrap.dedent(f'''\
            def test_{_safe(req_id)}_{_safe(inv_id)}():
                """[{req_id}.{inv_id}] {inv["rule"]}"""
                response = client.get("{path}", headers={{"Authorization": "Bearer valid-token"}})
                assert response.status_code == 200
                body = response.json()
                assert {forbidden_checks}, (
                    f"Forbidden fields found in response: {{body.keys()}}"
                )
            ''')
        )

    return "\n".join(lines)


def generate_and_write(spec_path: str) -> str:
    """Generate tests and write to the output path specified in the spec."""
    with open(spec_path) as f:
        spec = yaml.safe_load(f)

    req = spec["requirements"][0]
    output_path = req["verification"][0]["output"]

    content = generate_tests(spec_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)

    return output_path


def _safe(name: str) -> str:
    """Convert a spec ref like REQ-001 or FAIL-001 to a valid Python identifier."""
    return name.replace("-", "_")
