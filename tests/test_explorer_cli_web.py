"""RED tests for P11.4: Explore Agent CLI & Web Endpoint.

Tests the CLI entrypoint and the POST /api/explore web endpoint.
"""

import json
import subprocess
import sys
import pytest
from verify.explorer.agent import explore, ExploreResult


class TestExploreFunction:
    """Core explore function that ties detect + index + constitution."""

    def test_explore_dog_service(self):
        result = explore("dog-service")
        assert isinstance(result, ExploreResult)
        assert result.stack_profile.language == "java"
        assert result.stack_profile.framework == "spring-boot"
        assert len(result.codebase_index.endpoints) >= 4
        assert result.constitution_draft.yaml_content
        assert result.duration_seconds >= 0

    def test_explore_invalid_path(self):
        result = explore("/nonexistent/path")
        assert result.stack_profile.language == "unknown"
        assert result.stack_profile.confidence == 0.0
        assert result.duration_seconds >= 0

    def test_explore_result_to_dict(self):
        result = explore("dog-service")
        d = result.to_dict()
        assert "stack_profile" in d
        assert "codebase_index" in d
        assert "constitution_draft" in d
        assert "duration_seconds" in d
        assert "todo_count" in d
        assert d["stack_profile"]["language"] == "java"

    def test_explore_result_to_json(self):
        result = explore("dog-service")
        j = result.to_json()
        parsed = json.loads(j)
        assert parsed["stack_profile"]["framework"] == "spring-boot"


class TestExploreCLI:
    """CLI entrypoint: python -m verify.explorer <path>."""

    def test_cli_runs(self):
        result = subprocess.run(
            [sys.executable, "-m", "verify.explorer", "dog-service"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "spring-boot" in result.stdout
        assert "endpoint" in result.stdout.lower()

    def test_cli_json_mode(self):
        result = subprocess.run(
            [sys.executable, "-m", "verify.explorer", "dog-service", "--json"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["stack_profile"]["language"] == "java"

    def test_cli_invalid_path(self):
        result = subprocess.run(
            [sys.executable, "-m", "verify.explorer", "/nonexistent"],
            capture_output=True, text=True, timeout=30,
        )
        assert result.returncode == 0
        assert "unknown" in result.stdout.lower()


class TestExploreWebEndpoint:
    """POST /api/explore web endpoint."""

    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from verify.negotiation.web import app
        return TestClient(app)

    def test_explore_endpoint(self, client):
        resp = client.post("/api/explore", json={"path": "dog-service"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["stack_profile"]["language"] == "java"
        assert data["stack_profile"]["framework"] == "spring-boot"
        assert "constitution_draft" in data
        assert data["duration_seconds"] < 35

    def test_explore_invalid_path(self, client):
        resp = client.post("/api/explore", json={"path": "/nonexistent"})
        assert resp.status_code == 400

    def test_explore_missing_path(self, client):
        resp = client.post("/api/explore", json={})
        assert resp.status_code == 422 or resp.status_code == 400
