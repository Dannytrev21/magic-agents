"""Lightweight web UI for the negotiation loop with SSE streaming pipeline."""

import asyncio
import json
import logging
import os
import time
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.responses import StreamingResponse

from verify.context import VerificationContext
from verify.llm_client import LLMClient
from verify.negotiation.harness import NegotiationHarness
from verify.negotiation.phase1 import run_phase1
from verify.negotiation.phase2 import run_phase2
from verify.negotiation.phase3 import run_phase3
from verify.negotiation.phase4 import run_phase4
from verify.negotiation.phase5 import run_phase5
from verify.negotiation.phase6 import run_phase6
from verify.negotiation.phase7 import run_phase7
from verify.negotiation.synthesis import run_synthesis
from verify.negotiation.checkpoint import load_checkpoint, has_checkpoint, get_session_info
from verify.compiler import compile_and_write, compile_spec
from verify.generators import get_generator
from verify.generators.base import BaseGenerator
from verify.runner import run_and_parse, run_gradle_tests, parse_junit_xml
from verify.evaluator import evaluate_spec
from verify.pipeline import update_jira, load_constitution
from verify.scanner import scan_java_project
from verify.spec_diff import diff_specs, format_diff_summary
from verify.observability import HarnessLogger

logger = logging.getLogger(__name__)

app = FastAPI(title="Negotiation UI")

STATIC_DIR = Path(__file__).parent.parent.parent.parent / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory session (single-user localhost)
_session: dict = {}

PHASE_SKILLS = [
    ("Phase 1 of 7: Interface & Actor Discovery", run_phase1),
    ("Phase 2 of 7: Happy Path Contract", run_phase2),
    ("Phase 3 of 7: Precondition Formalization", run_phase3),
    ("Phase 4 of 7: Failure Mode Enumeration", run_phase4),
    ("Phase 5 of 7: Invariant Extraction", run_phase5),
    ("Phase 6 of 7: Completeness Sweep & Routing", run_phase6),
    ("Phase 7 of 7: EARS Formalization", run_phase7),
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
# Session Management (Feature 2.8: Checkpoint & Resume)
# ------------------------------------------------------------------


@app.get("/api/session/{jira_key}")
async def get_session(jira_key: str):
    """Check if a checkpoint exists for a given Jira key.

    Returns session info if found, or indicates no session exists.
    """
    if has_checkpoint(jira_key):
        info = get_session_info(jira_key)
        return JSONResponse({
            "has_checkpoint": True,
            "session": info,
        })
    else:
        return JSONResponse({
            "has_checkpoint": False,
        })


@app.post("/api/session/{jira_key}/resume")
async def resume_session(jira_key: str):
    """Resume a negotiation from a saved checkpoint.

    Loads the latest checkpoint for the given Jira key and restores
    the harness to continue negotiation from where it left off.
    """
    result = load_checkpoint(jira_key)
    if result is None:
        return JSONResponse(
            {"error": f"No checkpoint found for {jira_key}"},
            status_code=400,
        )

    ctx, phase_idx = result

    # Restore the session
    llm = LLMClient()
    harness = NegotiationHarness(ctx)

    _session["ctx"] = ctx
    _session["llm"] = llm
    _session["harness"] = harness
    _session["phase_idx"] = phase_idx

    # Map the phase_idx (from PHASES list) to the phase_number (for PHASE_SKILLS)
    # PHASES = [phase_0, phase_1, phase_2, phase_3, phase_4, phase_5, phase_6, phase_7]
    # PHASE_SKILLS = [Phase 1, Phase 2, Phase 3, Phase 4]
    # So phase_1 -> phase_number=1, phase_2 -> phase_number=2, etc.
    phase_skill_idx = max(0, phase_idx - 1)  # Map PHASES index to PHASE_SKILLS index
    phase_number = min(phase_skill_idx + 1, len(PHASE_SKILLS))

    return JSONResponse({
        "resumed": True,
        "jira_key": ctx.jira_key,
        "jira_summary": ctx.jira_summary,
        "current_phase": ctx.current_phase,
        "phase_number": phase_number,
        "log_entries": len(ctx.negotiation_log),
        "approved": ctx.approved,
    })


# ------------------------------------------------------------------
# Negotiation
# ------------------------------------------------------------------


@app.post("/api/start")
async def start_negotiation(request: Request):
    body = await request.json()

    # Load constitution from file or use provided/default
    constitution = body.get("constitution")
    if not constitution:
        constitution = load_constitution()
    if not constitution:
        constitution = {
            "project": {"framework": "spring-boot", "language": "java"},
            "api": {"base_path": "/api/v1"},
        }

    ctx = VerificationContext(
        jira_key=body.get("jira_key", "DEMO-001"),
        jira_summary=body.get("jira_summary", "User Profile Endpoint"),
        raw_acceptance_criteria=body.get("acceptance_criteria", [
            {"index": 0, "text": "User can view their profile via GET /api/v1/users/me", "checked": False},
        ]),
        constitution=constitution,
    )

    # Inject codebase context if available from prior scan
    if "codebase_summary" in _session:
        ctx.constitution["_codebase_index"] = _session.get("codebase_summary", "")

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

    # Log developer interaction
    harness.logger.log_developer_interaction(
        harness.current_phase,
        "feedback" if user_input.lower() not in ("approve", "skip", "") else "approval",
        data={"input": user_input[:100]}  # Log first 100 chars to avoid huge logs
    )

    harness.add_to_log(harness.current_phase, "human", user_input)

    # If not approve/skip, re-run current phase with developer feedback
    is_approval = user_input.lower() in ("approve", "skip", "")
    if not is_approval:
        return _rerun_current_phase(user_input)

    # Advance to next phase
    harness.advance_phase()
    _session["phase_idx"] = phase_idx + 1

    if _session["phase_idx"] >= len(PHASE_SKILLS):
        # Post-negotiation: build traceability map (invariants & EARS already populated by phases 5 & 7)
        from verify.negotiation.synthesis import build_traceability_map
        build_traceability_map(ctx)
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


@app.post("/api/spec-diff")
async def spec_diff_endpoint():
    """Compare the new compiled spec against the old spec file (if it exists).

    If a spec already exists for the jira_key in the specs/ directory,
    compares the current negotiation result against the previous version.
    Returns a structured diff showing what changed.

    Feature 17: Spec Diff on Re-negotiation from hackathon-roadmap.md
    """
    if "ctx" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    ctx: VerificationContext = _session["ctx"]
    try:
        # Compile the new spec (but don't write yet)
        new_spec = compile_spec(ctx)

        # Check if old spec exists
        old_spec_path = os.path.join("specs", f"{ctx.jira_key}.yaml")
        if not os.path.exists(old_spec_path):
            return JSONResponse({
                "has_old_spec": False,
                "message": "No previous spec found; treating as new spec",
                "jira_key": ctx.jira_key,
                "new_spec": new_spec,
            })

        # Perform diff
        diff_result = diff_specs(old_spec_path, new_spec)

        # Format response
        has_changes = bool(
            diff_result.get("added_requirements")
            or diff_result.get("removed_requirements")
            or diff_result.get("modified_requirements")
            or diff_result.get("changed_fields")
        )

        return JSONResponse({
            "has_old_spec": True,
            "has_changes": has_changes,
            "jira_key": ctx.jira_key,
            "old_spec_path": old_spec_path,
            "added_requirements": diff_result["added_requirements"],
            "removed_requirements": diff_result["removed_requirements"],
            "modified_requirements": {
                rid: {
                    field: {
                        "old": _serialize_for_json(old_val),
                        "new": _serialize_for_json(new_val),
                    }
                    for field, (old_val, new_val) in changes.items()
                }
                for rid, changes in diff_result["modified_requirements"].items()
            },
            "changed_fields": diff_result["changed_fields"],
            "summary": diff_result["summary"],
        })
    except Exception as e:
        import traceback
        return JSONResponse({
            "error": str(e),
            "traceback": traceback.format_exc(),
        }, status_code=500)


@app.post("/api/generate-tests")
async def generate_tests_endpoint():
    """Copy the appropriate verification skill into the target repo.

    Determines the skill type from the spec/constitution (e.g., cucumber_java),
    copies the skill files (SKILL.md, SCHEMA.md) into the target repo's
    .claude/skills/ directory, and returns the file contents so the user
    can run the skill themselves.
    """
    if "ctx" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    ctx: VerificationContext = _session["ctx"]
    if not ctx.spec_path:
        return JSONResponse({"error": "No spec compiled yet. Call /api/compile first."}, status_code=400)

    try:
        import shutil

        # Determine which skill to copy based on constitution
        constitution = BaseGenerator.load_constitution("constitution.yaml")
        language = constitution.get("project", {}).get("language", "java")
        framework = constitution.get("project", {}).get("framework", "spring-boot")

        # Map language/framework to skill directory
        skill_id = "verify-gherkin"  # default for Java/Spring Boot + Cucumber
        # Future: add mapping logic for other languages/frameworks

        # Source: our skill directory
        source_dir = Path(__file__).parent.parent.parent.parent / ".claude" / "skills" / skill_id

        # Destination: target repo's .claude/skills/ directory
        # Use the constitution's source_structure to find the target repo root
        test_dir = constitution.get("source_structure", {}).get("test", "dog-service/src/test/java")
        # Walk up from test dir to find the repo root (where .claude/ should go)
        repo_root = test_dir.split("/src/")[0] if "/src/" in test_dir else "dog-service"
        dest_dir = Path(repo_root) / ".claude" / "skills" / skill_id

        if not source_dir.exists():
            return JSONResponse({"error": f"Skill directory not found: {source_dir}"}, status_code=500)

        # Copy skill files
        os.makedirs(dest_dir, exist_ok=True)
        copied_files = {}
        for src_file in source_dir.iterdir():
            if src_file.is_file():
                dest_file = dest_dir / src_file.name
                shutil.copy2(src_file, dest_file)
                with open(dest_file) as f:
                    copied_files[src_file.name] = {
                        "path": str(dest_file),
                        "content": f.read(),
                    }

        # Also copy the spec into the target repo for reference
        spec_dest = Path(repo_root) / "specs" / Path(ctx.spec_path).name
        os.makedirs(spec_dest.parent, exist_ok=True)
        shutil.copy2(ctx.spec_path, spec_dest)

        return JSONResponse({
            "skill_id": skill_id,
            "skill_dest": str(dest_dir),
            "spec_dest": str(spec_dest),
            "copied_files": copied_files,
            "message": f"Skill '{skill_id}' copied to {dest_dir}. Run the skill with Claude Code in the target repo to generate tests.",
        })
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        print(f"generate-tests error:\n{tb}", flush=True)
        return JSONResponse({"error": str(e), "traceback": tb}, status_code=500)


# ------------------------------------------------------------------
# Constitution Loading
# ------------------------------------------------------------------


@app.get("/api/constitution")
async def get_constitution():
    """Load and return the project constitution."""
    constitution = load_constitution()
    return JSONResponse({"constitution": constitution, "loaded": bool(constitution)})


@app.post("/api/constitution")
async def set_constitution(request: Request):
    """Set constitution for the current session."""
    body = await request.json()
    if "ctx" in _session:
        _session["ctx"].constitution = body.get("constitution", {})
    return JSONResponse({"status": "ok"})


# ------------------------------------------------------------------
# Codebase Scanner (Feature 8)
# ------------------------------------------------------------------


@app.post("/api/scan")
async def scan_codebase(request: Request):
    """Scan the target codebase and return a structural index.

    If a project_root is provided, scans that directory.
    Otherwise defaults to 'dog-service'.
    """
    body = await request.json()
    project_root = body.get("project_root", "dog-service")

    try:
        index = scan_java_project(project_root)
        summary = index.summary()
        result = index.to_dict()

        # Store on session for use in negotiation
        _session["codebase_index"] = result
        _session["codebase_summary"] = summary

        return JSONResponse({
            "scanned": True,
            "summary": summary,
            "index": result,
        })
    except Exception as e:
        return JSONResponse({"error": str(e), "scanned": False}, status_code=500)


@app.get("/api/scan/status")
async def scan_status():
    """Check if a codebase scan has been performed."""
    has_scan = "codebase_index" in _session
    return JSONResponse({
        "scanned": has_scan,
        "summary": _session.get("codebase_summary", ""),
    })


# ------------------------------------------------------------------
# Evaluator-Optimizer (Feature 2.9)
# ------------------------------------------------------------------


@app.post("/api/evaluate-phase")
async def evaluate_phase_endpoint(request: Request):
    """Run the evaluator-optimizer on the current phase output.

    Provides adversarial critique of phase outputs — catches semantic gaps
    that deterministic validation (validate.py) can't.
    """
    if "context" not in _session and "ctx" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    ctx = _session.get("context") or _session.get("ctx")
    llm = _session.get("llm") or LLMClient()

    body = await request.json()
    phase = body.get("phase", "phase_1")

    try:
        from verify.negotiation.evaluator_optimizer import evaluate_phase_output
        result = evaluate_phase_output(ctx, phase, llm)
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# Negotiation Planner (Feature 2.10)
# ------------------------------------------------------------------


@app.post("/api/plan")
async def plan_endpoint():
    """Create a negotiation plan before starting Phase 1.

    Analyzes all ACs, groups related ones, identifies cross-cutting
    concerns, and estimates complexity.
    """
    if "context" not in _session and "ctx" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    ctx = _session.get("context") or _session.get("ctx")
    llm = _session.get("llm") or LLMClient()

    try:
        from verify.negotiation.planner import create_negotiation_plan
        plan = create_negotiation_plan(ctx, llm)
        return JSONResponse(plan)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# Pipeline Execution (Run Tests + Evaluate + Jira Update)
# ------------------------------------------------------------------


@app.post("/api/run-tests")
async def run_tests_endpoint():
    """Run Gradle tests against the dog-service target."""
    if "ctx" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    ctx: VerificationContext = _session["ctx"]
    if not ctx.spec_path:
        return JSONResponse({"error": "No spec compiled yet"}, status_code=400)

    try:
        project_dir = os.path.join(os.getcwd(), "dog-service")
        results_dir = os.path.join(os.getcwd(), ".verify", "results")

        if os.path.isdir(project_dir):
            xml_path = run_gradle_tests(project_dir, results_dir)
            test_results = parse_junit_xml(xml_path)
            result = {"test_cases": test_results}
        else:
            # Fallback: try pytest if no dog-service
            from verify.skills.framework import dispatch_skills_for_spec_path
            dispatch_skills_for_spec_path(ctx.spec_path)
            generated_test = f".verify/generated/test_{ctx.jira_key.lower().replace('-', '_')}.py"
            if os.path.exists(generated_test):
                result = run_and_parse(generated_test, results_dir)
            else:
                return JSONResponse({"error": "No test target found"}, status_code=400)

        passed = sum(1 for c in result["test_cases"] if c["status"] == "passed")
        total = len(result["test_cases"])

        _session["test_results"] = result

        return JSONResponse({
            "passed": passed,
            "total": total,
            "test_cases": result["test_cases"],
        })
    except Exception as e:
        import traceback
        tb = traceback.format_exc()
        logger.error(f"run-tests error:\n{tb}")
        return JSONResponse({"error": str(e), "traceback": tb}, status_code=500)


@app.post("/api/evaluate")
async def evaluate_endpoint():
    """Evaluate test results against the spec traceability map."""
    if "ctx" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    ctx: VerificationContext = _session["ctx"]
    if not ctx.spec_path:
        return JSONResponse({"error": "No spec compiled yet"}, status_code=400)

    test_results = _session.get("test_results")
    if not test_results:
        return JSONResponse({"error": "No test results. Run tests first."}, status_code=400)

    try:
        verdicts = evaluate_spec(ctx.spec_path, test_results)
        ctx.verdicts = verdicts
        ctx.all_passed = all(v["passed"] for v in verdicts)

        return JSONResponse({
            "verdicts": verdicts,
            "all_passed": ctx.all_passed,
        })
    except Exception as e:
        import traceback
        return JSONResponse({"error": str(e), "traceback": traceback.format_exc()}, status_code=500)


@app.post("/api/jira-update")
async def jira_update_endpoint():
    """Update Jira with verification results (checkboxes + evidence + transition)."""
    if "ctx" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    ctx: VerificationContext = _session["ctx"]
    if not ctx.verdicts:
        return JSONResponse({"error": "No verdicts. Run evaluation first."}, status_code=400)

    try:
        result = update_jira(
            jira_key=ctx.jira_key,
            verdicts=ctx.verdicts,
            spec_path=ctx.spec_path,
            transition_on_pass=True,
        )
        return JSONResponse(result)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ------------------------------------------------------------------
# SSE Streaming Pipeline (all steps streamed to UI)
# ------------------------------------------------------------------


@app.post("/api/pipeline/stream")
async def stream_pipeline():
    """Stream the full pipeline execution via SSE.

    Steps: compile → generate tests → run tests → evaluate → jira update
    Each step emits progress events.
    """
    if "ctx" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    ctx: VerificationContext = _session["ctx"]

    async def event_generator():
        def send_event(event_type: str, data: dict):
            payload = json.dumps({"type": event_type, **data})
            return f"data: {payload}\n\n"

        # Step 1: Compile spec
        yield send_event("step", {"step": "compile", "status": "running", "message": "Compiling spec from negotiation context..."})
        try:
            spec_path = compile_and_write(ctx, output_dir="specs")
            yield send_event("step", {"step": "compile", "status": "done", "message": f"Spec compiled: {spec_path}", "spec_path": spec_path})
        except Exception as e:
            yield send_event("step", {"step": "compile", "status": "error", "message": str(e)})
            yield send_event("done", {"success": False, "error": str(e)})
            return

        await asyncio.sleep(0.1)

        # Step 2: Generate tests
        yield send_event("step", {"step": "generate", "status": "running", "message": "Generating Cucumber tests via Claude API..."})
        try:
            llm: LLMClient = _session["llm"]
            constitution = BaseGenerator.load_constitution("constitution.yaml")
            generator = get_generator("cucumber_java")
            generated = generator.generate(ctx.spec_path, constitution, llm)
            valid, errors = generator.validate(generated)
            written_paths = generator.write(generated)

            generated_files = {}
            for path, content in generated.files.items():
                label = "feature" if path.endswith(".feature") else "step_definition"
                generated_files[label] = {"path": path, "content": content}

            yield send_event("step", {
                "step": "generate",
                "status": "done",
                "message": f"Generated {len(written_paths)} files",
                "paths": written_paths,
                "generated_files": generated_files,
                "validation_errors": errors if not valid else [],
            })
        except Exception as e:
            yield send_event("step", {"step": "generate", "status": "error", "message": str(e)})
            yield send_event("done", {"success": False, "error": str(e)})
            return

        await asyncio.sleep(0.1)

        # Step 3: Run tests
        yield send_event("step", {"step": "run_tests", "status": "running", "message": "Running Gradle tests..."})
        try:
            project_dir = os.path.join(os.getcwd(), "dog-service")
            results_dir = os.path.join(os.getcwd(), ".verify", "results")

            if os.path.isdir(project_dir):
                xml_path = run_gradle_tests(project_dir, results_dir)
                test_cases = parse_junit_xml(xml_path)
                test_results = {"test_cases": test_cases}
            else:
                test_results = {"test_cases": []}

            passed = sum(1 for c in test_results["test_cases"] if c["status"] == "passed")
            total = len(test_results["test_cases"])
            _session["test_results"] = test_results

            yield send_event("step", {
                "step": "run_tests",
                "status": "done",
                "message": f"{passed}/{total} tests passed",
                "passed": passed,
                "total": total,
            })
        except Exception as e:
            yield send_event("step", {"step": "run_tests", "status": "error", "message": str(e)})
            yield send_event("done", {"success": False, "error": str(e)})
            return

        await asyncio.sleep(0.1)

        # Step 4: Evaluate
        yield send_event("step", {"step": "evaluate", "status": "running", "message": "Evaluating verdicts against traceability map..."})
        try:
            verdicts = evaluate_spec(ctx.spec_path, test_results)
            ctx.verdicts = verdicts
            ctx.all_passed = all(v["passed"] for v in verdicts)

            yield send_event("step", {
                "step": "evaluate",
                "status": "done",
                "message": f"{'ALL PASSED' if ctx.all_passed else 'SOME FAILED'}",
                "verdicts": verdicts,
                "all_passed": ctx.all_passed,
            })
        except Exception as e:
            yield send_event("step", {"step": "evaluate", "status": "error", "message": str(e)})
            yield send_event("done", {"success": False, "error": str(e)})
            return

        await asyncio.sleep(0.1)

        # Step 5: Jira update (if configured)
        jira_configured = bool(
            os.environ.get("JIRA_BASE_URL")
            and os.environ.get("JIRA_EMAIL")
            and os.environ.get("JIRA_API_TOKEN")
        )

        if jira_configured and ctx.jira_key and not ctx.jira_key.startswith("DEMO"):
            yield send_event("step", {"step": "jira_update", "status": "running", "message": f"Updating Jira ticket {ctx.jira_key}..."})
            try:
                jira_result = update_jira(
                    jira_key=ctx.jira_key,
                    verdicts=ctx.verdicts,
                    spec_path=ctx.spec_path,
                )
                yield send_event("step", {
                    "step": "jira_update",
                    "status": "done",
                    "message": f"Jira updated: {len(jira_result['checkboxes_ticked'])} checkboxes ticked"
                        + (" | Transitioned to Done" if jira_result["transitioned"] else ""),
                    "jira_result": jira_result,
                })
            except Exception as e:
                yield send_event("step", {"step": "jira_update", "status": "error", "message": str(e)})
        else:
            yield send_event("step", {"step": "jira_update", "status": "skipped", "message": "Jira update skipped (not configured or demo ticket)"})

        # Done
        yield send_event("done", {
            "success": True,
            "all_passed": ctx.all_passed,
            "verdicts": ctx.verdicts,
        })

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# ------------------------------------------------------------------
# EARS Approval Gate
# ------------------------------------------------------------------


@app.post("/api/ears-approve")
async def ears_approve(request: Request):
    """Approve EARS statements before spec emission."""
    if "ctx" not in _session:
        return JSONResponse({"error": "No active session"}, status_code=400)

    body = await request.json()
    ctx: VerificationContext = _session["ctx"]

    ctx.approved = True
    ctx.approved_by = body.get("approved_by", "developer")
    ctx.approved_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    return JSONResponse({
        "approved": True,
        "approved_by": ctx.approved_by,
        "approved_at": ctx.approved_at,
        "ears_count": len(ctx.ears_statements),
    })


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _run_current_phase():
    ctx: VerificationContext = _session["ctx"]
    llm: LLMClient = _session["llm"]
    harness: NegotiationHarness = _session["harness"]
    phase_idx: int = _session["phase_idx"]

    title, skill_fn = PHASE_SKILLS[phase_idx]

    # Log LLM call
    harness.logger.log_llm_called(
        harness.current_phase,
        prompt_length=len(title),  # Rough estimate
        data={"phase_title": title}
    )

    results = skill_fn(ctx, llm)

    # Normalize results for logging — dict results (phase 6) vs list results
    result_count = len(results) if isinstance(results, list) else len(results.get("routing", results.get("checklist", []))) if isinstance(results, dict) else 0

    # Log LLM response
    harness.logger.log_llm_responded(
        harness.current_phase,
        response_length=len(str(results)),
        duration_ms=0,  # Not tracked in this simple version
        data={"result_count": result_count}
    )

    harness.add_to_log(
        harness.current_phase, "ai",
        f"{title}: produced {result_count} items",
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

    # Log LLM call with feedback
    harness.logger.log_llm_called(
        harness.current_phase,
        prompt_length=len(title) + len(feedback),
        data={"phase_title": title, "feedback_length": len(feedback)}
    )

    results = skill_fn(ctx, llm, feedback=feedback)

    # Normalize results for logging
    result_count = len(results) if isinstance(results, list) else len(results.get("routing", results.get("checklist", []))) if isinstance(results, dict) else 0

    # Log LLM response
    harness.logger.log_llm_responded(
        harness.current_phase,
        response_length=len(str(results)),
        duration_ms=0,
        data={"result_count": result_count, "revised": True}
    )

    harness.add_to_log(
        harness.current_phase, "ai",
        f"{title} (revised): produced {result_count} items",
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
        from verify.negotiation.phase5 import SYSTEM_PROMPT as P5
        from verify.negotiation.phase6 import SYSTEM_PROMPT as P6
        from verify.negotiation.phase7 import SYSTEM_PROMPT as P7
        prompts = [P1, P2, P3, P4, P5, P6, P7]
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


def _serialize_for_json(value):
    """Convert a value to a JSON-serializable format.

    Handles nested dicts and lists, truncates large structures.
    """
    if value is None:
        return None
    if isinstance(value, (bool, int, float, str)):
        return value
    if isinstance(value, dict):
        return {k: _serialize_for_json(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_serialize_for_json(v) for v in value]
    # Fallback: convert to string representation
    return str(value)
