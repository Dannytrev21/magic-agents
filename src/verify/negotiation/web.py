"""Lightweight web UI for the negotiation loop."""

import os
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.harness import NegotiationHarness
from verify.negotiation.phase1 import run_phase1
from verify.negotiation.phase2 import run_phase2
from verify.negotiation.phase3 import run_phase3
from verify.negotiation.phase4 import run_phase4
from verify.negotiation.synthesis import run_synthesis
from verify.compiler import compile_and_write
from verify.generator import generate_and_write
from verify.runner import run_and_parse
from verify.evaluator import evaluate_spec

app = FastAPI(title="Negotiation UI")

STATIC_DIR = Path(__file__).parent.parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory session (single-user localhost)
_session: dict = {}

PHASE_SKILLS = [
    ("Phase 1 of 4: Interface & Actor Discovery", run_phase1),
    ("Phase 2 of 4: Happy Path Contract", run_phase2),
    ("Phase 3 of 4: Precondition Formalization", run_phase3),
    ("Phase 4 of 4: Failure Mode Enumeration", run_phase4),
]


# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index():
    return (STATIC_DIR / "index.html").read_text()


# ------------------------------------------------------------------
# Jira integration
# ------------------------------------------------------------------


@app.get("/api/jira/configured")
async def jira_configured():
    """Check if Jira env vars are set."""
    configured = bool(
        os.environ.get("JIRA_BASE_URL")
        and os.environ.get("JIRA_EMAIL")
        and os.environ.get("JIRA_API_TOKEN")
    )
    return JSONResponse({"configured": configured})


@app.get("/api/jira/stories")
async def jira_stories():
    """Fetch in-progress stories from Jira."""
    try:
        from verify.jira_client import JiraClient
        client = JiraClient()
        stories = client.get_in_progress_stories()
        return JSONResponse({"stories": stories})
    except Exception as e:
        return JSONResponse({"error": str(e), "stories": []}, status_code=200)


@app.get("/api/jira/ticket/{jira_key}")
async def jira_ticket(jira_key: str):
    """Fetch a specific ticket with its AC."""
    try:
        from verify.jira_client import JiraClient
        client = JiraClient()
        issue = client.fetch_ticket(jira_key)
        ac = client.extract_acceptance_criteria(issue)
        fields = issue.get("fields", {})
        return JSONResponse({
            "key": jira_key,
            "summary": fields.get("summary", ""),
            "status": (fields.get("status") or {}).get("name", ""),
            "acceptance_criteria": ac,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# ------------------------------------------------------------------
# Negotiation
# ------------------------------------------------------------------


@app.post("/api/start")
async def start_negotiation(request: Request):
    body = await request.json()
    ctx = VerificationContext(
        jira_key=body.get("jira_key", "DEMO-001"),
        jira_summary=body.get("jira_summary", "User Profile Endpoint"),
        raw_acceptance_criteria=body.get("acceptance_criteria", [
            {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
        ]),
        constitution=body.get("constitution", {
            "project": {"framework": "fastapi"},
            "api": {"base_path": "/api/v1"},
        }),
    )
    llm = LLMClient()
    harness = NegotiationHarness(ctx)

    _session["ctx"] = ctx
    _session["llm"] = llm
    _session["harness"] = harness
    _session["phase_idx"] = 0

    return _run_current_phase()


@app.post("/api/respond")
async def respond(request: Request):
    body = await request.json()
    user_input = body.get("input", "approve").strip()

    if "harness" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    harness: NegotiationHarness = _session["harness"]
    ctx: VerificationContext = _session["ctx"]
    phase_idx: int = _session["phase_idx"]

    harness.add_to_log(harness.current_phase, "human", user_input)

    # If not approve/skip, re-run current phase with developer feedback
    is_approval = user_input.lower() in ("approve", "skip", "")
    if not is_approval:
        return _rerun_current_phase(user_input)

    # Advance to next phase
    harness.advance_phase()
    _session["phase_idx"] = phase_idx + 1

    if _session["phase_idx"] >= len(PHASE_SKILLS):
        run_synthesis(ctx)
        return JSONResponse({
            "done": True,
            "phase_number": len(PHASE_SKILLS),
            "total_phases": len(PHASE_SKILLS),
            "summary": _build_summary(ctx),
        })

    return _run_current_phase()


# ------------------------------------------------------------------
# Spec Compilation & Test Generation
# ------------------------------------------------------------------


@app.post("/api/compile")
async def compile_spec_endpoint():
    """Compile the negotiated context into a YAML spec file."""
    if "ctx" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    ctx: VerificationContext = _session["ctx"]
    try:
        spec_path = compile_and_write(ctx, output_dir="specs")
        with open(spec_path) as f:
            spec_content = f.read()
        return JSONResponse({
            "spec_path": spec_path,
            "spec_content": spec_content,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/generate-tests")
async def generate_tests_endpoint():
    """Generate tests from the compiled spec, run them, and evaluate."""
    if "ctx" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    ctx: VerificationContext = _session["ctx"]
    if not ctx.spec_path:
        return JSONResponse({"error": "No spec compiled yet. Call /api/compile first."}, status_code=400)

    steps = []
    try:
        # Step 1: Generate tests
        test_path = generate_and_write(ctx.spec_path)
        with open(test_path) as f:
            test_content = f.read()
        steps.append({"step": "generate", "status": "ok", "path": test_path})

        # Step 2: Run tests
        results = run_and_parse(test_path, ".verify/results")
        cases = results["test_cases"]
        passed = sum(1 for c in cases if c["status"] == "passed")
        steps.append({"step": "run", "status": "ok", "passed": passed, "total": len(cases)})

        # Step 3: Evaluate against spec
        verdicts = evaluate_spec(ctx.spec_path, results)
        all_passed = all(v["passed"] for v in verdicts)
        steps.append({"step": "evaluate", "status": "ok", "all_passed": all_passed})

        return JSONResponse({
            "steps": steps,
            "test_path": test_path,
            "test_content": test_content,
            "verdicts": verdicts,
            "all_passed": all_passed,
        })
    except Exception as e:
        steps.append({"step": "error", "status": "failed", "message": str(e)})
        return JSONResponse({"steps": steps, "error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _run_current_phase():
    ctx: VerificationContext = _session["ctx"]
    llm: LLMClient = _session["llm"]
    harness: NegotiationHarness = _session["harness"]
    phase_idx: int = _session["phase_idx"]

    title, skill_fn = PHASE_SKILLS[phase_idx]
    results = skill_fn(ctx, llm)

    harness.add_to_log(
        harness.current_phase, "ai",
        f"{title}: produced {len(results)} items",
    )

    questions = _extract_questions(phase_idx)

    return JSONResponse({
        "done": False,
        "phase_title": title,
        "phase_number": phase_idx + 1,
        "total_phases": len(PHASE_SKILLS),
        "results": results,
        "questions": questions,
        "revised": False,
    })


def _rerun_current_phase(feedback: str):
    """Re-run the current phase with developer feedback for revision."""
    ctx: VerificationContext = _session["ctx"]
    llm: LLMClient = _session["llm"]
    harness: NegotiationHarness = _session["harness"]
    phase_idx: int = _session["phase_idx"]

    title, skill_fn = PHASE_SKILLS[phase_idx]
    results = skill_fn(ctx, llm, feedback=feedback)

    harness.add_to_log(
        harness.current_phase, "ai",
        f"{title} (revised): produced {len(results)} items",
    )

    questions = _extract_questions(phase_idx)

    return JSONResponse({
        "done": False,
        "phase_title": title + " (revised)",
        "phase_number": phase_idx + 1,
        "total_phases": len(PHASE_SKILLS),
        "results": results,
        "questions": questions,
        "revised": True,
    })


def _extract_questions(phase_idx: int) -> list[str]:
    llm: LLMClient = _session["llm"]
    if llm._mock:
        from verify.negotiation.phase1 import SYSTEM_PROMPT as P1
        from verify.negotiation.phase2 import SYSTEM_PROMPT as P2
        from verify.negotiation.phase3 import SYSTEM_PROMPT as P3
        from verify.negotiation.phase4 import SYSTEM_PROMPT as P4
        prompts = [P1, P2, P3, P4]
        if phase_idx < len(prompts):
            mock_resp = llm._mock_response(prompts[phase_idx])
            if isinstance(mock_resp, dict):
                return mock_resp.get("questions", [])
    return []


def _build_summary(ctx: VerificationContext) -> dict:
    """Build the full summary with traceability per AC."""
    ac_details = []
    for ac in ctx.raw_acceptance_criteria:
        idx = ac["index"]
        clf = next((c for c in ctx.classifications if c.get("ac_index") == idx), None)
        pc = next((p for p in ctx.postconditions if p.get("ac_index") == idx), None)

        # Find related failure modes via preconditions
        related_failures = ctx.failure_modes  # In MVP, all failures relate to all ACs
        mapping = next(
            (m for m in ctx.traceability_map.get("ac_mappings", []) if m.get("ac_checkbox") == idx),
            None,
        )

        ac_details.append({
            "ac": ac,
            "classification": clf,
            "postcondition": pc,
            "preconditions": ctx.preconditions,
            "failure_modes": related_failures,
            "traceability": mapping,
        })

    return {
        "jira_key": ctx.jira_key,
        "jira_summary": ctx.jira_summary,
        "ac_details": ac_details,
        "invariants": ctx.invariants,
        "ears_statements": ctx.ears_statements,
        "traceability_map": ctx.traceability_map,
        "log_entries": len(ctx.negotiation_log),
        "counts": {
            "classifications": len(ctx.classifications),
            "postconditions": len(ctx.postconditions),
            "preconditions": len(ctx.preconditions),
            "failure_modes": len(ctx.failure_modes),
            "invariants": len(ctx.invariants),
            "ears": len(ctx.ears_statements),
        },
    }
