"""Lightweight web UI for the negotiation loop."""

import os
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import yaml

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.checkpoint import get_session_info
from verify.negotiation.phase1 import run_phase1
from verify.negotiation.phase2 import run_phase2
from verify.negotiation.phase3 import run_phase3
from verify.negotiation.phase4 import run_phase4
from verify.negotiation.phase5 import run_phase5
from verify.negotiation.phase6 import run_phase6
from verify.negotiation.phase7 import run_phase7
from verify.negotiation.synthesis import run_synthesis
from verify.runtime import RuntimeEvent, SessionState, SessionStore

app = FastAPI(title="Negotiation UI")

STATIC_DIR = Path(__file__).parent.parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

SESSION_STORE = SessionStore()

# Legacy alias kept for tests that clear the in-memory session dictionary directly.
_session = SESSION_STORE.sessions

SCAN_STATE: dict[str, Any] = {
    "project_root": "",
    "scanned": False,
    "summary": "",
}

PHASE_SKILLS = [
    ("Interface & Actor Discovery", run_phase1),
    ("Happy Path Contract", run_phase2),
    ("Precondition Formalization", run_phase3),
    ("Failure Mode Enumeration", run_phase4),
    ("Invariant Extraction", run_phase5),
    ("Routing & Completeness Sweep", run_phase6),
    ("EARS Formalization", run_phase7),
]


# ------------------------------------------------------------------
# Explore endpoint
# ------------------------------------------------------------------


@app.post("/api/explore")
async def explore_endpoint(request: Request):
    """Run codebase exploration on a given path."""
    from verify.explorer.agent import explore

    body = await request.json()
    path = body.get("path")
    if not path:
        return JSONResponse({"error": "path is required"}, status_code=400)

    from pathlib import Path as _Path
    if not _Path(path).exists():
        return JSONResponse({"error": f"path not found: {path}"}, status_code=400)

    result = explore(path)
    return JSONResponse(result.to_dict())


# ------------------------------------------------------------------
# Pages
# ------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
async def index():
    return _resolve_frontend_index().read_text()


def _resolve_frontend_index() -> Path:
    built_index = STATIC_DIR / "ui" / "index.html"
    if built_index.exists():
        return built_index
    return STATIC_DIR / "index.html"


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


@app.get("/api/skills")
async def skills_index():
    """Return skill descriptors for all registered skills."""
    from verify.skills.framework import get_all_descriptors

    descriptors = get_all_descriptors()
    skills = [
        {
            "skill_id": d.skill_id,
            "name": d.name,
            "description": d.description,
            "input_types": sorted(d.input_types),
            "output_format": d.output_format,
            "framework": d.framework,
            "version": d.version,
        }
        for d in descriptors
    ]
    return JSONResponse(skills)


@app.get("/api/scan/status")
async def scan_status():
    """Return the current code scan status for the inspector surface."""
    return JSONResponse(SCAN_STATE)


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


@app.get("/api/session/{jira_key}")
async def session_info(jira_key: str):
    """Return checkpoint metadata for a story if one exists."""
    session = get_session_info(jira_key)
    if session is None:
        return JSONResponse({"has_checkpoint": False})
    return JSONResponse({"has_checkpoint": True, "session": session})


@app.post("/api/session/{jira_key}/resume")
async def resume_session(jira_key: str):
    """Restore the most recent checkpoint for a story."""
    state = SESSION_STORE.restore(jira_key)
    if state is None:
        return JSONResponse(
            {"error": f"No checkpoint found for {jira_key}"},
            status_code=400,
        )
    return JSONResponse(_build_resumed_session_payload(state))


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
    state = SESSION_STORE.create(context=ctx, llm=LLMClient(), phase_idx=0)
    return _run_current_phase(state)


@app.post("/api/respond")
async def respond(request: Request):
    body = await request.json()
    user_input = str(body.get("input", "approve")).strip()

    resolved = _resolve_session_response(_extract_session_id(body))
    if isinstance(resolved, JSONResponse):
        return resolved

    state = resolved
    harness = state.harness
    ctx = state.context

    harness.add_to_log(harness.current_phase, "human", user_input)

    # If not approve/skip, re-run current phase with developer feedback
    is_approval = user_input.lower() in ("approve", "skip", "")
    if not is_approval:
        return _rerun_current_phase(state, user_input)

    # Advance to next phase
    current_phase = ctx.current_phase
    next_phase = harness.advance_phase()
    if next_phase != current_phase:
        state.phase_idx += 1

    if state.phase_idx >= len(PHASE_SKILLS):
        run_synthesis(ctx)
        return JSONResponse(
            _build_session_payload(
                state,
                done=True,
                phase_number=len(PHASE_SKILLS),
                phase_title=PHASE_SKILLS[-1][0],
                summary=_build_summary(ctx),
            )
        )

    return _run_current_phase(state)


# ------------------------------------------------------------------
# Spec Compilation & Test Generation
# ------------------------------------------------------------------


@app.post("/api/compile")
async def compile_spec_endpoint(request: Request):
    """Compile the negotiated context into a YAML spec file."""
    from verify.compiler import compile_and_write

    body = await _read_request_body(request)
    resolved = _resolve_session_response(_extract_session_id(body))
    if isinstance(resolved, JSONResponse):
        return resolved

    ctx = resolved.context
    approval_response = _require_approval(ctx, action="compile the spec")
    if approval_response is not None:
        return approval_response

    try:
        spec_path = compile_and_write(ctx, output_dir="specs")
        with open(spec_path) as f:
            spec_content = f.read()
        parsed_spec = yaml.safe_load(spec_content) or {}
        return JSONResponse({
            "spec_path": spec_path,
            "spec_content": spec_content,
            "requirements": parsed_spec.get("requirements", []),
            "traceability": parsed_spec.get("traceability", {}),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/generate-tests")
async def generate_tests_endpoint(request: Request):
    """Generate tests from the compiled spec, run them, and evaluate."""
    from verify.evaluator import evaluate_spec
    from verify.generator import generate_and_write
    from verify.runner import run_and_parse

    body = await _read_request_body(request)
    resolved = _resolve_session_response(_extract_session_id(body))
    if isinstance(resolved, JSONResponse):
        return resolved

    state = resolved
    ctx = state.context
    approval_response = _require_approval(ctx, action="generate verification artifacts")
    if approval_response is not None:
        return approval_response

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

        ctx.verdicts = verdicts
        ctx.all_passed = all_passed

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
# Jira Feedback
# ------------------------------------------------------------------


@app.post("/api/jira/update")
async def jira_update(request: Request):
    """Update Jira ticket with verdicts — tick checkboxes and post evidence."""
    from verify.pipeline import update_jira

    body = await _read_request_body(request)
    resolved = _resolve_session_response(_extract_session_id(body))
    if isinstance(resolved, JSONResponse):
        return resolved

    ctx = resolved.context
    verdicts = ctx.verdicts
    if not verdicts:
        return JSONResponse({"error": "No verdicts available. Run /api/generate-tests first."}, status_code=400)

    try:
        result = update_jira(ctx.jira_key, verdicts, ctx.spec_path)
        return JSONResponse({
            "status": "ok",
            "jira_key": ctx.jira_key,
            "checkboxes_ticked": len(result.get("checkboxes_ticked", [])),
            "evidence_posted": result.get("comment_posted", False),
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# EARS Approval Gate
# ------------------------------------------------------------------


@app.post("/api/ears-approve")
async def ears_approve_endpoint(request: Request):
    """Approve EARS statements and set context.approved."""
    from datetime import datetime, timezone

    body = await _read_request_body(request)
    resolved = _resolve_session_response(_extract_session_id(body))
    if isinstance(resolved, JSONResponse):
        return resolved

    ctx = resolved.context
    ctx.approved = True
    ctx.approved_by = body.get("approved_by", "web_operator")
    approved_at = datetime.now(timezone.utc).isoformat()
    ctx.approved_at = approved_at

    return JSONResponse({
        "approved": True,
        "approved_by": ctx.approved_by,
        "approved_at": approved_at,
    })


# ------------------------------------------------------------------
# Pipeline Streaming & Step Endpoints
# ------------------------------------------------------------------


@app.post("/api/pipeline/stream")
async def stream_pipeline_endpoint(request: Request):
    """SSE streaming pipeline execution (compile → test → evaluate)."""
    from verify.compiler import compile_and_write
    from verify.evaluator import evaluate_spec
    from verify.generator import generate_and_write
    from verify.runner import run_and_parse

    body = await _read_request_body(request)
    resolved = _resolve_session_response(_extract_session_id(body))
    if isinstance(resolved, JSONResponse):
        return resolved

    state = resolved
    ctx = state.context
    approval_response = _require_approval(ctx, action="run the verification pipeline")
    if approval_response is not None:
        return approval_response

    def stream() -> Any:
        try:
            parsed_spec: dict[str, Any] = {}

            if ctx.spec_path and os.path.exists(ctx.spec_path):
                spec_path = ctx.spec_path
                with open(spec_path) as handle:
                    spec_content = handle.read()
                parsed_spec = yaml.safe_load(spec_content) or {}
                yield RuntimeEvent(
                    type="step",
                    session_id=state.session_id,
                    step="compile",
                    status="skipped",
                    message="Reusing compiled spec",
                    data={"spec_path": spec_path},
                ).as_sse()
            else:
                yield RuntimeEvent(
                    type="step",
                    session_id=state.session_id,
                    step="compile",
                    status="running",
                    message="Compiling spec...",
                ).as_sse()
                spec_path = compile_and_write(ctx, output_dir="specs")
                with open(spec_path) as handle:
                    spec_content = handle.read()
                parsed_spec = yaml.safe_load(spec_content) or {}
                yield RuntimeEvent(
                    type="step",
                    session_id=state.session_id,
                    step="compile",
                    status="done",
                    message="Compiled spec",
                    data={"spec_path": spec_path},
                ).as_sse()

            yield RuntimeEvent(
                type="step",
                session_id=state.session_id,
                step="generate",
                status="running",
                message="Generating tests...",
            ).as_sse()
            test_path = generate_and_write(ctx.spec_path)
            with open(test_path) as handle:
                test_content = handle.read()
            yield RuntimeEvent(
                type="step",
                session_id=state.session_id,
                step="generate",
                status="done",
                message="Generated tests",
                data={"test_path": test_path},
            ).as_sse()

            yield RuntimeEvent(
                type="step",
                session_id=state.session_id,
                step="run",
                status="running",
                message="Running generated tests...",
            ).as_sse()
            results = run_and_parse(test_path, ".verify/results")
            cases = results.get("test_cases", [])
            passed = sum(1 for case in cases if case.get("status") == "passed")
            yield RuntimeEvent(
                type="step",
                session_id=state.session_id,
                step="run",
                status="done",
                message="Completed generated tests",
                data={"passed": passed, "total": len(cases)},
            ).as_sse()

            yield RuntimeEvent(
                type="step",
                session_id=state.session_id,
                step="evaluate",
                status="running",
                message="Evaluating verdicts...",
            ).as_sse()
            verdicts = evaluate_spec(ctx.spec_path, results)
            ctx.verdicts = verdicts
            all_passed = all(verdict.get("passed") for verdict in verdicts)
            yield RuntimeEvent(
                type="step",
                session_id=state.session_id,
                step="evaluate",
                status="done",
                message="Evaluated verdicts",
                data={"all_passed": all_passed},
            ).as_sse()

            done_event = RuntimeEvent(
                type="done",
                session_id=state.session_id,
                status="done",
                message="Pipeline complete",
                data={
                    "all_passed": all_passed,
                    "requirements": parsed_spec.get("requirements", []),
                    "spec_content": spec_content,
                    "spec_path": ctx.spec_path,
                    "success": True,
                    "test_content": test_content,
                    "test_path": test_path,
                    "traceability": parsed_spec.get("traceability", {}),
                    "verdicts": verdicts,
                },
            )
            state.latest_pipeline = done_event.payload()
            yield done_event.as_sse()
        except Exception as exc:
            error_event = RuntimeEvent(
                type="error",
                session_id=state.session_id,
                step="pipeline",
                status="failed",
                message=str(exc),
            )
            state.latest_pipeline = error_event.payload()
            yield error_event.as_sse()

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.post("/api/run-tests")
async def run_tests_endpoint(request: Request):
    """Run generated tests."""
    body = await _read_request_body(request)
    resolved = _resolve_session_response(_extract_session_id(body))
    if isinstance(resolved, JSONResponse):
        return resolved

    ctx = resolved.context
    approval_response = _require_approval(ctx, action="run generated tests")
    if approval_response is not None:
        return approval_response

    if not ctx.spec_path:
        return JSONResponse({"error": "No spec compiled yet."}, status_code=400)

    try:
        from verify.generator import generate_and_write
        from verify.runner import run_and_parse

        test_path = generate_and_write(ctx.spec_path)
        results = run_and_parse(test_path, ".verify/results")
        cases = results["test_cases"]
        passed = sum(1 for c in cases if c["status"] == "passed")
        return JSONResponse({
            "test_path": test_path,
            "passed": passed,
            "total": len(cases),
            "results": results,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/evaluate")
async def evaluate_endpoint(request: Request):
    """Evaluate test results against spec traceability."""
    body = await _read_request_body(request)
    resolved = _resolve_session_response(_extract_session_id(body))
    if isinstance(resolved, JSONResponse):
        return resolved

    ctx = resolved.context
    approval_response = _require_approval(ctx, action="evaluate verification results")
    if approval_response is not None:
        return approval_response

    if not ctx.spec_path:
        return JSONResponse({"error": "No spec compiled yet."}, status_code=400)

    try:
        from verify.evaluator import evaluate_spec
        from verify.runner import run_and_parse
        from verify.generator import generate_and_write

        test_path = generate_and_write(ctx.spec_path)
        results = run_and_parse(test_path, ".verify/results")
        verdicts = evaluate_spec(ctx.spec_path, results)
        ctx.verdicts = verdicts
        all_passed = all(v["passed"] for v in verdicts)
        return JSONResponse({
            "verdicts": verdicts,
            "all_passed": all_passed,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


@app.post("/api/jira-update")
async def jira_update_endpoint(request: Request):
    """Update Jira ticket with verdicts."""
    from verify.pipeline import update_jira

    body = await _read_request_body(request)
    resolved = _resolve_session_response(_extract_session_id(body))
    if isinstance(resolved, JSONResponse):
        return resolved

    ctx = resolved.context
    verdicts = ctx.verdicts
    if not verdicts:
        return JSONResponse({"error": "No verdicts available."}, status_code=400)

    try:
        result = update_jira(ctx.jira_key, verdicts, ctx.spec_path)
        return JSONResponse({
            "status": "ok",
            "jira_key": ctx.jira_key,
            **result,
        })
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# Codebase Scan
# ------------------------------------------------------------------


@app.post("/api/scan")
async def scan_endpoint(request: Request):
    """Run a codebase scan and update SCAN_STATE."""
    body = await request.json()
    project_root = body.get("project_root") or body.get("path", ".")

    try:
        from verify.scanner import scan_java_project

        index = scan_java_project(project_root)
        summary = {
            "language": getattr(index, "language", "unknown"),
            "controllers": len(getattr(index, "controllers", [])),
            "services": len(getattr(index, "services", [])),
            "models": len(getattr(index, "models", [])),
        }
        SCAN_STATE["project_root"] = project_root
        SCAN_STATE["scanned"] = True
        SCAN_STATE["summary"] = summary
        return JSONResponse({
            "status": "ok",
            "project_root": project_root,
            "scanned": True,
            "summary": summary,
        })
    except Exception as e:
        # Gracefully handle scan failures - return status with error info
        SCAN_STATE["project_root"] = project_root
        SCAN_STATE["scanned"] = True
        SCAN_STATE["summary"] = f"Scan failed: {e}"
        return JSONResponse({
            "status": "partial",
            "project_root": project_root,
            "scanned": True,
            "summary": str(e),
        })


# ------------------------------------------------------------------
# Constitution Endpoints
# ------------------------------------------------------------------


@app.get("/api/constitution")
async def get_constitution_endpoint():
    """Return the current constitution from file or session."""
    from verify.pipeline import load_constitution

    resolved = _resolve_session_response()
    if not isinstance(resolved, JSONResponse) and resolved.context.constitution:
        return JSONResponse({"constitution": resolved.context.constitution})

    constitution = load_constitution()
    return JSONResponse({"constitution": constitution})


@app.post("/api/constitution")
async def set_constitution_endpoint(request: Request):
    """Update the constitution for the current session."""
    body = await request.json()
    constitution = body.get("constitution", {})

    resolved = _resolve_session_response()
    if isinstance(resolved, JSONResponse):
        return resolved

    resolved.context.constitution = constitution
    return JSONResponse({"status": "ok", "constitution": constitution})


# ------------------------------------------------------------------
# Spec Diff
# ------------------------------------------------------------------


@app.post("/api/spec-diff")
async def spec_diff_endpoint():
    """Compare the current spec against a previous version."""
    from verify.spec_diff import diff_specs

    resolved = _resolve_session_response()
    if isinstance(resolved, JSONResponse):
        return resolved

    ctx = resolved.context
    jira_key = ctx.jira_key

    # Try to find an existing spec
    spec_dir = ".verify/specs"
    old_spec_path = os.path.join(spec_dir, f"{jira_key}.yaml")
    has_old_spec = os.path.exists(old_spec_path)

    return JSONResponse({
        "jira_key": jira_key,
        "has_old_spec": has_old_spec,
        "diff": diff_specs(old_spec_path, None) if has_old_spec else None,
    })


# ------------------------------------------------------------------
# Permission & Access Control
# ------------------------------------------------------------------


@app.get("/api/permissions")
async def get_permissions_endpoint():
    """Return the current permission context for the session."""
    resolved = _resolve_session_response()
    if isinstance(resolved, JSONResponse):
        return resolved

    ctx = resolved.context
    perm_ctx = getattr(ctx, "permission_context", None)
    if perm_ctx is None:
        return JSONResponse({"deny_names": [], "deny_prefixes": []})

    return JSONResponse({
        "deny_names": sorted(perm_ctx.deny_names),
        "deny_prefixes": list(perm_ctx.deny_prefixes),
    })


@app.post("/api/permissions")
async def set_permissions_endpoint(request: Request):
    """Set the permission context for the current session."""
    from verify.permissions import ToolPermissionContext

    resolved = _resolve_session_response()
    if isinstance(resolved, JSONResponse):
        return resolved

    body = await request.json()
    perm_ctx = ToolPermissionContext.from_iterables(
        deny_names=body.get("deny_names", []),
        deny_prefixes=body.get("deny_prefixes", []),
    )
    resolved.context.permission_context = perm_ctx

    return JSONResponse({
        "status": "ok",
        "deny_names": sorted(perm_ctx.deny_names),
        "deny_prefixes": list(perm_ctx.deny_prefixes),
    })


@app.get("/api/permissions/denials")
async def get_denials_endpoint():
    """Return all permission denial events for the current session."""
    resolved = _resolve_session_response()
    if isinstance(resolved, JSONResponse):
        return resolved

    denials = getattr(resolved.context, "permission_denials", [])
    return JSONResponse({
        "denials": [
            {"tool_name": d.tool_name, "reason": d.reason}
            for d in denials
        ] if denials else [],
    })


# ------------------------------------------------------------------
# Evaluate Phase (Quality Critique)
# ------------------------------------------------------------------


@app.post("/api/evaluate-phase")
async def evaluate_phase_endpoint(request: Request):
    """Analyze current phase output for completeness and issues."""
    resolved = _resolve_session_response()
    if isinstance(resolved, JSONResponse):
        return resolved

    body = await request.json()
    phase = body.get("phase", "phase_1")
    ctx = resolved.context

    issues = []
    suggestions = []

    if phase == "phase_1":
        # Check classification completeness
        types_found = {c.get("type") for c in ctx.classifications}
        if types_found == {"api_behavior"}:
            issues.append(
                "All ACs classified as api_behavior — consider if any are "
                "security_invariant, data_constraint, or performance_sla"
            )
            suggestions.append("Review ACs for non-functional requirements")
        if not ctx.classifications:
            issues.append("No classifications produced yet")
    elif phase == "phase_2":
        if not ctx.postconditions:
            issues.append("No postconditions defined")
    elif phase == "phase_3":
        if not ctx.preconditions:
            issues.append("No preconditions defined")
    elif phase == "phase_4":
        if not ctx.failure_modes:
            issues.append("No failure modes enumerated")

    return JSONResponse({
        "has_issues": len(issues) > 0,
        "issues": issues,
        "suggestions": suggestions,
    })


# ------------------------------------------------------------------
# Plan Endpoint
# ------------------------------------------------------------------


@app.post("/api/plan")
async def plan_endpoint():
    """Generate an execution plan by grouping ACs by endpoint."""
    resolved = _resolve_session_response()
    if isinstance(resolved, JSONResponse):
        return resolved

    ctx = resolved.context

    # Group ACs by endpoint
    endpoint_groups: dict[str, list[int]] = {}
    for clf in ctx.classifications:
        iface = clf.get("interface", {})
        endpoint = iface.get("path", "unknown")
        ac_idx = clf.get("ac_index", -1)
        endpoint_groups.setdefault(endpoint, []).append(ac_idx)

    ac_groups = []
    for endpoint, indices in endpoint_groups.items():
        methods = []
        for clf in ctx.classifications:
            if clf.get("interface", {}).get("path") == endpoint:
                method = clf.get("interface", {}).get("method", "GET")
                if method not in methods:
                    methods.append(method)
        ac_groups.append({
            "ac_indices": sorted(indices),
            "endpoint": endpoint,
            "methods": methods,
        })

    # Estimate complexity
    total_acs = len(ctx.raw_acceptance_criteria)
    if total_acs <= 2:
        complexity = "low"
    elif total_acs <= 5:
        complexity = "medium"
    else:
        complexity = "high"

    return JSONResponse({
        "ac_groups": ac_groups,
        "cross_ac_dependencies": [],
        "estimated_complexity": complexity,
    })


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _run_current_phase(state: SessionState):
    ctx = state.context
    title, skill_fn = PHASE_SKILLS[state.phase_idx]
    llm = _ensure_llm(state)
    results = skill_fn(ctx, llm)

    state.harness.add_to_log(
        state.harness.current_phase,
        "ai",
        _build_phase_log_message(title, results),
    )

    return JSONResponse(
        _build_session_payload(
            state,
            phase_number=state.phase_idx + 1,
            phase_title=title,
            questions=_extract_questions(llm, state.phase_idx),
            results=results,
            revised=False,
        )
    )


def _rerun_current_phase(state: SessionState, feedback: str):
    """Re-run the current phase with developer feedback for revision."""
    title, skill_fn = PHASE_SKILLS[state.phase_idx]
    llm = _ensure_llm(state)
    results = skill_fn(state.context, llm, feedback=feedback)

    state.harness.add_to_log(
        state.harness.current_phase,
        "ai",
        _build_phase_log_message(title, results, revised=True),
    )

    return JSONResponse(
        _build_session_payload(
            state,
            phase_number=state.phase_idx + 1,
            phase_title=f"{title} (revised)",
            questions=_extract_questions(llm, state.phase_idx),
            results=results,
            revised=True,
        )
    )


def _extract_questions(llm: LLMClient, phase_idx: int) -> list[str]:
    if llm._mock:
        from verify.negotiation.phase1 import SYSTEM_PROMPT as P1
        from verify.negotiation.phase2 import SYSTEM_PROMPT as P2
        from verify.negotiation.phase3 import SYSTEM_PROMPT as P3
        from verify.negotiation.phase4 import SYSTEM_PROMPT as P4
        from verify.negotiation.phase5 import SYSTEM_PROMPT as P5
        from verify.negotiation.phase6 import SYSTEM_PROMPT as P6
        from verify.negotiation.phase7 import SYSTEM_PROMPT as P7

        prompts = [P1, P2, P3, P4, P5, P6, P7]
        if phase_idx < len(prompts):
            mock_resp = llm._mock_response(prompts[phase_idx])
            if isinstance(mock_resp, dict):
                return mock_resp.get("questions", [])
    return []


def _ensure_llm(state: SessionState) -> LLMClient:
    if state.llm is None:
        state.llm = LLMClient()
    return state.llm


def _build_resumed_session_payload(state: SessionState) -> dict[str, Any]:
    phase_number = _resume_phase_number(state.context.current_phase)
    return _build_session_payload(
        state,
        phase_number=phase_number,
        phase_title=_phase_title_for_number(phase_number),
        resumed=True,
    )


def _build_session_payload(
    state: SessionState,
    *,
    done: bool = False,
    phase_number: int | None = None,
    phase_title: str | None = None,
    questions: list[str] | None = None,
    results: Any | None = None,
    revised: bool | None = None,
    resumed: bool = False,
    summary: dict[str, Any] | None = None,
) -> dict[str, Any]:
    ctx = state.context
    resolved_phase_number = phase_number if phase_number is not None else state.phase_idx + 1
    payload: dict[str, Any] = {
        "acceptance_criteria": ctx.raw_acceptance_criteria,
        "approved": ctx.approved,
        "approved_at": ctx.approved_at,
        "approved_by": ctx.approved_by,
        "classifications": ctx.classifications,
        "current_phase": ctx.current_phase,
        "done": done,
        "ears_statements": ctx.ears_statements,
        "failure_modes": ctx.failure_modes,
        "invariants": ctx.invariants,
        "jira_key": ctx.jira_key,
        "jira_summary": ctx.jira_summary,
        "log_entries": len(ctx.negotiation_log),
        "negotiation_log": ctx.negotiation_log,
        "phase_number": resolved_phase_number,
        "phase_title": phase_title or _phase_title_for_number(resolved_phase_number),
        "postconditions": ctx.postconditions,
        "preconditions": ctx.preconditions,
        "session_id": state.session_id,
        "session_events": state.history,
        "total_phases": len(PHASE_SKILLS),
        "traceability_map": ctx.traceability_map,
        "usage": ctx.usage or None,
        "verdicts": ctx.verdicts,
        "verification_routing": ctx.verification_routing,
    }
    if questions is not None:
        payload["questions"] = questions
    if results is not None:
        payload["results"] = results
    if revised is not None:
        payload["revised"] = revised
    if resumed:
        payload["resumed"] = True
    if summary is not None:
        payload["summary"] = summary
    return payload


async def _read_request_body(request: Request) -> dict[str, Any]:
    try:
        body = await request.json()
    except Exception:
        return {}

    return body if isinstance(body, dict) else {}


def _require_approval(
    ctx: VerificationContext,
    *,
    action: str,
) -> JSONResponse | None:
    if ctx.approved:
        return None

    return JSONResponse(
        {"error": f"Approve EARS before attempting to {action}."},
        status_code=400,
    )


def _resolve_session_response(
    session_id: str | None = None,
) -> SessionState | JSONResponse:
    state = SESSION_STORE.resolve(session_id)
    if state is not None:
        return state

    # Legacy fallback: tests may set _session["context"] directly
    ctx = _session.get("context")
    if isinstance(ctx, VerificationContext):
        llm = _session.get("llm") or LLMClient()
        state = SESSION_STORE.create(context=ctx, llm=llm)
        # Clear legacy keys so they don't cause confusion
        _session.pop("context", None)
        _session.pop("llm", None)
        return state

    return JSONResponse({"error": "No active session"}, status_code=400)


def _extract_session_id(body: dict[str, Any]) -> str | None:
    session_id = body.get("session_id")
    if isinstance(session_id, str) and session_id.strip():
        return session_id
    return None


def _phase_title_for_number(phase_number: int) -> str:
    if 1 <= phase_number <= len(PHASE_SKILLS):
        return PHASE_SKILLS[phase_number - 1][0]
    return PHASE_SKILLS[0][0]


def _resume_phase_number(current_phase: str) -> int:
    if not current_phase.startswith("phase_"):
        return 0
    try:
        return int(current_phase.split("_", 1)[1])
    except ValueError:
        return 0


def _result_count(results: Any) -> int:
    if hasattr(results, "__len__"):
        return len(results)
    return 1


def _build_phase_log_message(title: str, results: Any, revised: bool = False) -> str:
    count = _result_count(results)
    if isinstance(results, dict):
        if "routing" in results:
            message = f"{title}: routed {len(results.get('routing', []))} requirement groups"
        elif "checklist" in results:
            message = f"{title}: assessed {len(results.get('checklist', []))} completeness checks"
        else:
            message = f"{title}: updated the structured phase payload"
    elif count == 1:
        message = f"{title}: produced 1 structured item"
    else:
        message = f"{title}: produced {count} structured items"

    if revised:
        return f"{message} after operator feedback"
    return message


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
