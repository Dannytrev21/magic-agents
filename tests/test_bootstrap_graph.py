"""Tests for Epic P8: Bootstrap & Initialization Graph.

P8.1: Define BootstrapGraph with Ordered Stages
P8.2: Replace Ad-Hoc Initialization with Bootstrap Graph
P8.3: Health Check Endpoint with Stage Status
"""

import time

import pytest

from verify.context import VerificationContext


# ---------------------------------------------------------------
# P8.1 — BootstrapGraph with Ordered Stages
# ---------------------------------------------------------------


class TestBootstrapStageDefinition:
    """BootstrapStage should be a dataclass with name, description, deps, handler."""

    def test_stage_has_required_fields(self):
        from verify.bootstrap import BootstrapStage

        stage = BootstrapStage(
            name="test_stage",
            description="A test stage",
            dependencies=[],
            handler=lambda ctx: None,
        )
        assert stage.name == "test_stage"
        assert stage.description == "A test stage"
        assert stage.dependencies == []
        assert callable(stage.handler)

    def test_stage_with_dependencies(self):
        from verify.bootstrap import BootstrapStage

        stage = BootstrapStage(
            name="b",
            description="Stage B",
            dependencies=["a"],
            handler=lambda ctx: None,
        )
        assert stage.dependencies == ["a"]


class TestBootstrapGraphExecution:
    """BootstrapGraph should execute stages in topological order."""

    def test_bootstrap_order(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        order = []
        graph.add_stage(
            BootstrapStage(
                name="a",
                description="Stage A",
                dependencies=[],
                handler=lambda ctx: order.append("a"),
            )
        )
        graph.add_stage(
            BootstrapStage(
                name="b",
                description="Stage B",
                dependencies=["a"],
                handler=lambda ctx: order.append("b"),
            )
        )
        graph.execute({})
        assert order == ["a", "b"]

    def test_three_stage_chain(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        order = []
        graph.add_stage(BootstrapStage("c", "C", ["b"], lambda ctx: order.append("c")))
        graph.add_stage(BootstrapStage("a", "A", [], lambda ctx: order.append("a")))
        graph.add_stage(BootstrapStage("b", "B", ["a"], lambda ctx: order.append("b")))
        graph.execute({})
        assert order == ["a", "b", "c"]

    def test_diamond_dependency(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        order = []
        graph.add_stage(BootstrapStage("a", "A", [], lambda ctx: order.append("a")))
        graph.add_stage(BootstrapStage("b", "B", ["a"], lambda ctx: order.append("b")))
        graph.add_stage(BootstrapStage("c", "C", ["a"], lambda ctx: order.append("c")))
        graph.add_stage(
            BootstrapStage("d", "D", ["b", "c"], lambda ctx: order.append("d"))
        )
        graph.execute({})
        assert order[0] == "a"
        assert order[-1] == "d"
        assert set(order[1:3]) == {"b", "c"}

    def test_failed_stage_skips_dependents(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        def fail(_ctx):
            raise RuntimeError("boom")

        graph = BootstrapGraph()
        graph.add_stage(BootstrapStage("a", "A", [], fail))
        graph.add_stage(
            BootstrapStage("b", "B", ["a"], lambda ctx: None)
        )
        report = graph.execute({})
        assert report.stages["a"].status == "failed"
        assert report.stages["b"].status == "skipped"

    def test_failed_stage_records_error(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        graph.add_stage(
            BootstrapStage("a", "A", [], lambda ctx: (_ for _ in ()).throw(ValueError("bad")))
        )
        report = graph.execute({})
        assert "bad" in report.stages["a"].error

    def test_cycle_detection(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        graph.add_stage(BootstrapStage("a", "A", ["b"], lambda ctx: None))
        graph.add_stage(BootstrapStage("b", "B", ["a"], lambda ctx: None))
        with pytest.raises(ValueError, match="cycle"):
            graph.execute({})

    def test_duplicate_stage_name_raises(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        graph.add_stage(BootstrapStage("a", "A", [], lambda ctx: None))
        with pytest.raises(ValueError, match="duplicate"):
            graph.add_stage(BootstrapStage("a", "A2", [], lambda ctx: None))

    def test_unknown_dependency_raises(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        graph.add_stage(BootstrapStage("a", "A", ["nonexistent"], lambda ctx: None))
        with pytest.raises(ValueError, match="nonexistent"):
            graph.execute({})

    def test_report_includes_timing(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        graph.add_stage(
            BootstrapStage("a", "A", [], lambda ctx: time.sleep(0.01))
        )
        report = graph.execute({})
        assert report.stages["a"].duration_ms >= 5  # at least a few ms
        assert report.total_bootstrap_ms >= 5

    def test_report_success_flag(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        graph.add_stage(BootstrapStage("a", "A", [], lambda ctx: None))
        graph.add_stage(BootstrapStage("b", "B", ["a"], lambda ctx: None))
        report = graph.execute({})
        assert report.ready is True
        assert all(s.status == "success" for s in report.stages.values())

    def test_report_not_ready_on_failure(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        graph.add_stage(
            BootstrapStage("a", "A", [], lambda ctx: (_ for _ in ()).throw(RuntimeError("fail")))
        )
        report = graph.execute({})
        assert report.ready is False

    def test_handler_receives_context(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        received = {}

        def handler(ctx):
            received.update(ctx)

        graph = BootstrapGraph()
        graph.add_stage(BootstrapStage("a", "A", [], handler))
        graph.execute({"key": "value"})
        assert received["key"] == "value"

    def test_independent_stages_all_execute(self):
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        order = []
        graph.add_stage(BootstrapStage("x", "X", [], lambda ctx: order.append("x")))
        graph.add_stage(BootstrapStage("y", "Y", [], lambda ctx: order.append("y")))
        graph.add_stage(BootstrapStage("z", "Z", [], lambda ctx: order.append("z")))
        graph.execute({})
        assert set(order) == {"x", "y", "z"}

    def test_partial_failure_does_not_block_unrelated(self):
        """A failure in one branch should not block an independent branch."""
        from verify.bootstrap import BootstrapGraph, BootstrapStage

        graph = BootstrapGraph()
        order = []
        graph.add_stage(BootstrapStage("a", "A", [], lambda ctx: (_ for _ in ()).throw(RuntimeError("fail"))))
        graph.add_stage(BootstrapStage("b", "B", ["a"], lambda ctx: order.append("b")))
        graph.add_stage(BootstrapStage("c", "C", [], lambda ctx: order.append("c")))
        report = graph.execute({})
        assert report.stages["a"].status == "failed"
        assert report.stages["b"].status == "skipped"
        assert report.stages["c"].status == "success"
        assert "c" in order


# ---------------------------------------------------------------
# P8.2 — Build Bootstrap Graph for magic-agents
# ---------------------------------------------------------------


class TestBuildBootstrapGraph:
    """build_bootstrap_graph() should return a configured graph."""

    def test_build_returns_graph(self):
        from verify.bootstrap import build_bootstrap_graph

        graph = build_bootstrap_graph()
        assert len(graph._stages) >= 3

    def test_build_graph_executes_in_mock_mode(self, monkeypatch):
        from verify.bootstrap import build_bootstrap_graph

        monkeypatch.setenv("LLM_MOCK", "true")
        graph = build_bootstrap_graph()
        report = graph.execute({})
        # In mock mode, all stages should succeed
        assert report.ready is True

    def test_build_graph_includes_env_validation(self):
        from verify.bootstrap import build_bootstrap_graph

        graph = build_bootstrap_graph()
        assert "env_validation" in graph._stages

    def test_build_graph_includes_session_store_init(self):
        from verify.bootstrap import build_bootstrap_graph

        graph = build_bootstrap_graph()
        assert "session_store_init" in graph._stages

    def test_report_to_dict(self):
        from verify.bootstrap import build_bootstrap_graph

        graph = build_bootstrap_graph()
        report = graph.execute({})
        d = report.to_dict()
        assert "ready" in d
        assert "total_bootstrap_ms" in d
        assert "stages" in d


# ---------------------------------------------------------------
# P8.3 — Health Check Endpoint
# ---------------------------------------------------------------


class TestHealthEndpoint:
    """GET /api/health should return bootstrap readiness and stage status."""

    @pytest.fixture
    def client(self, monkeypatch):
        monkeypatch.setenv("LLM_MOCK", "true")
        from fastapi.testclient import TestClient
        from verify.negotiation.web import app

        return TestClient(app)

    def test_health_returns_200(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200

    def test_health_has_ready_field(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert "ready" in data
        assert isinstance(data["ready"], bool)

    def test_health_has_stages(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert "stages" in data
        assert isinstance(data["stages"], dict)

    def test_health_has_total_bootstrap_ms(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        assert "total_bootstrap_ms" in data
        assert isinstance(data["total_bootstrap_ms"], (int, float))

    def test_health_stages_have_duration(self, client):
        resp = client.get("/api/health")
        data = resp.json()
        for stage_name, stage_data in data["stages"].items():
            assert "status" in stage_data
            assert "duration_ms" in stage_data
