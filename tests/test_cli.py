"""Tests for the CLI interface (Feature 23)."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from verify.cli import (
    cmd_check,
    cmd_compile,
    cmd_execute,
    cmd_negotiate,
    cmd_status,
    main,
)
from verify.context import VerificationContext
from verify.jira_client import JiraNotFoundError


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_args_negotiate():
    """Mock arguments for negotiate command."""
    args = MagicMock()
    args.jira_key = "DEMO-001"
    args.auto = True
    args.compile = False
    return args


@pytest.fixture
def mock_args_compile():
    """Mock arguments for compile command."""
    args = MagicMock()
    args.jira_key = "DEMO-001"
    args.output_dir = None
    return args


@pytest.fixture
def mock_args_check():
    """Mock arguments for check command."""
    args = MagicMock()
    args.jira_key = "DEMO-001"
    args.spec_dir = None
    return args


@pytest.fixture
def mock_args_execute():
    """Mock arguments for execute command."""
    args = MagicMock()
    args.spec_path = ".verify/specs/DEMO-001.yaml"
    args.jira_key = None
    args.no_jira = True
    return args


@pytest.fixture
def mock_args_status():
    """Mock arguments for status command."""
    return MagicMock()


@pytest.fixture
def temp_spec_dir(tmp_path):
    """Create a temporary spec directory."""
    spec_dir = tmp_path / ".verify" / "specs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    return spec_dir


@pytest.fixture
def sample_jira_issue():
    """Sample Jira issue data."""
    return {
        "key": "DEMO-001",
        "fields": {
            "summary": "User should be able to create a dog via POST /api/v1/dogs",
            "description": {
                "version": 1,
                "type": "doc",
                "content": [
                    {
                        "type": "paragraph",
                        "content": [
                            {
                                "type": "text",
                                "text": "Acceptance criteria:",
                            }
                        ],
                    },
                    {
                        "type": "taskList",
                        "content": [
                            {
                                "type": "taskItem",
                                "attrs": {"checked": False},
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": "POST /api/v1/dogs accepts {name, breed, age}",
                                            }
                                        ],
                                    }
                                ],
                            },
                            {
                                "type": "taskItem",
                                "attrs": {"checked": False},
                                "content": [
                                    {
                                        "type": "paragraph",
                                        "content": [
                                            {
                                                "type": "text",
                                                "text": "Response includes id (auto-generated)",
                                            }
                                        ],
                                    }
                                ],
                            },
                        ],
                    },
                ],
            },
        },
    }


@pytest.fixture(autouse=True)
def setup_mock_mode():
    """Ensure LLM_MOCK mode is enabled for tests."""
    os.environ["LLM_MOCK"] = "true"
    yield
    # Cleanup
    if "LLM_MOCK" in os.environ:
        del os.environ["LLM_MOCK"]


# ──────────────────────────────────────────────────────────────────────────────
# Test: cmd_negotiate
# ──────────────────────────────────────────────────────────────────────────────


@patch("verify.cli.JiraClient")
@patch("verify.cli.LLMClient")
@patch("verify.cli.run_negotiation_auto")
def test_cmd_negotiate_auto(
    mock_negotiate_fn,
    mock_llm_client,
    mock_jira_client,
    mock_args_negotiate,
    sample_jira_issue,
):
    """Test negotiate command in auto mode."""
    # Setup mocks
    mock_jira = MagicMock()
    mock_jira.fetch_ticket.return_value = sample_jira_issue
    mock_jira.extract_acceptance_criteria.return_value = [
        {"index": 0, "text": "POST /api/v1/dogs accepts {name, breed, age}"},
        {"index": 1, "text": "Response includes id (auto-generated)"},
    ]
    mock_jira_client.return_value = mock_jira

    # Run command
    cmd_negotiate(mock_args_negotiate)

    # Verify calls
    mock_jira.fetch_ticket.assert_called_once_with("DEMO-001")
    mock_negotiate_fn.assert_called_once()


@patch("verify.cli.JiraClient")
def test_cmd_negotiate_jira_not_found(
    mock_jira_client,
    mock_args_negotiate,
):
    """Test negotiate command when ticket not found."""
    # Setup mocks to raise error
    mock_jira = MagicMock()
    mock_jira.fetch_ticket.side_effect = JiraNotFoundError("Ticket not found")
    mock_jira_client.return_value = mock_jira

    # Run command and expect exit
    with pytest.raises(SystemExit) as exc_info:
        cmd_negotiate(mock_args_negotiate)

    assert exc_info.value.code == 1


@patch("verify.cli.JiraClient")
def test_cmd_negotiate_no_acceptance_criteria(
    mock_jira_client,
    mock_args_negotiate,
    sample_jira_issue,
):
    """Test negotiate command when no acceptance criteria found."""
    # Setup mocks
    mock_jira = MagicMock()
    mock_jira.fetch_ticket.return_value = sample_jira_issue
    mock_jira.extract_acceptance_criteria.return_value = []  # No ACs
    mock_jira_client.return_value = mock_jira

    # Run command and expect exit
    with pytest.raises(SystemExit) as exc_info:
        cmd_negotiate(mock_args_negotiate)

    assert exc_info.value.code == 1


# ──────────────────────────────────────────────────────────────────────────────
# Test: cmd_compile
# ──────────────────────────────────────────────────────────────────────────────


@patch("verify.cli.JiraClient")
@patch("verify.cli.LLMClient")
@patch("verify.cli.run_negotiation_auto")
@patch("verify.cli.compile_and_write")
def test_cmd_compile(
    mock_compile,
    mock_negotiate_fn,
    mock_llm_client,
    mock_jira_client,
    mock_args_compile,
    sample_jira_issue,
):
    """Test compile command."""
    # Setup mocks
    mock_jira = MagicMock()
    mock_jira.fetch_ticket.return_value = sample_jira_issue
    mock_jira.extract_acceptance_criteria.return_value = [
        {"index": 0, "text": "POST /api/v1/dogs accepts {name, breed, age}"},
    ]
    mock_jira_client.return_value = mock_jira
    mock_compile.return_value = ".verify/specs/DEMO-001.yaml"

    # Run command
    cmd_compile(mock_args_compile)

    # Verify calls
    mock_jira.fetch_ticket.assert_called_once_with("DEMO-001")
    mock_compile.assert_called_once()


@patch("verify.cli.JiraClient")
def test_cmd_compile_jira_auth_error(
    mock_jira_client,
    mock_args_compile,
):
    """Test compile command with Jira auth error."""
    from verify.jira_client import JiraAuthError

    # Setup mocks to raise error
    mock_jira = MagicMock()
    mock_jira.fetch_ticket.side_effect = JiraAuthError("Auth failed")
    mock_jira_client.return_value = mock_jira

    # Run command and expect exit
    with pytest.raises(SystemExit) as exc_info:
        cmd_compile(mock_args_compile)

    assert exc_info.value.code == 1


# ──────────────────────────────────────────────────────────────────────────────
# Test: cmd_execute
# ──────────────────────────────────────────────────────────────────────────────


@patch("verify.cli.run_pipeline")
def test_cmd_execute_without_jira(
    mock_pipeline,
    mock_args_execute,
    tmp_path,
):
    """Test execute command without Jira updates."""
    # Create a dummy spec file
    spec_file = tmp_path / "DEMO-001.yaml"
    spec_file.write_text("meta: {}\nrequirements: []")
    mock_args_execute.spec_path = str(spec_file)

    # Mock pipeline to return all passing verdicts
    mock_pipeline.return_value = [
        {"passed": True, "ac_checkbox": 0},
        {"passed": True, "ac_checkbox": 1},
    ]

    # Run command (expects exit with 0)
    with pytest.raises(SystemExit) as exc_info:
        cmd_execute(mock_args_execute)

    assert exc_info.value.code == 0
    # Verify calls
    mock_pipeline.assert_called_once_with(str(spec_file))


@patch("verify.cli.run_pipeline_with_jira")
def test_cmd_execute_with_jira(
    mock_pipeline_jira,
    tmp_path,
):
    """Test execute command with Jira updates."""
    # Create arguments
    spec_file = tmp_path / "DEMO-001.yaml"
    spec_file.write_text("meta: {}\nrequirements: []")

    args = MagicMock()
    args.spec_path = str(spec_file)
    args.jira_key = "DEMO-001"
    args.no_jira = False

    # Mock pipeline to return all passing verdicts
    mock_pipeline_jira.return_value = [
        {"passed": True, "ac_checkbox": 0},
        {"passed": True, "ac_checkbox": 1},
    ]

    # Run command (expects exit with 0)
    with pytest.raises(SystemExit) as exc_info:
        cmd_execute(args)

    assert exc_info.value.code == 0
    # Verify calls
    mock_pipeline_jira.assert_called_once()


def test_cmd_execute_spec_not_found(mock_args_execute):
    """Test execute command when spec not found."""
    mock_args_execute.spec_path = "/nonexistent/spec.yaml"

    with pytest.raises(SystemExit) as exc_info:
        cmd_execute(mock_args_execute)

    assert exc_info.value.code == 1


# ──────────────────────────────────────────────────────────────────────────────
# Test: cmd_check
# ──────────────────────────────────────────────────────────────────────────────


def test_cmd_check_spec_exists(mock_args_check, temp_spec_dir):
    """Test check command when spec exists."""
    # Create a dummy spec file
    spec_file = temp_spec_dir / "DEMO-001.yaml"
    spec_file.write_text("""
meta:
  spec_version: "1.0"
  jira_key: DEMO-001
  jira_summary: "Test ticket"
  status: approved
requirements: []
""")

    mock_args_check.spec_dir = str(temp_spec_dir)

    # Run command (should not raise)
    cmd_check(mock_args_check)


def test_cmd_check_spec_not_found(mock_args_check, temp_spec_dir):
    """Test check command when spec does not exist."""
    mock_args_check.spec_dir = str(temp_spec_dir)

    # Run command and expect exit
    with pytest.raises(SystemExit) as exc_info:
        cmd_check(mock_args_check)

    assert exc_info.value.code == 1


# ──────────────────────────────────────────────────────────────────────────────
# Test: cmd_status
# ──────────────────────────────────────────────────────────────────────────────


def test_cmd_status(mock_args_status):
    """Test status command."""
    # Should not raise and should print info
    cmd_status(mock_args_status)
    # Just verify it runs without error


@patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"})
def test_cmd_status_with_api_key(mock_args_status):
    """Test status command with API key configured."""
    cmd_status(mock_args_status)
    # Verify it runs without error


# ──────────────────────────────────────────────────────────────────────────────
# Test: main entry point
# ──────────────────────────────────────────────────────────────────────────────


def test_main_no_args(capsys):
    """Test main with no arguments (should print help)."""
    with patch.object(sys, "argv", ["specify"]):
        # Should print help and exit with 0
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "usage:" in captured.out or "usage:" in captured.err
    assert "specify" in captured.out or "specify" in captured.err


@patch("verify.cli.cmd_status")
def test_main_status_command(mock_status_fn):
    """Test main with status command."""
    with patch.object(sys, "argv", ["specify", "status"]):
        # main() should call cmd_status and return normally (no exit)
        main()
        # Verify cmd_status was called
        mock_status_fn.assert_called_once()


@patch("verify.cli.JiraClient")
@patch("verify.cli.LLMClient")
@patch("verify.cli.run_negotiation_auto")
def test_main_negotiate_command(
    mock_negotiate_fn,
    mock_llm_client,
    mock_jira_client,
    sample_jira_issue,
):
    """Test main with negotiate command."""
    # Setup mocks
    mock_jira = MagicMock()
    mock_jira.fetch_ticket.return_value = sample_jira_issue
    mock_jira.extract_acceptance_criteria.return_value = [
        {"index": 0, "text": "Test AC"},
    ]
    mock_jira_client.return_value = mock_jira

    with patch.object(sys, "argv", ["specify", "negotiate", "DEMO-001", "--auto"]):
        try:
            main()
        except SystemExit:
            pass  # Expected to exit


# ──────────────────────────────────────────────────────────────────────────────
# Integration tests
# ──────────────────────────────────────────────────────────────────────────────


@patch("verify.cli.JiraClient")
@patch("verify.cli.LLMClient")
@patch("verify.cli.run_negotiation_auto")
@patch("verify.cli.compile_and_write")
def test_negotiate_to_compile_flow(
    mock_compile,
    mock_negotiate_fn,
    mock_llm_client,
    mock_jira_client,
    sample_jira_issue,
):
    """Test full negotiate + compile flow."""
    # Setup mocks
    mock_jira = MagicMock()
    mock_jira.fetch_ticket.return_value = sample_jira_issue
    mock_jira.extract_acceptance_criteria.return_value = [
        {"index": 0, "text": "AC 1"},
        {"index": 1, "text": "AC 2"},
    ]
    mock_jira_client.return_value = mock_jira
    mock_compile.return_value = ".verify/specs/DEMO-001.yaml"

    # Test negotiate with compile flag
    args = MagicMock()
    args.jira_key = "DEMO-001"
    args.auto = True
    args.compile = True
    args.func = cmd_negotiate

    cmd_negotiate(args)

    # Verify both functions called
    mock_negotiate_fn.assert_called_once()
    mock_compile.assert_called_once()


# ──────────────────────────────────────────────────────────────────────────────
# Edge case tests
# ──────────────────────────────────────────────────────────────────────────────


def test_cmd_check_invalid_yaml(mock_args_check, temp_spec_dir):
    """Test check command with invalid YAML in spec file."""
    # Create a spec file with invalid YAML
    spec_file = temp_spec_dir / "DEMO-001.yaml"
    spec_file.write_text("invalid: yaml: content: {")

    mock_args_check.spec_dir = str(temp_spec_dir)

    # Run command and expect it to handle gracefully (exit with error)
    with pytest.raises(SystemExit) as exc_info:
        cmd_check(mock_args_check)

    assert exc_info.value.code == 1


@patch("verify.cli.run_pipeline")
def test_cmd_execute_failed_verdicts(mock_pipeline, tmp_path):
    """Test execute command when verdicts show failures."""
    # Create a dummy spec file
    spec_file = tmp_path / "DEMO-001.yaml"
    spec_file.write_text("meta: {}\nrequirements: []")

    args = MagicMock()
    args.spec_path = str(spec_file)
    args.jira_key = None
    args.no_jira = True

    # Mock pipeline to return some failing verdicts
    mock_pipeline.return_value = [
        {"passed": True, "ac_checkbox": 0},
        {"passed": False, "ac_checkbox": 1},  # FAIL
    ]

    # Run command and expect exit with failure code
    with pytest.raises(SystemExit) as exc_info:
        cmd_execute(args)

    assert exc_info.value.code == 1


# ──────────────────────────────────────────────────────────────────────────────
# Help text tests
# ──────────────────────────────────────────────────────────────────────────────


def test_cli_help_negotiate(capsys):
    """Test help for negotiate subcommand."""
    with patch.object(sys, "argv", ["specify", "negotiate", "-h"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "negotiate" in captured.out
    assert "jira_key" in captured.out


def test_cli_help_execute(capsys):
    """Test help for execute subcommand."""
    with patch.object(sys, "argv", ["specify", "execute", "-h"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "execute" in captured.out


def test_cli_help_check(capsys):
    """Test help for check subcommand."""
    with patch.object(sys, "argv", ["specify", "check", "-h"]):
        with pytest.raises(SystemExit) as exc_info:
            main()
        assert exc_info.value.code == 0

    captured = capsys.readouterr()
    assert "check" in captured.out
