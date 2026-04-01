"""RED tests for Epic 6.1-6.2: Jira Feedback Loop.

Tests update_jira function that wires evaluator verdicts to Jira checkbox updates and evidence comments.
"""

import pytest
from unittest.mock import MagicMock, patch, call


class TestUpdateJiraExists:
    """Test that update_jira function exists and is callable."""

    def test_importable(self):
        from verify.pipeline import update_jira
        assert callable(update_jira)


class TestUpdateJiraCheckboxes:
    """Feature 6.1: Wire evaluator verdicts to Jira checkbox updates."""

    @patch("verify.jira_client.JiraClient")
    def test_ticks_passed_checkboxes(self, MockJiraClient):
        from verify.pipeline import update_jira

        mock_jira = MagicMock()
        MockJiraClient.return_value = mock_jira
        verdicts = [
            {"ac_checkbox": 0, "ac_text": "AC 0", "passed": True, "summary": "1/1", "evidence": []},
            {"ac_checkbox": 1, "ac_text": "AC 1", "passed": False, "summary": "0/1", "evidence": []},
            {"ac_checkbox": 2, "ac_text": "AC 2", "passed": True, "summary": "2/2", "evidence": []},
        ]

        update_jira("TEST-001", verdicts)

        # Should tick checkboxes for passed verdicts only
        mock_jira.tick_checkboxes.assert_called_once()
        ticked_indices = mock_jira.tick_checkboxes.call_args[0][1]
        assert 0 in ticked_indices
        assert 2 in ticked_indices
        assert 1 not in ticked_indices

    @patch("verify.jira_client.JiraClient")
    def test_skips_jira_update_when_no_verdicts_pass(self, MockJiraClient):
        from verify.pipeline import update_jira

        mock_jira = MagicMock()
        MockJiraClient.return_value = mock_jira
        verdicts = [
            {"ac_checkbox": 0, "passed": False, "ac_text": "AC", "summary": "0/1", "evidence": []},
        ]

        update_jira("TEST-001", verdicts)

        # Should not tick any checkboxes
        mock_jira.tick_checkboxes.assert_not_called()

    @patch("verify.jira_client.JiraClient")
    def test_handles_empty_verdicts(self, MockJiraClient):
        from verify.pipeline import update_jira

        update_jira("TEST-001", [])

        MockJiraClient.return_value.tick_checkboxes.assert_not_called()


class TestUpdateJiraEvidence:
    """Feature 6.2: Wire evaluator to evidence comment."""

    @patch("verify.jira_client.JiraClient")
    def test_posts_evidence_comment(self, MockJiraClient):
        from verify.pipeline import update_jira

        mock_jira = MagicMock()
        mock_jira.format_evidence_comment.return_value = "h3. Evidence..."
        MockJiraClient.return_value = mock_jira

        verdicts = [
            {"ac_checkbox": 0, "ac_text": "AC 0", "passed": True, "summary": "1/1", "evidence": [
                {"ref": "REQ-001.success", "passed": True, "details": "Test passed",
                 "description": "Happy path", "verification_type": "test_result"},
            ]},
        ]

        update_jira("TEST-001", verdicts, spec_path=".verify/specs/TEST-001.yaml")

        mock_jira.format_evidence_comment.assert_called_once_with(verdicts, ".verify/specs/TEST-001.yaml")
        mock_jira.post_comment.assert_called_once_with("TEST-001", "h3. Evidence...")

    @patch("verify.jira_client.JiraClient")
    def test_posts_evidence_even_when_some_fail(self, MockJiraClient):
        from verify.pipeline import update_jira

        mock_jira = MagicMock()
        mock_jira.format_evidence_comment.return_value = "h3. Evidence..."
        MockJiraClient.return_value = mock_jira

        verdicts = [
            {"ac_checkbox": 0, "ac_text": "AC 0", "passed": False, "summary": "0/1", "evidence": []},
        ]

        update_jira("TEST-001", verdicts, spec_path="spec.yaml")

        # Should still post evidence comment even if failures exist
        mock_jira.post_comment.assert_called_once()
