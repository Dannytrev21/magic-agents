"""Tests for the Codebase Pre-Scanner (Feature 8)."""

import os
import pytest
from verify.scanner import scan_java_project, CodebaseIndex


class TestCodebaseScanner:
    """Test the Java/Spring Boot codebase scanner."""

    def test_scan_dog_service(self):
        """Scan the dog-service project and verify endpoint discovery."""
        index = scan_java_project("dog-service")

        assert isinstance(index, CodebaseIndex)
        assert index.framework == "spring-boot"
        assert index.language == "java"

    def test_scan_finds_endpoints(self):
        """Scanner should discover all REST endpoints."""
        index = scan_java_project("dog-service")

        # Should find DogController endpoints
        assert len(index.endpoints) >= 4, f"Expected at least 4 endpoints, found {len(index.endpoints)}"

        # Check for specific endpoints
        endpoint_sigs = [(e.method, e.path) for e in index.endpoints]
        assert ("GET", "/api/v1/dogs") in endpoint_sigs, "Missing GET /api/v1/dogs"
        assert ("POST", "/api/v1/dogs") in endpoint_sigs, "Missing POST /api/v1/dogs"

    def test_scan_finds_security_config(self):
        """Scanner should detect security configuration."""
        index = scan_java_project("dog-service")

        assert index.security.has_security_config
        assert index.security.auth_mechanism == "jwt_bearer"

    def test_scan_produces_summary(self):
        """Scanner should produce a human-readable summary."""
        index = scan_java_project("dog-service")
        summary = index.summary()

        assert "spring-boot" in summary
        assert "Endpoints found:" in summary
        assert "DogController" in summary

    def test_scan_produces_dict(self):
        """Scanner should produce a serializable dict."""
        index = scan_java_project("dog-service")
        result = index.to_dict()

        assert "endpoints" in result
        assert "entities" in result
        assert "security" in result
        assert result["framework"] == "spring-boot"

    def test_scan_nonexistent_project(self):
        """Scanning a non-existent directory should return empty index."""
        index = scan_java_project("nonexistent-project")

        assert isinstance(index, CodebaseIndex)
        assert len(index.endpoints) == 0
        assert len(index.entities) == 0


class TestMultiACMockResponses:
    """Test that LLM mock responses handle multi-AC scenarios."""

    def test_dynamic_classify_multi_ac(self):
        """Dynamic classifier should produce one classification per AC."""
        from verify.llm_client import _dynamic_classify

        user_msg = """Jira: DEV-17 — Dog CRUD API

Acceptance Criteria:
[0] User can view their dog via GET /api/v1/dogs/{id}
[1] The endpoint returns 401 when no auth header is present
[2] Dog profile never exposes internal DB fields"""

        result = _dynamic_classify("classify acceptance criteria", user_msg)

        assert "classifications" in result
        classifications = result["classifications"]
        assert len(classifications) == 3

        # AC[0] should be api_behavior
        assert classifications[0]["ac_index"] == 0
        assert classifications[0]["type"] == "api_behavior"
        assert classifications[0]["interface"]["method"] == "GET"

        # AC[1] should be security_invariant (has "401" and "auth")
        assert classifications[1]["ac_index"] == 1
        assert classifications[1]["type"] == "security_invariant"

        # AC[2] should be security_invariant (has "expose" and "never")
        assert classifications[2]["ac_index"] == 2
        assert classifications[2]["type"] == "security_invariant"
