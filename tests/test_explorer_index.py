"""RED tests for P11.2: Structural Index Builder (Multi-Language).

Tests the CodebaseIndex builder that scans repos using language-appropriate
scanners dispatched based on detected StackProfile.
"""

import pytest
from verify.explorer.detect import StackProfile, detect_stack
from verify.explorer.index import (
    CodebaseIndex,
    EndpointInfo,
    ModelInfo,
    SchemaInfo,
    TestPatternInfo,
    build_codebase_index,
)


def _java_profile(**overrides) -> StackProfile:
    defaults = dict(
        language="java", framework="spring-boot",
        build_tool="gradle", runtime_version="17", confidence=0.9,
    )
    defaults.update(overrides)
    return StackProfile(**defaults)


def _python_profile(**overrides) -> StackProfile:
    defaults = dict(
        language="python", framework="fastapi",
        build_tool="pip", runtime_version="3.11", confidence=0.9,
    )
    defaults.update(overrides)
    return StackProfile(**defaults)


class TestCodebaseIndexDataclass:
    """CodebaseIndex should carry all structural index data."""

    def test_index_fields(self):
        index = CodebaseIndex(project_root="/tmp/test")
        assert index.endpoints == []
        assert index.models == []
        assert index.schemas == []
        assert index.test_patterns == []
        assert index.config_files == []
        assert index.directory_tree == []
        assert index.coverage_report == {"parsed_files": 0, "failed_files": 0, "total_files": 0}

    def test_to_dict(self):
        index = CodebaseIndex(
            project_root="/tmp/test",
            endpoints=[EndpointInfo(method="GET", path="/api/dogs", handler="DogController.list", file_path="Dog.java")],
        )
        d = index.to_dict()
        assert "endpoints" in d
        assert len(d["endpoints"]) == 1
        assert d["endpoints"][0]["method"] == "GET"


class TestJavaScanner:
    """Java scanner should extract Spring Boot constructs."""

    def test_java_endpoints_from_dog_service(self):
        profile = _java_profile()
        index = build_codebase_index(profile, "dog-service")
        assert len(index.endpoints) >= 4
        assert any(e.method == "GET" and "/dogs" in e.path for e in index.endpoints)

    def test_java_models(self, tmp_path):
        java_dir = tmp_path / "src" / "main" / "java"
        java_dir.mkdir(parents=True)
        (java_dir / "Dog.java").write_text(
            "@Entity\npublic class Dog {\n"
            "    private Long id;\n"
            "    private String name;\n"
            "}"
        )
        profile = _java_profile()
        index = build_codebase_index(profile, str(tmp_path))
        assert any(m.class_name == "Dog" for m in index.models)

    def test_java_dtos(self, tmp_path):
        java_dir = tmp_path / "src" / "main" / "java"
        java_dir.mkdir(parents=True)
        (java_dir / "DogDto.java").write_text(
            "public class DogDto {\n"
            "    private String name;\n"
            "    private String breed;\n"
            "}"
        )
        profile = _java_profile()
        index = build_codebase_index(profile, str(tmp_path))
        assert any(s.class_name == "DogDto" for s in index.schemas)

    def test_java_test_patterns(self):
        profile = _java_profile()
        index = build_codebase_index(profile, "dog-service")
        assert len(index.test_patterns) >= 1

    def test_java_config_files(self):
        profile = _java_profile()
        index = build_codebase_index(profile, "dog-service")
        assert any("application" in c for c in index.config_files)


class TestPythonScanner:
    """Python scanner should extract FastAPI/Flask constructs."""

    def test_python_fastapi_routes(self, tmp_path):
        (tmp_path / "main.py").write_text(
            "from fastapi import FastAPI, APIRouter\n"
            "app = FastAPI()\n"
            "router = APIRouter()\n"
            '@app.get("/api/users")\n'
            "async def list_users(): pass\n"
            '@router.post("/api/users")\n'
            "async def create_user(): pass\n"
        )
        profile = _python_profile()
        index = build_codebase_index(profile, str(tmp_path))
        assert len(index.endpoints) >= 2
        assert any(e.method == "GET" and "/users" in e.path for e in index.endpoints)

    def test_python_pydantic_models(self, tmp_path):
        (tmp_path / "models.py").write_text(
            "from pydantic import BaseModel\n\n"
            "class UserCreate(BaseModel):\n"
            "    name: str\n"
            "    email: str\n"
        )
        profile = _python_profile()
        index = build_codebase_index(profile, str(tmp_path))
        assert any(s.class_name == "UserCreate" for s in index.schemas)

    def test_python_sqlalchemy_models(self, tmp_path):
        (tmp_path / "models.py").write_text(
            "from sqlalchemy.orm import DeclarativeBase\n"
            "class Base(DeclarativeBase): pass\n\n"
            "class User(Base):\n"
            "    __tablename__ = 'users'\n"
            "    id = Column(Integer, primary_key=True)\n"
            "    name = Column(String)\n"
        )
        profile = _python_profile()
        index = build_codebase_index(profile, str(tmp_path))
        assert any(m.class_name == "User" for m in index.models)

    def test_python_test_patterns(self, tmp_path):
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_users.py").write_text(
            "import pytest\n\n"
            "class TestUsers:\n"
            "    def test_list(self): pass\n"
        )
        (test_dir / "conftest.py").write_text("import pytest\n")
        profile = _python_profile()
        index = build_codebase_index(profile, str(tmp_path))
        assert len(index.test_patterns) >= 1
        assert any("pytest" in t.framework for t in index.test_patterns)


class TestTypeScriptScanner:
    """TypeScript scanner should extract Express/Next.js constructs."""

    def test_ts_express_routes(self, tmp_path):
        (tmp_path / "app.ts").write_text(
            "import express from 'express';\n"
            "const app = express();\n"
            "app.get('/api/items', handler);\n"
            "app.post('/api/items', createHandler);\n"
        )
        profile = StackProfile(
            language="typescript", framework="express",
            build_tool="npm", runtime_version="20", confidence=0.9,
        )
        index = build_codebase_index(profile, str(tmp_path))
        assert len(index.endpoints) >= 2

    def test_ts_interfaces(self, tmp_path):
        (tmp_path / "types.ts").write_text(
            "export interface User {\n"
            "  id: number;\n"
            "  name: string;\n"
            "}\n"
            "export type CreateUserInput = {\n"
            "  name: string;\n"
            "};\n"
        )
        profile = StackProfile(
            language="typescript", framework="express",
            build_tool="npm", runtime_version="20", confidence=0.9,
        )
        index = build_codebase_index(profile, str(tmp_path))
        assert any(s.class_name == "User" for s in index.schemas)

    def test_ts_test_patterns(self, tmp_path):
        test_dir = tmp_path / "__tests__"
        test_dir.mkdir()
        (test_dir / "app.test.ts").write_text(
            "import { describe, it, expect } from 'vitest';\n"
            "describe('app', () => { it('works', () => {}); });\n"
        )
        profile = StackProfile(
            language="typescript", framework="express",
            build_tool="npm", runtime_version="20", confidence=0.9,
        )
        index = build_codebase_index(profile, str(tmp_path))
        assert len(index.test_patterns) >= 1


class TestPartialFailureHandling:
    """Unparseable files should be logged, not abort scanning."""

    def test_binary_file_skipped(self, tmp_path):
        (tmp_path / "good.py").write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            '@app.get("/health")\n'
            "async def health(): pass\n"
        )
        (tmp_path / "bad.py").write_bytes(b"\x00\x01\x02\xff\xfe")
        profile = _python_profile()
        index = build_codebase_index(profile, str(tmp_path))
        assert index.coverage_report["parsed_files"] >= 1
        assert index.coverage_report["failed_files"] >= 0

    def test_nonexistent_path(self):
        profile = _java_profile()
        index = build_codebase_index(profile, "/nonexistent/path")
        assert index.endpoints == []
        assert index.coverage_report["total_files"] == 0


class TestScannerDispatch:
    """Scanner should dispatch to the correct language scanner."""

    def test_java_dispatch(self):
        profile = _java_profile()
        index = build_codebase_index(profile, "dog-service")
        assert index.endpoints  # Java scanner ran

    def test_python_dispatch(self, tmp_path):
        (tmp_path / "main.py").write_text(
            "from fastapi import FastAPI\n"
            "app = FastAPI()\n"
            '@app.get("/api/health")\n'
            "async def health(): pass\n"
        )
        profile = _python_profile()
        index = build_codebase_index(profile, str(tmp_path))
        assert index.endpoints  # Python scanner ran


class TestCoverageReport:
    """Coverage report should track parsed vs failed files."""

    def test_coverage_report_populated(self):
        profile = _java_profile()
        index = build_codebase_index(profile, "dog-service")
        report = index.coverage_report
        assert report["total_files"] > 0
        assert report["parsed_files"] > 0
        assert report["failed_files"] >= 0
        assert report["parsed_files"] + report["failed_files"] == report["total_files"]
