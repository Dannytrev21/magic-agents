"""Launch the negotiation web UI.

Usage:
    python run_web.py                              # uses ANTHROPIC_API_KEY from .env or env
    ANTHROPIC_API_KEY=sk-... python run_web.py     # pass key inline
    LLM_MOCK=true python run_web.py                # mock mode (no API key needed)
"""

import os

from dotenv import load_dotenv

load_dotenv()  # Load .env file (JIRA_*, ANTHROPIC_API_KEY, etc.)

import uvicorn

has_key = bool(os.environ.get("ANTHROPIC_API_KEY"))
is_mock = os.environ.get("LLM_MOCK", "").lower() == "true"

if not has_key and not is_mock:
    print("  No ANTHROPIC_API_KEY found. Set it in .env or environment.")
    print("  Starting in mock mode (canned responses, no real LLM calls).\n")
    os.environ["LLM_MOCK"] = "true"
elif has_key:
    print("  Using Claude API (live LLM calls).\n")
else:
    print("  Running in mock mode.\n")

from verify.negotiation.web import app

if __name__ == "__main__":
    print("  Open http://127.0.0.1:8000 in your browser\n")
    uvicorn.run(app, host="127.0.0.1", port=8000)
