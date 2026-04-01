"""Structural Index Builder — multi-language codebase scanner (P11.2).

Scans a repository using language-appropriate scanners dispatched
based on the detected StackProfile. Builds a CodebaseIndex containing
endpoints, models, schemas, test patterns, config files, and directory structure.

100% deterministic, read-only, pluggable per-language scanners.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from pathlib import Path

from .detect import StackProfile

logger = logging.getLogger(__name__)

# Directories to skip during scanning
_SKIP_DIRS: frozenset[str] = frozenset({
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "build", "dist", "target", ".gradle", ".idea", ".vscode",
    ".next", ".nuxt", "vendor", "pkg",
})


@dataclass
class EndpointInfo:
    method: str
    path: str
    handler: str
    file_path: str


@dataclass
class ModelInfo:
    class_name: str
    fields: list[dict] = field(default_factory=list)
    file_path: str = ""


@dataclass
class SchemaInfo:
    class_name: str
    fields: list[dict] = field(default_factory=list)
    file_path: str = ""


@dataclass
class TestPatternInfo:
    file_path: str
    framework: str
    pattern: str = ""


@dataclass
class CodebaseIndex:
    """Structural index of a scanned codebase."""

    project_root: str = ""
    endpoints: list[EndpointInfo] = field(default_factory=list)
    models: list[ModelInfo] = field(default_factory=list)
    schemas: list[SchemaInfo] = field(default_factory=list)
    test_patterns: list[TestPatternInfo] = field(default_factory=list)
    config_files: list[str] = field(default_factory=list)
    directory_tree: list[str] = field(default_factory=list)
    coverage_report: dict = field(default_factory=lambda: {
        "parsed_files": 0, "failed_files": 0, "total_files": 0,
    })

    def to_dict(self) -> dict:
        return {
            "project_root": self.project_root,
            "endpoints": [
                {"method": e.method, "path": e.path, "handler": e.handler, "file_path": e.file_path}
                for e in self.endpoints
            ],
            "models": [
                {"class_name": m.class_name, "fields": m.fields, "file_path": m.file_path}
                for m in self.models
            ],
            "schemas": [
                {"class_name": s.class_name, "fields": s.fields, "file_path": s.file_path}
                for s in self.schemas
            ],
            "test_patterns": [
                {"file_path": t.file_path, "framework": t.framework, "pattern": t.pattern}
                for t in self.test_patterns
            ],
            "config_files": self.config_files,
            "directory_tree": self.directory_tree,
            "coverage_report": self.coverage_report,
        }

    def summary(self) -> str:
        lines = [f"Project: {self.project_root}"]
        if self.endpoints:
            lines.append(f"Endpoints: {len(self.endpoints)}")
            for ep in self.endpoints:
                lines.append(f"  {ep.method} {ep.path} -> {ep.handler}")
        if self.models:
            lines.append(f"Models: {len(self.models)}")
            for m in self.models:
                lines.append(f"  {m.class_name}")
        if self.schemas:
            lines.append(f"Schemas: {len(self.schemas)}")
            for s in self.schemas:
                lines.append(f"  {s.class_name}")
        if self.test_patterns:
            lines.append(f"Test files: {len(self.test_patterns)}")
        return "\n".join(lines)


# --- Scanner registry ---

_SCANNERS: dict[str, type] = {}


def _register_scanner(language: str):
    def decorator(cls):
        _SCANNERS[language] = cls
        return cls
    return decorator


def build_codebase_index(profile: StackProfile, path: str) -> CodebaseIndex:
    """Build a structural index using a language-appropriate scanner.

    Args:
        profile: Detected StackProfile for the project.
        path: Directory path to scan.

    Returns:
        A CodebaseIndex with discovered constructs.
    """
    root = Path(path)
    index = CodebaseIndex(project_root=path)

    if not root.exists() or not root.is_dir():
        return index

    # Build directory tree (top-level only)
    try:
        index.directory_tree = sorted(
            e.name for e in root.iterdir()
            if e.name not in _SKIP_DIRS and not e.name.startswith(".")
        )
    except PermissionError:
        pass

    # Dispatch to language scanner
    scanner_cls = _SCANNERS.get(profile.language)
    if scanner_cls:
        scanner = scanner_cls(root, profile, index)
        scanner.scan()
    else:
        # Fallback: just count files
        _scan_generic(root, index)

    return index


def _read_file(path: Path) -> str | None:
    """Read a file, returning None on failure."""
    try:
        return path.read_text(encoding="utf-8", errors="ignore")
    except Exception:
        return None


def _walk_files(root: Path, extensions: set[str], max_depth: int = 8) -> list[Path]:
    """Walk directory tree yielding files with given extensions."""
    results: list[Path] = []
    _walk_recursive(root, extensions, results, 0, max_depth)
    return results


def _walk_recursive(
    directory: Path, extensions: set[str],
    results: list[Path], depth: int, max_depth: int,
) -> None:
    if depth > max_depth:
        return
    try:
        entries = sorted(directory.iterdir())
    except PermissionError:
        return
    for entry in entries:
        if entry.is_file() and entry.suffix.lower() in extensions:
            results.append(entry)
        elif entry.is_dir() and entry.name not in _SKIP_DIRS:
            _walk_recursive(entry, extensions, results, depth + 1, max_depth)


def _scan_generic(root: Path, index: CodebaseIndex) -> None:
    """Generic scanner that just counts files and finds config."""
    all_files = _walk_files(root, {".py", ".java", ".ts", ".js", ".go", ".rs"})
    index.coverage_report["total_files"] = len(all_files)
    index.coverage_report["parsed_files"] = len(all_files)
    _discover_config_files(root, index)


def _discover_config_files(root: Path, index: CodebaseIndex) -> None:
    """Discover common config files at the project root and resource dirs."""
    config_names = {
        "application.yaml", "application.yml", "application.properties",
        ".env", ".env.example", "config.yaml", "config.yml", "config.json",
        "settings.py", "settings.yaml",
    }
    for config_name in config_names:
        path = root / config_name
        if path.exists():
            index.config_files.append(str(path))

    # Check resources directories
    for resources in root.rglob("resources"):
        if resources.is_dir() and "test" not in str(resources):
            for entry in resources.iterdir():
                if entry.is_file() and entry.name in config_names:
                    index.config_files.append(str(entry))


# --- Java Scanner ---

_JAVA_CLASS_RE = re.compile(r"public\s+class\s+(\w+)")
_JAVA_FIELD_RE = re.compile(r"private\s+(\w+(?:<[\w<>,\s]+>)?)\s+(\w+)\s*[;=]")
_JAVA_ENTITY_RE = re.compile(r"@Entity\b")
_JAVA_CONTROLLER_RE = re.compile(r"@(?:Rest)?Controller\b")
_JAVA_REQUEST_MAPPING_RE = re.compile(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?"([^"]+)"')
_JAVA_MAPPING_ANNOTATIONS = {
    "@GetMapping": "GET",
    "@PostMapping": "POST",
    "@PutMapping": "PUT",
    "@DeleteMapping": "DELETE",
    "@PatchMapping": "PATCH",
}
_JAVA_TEST_RE = re.compile(r"@(?:Test|SpringBootTest|WebMvcTest|DataJpaTest)\b")


@_register_scanner("java")
class JavaScanner:
    def __init__(self, root: Path, profile: StackProfile, index: CodebaseIndex):
        self.root = root
        self.profile = profile
        self.index = index

    def scan(self) -> None:
        java_files = _walk_files(self.root, {".java"})
        parsed = 0
        failed = 0

        for java_file in java_files:
            content = _read_file(java_file)
            if content is None:
                failed += 1
                continue
            parsed += 1
            file_str = str(java_file)

            self._scan_endpoints(content, file_str)
            self._scan_models(content, file_str)
            self._scan_schemas(content, file_str)
            self._scan_tests(content, file_str)

        self.index.coverage_report = {
            "total_files": parsed + failed,
            "parsed_files": parsed,
            "failed_files": failed,
        }
        _discover_config_files(self.root, self.index)

    def _scan_endpoints(self, content: str, file_path: str) -> None:
        if not _JAVA_CONTROLLER_RE.search(content):
            return
        class_match = _JAVA_CLASS_RE.search(content)
        class_name = class_match.group(1) if class_match else "Unknown"

        base_path = ""
        rm_match = _JAVA_REQUEST_MAPPING_RE.search(content)
        if rm_match:
            base_path = rm_match.group(1).rstrip("/")

        for annotation, http_method in _JAVA_MAPPING_ANNOTATIONS.items():
            pattern = re.escape(annotation) + r'\s*(?:\(\s*(?:value\s*=\s*)?(?:"([^"]*)")?\s*\))?'
            for match in re.finditer(pattern, content):
                path_suffix = match.group(1) if match.group(1) else ""
                full_path = base_path + ("/" + path_suffix.lstrip("/") if path_suffix else "")
                if not full_path:
                    full_path = base_path or "/"

                after = content[match.end():]
                method_match = re.search(r"public\s+\w+(?:<[\w<>,\s]+>)?\s+(\w+)\s*\(", after)
                method_name = method_match.group(1) if method_match else "unknown"

                self.index.endpoints.append(EndpointInfo(
                    method=http_method,
                    path=full_path,
                    handler=f"{class_name}.{method_name}",
                    file_path=file_path,
                ))

    def _scan_models(self, content: str, file_path: str) -> None:
        if not _JAVA_ENTITY_RE.search(content):
            return
        class_match = _JAVA_CLASS_RE.search(content)
        if not class_match:
            return
        fields = []
        for fm in _JAVA_FIELD_RE.finditer(content):
            field_name = fm.group(2)
            if field_name == "serialVersionUID":
                continue
            fields.append({"name": field_name, "type": fm.group(1)})
        self.index.models.append(ModelInfo(
            class_name=class_match.group(1), fields=fields, file_path=file_path,
        ))

    def _scan_schemas(self, content: str, file_path: str) -> None:
        class_match = _JAVA_CLASS_RE.search(content)
        if not class_match:
            return
        class_name = class_match.group(1)
        if not any(class_name.endswith(s) for s in ("Dto", "DTO", "Response", "Request")):
            return
        fields = []
        for fm in _JAVA_FIELD_RE.finditer(content):
            fields.append({"name": fm.group(2), "type": fm.group(1)})
        # Also handle Java records
        record_match = re.search(r"record\s+\w+\s*\(([^)]+)\)", content)
        if record_match:
            for param in record_match.group(1).split(","):
                parts = param.strip().split()
                if len(parts) >= 2:
                    fields.append({"name": parts[-1], "type": parts[0]})
        if fields:
            self.index.schemas.append(SchemaInfo(
                class_name=class_name, fields=fields, file_path=file_path,
            ))

    def _scan_tests(self, content: str, file_path: str) -> None:
        if not _JAVA_TEST_RE.search(content):
            return
        framework = "junit5"
        if "@SpringBootTest" in content:
            framework = "spring-boot-test"
        elif "@WebMvcTest" in content:
            framework = "webmvc-test"
        self.index.test_patterns.append(TestPatternInfo(
            file_path=file_path, framework=framework,
        ))


# --- Python Scanner ---

_PY_ROUTE_RE = re.compile(
    r'@(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']'
)
_PY_PYDANTIC_RE = re.compile(r"class\s+(\w+)\s*\(\s*(?:\w+\.)?BaseModel\s*\)")
_PY_SQLALCHEMY_RE = re.compile(r"class\s+(\w+)\s*\(\s*(?:\w+\.)?(?:Base|Model)\s*\)")
_PY_TABLENAME_RE = re.compile(r"__tablename__\s*=")
_PY_FIELD_RE = re.compile(r"^\s+(\w+)\s*[:=]", re.MULTILINE)


@_register_scanner("python")
class PythonScanner:
    def __init__(self, root: Path, profile: StackProfile, index: CodebaseIndex):
        self.root = root
        self.profile = profile
        self.index = index

    def scan(self) -> None:
        py_files = _walk_files(self.root, {".py"})
        parsed = 0
        failed = 0

        for py_file in py_files:
            content = _read_file(py_file)
            if content is None:
                failed += 1
                continue
            parsed += 1
            file_str = str(py_file)

            self._scan_endpoints(content, file_str)
            self._scan_models(content, file_str)
            self._scan_schemas(content, file_str)
            self._scan_tests(content, file_str, py_file.name)

        self.index.coverage_report = {
            "total_files": parsed + failed,
            "parsed_files": parsed,
            "failed_files": failed,
        }
        _discover_config_files(self.root, self.index)

    def _scan_endpoints(self, content: str, file_path: str) -> None:
        for match in _PY_ROUTE_RE.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            # Try to find handler function name
            after = content[match.end():]
            fn_match = re.search(r"(?:async\s+)?def\s+(\w+)", after)
            handler = fn_match.group(1) if fn_match else "unknown"
            self.index.endpoints.append(EndpointInfo(
                method=method, path=path, handler=handler, file_path=file_path,
            ))

    def _scan_models(self, content: str, file_path: str) -> None:
        if not _PY_TABLENAME_RE.search(content):
            return
        for match in _PY_SQLALCHEMY_RE.finditer(content):
            class_name = match.group(1)
            if class_name in ("Base", "Model"):
                continue
            fields = self._extract_python_fields(content, match.end())
            self.index.models.append(ModelInfo(
                class_name=class_name, fields=fields, file_path=file_path,
            ))

    def _scan_schemas(self, content: str, file_path: str) -> None:
        for match in _PY_PYDANTIC_RE.finditer(content):
            class_name = match.group(1)
            fields = self._extract_python_fields(content, match.end())
            self.index.schemas.append(SchemaInfo(
                class_name=class_name, fields=fields, file_path=file_path,
            ))

    def _extract_python_fields(self, content: str, start: int) -> list[dict]:
        """Extract field names from a class body."""
        fields = []
        lines = content[start:].split("\n")
        for line in lines[1:]:  # skip class declaration line
            if line.strip() and not line.startswith((" ", "\t")):
                break  # End of class body
            fm = re.match(r"\s+(\w+)\s*[:=]", line)
            if fm:
                name = fm.group(1)
                if not name.startswith("_"):
                    fields.append({"name": name})
        return fields

    def _scan_tests(self, content: str, file_path: str, filename: str) -> None:
        if not (filename.startswith("test_") or filename.endswith("_test.py") or filename == "conftest.py"):
            return
        framework = "pytest"
        if "unittest" in content:
            framework = "unittest"
        self.index.test_patterns.append(TestPatternInfo(
            file_path=file_path, framework=framework,
        ))


# --- TypeScript Scanner ---

_TS_ROUTE_RE = re.compile(
    r"(?:app|router)\.(get|post|put|delete|patch)\s*\(\s*['\"]([^'\"]+)['\"]"
)
_TS_INTERFACE_RE = re.compile(r"(?:export\s+)?interface\s+(\w+)")
_TS_TYPE_RE = re.compile(r"(?:export\s+)?type\s+(\w+)\s*=\s*\{")


@_register_scanner("typescript")
class TypeScriptScanner:
    def __init__(self, root: Path, profile: StackProfile, index: CodebaseIndex):
        self.root = root
        self.profile = profile
        self.index = index

    def scan(self) -> None:
        ts_files = _walk_files(self.root, {".ts", ".tsx"})
        parsed = 0
        failed = 0

        for ts_file in ts_files:
            content = _read_file(ts_file)
            if content is None:
                failed += 1
                continue
            parsed += 1
            file_str = str(ts_file)

            self._scan_endpoints(content, file_str)
            self._scan_schemas(content, file_str)
            self._scan_tests(content, file_str, ts_file.name)

        self.index.coverage_report = {
            "total_files": parsed + failed,
            "parsed_files": parsed,
            "failed_files": failed,
        }
        _discover_config_files(self.root, self.index)

    def _scan_endpoints(self, content: str, file_path: str) -> None:
        for match in _TS_ROUTE_RE.finditer(content):
            method = match.group(1).upper()
            path = match.group(2)
            self.index.endpoints.append(EndpointInfo(
                method=method, path=path, handler="handler", file_path=file_path,
            ))

    def _scan_schemas(self, content: str, file_path: str) -> None:
        for match in _TS_INTERFACE_RE.finditer(content):
            self.index.schemas.append(SchemaInfo(
                class_name=match.group(1), file_path=file_path,
            ))
        for match in _TS_TYPE_RE.finditer(content):
            self.index.schemas.append(SchemaInfo(
                class_name=match.group(1), file_path=file_path,
            ))

    def _scan_tests(self, content: str, file_path: str, filename: str) -> None:
        is_test = any(p in filename for p in (".test.", ".spec.", "__tests__"))
        if not is_test and "__tests__" not in file_path:
            return
        framework = "jest"
        if "vitest" in content:
            framework = "vitest"
        self.index.test_patterns.append(TestPatternInfo(
            file_path=file_path, framework=framework,
        ))


# Also register JavaScript scanner (reuses TypeScript scanner)
_SCANNERS["javascript"] = TypeScriptScanner
