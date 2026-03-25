"""RED tests for Epic 4.3: Tag Contract Enforcement.

Tests the validate_tags function that ensures spec ref coverage in generated tests.
"""

import pytest


class TestValidateTags:
    """Test the validate_tags function."""

    def test_importable(self):
        from verify.skills.tag_enforcer import validate_tags
        assert callable(validate_tags)

    def test_returns_dict_with_expected_keys(self):
        from verify.skills.tag_enforcer import validate_tags
        result = validate_tags("some content", ["REQ-001.success"])
        assert "covered" in result
        assert "missing" in result
        assert "extra" in result

    def test_finds_bracket_refs(self):
        from verify.skills.tag_enforcer import validate_tags
        content = '''
        def test_success():
            """[REQ-001.success] Happy path"""
            pass
        '''
        result = validate_tags(content, ["REQ-001.success"])
        assert "REQ-001.success" in result["covered"]
        assert len(result["missing"]) == 0

    def test_finds_underscore_refs_in_function_names(self):
        from verify.skills.tag_enforcer import validate_tags
        content = '''
        def test_REQ_001_FAIL_001():
            pass
        '''
        result = validate_tags(content, ["REQ-001.FAIL-001"])
        assert "REQ-001.FAIL-001" in result["covered"]

    def test_detects_missing_refs(self):
        from verify.skills.tag_enforcer import validate_tags
        content = '''
        def test_success():
            """[REQ-001.success] Happy path"""
            pass
        '''
        result = validate_tags(content, ["REQ-001.success", "REQ-001.FAIL-001", "REQ-001.FAIL-002"])
        assert "REQ-001.success" in result["covered"]
        assert "REQ-001.FAIL-001" in result["missing"]
        assert "REQ-001.FAIL-002" in result["missing"]

    def test_detects_extra_refs(self):
        from verify.skills.tag_enforcer import validate_tags
        content = '''
        def test_a():
            """[REQ-001.success] test"""
            pass
        def test_b():
            """[REQ-001.FAIL-001] test"""
            pass
        '''
        result = validate_tags(content, ["REQ-001.success"])
        assert "REQ-001.FAIL-001" in result["extra"]

    def test_full_coverage_returns_empty_missing(self):
        from verify.skills.tag_enforcer import validate_tags
        content = '[REQ-001.success] [REQ-001.FAIL-001]'
        result = validate_tags(content, ["REQ-001.success", "REQ-001.FAIL-001"])
        assert len(result["missing"]) == 0
        assert len(result["covered"]) == 2

    def test_empty_content(self):
        from verify.skills.tag_enforcer import validate_tags
        result = validate_tags("", ["REQ-001.success"])
        assert "REQ-001.success" in result["missing"]
        assert len(result["covered"]) == 0

    def test_empty_expected_refs(self):
        from verify.skills.tag_enforcer import validate_tags
        result = validate_tags("[REQ-001.success]", [])
        assert len(result["missing"]) == 0
        assert "REQ-001.success" in result["extra"]
