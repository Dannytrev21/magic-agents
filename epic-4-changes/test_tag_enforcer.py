"""RED tests for Feature 4.3: Tag Contract Enforcement.

Tests validate_tags() for spec ref coverage analysis.
"""

import os
import pytest

os.environ["LLM_MOCK"] = "true"


class TestValidateTags:
    """Test the validate_tags function."""

    def test_validate_tags_exists(self):
        from verify.skills.tag_enforcer import validate_tags
        assert callable(validate_tags)

    def test_returns_dict_with_required_keys(self):
        from verify.skills.tag_enforcer import validate_tags

        result = validate_tags("some content", [])
        assert isinstance(result, dict)
        assert "covered" in result
        assert "missing" in result
        assert "extra" in result

    def test_all_refs_covered(self):
        from verify.skills.tag_enforcer import validate_tags

        content = """
        def test_success_REQ_001():
            \"\"\"[REQ-001.success] Happy path\"\"\"
            pass

        def test_fail_001():
            \"\"\"[REQ-001.FAIL-001] No auth\"\"\"
            pass
        """
        result = validate_tags(content, ["REQ-001.success", "REQ-001.FAIL-001"])
        assert "REQ-001.success" in result["covered"]
        assert "REQ-001.FAIL-001" in result["covered"]
        assert len(result["missing"]) == 0

    def test_detects_missing_refs(self):
        from verify.skills.tag_enforcer import validate_tags

        content = """
        def test_success_REQ_001():
            \"\"\"[REQ-001.success] Happy path\"\"\"
            pass
        """
        result = validate_tags(content, ["REQ-001.success", "REQ-001.FAIL-001", "REQ-001.FAIL-002"])
        assert "REQ-001.success" in result["covered"]
        assert "REQ-001.FAIL-001" in result["missing"]
        assert "REQ-001.FAIL-002" in result["missing"]

    def test_counts_correct(self):
        from verify.skills.tag_enforcer import validate_tags

        content = "[REQ-001.success] [REQ-001.FAIL-001]"
        result = validate_tags(content, ["REQ-001.success", "REQ-001.FAIL-001", "REQ-001.FAIL-002"])
        assert len(result["covered"]) == 2
        assert len(result["missing"]) == 1

    def test_detects_extra_refs(self):
        from verify.skills.tag_enforcer import validate_tags

        content = "[REQ-001.success] [REQ-001.FAIL-001] [REQ-001.EXTRA-001]"
        result = validate_tags(content, ["REQ-001.success"])
        assert "REQ-001.success" in result["covered"]
        assert len(result["extra"]) >= 1

    def test_empty_content(self):
        from verify.skills.tag_enforcer import validate_tags

        result = validate_tags("", ["REQ-001.success"])
        assert len(result["covered"]) == 0
        assert "REQ-001.success" in result["missing"]

    def test_empty_expected_refs(self):
        from verify.skills.tag_enforcer import validate_tags

        result = validate_tags("[REQ-001.success]", [])
        assert len(result["missing"]) == 0
        assert len(result["covered"]) == 0


class TestTagEnforcerIntegration:
    """Test tag enforcement with actual generated test content."""

    def test_generated_tests_have_full_coverage(self):
        """Generated tests from the pytest skill should cover all spec refs."""
        from verify.skills.pytest_skill import PytestSkill
        from verify.skills.tag_enforcer import validate_tags
        import yaml

        spec = yaml.safe_load(open(".verify/specs/DEMO-001.yaml"))
        skill = PytestSkill()
        content = skill.generate(spec, spec["requirements"][0], {})

        expected_refs = []
        for req in spec["requirements"]:
            req_id = req["id"]
            for v in req.get("verification", []):
                for ref in v.get("refs", []):
                    if ref.startswith("REQ"):
                        expected_refs.append(ref)
                    else:
                        expected_refs.append(f"{req_id}.{ref}")

        result = validate_tags(content, expected_refs)
        assert len(result["missing"]) == 0, f"Missing refs: {result['missing']}"
