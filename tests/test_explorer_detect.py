"""RED tests for P11.1: Language & Framework Auto-Detection.

Tests the StackProfile dataclass and detect_stack() function which
auto-detect language, framework, build tool, and runtime version
from a project directory.
"""

import pytest
from verify.explorer.detect import StackProfile, detect_stack


class TestStackProfileDataclass:
    """StackProfile should carry all detection results."""

    def test_stack_profile_fields(self):
        profile = StackProfile(
            language="java",
            framework="spring-boot",
            build_tool="gradle",
            runtime_version="17",
            confidence=0.9,
        )
        assert profile.language == "java"
        assert profile.framework == "spring-boot"
        assert profile.build_tool == "gradle"
        assert profile.runtime_version == "17"
        assert profile.confidence == 0.9
        assert profile.secondary_languages == []

    def test_stack_profile_secondary_languages(self):
        profile = StackProfile(
            language="java",
            framework="spring-boot",
            build_tool="gradle",
            runtime_version="17",
            confidence=0.9,
            secondary_languages=["kotlin", "groovy"],
        )
        assert profile.secondary_languages == ["kotlin", "groovy"]

    def test_stack_profile_unknown_defaults(self):
        profile = StackProfile(
            language="unknown",
            framework="unknown",
            build_tool="unknown",
            runtime_version="",
            confidence=0.0,
        )
        assert profile.confidence == 0.0
        assert profile.framework == "unknown"


class TestDetectJavaSpringBoot:
    """detect_stack should identify Java/Spring Boot projects."""

    def test_detect_spring_boot_gradle(self, tmp_path):
        (tmp_path / "build.gradle").write_text(
            "plugins { id 'org.springframework.boot' version '3.2.0' }"
        )
        src = tmp_path / "src" / "main" / "java"
        src.mkdir(parents=True)
        (src / "App.java").write_text("public class App {}")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "java"
        assert profile.framework == "spring-boot"
        assert profile.build_tool == "gradle"
        assert profile.confidence >= 0.8

    def test_detect_spring_boot_maven(self, tmp_path):
        (tmp_path / "pom.xml").write_text(
            "<project><parent><artifactId>spring-boot-starter-parent</artifactId></parent></project>"
        )
        src = tmp_path / "src" / "main" / "java"
        src.mkdir(parents=True)
        (src / "App.java").write_text("public class App {}")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "java"
        assert profile.framework == "spring-boot"
        assert profile.build_tool == "maven"
        assert profile.confidence >= 0.8

    def test_detect_java_no_framework(self, tmp_path):
        (tmp_path / "build.gradle").write_text("plugins { id 'java' }")
        src = tmp_path / "src" / "main" / "java"
        src.mkdir(parents=True)
        (src / "App.java").write_text("public class App {}")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "java"
        assert profile.build_tool == "gradle"
        assert profile.confidence < 0.8


class TestDetectPython:
    """detect_stack should identify Python projects with various frameworks."""

    def test_detect_fastapi(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[project]\ndependencies = ["fastapi", "uvicorn"]'
        )
        (tmp_path / "main.py").write_text("from fastapi import FastAPI\napp = FastAPI()")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "python"
        assert profile.framework == "fastapi"
        assert profile.build_tool in ("poetry", "pip", "uv")
        assert profile.confidence >= 0.8

    def test_detect_django(self, tmp_path):
        (tmp_path / "manage.py").write_text("#!/usr/bin/env python\nimport django")
        (tmp_path / "requirements.txt").write_text("django==4.2\n")
        (tmp_path / "settings.py").write_text("INSTALLED_APPS = ['django.contrib.admin']")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "python"
        assert profile.framework == "django"
        assert profile.confidence >= 0.8

    def test_detect_python_no_framework(self, tmp_path):
        (tmp_path / "setup.py").write_text("from setuptools import setup\nsetup(name='foo')")
        (tmp_path / "foo.py").write_text("print('hello')")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "python"
        assert profile.framework == "unknown"
        assert profile.confidence < 0.5


class TestDetectTypeScript:
    """detect_stack should identify TypeScript projects."""

    def test_detect_nextjs(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"dependencies": {"next": "14.0.0", "react": "18.0.0"}}'
        )
        (tmp_path / "tsconfig.json").write_text("{}")
        (tmp_path / "pages").mkdir()
        (tmp_path / "pages" / "index.tsx").write_text("export default function Home() {}")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "typescript"
        assert profile.framework == "nextjs"
        assert profile.build_tool == "npm"
        assert profile.confidence >= 0.8

    def test_detect_express(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"dependencies": {"express": "4.18.0"}, "devDependencies": {"typescript": "5.0.0"}}'
        )
        (tmp_path / "tsconfig.json").write_text("{}")
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "app.ts").write_text("import express from 'express'")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "typescript"
        assert profile.framework == "express"
        assert profile.confidence >= 0.8

    def test_detect_javascript_no_ts(self, tmp_path):
        (tmp_path / "package.json").write_text(
            '{"dependencies": {"express": "4.18.0"}}'
        )
        (tmp_path / "app.js").write_text("const express = require('express')")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "javascript"
        assert profile.framework == "express"


class TestDetectGoRust:
    """detect_stack should identify Go and Rust projects."""

    def test_detect_go(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/myapp\n\ngo 1.21\n")
        (tmp_path / "main.go").write_text("package main\nfunc main() {}")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "go"
        assert profile.build_tool == "go"
        assert profile.runtime_version == "1.21"
        assert profile.confidence >= 0.8

    def test_detect_rust_actix(self, tmp_path):
        (tmp_path / "Cargo.toml").write_text(
            '[package]\nname = "myapp"\n\n[dependencies]\nactix-web = "4"'
        )
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.rs").write_text("use actix_web::*;")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "rust"
        assert profile.framework == "actix"
        assert profile.build_tool == "cargo"
        assert profile.confidence >= 0.8


class TestDetectEdgeCases:
    """Edge cases and invariants."""

    def test_unknown_project(self, tmp_path):
        (tmp_path / "script.sh").write_text("#!/bin/bash\necho hello")
        profile = detect_stack(str(tmp_path))
        assert profile.confidence < 0.5
        assert profile.framework == "unknown"

    def test_empty_directory(self, tmp_path):
        profile = detect_stack(str(tmp_path))
        assert profile.confidence < 0.5
        assert profile.language == "unknown"

    def test_nonexistent_directory(self, tmp_path):
        profile = detect_stack(str(tmp_path / "nonexistent"))
        assert profile.confidence == 0.0
        assert profile.language == "unknown"

    def test_deterministic(self, tmp_path):
        (tmp_path / "go.mod").write_text("module example.com/app\n\ngo 1.22\n")
        (tmp_path / "main.go").write_text("package main")
        p1 = detect_stack(str(tmp_path))
        p2 = detect_stack(str(tmp_path))
        assert p1 == p2

    def test_secondary_languages(self, tmp_path):
        # Java project with some Python scripts
        (tmp_path / "build.gradle").write_text(
            "plugins { id 'org.springframework.boot' }"
        )
        java_dir = tmp_path / "src" / "main" / "java"
        java_dir.mkdir(parents=True)
        (java_dir / "App.java").write_text("public class App {}")
        (java_dir / "Service.java").write_text("public class Service {}")
        scripts = tmp_path / "scripts"
        scripts.mkdir()
        (scripts / "deploy.py").write_text("print('deploy')")
        profile = detect_stack(str(tmp_path))
        assert profile.language == "java"
        assert "python" in profile.secondary_languages

    def test_monorepo_detection(self, tmp_path):
        # Root with a backend and frontend sub-directory
        backend = tmp_path / "backend"
        backend.mkdir()
        (backend / "go.mod").write_text("module example.com/backend\n\ngo 1.21\n")
        (backend / "main.go").write_text("package main")
        frontend = tmp_path / "frontend"
        frontend.mkdir()
        (frontend / "package.json").write_text('{"dependencies": {"next": "14.0.0"}}')
        (frontend / "tsconfig.json").write_text("{}")
        profile = detect_stack(str(tmp_path))
        # Should detect something — the primary stack
        assert profile.language != "unknown" or len(profile.secondary_languages) > 0


class TestDetectRealProject:
    """Integration test against the real dog-service repo."""

    def test_detect_dog_service(self):
        profile = detect_stack("dog-service")
        assert profile.language == "java"
        assert profile.framework == "spring-boot"
        assert profile.build_tool == "gradle"
        assert profile.confidence >= 0.8
