"""Codebase Pre-Scanner — structural index of the target project.

Scans a Java/Spring Boot project for endpoints, entities, DTOs, security config,
and error handling. Feeds this structural context to negotiation phases so the AI
can say "I found your DogEntity with 5 fields — your DTO exposes 3" instead of guessing.

Feature 8 from hackathon-roadmap.md.
100% deterministic — zero AI.
"""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class EndpointInfo:
    method: str
    path: str
    class_name: str
    method_name: str
    file_path: str
    auth_required: bool = True


@dataclass
class EntityInfo:
    class_name: str
    fields: list[dict] = field(default_factory=list)
    file_path: str = ""


@dataclass
class DTOInfo:
    class_name: str
    fields: list[dict] = field(default_factory=list)
    file_path: str = ""


@dataclass
class SecurityInfo:
    has_security_config: bool = False
    auth_mechanism: str = ""
    public_paths: list[str] = field(default_factory=list)
    secured_paths: list[str] = field(default_factory=list)
    file_path: str = ""


@dataclass
class CodebaseIndex:
    """Structural index of a scanned codebase."""
    project_root: str = ""
    framework: str = ""
    language: str = ""
    endpoints: list[EndpointInfo] = field(default_factory=list)
    entities: list[EntityInfo] = field(default_factory=list)
    dtos: list[DTOInfo] = field(default_factory=list)
    security: SecurityInfo = field(default_factory=SecurityInfo)
    error_handler_class: str = ""
    error_handler_file: str = ""

    def to_dict(self) -> dict:
        """Convert to a serializable dict for embedding in negotiation context."""
        return {
            "project_root": self.project_root,
            "framework": self.framework,
            "language": self.language,
            "endpoints": [
                {
                    "method": e.method,
                    "path": e.path,
                    "class": e.class_name,
                    "method_name": e.method_name,
                    "auth_required": e.auth_required,
                }
                for e in self.endpoints
            ],
            "entities": [
                {"class": e.class_name, "fields": e.fields}
                for e in self.entities
            ],
            "dtos": [
                {"class": d.class_name, "fields": d.fields}
                for d in self.dtos
            ],
            "security": {
                "has_config": self.security.has_security_config,
                "auth_mechanism": self.security.auth_mechanism,
                "public_paths": self.security.public_paths,
            },
            "error_handler": self.error_handler_class,
        }

    def summary(self) -> str:
        """Human-readable summary for embedding in prompts."""
        lines = [f"Codebase: {self.framework} ({self.language})"]
        if self.endpoints:
            lines.append(f"Endpoints found: {len(self.endpoints)}")
            for ep in self.endpoints:
                lines.append(f"  {ep.method} {ep.path} -> {ep.class_name}.{ep.method_name}")
        if self.entities:
            lines.append(f"Entities found: {len(self.entities)}")
            for ent in self.entities:
                field_names = [f['name'] for f in ent.fields]
                lines.append(f"  {ent.class_name}: {', '.join(field_names)}")
        if self.dtos:
            lines.append(f"DTOs found: {len(self.dtos)}")
            for dto in self.dtos:
                field_names = [f['name'] for f in dto.fields]
                lines.append(f"  {dto.class_name}: {', '.join(field_names)}")
        if self.security.has_security_config:
            lines.append(f"Security: {self.security.auth_mechanism}")
            if self.security.public_paths:
                lines.append(f"  Public paths: {', '.join(self.security.public_paths)}")
        if self.error_handler_class:
            lines.append(f"Error handler: {self.error_handler_class}")
        return "\n".join(lines)


# ------------------------------------------------------------------
# Java/Spring Boot scanner
# ------------------------------------------------------------------

# HTTP mapping annotations
_MAPPING_ANNOTATIONS = {
    "@GetMapping": "GET",
    "@PostMapping": "POST",
    "@PutMapping": "PUT",
    "@DeleteMapping": "DELETE",
    "@PatchMapping": "PATCH",
}

# Patterns
_CLASS_PATTERN = re.compile(r"public\s+class\s+(\w+)")
_FIELD_PATTERN = re.compile(r"private\s+(\w+(?:<[\w<>,\s]+>)?)\s+(\w+)\s*[;=]")
_REQUEST_MAPPING_PATTERN = re.compile(r'@RequestMapping\s*\(\s*(?:value\s*=\s*)?"([^"]+)"')
_MAPPING_VALUE_PATTERN = re.compile(r'@\w+Mapping\s*\(\s*(?:value\s*=\s*)?(?:"([^"]*)")?')
_ENTITY_ANNOTATION = re.compile(r"@Entity\b")
_CONTROLLER_ADVICE = re.compile(r"@(?:Controller|Rest)Advice\b")
_SECURITY_CONFIG = re.compile(r"(?:SecurityFilterChain|WebSecurityConfigurerAdapter|SecurityConfig)")
_PERMIT_ALL_PATTERN = re.compile(r'\.(?:requestMatchers|antMatchers)\s*\(\s*"([^"]+)".*?\.permitAll')
_JWT_PATTERN = re.compile(r"(?:jwt|JwtDecoder|BearerToken|oauth2ResourceServer)", re.IGNORECASE)


def scan_java_project(project_root: str) -> CodebaseIndex:
    """Scan a Java/Spring Boot project and build a structural index.

    Args:
        project_root: Path to the project root (e.g., "dog-service").

    Returns:
        A CodebaseIndex with discovered endpoints, entities, DTOs, and security info.
    """
    index = CodebaseIndex(
        project_root=project_root,
        framework="spring-boot",
        language="java",
    )

    main_dir = os.path.join(project_root, "src", "main", "java")
    if not os.path.isdir(main_dir):
        return index

    java_files = list(Path(main_dir).rglob("*.java"))

    for java_file in java_files:
        try:
            content = java_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        file_path = str(java_file)

        # Scan for controllers with endpoints
        if _is_controller(content):
            _scan_controller(content, file_path, index)

        # Scan for entities
        if _ENTITY_ANNOTATION.search(content):
            _scan_entity(content, file_path, index)

        # Scan for DTOs (by naming convention)
        class_match = _CLASS_PATTERN.search(content)
        if class_match:
            class_name = class_match.group(1)
            if any(class_name.endswith(suffix) for suffix in ("Dto", "DTO", "Response", "Request")):
                _scan_dto(content, file_path, class_name, index)

        # Scan for @ControllerAdvice / error handler
        if _CONTROLLER_ADVICE.search(content):
            if class_match:
                index.error_handler_class = class_match.group(1)
                index.error_handler_file = file_path

        # Scan for security config
        if _SECURITY_CONFIG.search(content):
            _scan_security(content, file_path, index)

    return index


def _is_controller(content: str) -> bool:
    """Check if a Java file is a REST controller."""
    return any(ann in content for ann in ("@RestController", "@Controller"))


def _scan_controller(content: str, file_path: str, index: CodebaseIndex) -> None:
    """Extract endpoints from a Spring controller."""
    class_match = _CLASS_PATTERN.search(content)
    class_name = class_match.group(1) if class_match else "Unknown"

    # Get class-level @RequestMapping prefix
    base_path = ""
    rm_match = _REQUEST_MAPPING_PATTERN.search(content)
    if rm_match:
        base_path = rm_match.group(1).rstrip("/")

    # Find all method-level mappings
    for annotation, http_method in _MAPPING_ANNOTATIONS.items():
        for match in re.finditer(re.escape(annotation) + r'\s*(?:\(\s*(?:value\s*=\s*)?(?:"([^"]*)")?\s*\))?', content):
            path_suffix = match.group(1) if match.group(1) else ""
            full_path = base_path + ("/" + path_suffix.lstrip("/") if path_suffix else "")
            if not full_path:
                full_path = base_path or "/"

            # Try to find the method name (next public method after annotation)
            after = content[match.end():]
            method_match = re.search(r"public\s+\w+(?:<[\w<>,\s]+>)?\s+(\w+)\s*\(", after)
            method_name = method_match.group(1) if method_match else "unknown"

            index.endpoints.append(EndpointInfo(
                method=http_method,
                path=full_path,
                class_name=class_name,
                method_name=method_name,
                file_path=file_path,
            ))


def _scan_entity(content: str, file_path: str, index: CodebaseIndex) -> None:
    """Extract entity class name and fields."""
    class_match = _CLASS_PATTERN.search(content)
    if not class_match:
        return

    fields = []
    for fm in _FIELD_PATTERN.finditer(content):
        field_type = fm.group(1)
        field_name = fm.group(2)
        # Skip common framework fields
        if field_name in ("serialVersionUID",):
            continue
        fields.append({"name": field_name, "type": field_type})

    index.entities.append(EntityInfo(
        class_name=class_match.group(1),
        fields=fields,
        file_path=file_path,
    ))


def _scan_dto(content: str, file_path: str, class_name: str, index: CodebaseIndex) -> None:
    """Extract DTO fields."""
    fields = []
    for fm in _FIELD_PATTERN.finditer(content):
        fields.append({"name": fm.group(2), "type": fm.group(1)})

    # Also check for record-style DTOs (Java records)
    record_match = re.search(r"record\s+\w+\s*\(([^)]+)\)", content)
    if record_match:
        params = record_match.group(1)
        for param in params.split(","):
            parts = param.strip().split()
            if len(parts) >= 2:
                fields.append({"name": parts[-1], "type": parts[0]})

    if fields:
        index.dtos.append(DTOInfo(
            class_name=class_name,
            fields=fields,
            file_path=file_path,
        ))


def _scan_security(content: str, file_path: str, index: CodebaseIndex) -> None:
    """Extract security configuration details."""
    index.security.has_security_config = True
    index.security.file_path = file_path

    if _JWT_PATTERN.search(content):
        index.security.auth_mechanism = "jwt_bearer"
    elif "httpBasic" in content:
        index.security.auth_mechanism = "basic"
    elif "formLogin" in content:
        index.security.auth_mechanism = "form"

    # Find public paths
    for match in _PERMIT_ALL_PATTERN.finditer(content):
        index.security.public_paths.append(match.group(1))
