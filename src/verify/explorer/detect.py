"""Language & Framework Auto-Detection (P11.1).

Deterministic detection of project language, framework, build tool,
and runtime version by analyzing file extensions, manifest files,
and framework-specific markers.

100% deterministic — zero AI. Same directory always produces the same result.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

# Extension → language mapping
_LANG_EXTENSIONS: dict[str, str] = {
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".py": "python",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".cs": "csharp",
    ".swift": "swift",
    ".scala": "scala",
    ".groovy": "groovy",
}

# Directories to skip during file scanning
_SKIP_DIRS: frozenset[str] = frozenset({
    "node_modules", ".git", "__pycache__", ".venv", "venv",
    "build", "dist", "target", ".gradle", ".idea", ".vscode",
    ".next", ".nuxt", "vendor", "pkg",
})

# Maximum directory depth for file scanning
_MAX_DEPTH = 8


@dataclass
class StackProfile:
    """Result of language/framework auto-detection."""

    language: str
    framework: str
    build_tool: str
    runtime_version: str
    confidence: float
    secondary_languages: list[str] = field(default_factory=list)


def detect_stack(path: str) -> StackProfile:
    """Detect the primary language, framework, build tool, and runtime version.

    Args:
        path: Directory path to analyze.

    Returns:
        A StackProfile with detection results.
    """
    root = Path(path)
    if not root.exists() or not root.is_dir():
        return StackProfile(
            language="unknown",
            framework="unknown",
            build_tool="unknown",
            runtime_version="",
            confidence=0.0,
        )

    # Count source files by language
    lang_counts = _count_languages(root)

    # Detect from manifest files (higher confidence than extension counting)
    manifest = _detect_from_manifests(root)

    # Determine primary language
    if manifest.language != "unknown":
        primary_lang = manifest.language
    elif lang_counts:
        primary_lang = lang_counts.most_common(1)[0][0]
    else:
        return StackProfile(
            language="unknown",
            framework="unknown",
            build_tool="unknown",
            runtime_version="",
            confidence=0.0,
        )

    # Build secondary languages list (everything except primary)
    secondary = [
        lang for lang, _ in lang_counts.most_common()
        if lang != primary_lang
    ]

    # Compute confidence
    confidence = manifest.confidence
    if confidence == 0.0 and lang_counts:
        total = sum(lang_counts.values())
        primary_count = lang_counts.get(primary_lang, 0)
        confidence = min(0.4, (primary_count / total) * 0.4) if total else 0.0

    return StackProfile(
        language=primary_lang,
        framework=manifest.framework,
        build_tool=manifest.build_tool,
        runtime_version=manifest.runtime_version,
        confidence=confidence,
        secondary_languages=secondary,
    )


@dataclass
class _ManifestResult:
    """Intermediate detection result from manifest analysis."""

    language: str = "unknown"
    framework: str = "unknown"
    build_tool: str = "unknown"
    runtime_version: str = ""
    confidence: float = 0.0


def _count_languages(root: Path) -> Counter[str]:
    """Count source files by detected language, skipping vendor directories."""
    counts: Counter[str] = Counter()
    for file_path in _walk_source_files(root):
        ext = file_path.suffix.lower()
        lang = _LANG_EXTENSIONS.get(ext)
        if lang:
            counts[lang] += 1
    return counts


def _walk_source_files(root: Path, depth: int = 0) -> list[Path]:
    """Walk directory tree yielding source files, respecting skip rules."""
    if depth > _MAX_DEPTH:
        return []
    results: list[Path] = []
    try:
        entries = sorted(root.iterdir())
    except PermissionError:
        return results
    for entry in entries:
        if entry.is_file():
            results.append(entry)
        elif entry.is_dir() and entry.name not in _SKIP_DIRS:
            results.extend(_walk_source_files(entry, depth + 1))
    return results


def _detect_from_manifests(root: Path) -> _ManifestResult:
    """Detect language/framework from manifest files at the project root."""
    # Order matters: check most specific first
    checkers = [
        _check_go_mod,
        _check_cargo_toml,
        _check_build_gradle,
        _check_pom_xml,
        _check_package_json,
        _check_pyproject_toml,
        _check_python_fallback,
    ]
    for checker in checkers:
        result = checker(root)
        if result.language != "unknown":
            return result
    return _ManifestResult()


# --- Manifest checkers ---


def _check_go_mod(root: Path) -> _ManifestResult:
    go_mod = root / "go.mod"
    if not go_mod.exists():
        return _ManifestResult()
    content = go_mod.read_text(errors="ignore")
    version = ""
    match = re.search(r"^go\s+([\d.]+)", content, re.MULTILINE)
    if match:
        version = match.group(1)
    return _ManifestResult(
        language="go",
        framework="stdlib",
        build_tool="go",
        runtime_version=version,
        confidence=0.9,
    )


def _check_cargo_toml(root: Path) -> _ManifestResult:
    cargo = root / "Cargo.toml"
    if not cargo.exists():
        return _ManifestResult()
    content = cargo.read_text(errors="ignore")
    framework = "unknown"
    confidence = 0.8
    if "actix-web" in content or "actix_web" in content:
        framework = "actix"
        confidence = 0.9
    elif "rocket" in content:
        framework = "rocket"
        confidence = 0.9
    elif "axum" in content:
        framework = "axum"
        confidence = 0.9
    return _ManifestResult(
        language="rust",
        framework=framework,
        build_tool="cargo",
        runtime_version="",
        confidence=confidence,
    )


def _check_build_gradle(root: Path) -> _ManifestResult:
    for name in ("build.gradle", "build.gradle.kts"):
        gradle_file = root / name
        if gradle_file.exists():
            content = gradle_file.read_text(errors="ignore")
            framework = "unknown"
            confidence = 0.7
            if "org.springframework.boot" in content or "spring-boot" in content:
                framework = "spring-boot"
                confidence = 0.95
            version = ""
            v_match = re.search(r"sourceCompatibility\s*=\s*['\"]?(\d+)", content)
            if v_match:
                version = v_match.group(1)
            return _ManifestResult(
                language="java",
                framework=framework,
                build_tool="gradle",
                runtime_version=version,
                confidence=confidence,
            )
    return _ManifestResult()


def _check_pom_xml(root: Path) -> _ManifestResult:
    pom = root / "pom.xml"
    if not pom.exists():
        return _ManifestResult()
    content = pom.read_text(errors="ignore")
    framework = "unknown"
    confidence = 0.7
    if "spring-boot" in content:
        framework = "spring-boot"
        confidence = 0.95
    version = ""
    v_match = re.search(r"<java.version>(\d+)</java.version>", content)
    if v_match:
        version = v_match.group(1)
    return _ManifestResult(
        language="java",
        framework=framework,
        build_tool="maven",
        runtime_version=version,
        confidence=confidence,
    )


def _check_package_json(root: Path) -> _ManifestResult:
    pkg = root / "package.json"
    if not pkg.exists():
        return _ManifestResult()
    try:
        data = json.loads(pkg.read_text(errors="ignore"))
    except (json.JSONDecodeError, OSError):
        return _ManifestResult()

    deps = {}
    deps.update(data.get("dependencies", {}))
    dev_deps = data.get("devDependencies", {})

    # Determine if TypeScript or JavaScript
    has_ts_config = (root / "tsconfig.json").exists()
    has_ts_dep = "typescript" in dev_deps or "typescript" in deps
    language = "typescript" if (has_ts_config or has_ts_dep) else "javascript"

    # Detect framework
    framework = "unknown"
    confidence = 0.7
    if "next" in deps:
        framework = "nextjs"
        confidence = 0.9
    elif "nuxt" in deps:
        framework = "nuxt"
        confidence = 0.9
    elif "express" in deps:
        framework = "express"
        confidence = 0.85
    elif "fastify" in deps:
        framework = "fastify"
        confidence = 0.85
    elif "react" in deps:
        framework = "react"
        confidence = 0.8

    # Detect build tool
    build_tool = "npm"
    if (root / "yarn.lock").exists():
        build_tool = "yarn"
    elif (root / "pnpm-lock.yaml").exists():
        build_tool = "pnpm"
    elif (root / "bun.lockb").exists():
        build_tool = "bun"

    # Runtime version
    version = ""
    engines = data.get("engines", {})
    if "node" in engines:
        v_match = re.search(r"(\d+)", engines["node"])
        if v_match:
            version = v_match.group(1)

    return _ManifestResult(
        language=language,
        framework=framework,
        build_tool=build_tool,
        runtime_version=version,
        confidence=confidence,
    )


def _check_pyproject_toml(root: Path) -> _ManifestResult:
    pyproject = root / "pyproject.toml"
    if not pyproject.exists():
        return _ManifestResult()
    content = pyproject.read_text(errors="ignore")
    framework, confidence = _detect_python_framework(content, root)

    # Detect build tool from pyproject.toml
    build_tool = "pip"
    if "[tool.poetry]" in content:
        build_tool = "poetry"
    elif "[tool.uv]" in content or "uv" in content.split("[build-system]")[0] if "[build-system]" in content else "":
        build_tool = "uv"

    version = ""
    v_match = re.search(r'python_requires\s*=\s*["\']>=?([\d.]+)', content)
    if not v_match:
        v_match = re.search(r'requires-python\s*=\s*["\']>=?([\d.]+)', content)
    if v_match:
        version = v_match.group(1)

    return _ManifestResult(
        language="python",
        framework=framework,
        build_tool=build_tool,
        runtime_version=version,
        confidence=confidence,
    )


def _check_python_fallback(root: Path) -> _ManifestResult:
    """Fallback detection for Python projects without pyproject.toml."""
    markers = [
        root / "setup.py",
        root / "setup.cfg",
        root / "requirements.txt",
        root / "Pipfile",
        root / "manage.py",
    ]
    found = any(m.exists() for m in markers)
    if not found:
        return _ManifestResult()

    # Check requirements files for framework hints
    framework = "unknown"
    confidence = 0.4
    for req_file in (root / "requirements.txt", root / "Pipfile"):
        if req_file.exists():
            content = req_file.read_text(errors="ignore").lower()
            fw, conf = _detect_python_framework(content, root)
            if conf > confidence:
                framework = fw
                confidence = conf

    # manage.py is a strong Django signal
    if (root / "manage.py").exists():
        manage_content = (root / "manage.py").read_text(errors="ignore")
        if "django" in manage_content.lower():
            framework = "django"
            confidence = max(confidence, 0.9)

    build_tool = "pip"
    if (root / "Pipfile").exists():
        build_tool = "pipenv"

    return _ManifestResult(
        language="python",
        framework=framework,
        build_tool=build_tool,
        runtime_version="",
        confidence=confidence,
    )


def _detect_python_framework(content: str, root: Path) -> tuple[str, float]:
    """Detect Python web framework from dependency content."""
    content_lower = content.lower()

    if "fastapi" in content_lower:
        return "fastapi", 0.9
    if "django" in content_lower:
        return "django", 0.9
    if "flask" in content_lower:
        return "flask", 0.85
    if "starlette" in content_lower:
        return "starlette", 0.8
    if "tornado" in content_lower:
        return "tornado", 0.8

    return "unknown", 0.4
