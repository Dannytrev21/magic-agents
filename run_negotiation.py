"""Run the interactive negotiation CLI."""

from verify.negotiation.cli import run_negotiation_cli
from verify.context import VerificationContext
from verify.llm_client import LLMClient

ctx = VerificationContext(
    jira_key="DEMO-001",
    jira_summary="User Profile Endpoint",
    raw_acceptance_criteria=[
        {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False}
    ],
    constitution={"project": {"framework": "fastapi"}, "api": {"base_path": "/api/v1"}},
)
run_negotiation_cli(ctx, LLMClient())
